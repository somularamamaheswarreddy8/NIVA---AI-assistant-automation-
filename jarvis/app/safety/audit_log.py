"""
Action Audit Logger for NIVA.
Maintains persistent, timestamped logs of all autonomous actions taken on the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NIVA.Audit")


@dataclass
class AuditEntry:
    timestamp: datetime = field(default_factory=datetime.now)
    action_type: str = ""
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "SUCCESS"  # SUCCESS, FAILED, BLOCKED, CANCELLED
    details: str = ""
    user_confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "status": self.status,
            "details": self.details,
            "user_confirmed": self.user_confirmed,
        }


class AuditLogger:
    """Manages appending and querying action audit records."""

    def __init__(self, log_file: Optional[str] = None):
        if not log_file:
            log_dir = os.path.join(os.path.expanduser("~"), ".niva")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "jarvis_audit.jsonl")
        self.log_file = log_file
        self._memory_entries: List[AuditEntry] = []

    def log(
        self,
        action_type: str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        details: str = "",
        user_confirmed: bool = False,
    ) -> AuditEntry:
        """Record an action in the audit log."""
        entry = AuditEntry(
            action_type=action_type,
            target=target,
            parameters=parameters or {},
            status=status,
            details=details,
            user_confirmed=user_confirmed,
        )
        self._memory_entries.append(entry)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed writing audit log to file: {e}")

        logger.info(f"AUDIT [{entry.status}]: {entry.action_type} -> {entry.target} ({entry.details})")
        return entry

    def get_recent(self, limit: int = 20) -> List[AuditEntry]:
        """Returns the most recent entries."""
        return self._memory_entries[-limit:]
