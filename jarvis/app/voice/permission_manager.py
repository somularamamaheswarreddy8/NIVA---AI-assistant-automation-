"""
Microphone Hardware and Permission Manager for NIVA.
Verifies audio input device availability, handles Windows privacy checks,
and provides persistent permission tracking.
"""

import logging
import os
import subprocess
from typing import Optional, Tuple
import speech_recognition as sr

logger = logging.getLogger("NIVA.VoicePermission")


class MicrophonePermissionManager:
    """Manages audio capture device discovery and Windows microphone permissions."""

    @staticmethod
    def check_device_available() -> Tuple[bool, str]:
        """Checks if at least one audio input device (microphone) exists on the system."""
        try:
            device_names = sr.Microphone.list_microphone_names()
            if not device_names:
                return False, "No audio input devices (microphones) were found on this computer."
            first_device = device_names[0]
            logger.info(f"Detected {len(device_names)} audio input device(s). Default: '{first_device}'")
            return True, f"Found {len(device_names)} device(s). Default: {first_device}"
        except Exception as e:
            err_str = str(e)
            # Handle PortAudio multi-instance enumeration contention when a stream is already active
            if "-2147483640" in err_str or "not initialized" in err_str.lower():
                logger.debug("PortAudio enumeration contention detected; audio subsystem is active.")
                return True, "Audio capture device active."
            err_msg = f"Failed to query audio input devices: {e}"
            logger.error(err_msg)
            return False, err_msg

    @staticmethod
    def test_microphone_stream() -> Tuple[bool, str]:
        """
        Attempts to open the microphone audio stream to test hardware access
        and Windows privacy permission.
        """
        has_device, dev_msg = MicrophonePermissionManager.check_device_available()
        if not has_device:
            return False, dev_msg

        try:
            mic = sr.Microphone()
            with mic as source:
                # Successfully acquired audio capture stream
                pass
            return True, "Microphone stream opened successfully. Permission is active."
        except Exception as e:
            err_str = str(e).lower()
            if "-2147483640" in err_str:
                return True, "Microphone stream is currently active."
            if "permission" in err_str or "denied" in err_str or "access" in err_str or "-9996" in err_str or "-9999" in err_str:
                msg = (
                    "Microphone access is blocked by Windows privacy settings. "
                    "Please allow microphone access in Windows Settings > Privacy & security > Microphone."
                )
                logger.warning(msg)
                return False, msg
            err_msg = f"Microphone stream error: {e}"
            logger.warning(err_msg)
            return False, err_msg

    @staticmethod
    def get_permission_state(db) -> str:
        """
        Retrieves stored permission state from SQLite database.
        Returns: 'granted', 'denied', or 'prompt' (default).
        """
        if not db:
            return "granted"
        return str(db.get_setting("MIC_PERMISSION_STATUS", "prompt")).lower()

    @staticmethod
    def set_permission_state(db, state: str) -> None:
        """Stores updated permission state ('granted' or 'denied')."""
        if db:
            db.set_setting("MIC_PERMISSION_STATUS", state.lower().strip())
            logger.info(f"Microphone permission state set to '{state.lower().strip()}'.")

    @staticmethod
    def open_windows_microphone_settings() -> bool:
        """Launches the Windows Settings page for Microphone Privacy."""
        try:
            logger.info("Opening Windows Microphone Privacy Settings (ms-settings:privacy-microphone)...")
            subprocess.Popen(["cmd.exe", "/c", "start", "ms-settings:privacy-microphone"], shell=False)
            return True
        except Exception as e:
            logger.error(f"Failed to launch Windows settings: {e}")
            return False
