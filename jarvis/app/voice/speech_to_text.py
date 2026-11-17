"""
Speech-to-Text (STT) Engine for NIVA.
Converts spoken audio into text transcripts cleanly.
Command understanding is handled downstream by the trained NLU model.
"""

import io
import logging
import re
from typing import Callable, Optional
import speech_recognition as sr
import speech_recognition.recognizers.google as google_recognizer

# Force HTTPS endpoint for Google Speech API to eliminate HTTP 302 redirect errors on Windows
google_recognizer.ENDPOINT = "https://www.google.com/speech-api/v2/recognize"
GOOGLE_SPEECH_HTTPS_ENDPOINT = "https://www.google.com/speech-api/v2/recognize"

from app.config import ASSISTANT_NAME

logger = logging.getLogger("NIVA.STT")


class SpeechToTextEngine:
    """Handles audio transcription and mixed-language command normalization."""

    # Normalization rules for Telugu-English colloquial automation phrasing
    TELUGU_ENGLISH_PATTERNS = [
        # Contextual compound patterns first: "Excel lo monthly expenses create chey" -> "create monthly expenses in excel"
        (r"^(?:jarvis\s+)?(.*?)\s+lo\s+(.*?)\s+create\s+chey$", r"create \2 in \1"),
        (r"^(?:jarvis\s+)?(.*?)\s+lo\s+(.*?)\s+search\s+chey$", r"search \2 in \1"),
        # Action patterns: "... open chey" -> "open ..."
        (r"^(.*?)\s+(?:open|start|launch)\s+chey(?:\s+brother|\s+ra)?$", r"open \1"),
        (r"^(?:jarvis\s+)?(.*?)\s+close\s+chey$", r"close \1"),
        (r"^(?:jarvis\s+)?(.*?)\s+create\s+chey$", r"create \1"),
        (r"^(?:jarvis\s+)?(.*?)\s+delete\s+chey$", r"delete \1"),
        (r"^(?:jarvis\s+)?(.*?)\s+search\s+chey$", r"search \1"),
        # Setting patterns: "Bluetooth on chey" -> "turn bluetooth on"
        (r"^bluetooth\s+on\s+chey$", "turn bluetooth on"),
        (r"^bluetooth\s+off\s+chey$", "turn bluetooth off"),
        (r"^wifi\s+on\s+chey$", "turn wifi on"),
        (r"^wifi\s+off\s+chey$", "turn wifi off"),
        (r"^volume\s+penchu$", "increase volume"),
        (r"^volume\s+tagginchu$", "decrease volume"),
        # Interruption patterns in Telugu
        (r"^(?:aapu|aapey|aagandi|vaddu)$", "stop"),
        (r"^(?:koncham\s+aagu|agandi)$", "pause"),
        (r"^(?:malli\s+chey|continue\s+chey)$", "resume"),
        (r"^(?:venakki\s+teesko)$", "undo"),
    ]

    def __init__(self, language: str = "en-IN"):
        self.recognizer = sr.Recognizer()
        self.language = language
        # Tune recognizer thresholds for responsive detection
        self.recognizer.energy_threshold = 200
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.8
        self.last_error: Optional[str] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def transcribe(self, audio_data: sr.AudioData) -> Optional[str]:
        """Transcribes raw audio to text and normalizes colloquial phrasing."""
        try:
            # Uses Google Speech API over HTTPS with secondary locale fallback
            try:
                raw_text = self.recognizer.recognize_google(
                    audio_data,
                    language=self.language,
                    endpoint=GOOGLE_SPEECH_HTTPS_ENDPOINT
                )
            except sr.UnknownValueError:
                if self.language != "en-US":
                    raw_text = self.recognizer.recognize_google(
                        audio_data,
                        language="en-US",
                        endpoint=GOOGLE_SPEECH_HTTPS_ENDPOINT
                    )
                else:
                    raise

            logger.info(f"STT raw recognition: '{raw_text}'")
            self.last_error = None

            # Phonetic normalization for assistant name variations from speech recognition
            raw_text = re.sub(
                r"\b(?:nivea|neeva|neva|neba|niwa|naiva|niver|nova)\b",
                "niva",
                raw_text,
                flags=re.IGNORECASE
            )

            normalized = self.normalize_mixed_language(raw_text)
            return normalized
        except sr.UnknownValueError:
            logger.debug("Speech unrecognized (silence or unintelligible noise).")
            return None
        except sr.RequestError as e:
            err_msg = f"Speech Recognition service error: {e}"
            logger.warning(err_msg)
            self.last_error = err_msg
            if self.on_error:
                try:
                    self.on_error(err_msg)
                except Exception:
                    pass
            return None
        except Exception as e:
            err_msg = f"Speech Recognition error: {e}"
            logger.error(err_msg)
            self.last_error = err_msg
            if self.on_error:
                try:
                    self.on_error(err_msg)
                except Exception:
                    pass
            return None

    @classmethod
    def normalize_mixed_language(cls, text: str) -> str:
        """Translates Telugu-English colloquial command phrasing into canonical commands."""
        cleaned = text.strip().lower()

        # If user spoke only the assistant's name or greeting, preserve it
        if cleaned in [ASSISTANT_NAME.lower(), "niva", "hey niva", "ok niva", "hi niva", "hello niva", "hello", "hi", "hey"]:
            return text.strip()

        # Remove polite wake words / prefixes for command parsing
        prefix_stripped = re.sub(rf"^(?:hey\s+|ok\s+|hi\s+)?(?:{re.escape(ASSISTANT_NAME.lower())}|niva|jarvis)[,\s:]*", "", cleaned, flags=re.IGNORECASE).strip()

        # If prefix removal leaves nothing, return original
        target = prefix_stripped if prefix_stripped else cleaned

        for pattern, replacement in cls.TELUGU_ENGLISH_PATTERNS:
            if re.search(pattern, target):
                result = re.sub(pattern, replacement, target).strip()
                logger.info(f"Normalized Telugu-English command: '{text}' -> '{result}'")
                return result

        return text.strip()
