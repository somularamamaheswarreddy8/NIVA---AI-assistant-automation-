"""
Text-to-Speech (TTS) Engine for NIVA.
Provides non-blocking asynchronous audio responses with immediate interruption capability,
volume/rate/voice controls, and explicit error reporting.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from app.config import ASSISTANT_NAME

logger = logging.getLogger(f"{ASSISTANT_NAME}.TTS")


class TextToSpeechEngine:
    """Non-blocking, interruptible speech synthesis worker using Windows SAPI with pyttsx3 fallback."""

    def __init__(self, rate: int = 0, volume: int = 100):
        # SAPI Rate is -10 to 10 (0 is normal speed)
        self.rate = rate
        # SAPI Volume is 0 to 100
        self.volume = volume
        self.enabled = True
        self.current_voice_id: Optional[str] = None
        self.last_error: Optional[str] = None
        self.audio_output_available: bool = True
        self.last_spoken_text: str = ""
        self.last_spoken_timestamp: float = 0.0

        self._speech_queue: queue.Queue = queue.Queue()
        self._is_running = True
        self._is_speaking = False
        self._lock = threading.Lock()

        # Telemetry Callbacks
        self.on_speaking_started: Optional[Callable[[str], None]] = None
        self.on_speaking_finished: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Dedicated worker thread for TTS engine
        self._worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._worker_thread.start()

    def _tts_worker(self) -> None:
        """Background loop continuously consuming queued speech items."""
        speaker = None
        engine_type = "none"

        # 1. Try Windows SAPI.SpVoice with COM
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Volume = self.volume
            speaker.Rate = self.rate
            engine_type = "sapi"
            logger.info("Initialized native Windows SAPI.SpVoice audio engine.")
        except Exception as e:
            logger.warning(f"Could not initialize win32com SAPI: {e}. Attempting pyttsx3 fallback...")
            try:
                import pyttsx3
                speaker = pyttsx3.init()
                speaker.setProperty('volume', self.volume / 100.0)
                speaker.setProperty('rate', 185)
                engine_type = "pyttsx3"
                logger.info("Initialized pyttsx3 speech engine.")
            except Exception as e2:
                err_msg = f"Failed to initialize any TTS audio subsystem: SAPI error: {e} | pyttsx3 error: {e2}"
                logger.error(err_msg)
                self.last_error = err_msg
                if self.on_error:
                    self.on_error(err_msg)
                speaker = None
                engine_type = "none"

        while self._is_running:
            try:
                item = self._speech_queue.get(timeout=0.2)
                if not item:
                    continue

                cmd, arg = item

                if cmd == "STOP":
                    if speaker and engine_type == "sapi":
                        try:
                            speaker.Speak("", 2)  # SVSFPurgeBeforeSpeak (stops immediately)
                        except Exception:
                            pass
                    self._is_speaking = False
                    self._speech_queue.task_done()
                    continue

                elif cmd == "SET_VOLUME":
                    self.volume = arg
                    if speaker:
                        try:
                            if engine_type == "sapi":
                                speaker.Volume = self.volume
                            elif engine_type == "pyttsx3":
                                speaker.setProperty('volume', self.volume / 100.0)
                        except Exception:
                            pass
                    self._speech_queue.task_done()
                    continue

                elif cmd == "SET_RATE":
                    self.rate = arg
                    if speaker:
                        try:
                            if engine_type == "sapi":
                                speaker.Rate = self.rate
                            elif engine_type == "pyttsx3":
                                speaker.setProperty('rate', int(185 + (self.rate * 10)))
                        except Exception:
                            pass
                    self._speech_queue.task_done()
                    continue

                elif cmd == "SET_VOICE":
                    if speaker and engine_type == "sapi":
                        try:
                            voice_target = str(arg).lower()
                            count = speaker.GetVoices().Count
                            for i in range(count):
                                v = speaker.GetVoices().Item(i)
                                if voice_target in v.GetDescription().lower() or voice_target in v.Id.lower():
                                    speaker.Voice = v
                                    self.current_voice_id = v.Id
                                    logger.info(f"Switched SAPI Voice to: {v.GetDescription()}")
                                    break
                        except Exception as e:
                            logger.error(f"Failed to set SAPI voice: {e}")
                    self._speech_queue.task_done()
                    continue

                elif cmd == "SPEAK":
                    text = arg
                    if not self.enabled:
                        logger.info(f"[TTS Muted]: '{text}'")
                        self._speech_queue.task_done()
                        continue

                    if not speaker:
                        err_msg = f"Cannot speak: Audio output device unavailable ({self.last_error or 'No TTS engine'}). Text was: '{text}'"
                        logger.error(err_msg)
                        if self.on_error:
                            self.on_error(err_msg)
                        self._speech_queue.task_done()
                        continue

                    self._is_speaking = True
                    logger.info(f"{ASSISTANT_NAME} Speaking: '{text}'")
                    if self.on_speaking_started:
                        try:
                            self.on_speaking_started(text)
                        except Exception:
                            pass

                    try:
                        if engine_type == "sapi":
                            # Speak asynchronously so stop_speaking can interrupt at any point
                            speaker.Speak(text, 1)  # SVSFlagsAsync
                            # Wait until done speaking or stop was requested
                            while speaker.Status.RunningState == 2 and self._is_running:
                                time.sleep(0.05)
                        elif engine_type == "pyttsx3":
                            speaker.say(text)
                            speaker.runAndWait()
                    except Exception as e:
                        err_msg = f"Audio playback error: {e}"
                        logger.error(err_msg)
                        self.last_error = err_msg
                        if self.on_error:
                            self.on_error(err_msg)
                    finally:
                        self._is_speaking = False
                        self.last_spoken_text = str(text)
                        self.last_spoken_timestamp = time.time()
                        if self.on_speaking_finished:
                            try:
                                self.on_speaking_finished(text)
                            except Exception:
                                pass

                    self._speech_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"TTS Worker loop notice: {e}")

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak(self, text: str) -> None:
        """Enqueues text for asynchronous non-blocking speech."""
        if not text or not str(text).strip():
            return
        self._speech_queue.put(("SPEAK", str(text).strip()))

    def stop_speaking(self) -> None:
        """Immediately halts any speech and clears pending utterances."""
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except Exception:
                break
        self._speech_queue.put(("STOP", None))
        self._is_speaking = False

    def set_volume(self, volume: int) -> None:
        """Sets output volume (0 to 100)."""
        vol = max(0, min(100, int(volume)))
        self._speech_queue.put(("SET_VOLUME", vol))

    def set_rate(self, rate: int) -> None:
        """Sets speech rate (-10 slow to +10 fast)."""
        r = max(-10, min(10, int(rate)))
        self._speech_queue.put(("SET_RATE", r))

    def set_voice(self, voice_name_or_id: str) -> None:
        """Sets current voice by name or ID."""
        self._speech_queue.put(("SET_VOICE", voice_name_or_id))

    def set_speaking_enabled(self, enabled: bool) -> None:
        """Mutes or unmutes speech output."""
        self.enabled = bool(enabled)
        if not self.enabled:
            self.stop_speaking()

    def list_voices(self) -> List[Dict[str, Any]]:
        """Returns available system voices."""
        voices = []
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            sp = win32com.client.Dispatch("SAPI.SpVoice")
            for i in range(sp.GetVoices().Count):
                v = sp.GetVoices().Item(i)
                voices.append({"index": i, "id": v.Id, "name": v.GetDescription()})
        except Exception:
            try:
                import pyttsx3
                eng = pyttsx3.init()
                for v in eng.getProperty('voices'):
                    voices.append({"id": v.id, "name": v.name})
            except Exception:
                pass
        return voices

    def is_available(self) -> bool:
        """Returns True if audio output engine is active and operational."""
        return self.audio_output_available and self.last_error is None

    def shutdown(self) -> None:
        """Stops worker thread."""
        self.stop_speaking()
        self._is_running = False
