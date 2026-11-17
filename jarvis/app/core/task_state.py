"""
Task state management, step definitions, and status enums for JARVIS.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class TaskStatus(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class TaskStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    can_undo: bool = False
    undo_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "status": self.status.value,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "can_undo": self.can_undo,
        }


@dataclass
class Checkpoint:
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_index: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    screen_state: Optional[str] = None
    active_window: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_prompt: str = ""
    steps: List[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    status: TaskStatus = TaskStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    checkpoints: List[Checkpoint] = field(default_factory=list)
    error_message: Optional[str] = None
    cancellation_requested: bool = False
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    unsupported_reason: Optional[str] = None
    nlu_result: Optional[Any] = None
    result_summary: Optional[str] = None

    @property
    def progress_percentage(self) -> int:
        if not self.steps:
            return 0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return int((completed / len(self.steps)) * 100)

    @property
    def current_step(self) -> Optional[TaskStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def add_checkpoint(self, active_window: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        cp = Checkpoint(
            step_index=self.current_step_index,
            active_window=active_window,
            metadata=metadata or {}
        )
        self.checkpoints.append(cp)
        return cp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_prompt": self.user_prompt,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "progress_percentage": self.progress_percentage,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "unsupported_reason": self.unsupported_reason,
        }
