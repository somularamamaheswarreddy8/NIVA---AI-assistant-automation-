"""
Unit tests for Conversational Q&A, Task Result Verification Summaries,
and Unsupported Capability Guardrails in NIVA.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.assistant import NivaAssistant
from app.core.task_state import StepStatus, Task, TaskStatus, TaskStep


class TestConversationalAndVerification(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assistant = NivaAssistant(safe_mode=False)

    def test_conversational_identity_question(self):
        """Workflow 1: Simple conversational question returns informative answer."""
        task = self.assistant.process_command("Who are you?")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIn("NIVA", task.result_summary)
        self.assertIn("Windows", task.result_summary)

    def test_conversational_knowledge_question(self):
        """Workflow 1: Knowledge question returns accurate technical description."""
        task = self.assistant.process_command("What is Python?")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIn("Python", task.result_summary)
        self.assertIn("programming language", task.result_summary.lower())

    def test_conversational_telugu_question(self):
        """Workflow 1: Code-mixed Telugu conversational question returns Telugu response."""
        task = self.assistant.process_command("Nuvvu evaru?")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIn("NIVA", task.result_summary)
        self.assertIn("assistant", task.result_summary.lower())

    def test_unsupported_physical_actions(self):
        """Workflow 3: Physical world actions are recognized as unsupported and explained honestly."""
        unsupported_queries = [
            "Cook dinner for me",
            "Make me a cup of tea",
            "Wash the dishes",
            "Coffee ivvu",
            "Call 911",
        ]
        for query in unsupported_queries:
            task = self.assistant.process_command(query)
            self.assertEqual(task.status, TaskStatus.FAILED, f"Query '{query}' should fail")
            self.assertIsNotNone(task.unsupported_reason, f"Query '{query}' should set unsupported_reason")
            self.assertTrue(
                "cannot" in task.unsupported_reason.lower() or "not" in task.unsupported_reason.lower(),
                f"Reason for '{query}' should explain lack of physical capability"
            )

    def test_task_outcome_summary_synthesis(self):
        """Workflow 2 outcome verification: Synthesizes specific action summary instead of generic success."""
        task = Task(user_prompt="Open Notepad and type Hello Somu")
        task.steps = [
            TaskStep(
                description="Launch application 'notepad'",
                tool_name="launch_app",
                parameters={"app_name": "notepad"},
                status=StepStatus.COMPLETED,
                result="Successfully launched 'notepad'"
            ),
            TaskStep(
                description="Type text: 'Hello Somu'",
                tool_name="type_text",
                parameters={"text": "Hello Somu"},
                status=StepStatus.COMPLETED,
                result="Successfully typed 'Hello Somu'"
            )
        ]
        summary = self.assistant._generate_task_completion_summary(task)
        self.assertEqual(summary, "Done. Opened notepad and typed 'Hello Somu'.")

    def test_task_outcome_summary_single_action(self):
        """Outcome summary for single action produces concise past-tense confirmation."""
        task = Task(user_prompt="Create folder NIVA on Desktop")
        task.steps = [
            TaskStep(
                description="Create folder",
                tool_name="create_folder",
                parameters={"path": "Desktop\\NIVA"},
                status=StepStatus.COMPLETED,
                result="Created folder"
            )
        ]
        summary = self.assistant._generate_task_completion_summary(task)
        self.assertEqual(summary, "Done. Created folder 'Desktop\\NIVA'.")


if __name__ == "__main__":
    unittest.main()
