"""
Context and Memory Manager for NIVA.
Tracks active tasks, conversation history, recent entities (files, applications, URLs),
and window state to support multi-turn commands.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from app.storage.database import Database

logger = logging.getLogger("NIVA.Context")


@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)


class ContextManager:
    """
    Maintains conversational memory and system state across user turns.
    Enables reference resolution like 'open the second result' or 'search Python tutorials'.
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.turns: List[ConversationTurn] = []
        # Current entity state
        self.active_application: Optional[str] = None
        self.active_window_title: Optional[str] = None
        self.last_touched_file: Optional[str] = None
        self.last_search_query: Optional[str] = None
        self.last_browser_url: Optional[str] = None
        self.recent_search_results: List[str] = []
        self.active_planning_session: Optional[Dict[str, Any]] = None
        self.custom_variables: Dict[str, Any] = {}

    def start_planning_session(self, session_type: str, data: Dict[str, Any]) -> None:
        self.active_planning_session = {"type": session_type, **data}

    def clear_planning_session(self) -> None:
        self.active_planning_session = None

    def get_planning_session(self) -> Optional[Dict[str, Any]]:
        return self.active_planning_session

    def add_user_message(self, text: str, intent: Optional[str] = None) -> None:
        turn = ConversationTurn(role="user", text=text, intent=intent)
        self.turns.append(turn)
        self.db.add_conversation("user", text, {"intent": intent})

    def add_assistant_message(self, text: str, tools_used: Optional[List[str]] = None) -> None:
        turn = ConversationTurn(role="assistant", text=text, tools_used=tools_used or [])
        self.turns.append(turn)
        self.db.add_conversation("assistant", text, {"tools": tools_used or []})

    def update_active_app(self, app_name: str, window_title: Optional[str] = None) -> None:
        self.active_application = app_name
        if window_title:
            self.active_window_title = window_title
        logger.debug(f"Context: Active application updated to '{app_name}'")

    def update_last_file(self, file_path: str) -> None:
        self.last_touched_file = file_path
        logger.debug(f"Context: Last touched file updated to '{file_path}'")

    def update_search_context(self, query: str, results: Optional[List[str]] = None) -> None:
        self.last_search_query = query
        if results:
            self.recent_search_results = results
        logger.debug(f"Context: Search context updated for query '{query}'")

    def get_conversation_history(self, limit: int = 6) -> List[Dict[str, str]]:
        recent = self.turns[-limit:]
        return [{"role": t.role, "content": t.text} for t in recent]

    @staticmethod
    def _extract_result_index(text: str) -> Optional[int]:
        import re
        ord_map = {
            "first": 1, "1st": 1, "one": 1, "1": 1,
            "second": 2, "2nd": 2, "two": 2, "2": 2,
            "third": 3, "3rd": 3, "three": 3, "3": 3,
            "fourth": 4, "4th": 4, "four": 4, "4": 4,
            "fifth": 5, "5th": 5, "five": 5, "5": 5,
            "sixth": 6, "6th": 6, "6": 6,
        }
        m = re.search(r"(?:open|play|click|watch|navigate\s+to)\s+(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|sixth|6th|\d+)(?:st|nd|rd|th)?\s+(?:video|result|link|song)", text, re.IGNORECASE)
        if m:
            val = m.group(1).lower()
            return ord_map.get(val, int(val) if val.isdigit() else 1)
        m2 = re.search(r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|\d+)(?:st|nd|rd|th)?\s+(?:video|result|link)\b", text, re.IGNORECASE)
        if m2:
            val = m2.group(1).lower()
            return ord_map.get(val, int(val) if val.isdigit() else 1)
        m3 = re.search(r"(?:open|play|click|watch|navigate\s+to)?\s*(?:the\s+)?(?:result|video|link)\s*#?\s*(\d+)", text.strip(), re.IGNORECASE)
        if m3:
            return int(m3.group(1))
        return None

    def resolve_contextual_query(self, prompt: str) -> str:
        """
        Resolves implicit context in short follow-up prompts.
        e.g., if active_application is Chrome and prompt is 'search python', returns explicit intent.
        """
        import re
        p_lower = prompt.lower().strip()

        # Follow-up: 'open the second result' / 'click the 3rd video'
        # Do not override compound instructions that contain multiple action clauses
        if not re.search(r"\b(?:and|then|after that|chesi|tharuvatha)\b", p_lower):
            idx = self._extract_result_index(p_lower)
            if idx is not None:
                return prompt

        # Follow-up: 'search X' without specifying browser
        if (p_lower.startswith("search ") or p_lower.startswith("find ")) and self.active_application in ["chrome", "edge", "browser"]:
            if "youtube" in str(self.last_browser_url or "").lower() or getattr(self, "last_search_engine", "") == "youtube":
                return f"{prompt} on youtube"
            return f"{prompt} in {self.active_application}"

        return prompt

    def get_summary_dict(self) -> Dict[str, Any]:
        return {
            "active_application": self.active_application,
            "active_window_title": self.active_window_title,
            "last_touched_file": self.last_touched_file,
            "last_search_query": self.last_search_query,
            "last_browser_url": self.last_browser_url,
            "last_search_engine": getattr(self, "last_search_engine", "youtube" if "youtube" in str(self.last_browser_url or "").lower() else "google"),
            "recent_turns_count": len(self.turns)
        }
