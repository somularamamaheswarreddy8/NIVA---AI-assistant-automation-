"""
Continuous Voice Listener for JARVIS.
Operates on a dedicated background thread, decoupled from task execution.
Streams audio amplitude for the UI waveform, monitors wake word,
and immediately triggers high-priority interruption on STOP commands.
"""

import logging
import threading
import time
from typing import Callable, List, Optional, Any
import speech_recognition as sr

from app.config import ASSISTANT_NAME
from app.interruption.controller import InterruptionController
from app.voice.speech_to_text import SpeechToTextEngine
from app.voice.wake_word import WakeWordDetector

logger = logging.getLogger(f"{ASSISTANT_NAME}.VoiceListener")


class VoiceListener:
    """Continuous audio listener with microphone toggle and waveform telemetry."""

    def __init__(
        self,
        stt_engine: Optional[SpeechToTextEngine] = None,
        wake_detector: Optional[WakeWordDetector] = None,
        interruption_controller: Optional[InterruptionController] = None,
        tts_engine: Optional[Any] = None,
        silence_threshold: float = 1.0,
    ):
        self.stt = stt_engine or SpeechToTextEngine()
        self.wake_detector = wake_detector or WakeWordDetector(enabled=False)
        self.interruption = interruption_controller
        self.tts = tts_engine
        self.silence_threshold = silence_threshold

        self.is_listening = False
        self.mic_enabled = True
        self.awaiting_command = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_processed_transcript: str = ""
        self._last_processed_time: float = 0.0

        # Callbacks to UI
        self.on_speech_recognized: Optional[Callable[[str], None]] = None
        self.on_transcript_preview: Optional[Callable[[str], None]] = None
        self.on_waveform_data: Optional[Callable[[float], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Wire STT error propagation
        self.stt.on_error = self._on_stt_error

    def set_silence_threshold(self, threshold: float) -> None:
        """Sets the pause duration in seconds required to signal speech endpoint."""
        self.silence_threshold = max(0.5, float(threshold))
        try:
            self.stt.recognizer.pause_threshold = self.silence_threshold
            self.stt.recognizer.non_speaking_duration = min(self.silence_threshold, 0.8)
            logger.info(f"VoiceListener silence threshold set to {self.silence_threshold}s")
        except Exception as e:
            logger.debug(f"Could not configure recognizer pause_threshold: {e}")

    def _on_stt_error(self, err: str) -> None:
        if self.on_error:
            try:
                self.on_error(err)
            except Exception:
                pass
        if self.on_transcript_preview:
            try:
                self.on_transcript_preview(f"[Audio Error] {err}")
            except Exception:
                pass

    def _is_self_echo(self, text: str) -> bool:
        """Determines if text matches NIVA's own spoken output within a 3.0s window."""
        if not self.tts:
            return False
        last_spoken = getattr(self.tts, "last_spoken_text", "").lower().strip()
        last_spoken_time = getattr(self.tts, "last_spoken_timestamp", 0.0)
        if not last_spoken:
            return False
        if (time.time() - last_spoken_time) > 3.0:
            return False
        cleaned_lower = text.lower().strip()
        return (
            cleaned_lower == last_spoken or
            cleaned_lower in last_spoken or
            last_spoken in cleaned_lower or
            (len(cleaned_lower) > 4 and cleaned_lower in "how can i help you sir")
        )

    def _is_duplicate_utterance(self, text: str) -> bool:
        """Determines if text is a duplicate of the last processed transcript within 3.0s."""
        cleaned_lower = text.lower().strip()
        now = time.time()
        return (cleaned_lower == self._last_processed_transcript and (now - self._last_processed_time) < 3.0)

    def start(self) -> None:
        """Starts the background listening loop."""
        if self.is_listening:
            return

        self._stop_event.clear()
        self.is_listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Continuous Voice Listener started.")
        if self.on_status_change:
            self.on_status_change("LISTENING")

    def stop(self) -> None:
        """Stops the listener."""
        self._stop_event.set()
        self.is_listening = False
        if self.on_status_change:
            self.on_status_change("MUTED")

    def toggle_microphone(self) -> bool:
        """Toggles mic on/off."""
        self.mic_enabled = not self.mic_enabled
        if self.on_status_change:
            self.on_status_change("LISTENING" if self.mic_enabled else "MUTED")
        return self.mic_enabled

    def _listen_loop(self) -> None:
        """Continuous audio acquisition loop with persistent stream."""
        while not self._stop_event.is_set():
            if not self.mic_enabled:
                time.sleep(0.3)
                continue

            try:
                mic = sr.Microphone()
                with mic as source:
                    logger.info("Microphone stream opened. Calibrating noise floor...")
                    try:
                        self.stt.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    except Exception as e:
                        logger.debug(f"Noise adjust notice: {e}")

                    # In continuous voice assistants, dynamic_energy_threshold must be FALSE to prevent
                    # the energy threshold from drifting down to room noise floor during quiet periods,
                    # which causes listen() to mistake silence for continuous speech and lock up.
                    ambient = self.stt.recognizer.energy_threshold
                    self.stt.recognizer.dynamic_energy_threshold = False
                    # Speech is typically 300-2000 RMS; ambient room noise is 5-40 RMS.
                    # Set threshold safely above room floor (min 150) so background noise is ignored.
                    self.stt.recognizer.energy_threshold = max(150, min(int(ambient * 2.5), 600))
                    logger.info(f"Microphone calibrated: ambient={ambient:.1f}, fixed energy_threshold={self.stt.recognizer.energy_threshold}")
                    self.stt.recognizer.pause_threshold = self.silence_threshold
                    self.stt.recognizer.non_speaking_duration = min(self.silence_threshold, 0.5)

                    if self.on_status_change:
                        self.on_status_change("LISTENING" if self.mic_enabled else "MUTED")

                    # Inner loop keeps the microphone audio stream open continuously without re-opening
                    while not self._stop_event.is_set():
                        if not self.mic_enabled:
                            time.sleep(0.3)
                            continue

                        # Echo prevention / speaking guard: do not listen while assistant is speaking
                        if self.tts and getattr(self.tts, "is_speaking", False):
                            time.sleep(0.15)
                            continue

                        try:
                            # Stream baseline amplitude for visualizer
                            if self.on_waveform_data:
                                self.on_waveform_data(0.15)

                            # Drain any accumulated unread audio frames to ensure live capture without buffer overflow
                            if hasattr(source, "stream") and hasattr(source.stream, "pyaudio_stream"):
                                try:
                                    avail = source.stream.pyaudio_stream.get_read_available()
                                    if avail > 0:
                                        source.stream.pyaudio_stream.read(avail, exception_on_overflow=False)
                                except Exception:
                                    pass

                            audio = self.stt.recognizer.listen(source, timeout=1.5, phrase_time_limit=10.0)

                            # Emit waveform activity peak
                            if self.on_waveform_data:
                                self.on_waveform_data(0.85)

                            if self.on_status_change:
                                self.on_status_change("PROCESSING_SPEECH")

                            # Transcribe speech
                            text = self.stt.transcribe(audio)

                            if text:
                                cleaned_str = text.strip()
                                cleaned_lower = cleaned_str.lower()

                                # 1. Self-echo suppression: drop transcripts produced by NIVA's own spoken output
                                if self._is_self_echo(cleaned_str):
                                    logger.info(f"Suppressed self-echo from NIVA audio output: '{cleaned_str}'")
                                    continue

                                # 2. Duplicate transcript suppression: prevent executing the exact same utterance twice
                                if self._is_duplicate_utterance(cleaned_str):
                                    logger.info(f"Suppressed duplicate transcript within 3.0s window: '{cleaned_str}'")
                                    continue

                                self._last_processed_transcript = cleaned_lower
                                self._last_processed_time = time.time()

                                logger.info(f"User Spoke: '{cleaned_str}'")
                                if self.on_transcript_preview:
                                    self.on_transcript_preview(cleaned_str)

                                # High-priority interruption fast-path check FIRST
                                if self.interruption:
                                    handled, response_msg = self.interruption.handle_interruption(text)
                                    if handled:
                                        logger.info(f"Fast-path interruption handled: {response_msg}")
                                        self.awaiting_command = False
                                        if self.on_status_change:
                                            self.on_status_change("LISTENING")
                                        continue

                                # If already prompted and waiting for full command
                                if self.awaiting_command:
                                    self.awaiting_command = False
                                    if self.on_status_change:
                                        self.on_status_change("PROCESSING_SPEECH")
                                    if self.on_speech_recognized:
                                        self.on_speech_recognized(text.strip())
                                    if self.on_status_change:
                                        self.on_status_change("LISTENING")
                                    continue

                                # Check wake word
                                if self.wake_detector.enabled:
                                    if self.wake_detector.is_wake_word_only(text):
                                        prompt_msg = "How can I help you, sir?"
                                        logger.info(f"Wake word detected alone. Prompting user: '{prompt_msg}'")
                                        self.awaiting_command = True
                                        if self.tts:
                                            self.tts.speak(prompt_msg)
                                        if self.on_transcript_preview:
                                            self.on_transcript_preview(f"[NIVA] {prompt_msg}")
                                        if self.on_status_change:
                                            self.on_status_change("AWAITING_REQUEST")
                                        continue

                                    triggered, clean_cmd = self.wake_detector.check_wake_word(text)
                                    if triggered:
                                        cmd_to_process = clean_cmd if clean_cmd else text.strip()
                                        if self.on_speech_recognized:
                                            self.on_speech_recognized(cmd_to_process)
                                    else:
                                        logger.info(f"Speech heard but wake word missing (Wake word mode ON): '{text}'")
                                        if self.on_transcript_preview:
                                            self.on_transcript_preview(f"[Say 'NIVA' first]: \"{text}\"")
                                else:
                                    # Direct continuous listening mode
                                    if self.on_speech_recognized:
                                        self.on_speech_recognized(text.strip())

                            if self.on_status_change:
                                self.on_status_change("LISTENING" if self.mic_enabled else "MUTED")

                        except sr.WaitTimeoutError:
                            # Silence timeout - continue next listen cycle seamlessly
                            continue
                        except Exception as inner_e:
                            logger.debug(f"Audio capture cycle notice: {inner_e}")
                            break

            except Exception as outer_e:
                err_msg = f"Microphone error: {outer_e}"
                logger.warning(err_msg)
                if self.on_error:
                    try:
                        self.on_error(err_msg)
                    except Exception:
                        pass
                if self.on_status_change:
                    self.on_status_change("MIC_ERROR")
                time.sleep(1.0)
