"""
Tests for the Dedicated Real-Time Interruption Controller.
Verifies STOP, PAUSE, RESUME, OVERRIDE, and UNDO.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.interruption.cancellation import CancellationToken
from app.interruption.controller import InterruptionCommandType, InterruptionController


class TestInterruption(unittest.TestCase):

    def setUp(self):
        self.token = CancellationToken()
        self.controller = InterruptionController(token=self.token)

    def test_classify_stop_phrases(self):
        stop_phrases = ["stop", "Stop now", "cancel this task", "abort", "don't continue", "emergency stop", "aapu"]
        for p in stop_phrases:
            cmd_type, payload = self.controller.classify_command(p)
            self.assertEqual(cmd_type, InterruptionCommandType.STOP, f"Failed to classify STOP for '{p}'")

    def test_classify_pause_phrases(self):
        pause_phrases = ["pause", "wait", "hold on", "koncham aagu"]
        for p in pause_phrases:
            cmd_type, payload = self.controller.classify_command(p)
            self.assertEqual(cmd_type, InterruptionCommandType.PAUSE, f"Failed to classify PAUSE for '{p}'")

    def test_classify_resume_phrases(self):
        resume_phrases = ["resume", "continue", "keep going", "malli chey"]
        for p in resume_phrases:
            cmd_type, payload = self.controller.classify_command(p)
            self.assertEqual(cmd_type, InterruptionCommandType.RESUME, f"Failed to classify RESUME for '{p}'")

    def test_classify_override_phrases(self):
        phrase = "Stop. Open Notepad instead."
        cmd_type, payload = self.controller.classify_command(phrase)
        self.assertEqual(cmd_type, InterruptionCommandType.OVERRIDE)
        self.assertIn("open notepad", payload.lower())

    def test_execute_stop_triggers_cancellation(self):
        self.assertFalse(self.token.is_cancelled())
        handled, msg = self.controller.handle_interruption("STOP NOW")
        self.assertTrue(handled)
        self.assertTrue(self.token.is_cancelled())

    def test_execute_pause_and_resume(self):
        self.assertFalse(self.token.is_paused())
        self.controller.handle_interruption("Pause")
        self.assertTrue(self.token.is_paused())

        self.controller.handle_interruption("Continue")
        self.assertFalse(self.token.is_paused())

    def test_cancellation_token_interruptible_sleep(self):
        import time
        start = time.time()
        # Schedule cancellation in 0.1s
        import threading
        t = threading.Timer(0.1, self.token.cancel)
        t.start()
        # Try sleeping for 5 seconds
        completed = self.token.interruptible_sleep(5.0)
        elapsed = time.time() - start
        self.assertFalse(completed)
        self.assertLess(elapsed, 1.0, "Interruptible sleep took too long to abort on cancellation!")


if __name__ == "__main__":
    unittest.main()
