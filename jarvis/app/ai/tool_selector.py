"""
Tool Selector for NIVA.
Discovers and matches planned actions against active tool registrations.
"""

from typing import Any, Dict, List, Optional
from app.tools.registry import ToolRegistry


class ToolSelector:
    """Matches tool names and schemas to execution requests."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def select_tool(self, tool_name: str) -> Optional[Any]:
        return self.registry.get_tool(tool_name)

    def validate_tool_availability(self, required_tool_name: str) -> bool:
        return self.registry.get_tool(required_tool_name) is not None
