"""
Tests for Voice Recognition, Speech Synthesis, Wake Word Detection, and Mixed-Language Handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.voice.speech_to_text import SpeechToTextEngine
from app.voice.wake_word import WakeWordDetector


class TestVoice(unittest.TestCase):

    def test_telugu_english_mixed_normalization(self):
        cases = [
            ("JARVIS, Chrome open chey", "open chrome"),
            ("Downloads folder open chey", "open downloads folder"),
            ("Bluetooth on chey", "turn bluetooth on"),
            ("Bluetooth off chey", "turn bluetooth off"),
            ("Excel lo monthly expenses create chey", "create monthly expenses in excel"),
            ("aapu", "stop"),
            ("koncham aagu", "pause"),
            ("malli chey", "resume"),
        ]
        for spoken, expected in cases:
            res = SpeechToTextEngine.normalize_mixed_language(spoken)
            self.assertEqual(res.lower(), expected.lower(), f"Normalization mismatch for '{spoken}'")

    def test_wake_word_detector(self):
        detector = WakeWordDetector(wake_word="niva", enabled=True)

        # Matched with NIVA command
        triggered, cmd = detector.check_wake_word("NIVA, open Chrome")
        self.assertTrue(triggered)
        self.assertEqual(cmd.lower(), "open chrome")

        # Hey Niva
        triggered, cmd = detector.check_wake_word("Hey Niva, search Python tutorials")
        self.assertTrue(triggered)
        self.assertEqual(cmd.lower(), "search python tutorials")

        # Also supports legacy Jarvis if configured
        jarvis_detector = WakeWordDetector(wake_word="jarvis", enabled=True)
        trig_j, cmd_j = jarvis_detector.check_wake_word("JARVIS, open Chrome")
        self.assertTrue(trig_j)
        self.assertEqual(cmd_j.lower(), "open chrome")

        # Wake word not present
        triggered, cmd = detector.check_wake_word("Open notepad")
        self.assertFalse(triggered)

        # Wake word disabled mode
        disabled_detector = WakeWordDetector(enabled=False)
        trig, c = disabled_detector.check_wake_word("Open notepad")
        self.assertTrue(trig)
        self.assertEqual(c, "Open notepad")


if __name__ == "__main__":
    unittest.main()
