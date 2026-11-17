"""
SQLite database storage for NIVA.
Stores persistent task history, dialogue context, audit events, and user settings.
Provides controls to toggle local history recording and clear history securely.
"""

from datetime import datetime
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from app.config import ASSISTANT_NAME, DATABASE_PATH, STORAGE_DIR

logger = logging.getLogger(f"{ASSISTANT_NAME}.Storage")


class Database:
    """Manages SQLite tables and transactions for NIVA."""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            os.makedirs(STORAGE_DIR, exist_ok=True)
            db_path = DATABASE_PATH
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """Create required tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step_index INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata_json TEXT
                )
            """)

            # Task Steps table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_steps (
                    step_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    description TEXT,
                    tool_name TEXT,
                    parameters_json TEXT,
                    status TEXT,
                    result_text TEXT,
                    error_text TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
                )
            """)

            # Conversation Memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context_meta TEXT
                )
            """)

            # Settings / Key-Value table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_history_enabled(self) -> bool:
        """Checks whether history storage is enabled (privacy setting)."""
        val = self.get_setting("HISTORY_ENABLED", True)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ["true", "1", "yes"]

    def set_history_enabled(self, enabled: bool) -> None:
        """Updates the privacy setting for local history retention."""
        self.set_setting("HISTORY_ENABLED", enabled)
        logger.info(f"Local history storage set to: {enabled}")

    def clear_history(self) -> Dict[str, Any]:
        """Securely clears all stored task history and dialogue records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations")
                cursor.execute("DELETE FROM task_steps")
                cursor.execute("DELETE FROM tasks")
                conn.commit()
            logger.info("Local dialogue and task history cleared successfully.")
            return {"success": True, "message": "History cleared successfully."}
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return {"success": False, "error": str(e)}

    def save_task(self, task_id: str, prompt: str, status: str, current_step_index: int = 0, total_steps: int = 0, error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not self.is_history_enabled():
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tasks (task_id, prompt, status, current_step_index, total_steps, error_message, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                prompt,
                status,
                current_step_index,
                total_steps,
                error_message,
                datetime.now().isoformat(),
                json.dumps(metadata or {})
            ))
            conn.commit()

    def update_task_status(self, task_id: str, status: str, error_message: Optional[str] = None) -> None:
        if not self.is_history_enabled():
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks
                SET status = ?, error_message = ?, completed_at = ?
                WHERE task_id = ?
            """, (status, error_message, datetime.now().isoformat(), task_id))
            conn.commit()

    def add_conversation(self, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
        if not self.is_history_enabled():
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (role, content, context_meta)
                VALUES (?, ?, ?)
            """, (role, content, json.dumps(meta or {})))
            conn.commit()

    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, created_at, context_meta
                FROM conversations
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            result = []
            for r in reversed(rows):
                result.append({
                    "role": r["role"],
                    "content": r["content"],
                    "created_at": r["created_at"],
                    "meta": json.loads(r["context_meta"] or "{}")
                })
            return result

    def set_setting(self, key: str, value: Any) -> None:
        val_str = json.dumps(value) if not isinstance(value, str) else value
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, val_str, datetime.now().isoformat()))
            conn.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default
