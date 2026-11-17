"""
Task Planner for NIVA.
Translates user instructions into structured execution plans composed of TaskStep items.
Integrates trained statistical NLU model with slot extractors, conversational context,
cloud LLMs (Gemini, OpenAI), and fallback parsers.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from app.ai.intent_parser import IntentParser
from app.ai.llm_provider import LLMProvider
from app.ai.nlu_engine import NLUEngine, NLUResult
from app.config import ASSISTANT_NAME
from app.core.context_manager import ContextManager
from app.core.task_state import StepStatus, Task, TaskStep
from app.tools.registry import ToolRegistry

logger = logging.getLogger(f"{ASSISTANT_NAME}.Planner")


class TaskPlanner:
    """Creates structured multi-step execution plans."""

    def __init__(self, tool_registry: ToolRegistry, llm_provider: Optional[LLMProvider] = None, context: Optional[ContextManager] = None):
        self.registry = tool_registry
        self.llm = llm_provider or LLMProvider()
        self.context = context or ContextManager()
        self.nlu = NLUEngine()

    def create_plan(self, user_prompt: str) -> Task:
        """
        Creates a new Task containing planned execution steps for user_prompt.
        """
        logger.info(f"Planning execution for user request: '{user_prompt}'")
        task = Task(user_prompt=user_prompt)

        # Contextual reference resolution (e.g., 'search python' -> 'search python in chrome')
        resolved_prompt = self.context.resolve_contextual_query(user_prompt)

        steps_dicts: Optional[List[Dict[str, Any]]] = None

        # 1. Try Cloud or Local LLM if configured
        if self.llm.is_configured():
            try:
                available_tools = self.registry.list_tools()
                context_summary = self.context.get_summary_dict()
                steps_dicts = self.llm.generate_plan(resolved_prompt, available_tools, context_summary)
            except Exception as e:
                logger.warning(f"LLM planner exception: {e}. Falling back to statistical NLU engine...")

        # 2. Trained Machine Learning NLU model
        if not steps_dicts:
            logger.info("Using trained statistical NLU engine...")
            nlu_res: NLUResult = self.nlu.parse(resolved_prompt, self.context.get_summary_dict())
            task.nlu_result = nlu_res

            if nlu_res.needs_clarification:
                task.needs_clarification = True
                task.clarification_question = nlu_res.clarification_question
                logger.info(f"NLU flagged clarification needed: '{nlu_res.clarification_question}'")
            elif not nlu_res.is_supported:
                task.unsupported_reason = nlu_res.unsupported_reason or "This operation is not supported by available computer control capabilities."
                logger.info(f"NLU flagged unsupported command: {task.unsupported_reason}")
            elif nlu_res.planned_steps:
                steps_dicts = nlu_res.planned_steps
            elif nlu_res.intent in ["conversational_greeting", "conversational_presence", "conversational_identity"]:
                logger.info(f"NLU recognized conversational intent: '{nlu_res.intent}'")
                steps_dicts = []
            else:
                # 3. Rule-based IntentParser fallback
                logger.info("Falling back to rule-based IntentParser...")
                steps_dicts = IntentParser.parse_full_request(resolved_prompt)

        # Convert dicts into TaskStep dataclasses
        if steps_dicts:
            for s in steps_dicts:
                step = TaskStep(
                    description=s.get("description", "Execute operation"),
                    tool_name=s.get("tool_name", ""),
                    parameters=s.get("parameters", {}),
                    status=StepStatus.PENDING
                )
                task.steps.append(step)
        else:
            if nlu_res and nlu_res.intent in ["conversational_greeting", "conversational_presence", "conversational_identity"]:
                task.unsupported_reason = None
            elif not task.needs_clarification and not task.unsupported_reason:
                task.unsupported_reason = f"I heard '{user_prompt}', but could not identify the matching computer action. Could you please specify which app or task you want to run?"
                logger.warning(f"No execution steps identified for: '{user_prompt}'")

        return task
