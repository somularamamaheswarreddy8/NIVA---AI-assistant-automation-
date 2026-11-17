"""
High-priority cancellation token and cooperative pause/cancellation utilities.
Provides interruptible sleeps and safe concurrency primitives.
"""

import threading
import time
from typing import Callable, List, Optional


class CancellationToken:
    """
    Thread-safe cooperative cancellation and pause controller.
    Ensures actions can be interrupted instantaneously without waiting for LLM or blocking calls.
    """

    def __init__(self):
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # set() means RUNNING; clear() means PAUSED
        self._lock = threading.RLock()
        self._cleanup_callbacks: List[Callable[[], None]] = []

    def cancel(self) -> None:
        """Immediately trigger cancellation."""
        with self._lock:
            self._cancel_event.set()
            # If paused, unpause so threads can wake up and detect cancellation
            self._pause_event.set()
            # Run cleanup callbacks (releasing mouse/keys, etc.)
            for cb in self._cleanup_callbacks:
                try:
                    cb()
                except Exception:
                    pass

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_event.is_set()

    def pause(self) -> None:
        """Pause execution."""
        with self._lock:
            self._pause_event.clear()

    def resume(self) -> None:
        """Resume execution."""
        with self._lock:
            self._pause_event.set()

    def is_paused(self) -> bool:
        """Check if currently paused."""
        return not self._pause_event.is_set()

    def reset(self) -> None:
        """Reset state for a new task."""
        with self._lock:
            self._cancel_event.clear()
            self._pause_event.set()
            self._cleanup_callbacks.clear()

    def register_cleanup(self, callback: Callable[[], None]) -> None:
        """Register a callback to be executed immediately upon cancellation."""
        with self._lock:
            self._cleanup_callbacks.append(callback)

    def wait_if_paused(self, timeout: Optional[float] = None) -> bool:
        """
        Blocks while paused until resumed or cancelled.
        Returns False if cancelled during pause.
        """
        while not self._pause_event.is_set():
            if self.is_cancelled():
                return False
            self._pause_event.wait(timeout=0.1)
        return not self.is_cancelled()

    def check_cancellation(self) -> None:
        """
        Raises InterruptedError if cancelled.
        Also blocks if paused until resumed.
        """
        self.wait_if_paused()
        if self.is_cancelled():
            raise InterruptedError("Operation cancelled by user.")

    def interruptible_sleep(self, seconds: float, slice_sec: float = 0.05) -> bool:
        """
        Sleeps for `seconds` in small slices, checking for cancellation and pause.
        Returns True if slept full duration, False if cancelled.
        """
        end_time = time.time() + seconds
        while time.time() < end_time:
            if not self.wait_if_paused():
                return False
            if self.is_cancelled():
                return False
            time.sleep(min(slice_sec, max(0.0, end_time - time.time())))
        return not self.is_cancelled()
