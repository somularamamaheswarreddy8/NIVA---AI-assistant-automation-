"""
Execution checkpoints and safe rollback/undo manager.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
import shutil
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger("NIVA.Checkpoints")


@dataclass
class CheckpointRecord:
    checkpoint_id: str
    task_id: str
    step_id: str
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    undo_action: Optional[Callable[[], bool]] = None
    undo_data: Dict[str, Any] = field(default_factory=dict)
    is_reverted: bool = False


class CheckpointManager:
    """Manages undo history and state restoration."""

    def __init__(self, max_history: int = 50):
        self._history: List[CheckpointRecord] = []
        self._max_history = max_history

    def register_file_creation(self, task_id: str, step_id: str, file_path: str) -> CheckpointRecord:
        """Register that a file was created so it can be deleted on undo."""
        def undo_func():
            try:
                if os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path, ignore_errors=True)
                    else:
                        os.remove(file_path)
                    logger.info(f"Undo: Removed created file {file_path}")
                    return True
            except Exception as e:
                logger.error(f"Undo failed for file {file_path}: {e}")
                return False
            return True

        record = CheckpointRecord(
            checkpoint_id=f"chk_{len(self._history) + 1}",
            task_id=task_id,
            step_id=step_id,
            description=f"Created file: {file_path}",
            undo_action=undo_func,
            undo_data={"action": "delete_created_file", "path": file_path}
        )
        self._add_record(record)
        return record

    def register_file_move(self, task_id: str, step_id: str, source: str, destination: str) -> CheckpointRecord:
        """Register that a file was moved so it can be moved back on undo."""
        def undo_func():
            try:
                if os.path.exists(destination):
                    os.makedirs(os.path.dirname(source), exist_ok=True)
                    shutil.move(destination, source)
                    logger.info(f"Undo: Restored file from {destination} to {source}")
                    return True
            except Exception as e:
                logger.error(f"Undo failed for move {destination} -> {source}: {e}")
                return False
            return True

        record = CheckpointRecord(
            checkpoint_id=f"chk_{len(self._history) + 1}",
            task_id=task_id,
            step_id=step_id,
            description=f"Moved file from {source} to {destination}",
            undo_action=undo_func,
            undo_data={"action": "move_back", "source": destination, "dest": source}
        )
        self._add_record(record)
        return record

    def register_custom_undo(self, task_id: str, step_id: str, description: str, undo_func: Callable[[], bool], undo_data: Optional[Dict[str, Any]] = None) -> CheckpointRecord:
        record = CheckpointRecord(
            checkpoint_id=f"chk_{len(self._history) + 1}",
            task_id=task_id,
            step_id=step_id,
            description=description,
            undo_action=undo_func,
            undo_data=undo_data or {}
        )
        self._add_record(record)
        return record

    def _add_record(self, record: CheckpointRecord) -> None:
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def undo_last(self) -> Optional[str]:
        """Revert the most recent reversible action."""
        for record in reversed(self._history):
            if not record.is_reverted and record.undo_action:
                try:
                    success = record.undo_action()
                    if success:
                        record.is_reverted = True
                        return f"Successfully reverted: {record.description}"
                    else:
                        return f"Failed to revert: {record.description}"
                except Exception as e:
                    return f"Error during undo: {e}"
        return "No reversible actions available in history."
