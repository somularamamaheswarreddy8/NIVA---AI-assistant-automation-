"""
Task Manager for NIVA.
Coordinates asynchronous task lifecycle, state transitions, and cancellation hooks.
"""

from datetime import datetime
import logging
import threading
from typing import Callable, List, Optional

from app.core.executor import TaskExecutor
from app.core.planner import TaskPlanner
from app.core.task_state import Task, TaskStatus
from app.interruption.cancellation import CancellationToken
from app.storage.database import Database

logger = logging.getLogger("NIVA.TaskManager")


class TaskManager:
    """Oversees background task execution threads and status coordination."""

    def __init__(self, planner: TaskPlanner, executor: TaskExecutor, token: CancellationToken, db: Optional[Database] = None):
        self.planner = planner
        self.executor = executor
        self.token = token
        self.db = db or Database()

        self.current_task: Optional[Task] = None
        self._execution_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Callbacks
        self.on_task_state_changed: Optional[Callable[[Task], None]] = None

    def start_new_task(self, prompt: str) -> Task:
        """
        Plans and initiates execution of a new user command.
        If a previous task was running, cancels it first.
        """
        with self._lock:
            if self.is_running():
                logger.warning("Preempting existing task with new command.")
                self.stop_current_task()

            self.token.reset()
            task = self.planner.create_plan(prompt)
            self.current_task = task

            # Persist initial task in DB
            self.db.save_task(task.task_id, task.user_prompt, task.status.value, total_steps=len(task.steps))

            if task.needs_clarification:
                task.status = TaskStatus.AWAITING_CONFIRMATION
                self.db.update_task_status(task.task_id, task.status.value, task.clarification_question)
                if self.on_task_state_changed:
                    self.on_task_state_changed(task)
                return task

            if task.unsupported_reason:
                task.status = TaskStatus.FAILED
                task.error_message = task.unsupported_reason
                self.db.update_task_status(task.task_id, task.status.value, task.unsupported_reason)
                if self.on_task_state_changed:
                    self.on_task_state_changed(task)
                return task

            if not task.steps:
                task.status = TaskStatus.FAILED
                task.error_message = "No executable steps were planned for this request."
                self.db.update_task_status(task.task_id, task.status.value, task.error_message)
                if self.on_task_state_changed:
                    self.on_task_state_changed(task)
                return task

            if self.on_task_state_changed:
                self.on_task_state_changed(task)

            task.status = TaskStatus.RUNNING
            # Spawn execution thread
            self._execution_thread = threading.Thread(target=self._run_task_worker, args=(task,), daemon=True)
            self._execution_thread.start()
            return task

    def _run_task_worker(self, task: Task) -> None:
        """Background execution worker."""
        try:
            executed_task = self.executor.execute_task(task)
            self.db.update_task_status(executed_task.task_id, executed_task.status.value, executed_task.error_message)
        except Exception as e:
            logger.exception(f"Unexpected error executing task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            self.db.update_task_status(task.task_id, task.status.value, str(e))
        finally:
            if self.on_task_state_changed:
                self.on_task_state_changed(task)

    def is_running(self) -> bool:
        """Checks if a task is actively running or paused."""
        if self.current_task and self.current_task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.PLANNING]:
            return True
        return False

    def stop_current_task(self) -> None:
        """Immediately halts the active task."""
        with self._lock:
            self.token.cancel()
            if self.current_task:
                self.current_task.status = TaskStatus.STOPPED
                self.db.update_task_status(self.current_task.task_id, TaskStatus.STOPPED.value, "Cancelled by user.")
                if self.on_task_state_changed:
                    self.on_task_state_changed(self.current_task)

    def pause_current_task(self) -> None:
        """Suspends execution."""
        with self._lock:
            self.token.pause()
            if self.current_task:
                self.current_task.status = TaskStatus.PAUSED
                if self.on_task_state_changed:
                    self.on_task_state_changed(self.current_task)

    def resume_current_task(self) -> None:
        """Resumes suspended execution."""
        with self._lock:
            self.token.resume()
            if self.current_task:
                self.current_task.status = TaskStatus.RUNNING
                if self.on_task_state_changed:
                    self.on_task_state_changed(self.current_task)

    def wait_for_completion(self, timeout: float = 10.0) -> bool:
        """Waits for current task execution worker thread to complete."""
        thread = self._execution_thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            return not thread.is_alive()
        return True
