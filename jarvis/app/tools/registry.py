"""
Central Tool Registry for NIVA.
Stores tool definitions, handles parameter validation via Pydantic schemas,
and routes execution to underlying automation modules.
"""

from dataclasses import dataclass
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

from app.safety.permissions import PermissionManager
from app.safety.audit_log import AuditLogger
from app.tools import schemas

logger = logging.getLogger("NIVA.Registry")


@dataclass
class ToolDefinition:
    name: str
    description: str
    schema_cls: Type[BaseModel]
    handler: Callable[..., Any]
    category: str = "general"


class ToolRegistry:
    """Central registry and dispatch engine for all NIVA tools."""

    def __init__(self, permissions: Optional[PermissionManager] = None, audit: Optional[AuditLogger] = None):
        self._tools: Dict[str, ToolDefinition] = {}
        self.permissions = permissions or PermissionManager()
        self.audit = audit or AuditLogger()

    def register(self, name: str, description: str, schema_cls: Type[BaseModel], handler: Callable[..., Any], category: str = "general") -> None:
        """Register a new tool."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            schema_cls=schema_cls,
            handler=handler,
            category=category
        )
        self.permissions.register_allowlisted_tool(name)
        logger.debug(f"Registered tool: {name} ({category})")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools with descriptions and schema schemas."""
        result = []
        for name, tool in self._tools.items():
            result.append({
                "name": name,
                "description": tool.description,
                "category": tool.category,
                "parameters_schema": tool.schema_cls.model_json_schema()
            })
        return result

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates parameters against schema, checks permissions, executes the handler,
        and logs the outcome in audit.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            err_msg = f"Unknown tool '{tool_name}'. Available tools: {list(self._tools.keys())}"
            self.audit.log(tool_name, "unknown", params, status="FAILED", details=err_msg)
            return {"success": False, "error": err_msg}

        # Validate parameters against Pydantic schema
        try:
            validated_obj = tool.schema_cls.model_validate(params)
            validated_kwargs = validated_obj.model_dump()
        except ValidationError as e:
            err_msg = f"Parameter validation failed for tool '{tool_name}': {e}"
            self.audit.log(tool_name, "validation", params, status="FAILED", details=err_msg)
            return {"success": False, "error": err_msg}

        # Check safety permissions
        allowed, reason = self.permissions.check_permission(tool_name, validated_kwargs)
        if not allowed:
            self.audit.log(tool_name, "safety", validated_kwargs, status="BLOCKED", details=reason)
            return {"success": False, "error": f"Security restriction: {reason}", "blocked": True}

        # Execute handler
        try:
            logger.info(f"Executing tool '{tool_name}' with arguments: {validated_kwargs}")
            try:
                raw_result = tool.handler(**validated_kwargs)
            except TypeError:
                try:
                    raw_result = tool.handler(validated_obj)
                except TypeError:
                    if len(validated_kwargs) == 1:
                        raw_result = tool.handler(next(iter(validated_kwargs.values())))
                    else:
                        raise

            # Standardize return dictionary
            if isinstance(raw_result, dict):
                result = raw_result
                if "success" not in result:
                    result["success"] = True
            else:
                result = {"success": True, "result": raw_result}

            status_str = "SUCCESS" if result.get("success", False) else "FAILED"
            self.audit.log(
                tool_name,
                str(validated_kwargs.get("path") or validated_kwargs.get("app_name") or validated_kwargs.get("url") or "system"),
                validated_kwargs,
                status=status_str,
                details=str(result.get("error") or result.get("message") or "Completed")
            )
            return result

        except Exception as e:
            logger.exception(f"Exception during execution of '{tool_name}': {e}")
            self.audit.log(tool_name, "execution_error", validated_kwargs, status="FAILED", details=str(e))
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}
