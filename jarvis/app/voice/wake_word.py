"""
Wake Word Detection for NIVA.
Detects activation triggers such as "NIVA" or "Hey NIVA" (dynamically configurable).
"""

import os
import re
from typing import List, Optional, Tuple

from app.config import ASSISTANT_NAME, DEFAULT_WAKE_WORDS


class WakeWordDetector:
    """Detects and strips wake words from recognized speech."""

    def __init__(self, wake_word: Optional[str] = None, enabled: bool = True):
        self.wake_word = (wake_word or ASSISTANT_NAME).lower().strip()
        self.enabled = enabled
        self._build_wake_word_list()

    def _build_wake_word_list(self) -> None:
        phonetic_variants = ["niva", "nivea", "neeva", "neva", "nova", "niwa", "neba"]
        self.wake_word_list = []
        bases = [self.wake_word] + [p for p in phonetic_variants if p != self.wake_word]
        for w in bases:
            for item in [w, f"hey {w}", f"ok {w}", f"hi {w}", f"hello {w}"]:
                if item not in self.wake_word_list:
                    self.wake_word_list.append(item)

    def set_wake_word(self, name: str) -> None:
        """Dynamically update configured wake word."""
        self.wake_word = name.lower().strip()
        self._build_wake_word_list()

    def is_wake_word_only(self, text: str) -> bool:
        """Checks if text contains solely the wake word with no attached command."""
        if not text or not text.strip():
            return False
        cleaned = re.sub(r"[,\s:\.\!\?]+$", "", text.strip()).lower()
        cleaned_no_prefix = re.sub(r"^(?:hey|ok|hi|hello)\s+", "", cleaned).strip()
        if cleaned_no_prefix in ["niva", "nivea", "neeva", "neva", "nova", "niwa", "neba", self.wake_word]:
            return True
        return cleaned in [w.lower() for w in self.wake_word_list]

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Determines whether the wake word is present.
        If wake word detection is disabled, returns (True, text.strip()).
        If user spoke only the wake word, returns (True, "").
        If user spoke wake word with command, returns (True, clean_command_text).
        If wake word is absent, returns (False, text.strip()).
        """
        if not text or not text.strip():
            return False, ""

        if not self.enabled:
            return True, text.strip()

        cleaned = text.strip()

        if self.is_wake_word_only(cleaned):
            return True, ""

        # Check all configured wake words
        for ww in self.wake_word_list:
            pattern = rf"^(?:hey\s+|ok\s+|hi\s+)?{re.escape(ww)}[,\s:]*"
            match = re.match(pattern, cleaned, re.IGNORECASE)
            if match:
                command_part = cleaned[match.end():].strip()
                return True, command_part

        wake_targets = [self.wake_word, "niva", "nivea", "neeva", "neva", "nova"]
        if any(w in cleaned.lower() for w in wake_targets):
            pattern = rf"\b(?:hey\s+|ok\s+|hi\s+|hello\s+)?(?:{'|'.join(re.escape(w) for w in wake_targets)})[,\s:]*"
            sub = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            return True, sub

        return False, text.strip()
