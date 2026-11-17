"""
Task Execution Engine for NIVA.
Safely and sequentially executes planned TaskStep actions with real-time cancellation,
pause/resume checks, checkpoint registration, and progress telemetry.
"""

from datetime import datetime
import logging
import time
from typing import Callable, Optional

from app.core.task_state import StepStatus, Task, TaskStatus, TaskStep
from app.interruption.cancellation import CancellationToken
from app.interruption.checkpoints import CheckpointManager
from app.tools.registry import ToolRegistry

logger = logging.getLogger("NIVA.Executor")


class TaskExecutor:
    """Executes Task steps sequentially with cooperative interruption."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        cancellation_token: CancellationToken,
        checkpoint_mgr: Optional[CheckpointManager] = None
    ):
        self.registry = tool_registry
        self.token = cancellation_token
        self.checkpoint_mgr = checkpoint_mgr or CheckpointManager()

        # Telemetry Callbacks
        self.on_step_started: Optional[Callable[[Task, TaskStep, int], None]] = None
        self.on_step_completed: Optional[Callable[[Task, TaskStep, int], None]] = None
        self.on_task_finished: Optional[Callable[[Task], None]] = None

    def execute_task(self, task: Task) -> Task:
        """
        Executes all pending steps in the task sequentially.
        Respects interruption (STOP, PAUSE, RESUME).
        """
        if not task.steps:
            task.status = TaskStatus.FAILED
            task.error_message = "No executable steps were planned for this request."
            if self.on_task_finished:
                self.on_task_finished(task)
            return task

        task.status = TaskStatus.RUNNING
        logger.info(f"Starting execution of Task {task.task_id}: '{task.user_prompt}' ({len(task.steps)} steps)")

        for index, step in enumerate(task.steps):
            task.current_step_index = index
            task.updated_at = datetime.now()

            # 1. High-priority interruption & pause check
            if not self.token.wait_if_paused():
                logger.warning(f"Task {task.task_id} interrupted while paused.")
                task.status = TaskStatus.STOPPED
                break

            if self.token.is_cancelled():
                logger.warning(f"Task {task.task_id} cancelled by user.")
                task.status = TaskStatus.STOPPED
                break

            # 2. Step Start Notification
            step.status = StepStatus.IN_PROGRESS
            step.started_at = datetime.now()
            logger.info(f"Executing step {index + 1}/{len(task.steps)}: {step.description} [{step.tool_name}]")
            if self.on_step_started:
                self.on_step_started(task, step, index)

            # 3. Checkpoint snapshot before modification
            task.add_checkpoint(metadata={"step_id": step.step_id, "tool": step.tool_name})

            # 4. Dispatch Tool Execution
            exec_result = self.registry.execute(step.tool_name, step.parameters)

            # Check if cancelled during tool execution
            if self.token.is_cancelled():
                step.status = StepStatus.FAILED
                step.error = "Interrupted during execution."
                task.status = TaskStatus.STOPPED
                break

            # 5. Process Result
            if exec_result.get("success", False):
                step.status = StepStatus.COMPLETED
                step.result = exec_result.get("message") or exec_result.get("result") or "Success"
                step.completed_at = datetime.now()

                # Register undo data if applicable
                self._register_step_undo(task.task_id, step)

                logger.info(f"Step {index + 1} completed: {step.result}")
            else:
                step.status = StepStatus.FAILED
                step.error = exec_result.get("error", "Execution failed")
                step.completed_at = datetime.now()
                task.status = TaskStatus.FAILED
                task.error_message = f"Failed at step {index + 1} ({step.description}): {step.error}"
                logger.error(f"Step {index + 1} failed: {step.error}")

                if self.on_step_completed:
                    self.on_step_completed(task, step, index)
                break

            if self.on_step_completed:
                self.on_step_completed(task, step, index)

            # Brief interruptible cadence between steps
            if not self.token.interruptible_sleep(0.3):
                task.status = TaskStatus.STOPPED
                break

        # Final task status assignment
        if task.status == TaskStatus.RUNNING:
            all_done = all(s.status == StepStatus.COMPLETED for s in task.steps)
            task.status = TaskStatus.COMPLETED if all_done else TaskStatus.FAILED

        task.updated_at = datetime.now()
        logger.info(f"Task {task.task_id} finished with status: {task.status.value}")

        if self.on_task_finished:
            self.on_task_finished(task)

        return task

    def _register_step_undo(self, task_id: str, step: TaskStep) -> None:
        """Hooks successful modifications into the checkpoint manager."""
        if step.tool_name in ["create_file", "create_excel", "create_word", "create_presentation"]:
            path = step.parameters.get("path")
            if path:
                self.checkpoint_mgr.register_file_creation(task_id, step.step_id, path)
                step.can_undo = True

        elif step.tool_name == "move_file":
            src = step.parameters.get("source")
            dst = step.parameters.get("destination")
            if src and dst:
                self.checkpoint_mgr.register_file_move(task_id, step.step_id, src, dst)
                step.can_undo = True
