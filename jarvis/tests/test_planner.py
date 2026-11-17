"""
Unit and integration tests for the JARVIS Task Planner & NLP Intent Parser.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.intent_parser import IntentParser
from app.core.planner import TaskPlanner
from app.tools.registry import ToolRegistry


class TestPlanner(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.planner = TaskPlanner(tool_registry=self.registry)

    def test_split_compound_commands(self):
        text = "Open Chrome and then open Notepad"
        clauses = IntentParser.split_compound_commands(text)
        self.assertEqual(len(clauses), 2)
        self.assertIn("open chrome", clauses[0].lower())
        self.assertIn("open notepad", clauses[1].lower())

    def test_parse_settings_bluetooth(self):
        # Bluetooth OFF
        parsed_off = IntentParser.parse_clause("Turn Bluetooth off")
        self.assertIsNotNone(parsed_off)
        self.assertEqual(parsed_off["tool_name"], "set_setting")
        self.assertEqual(parsed_off["parameters"]["setting"], "bluetooth")
        self.assertEqual(parsed_off["parameters"]["value"], "off")

        # Bluetooth ON
        parsed_on = IntentParser.parse_clause("Turn Bluetooth on")
        self.assertIsNotNone(parsed_on)
        self.assertEqual(parsed_on["tool_name"], "set_setting")
        self.assertEqual(parsed_on["parameters"]["setting"], "bluetooth")
        self.assertEqual(parsed_on["parameters"]["value"], "on")

    def test_parse_volume(self):
        parsed = IntentParser.parse_clause("Set volume to 75%")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["tool_name"], "set_setting")
        self.assertEqual(parsed["parameters"]["setting"], "volume")
        self.assertEqual(parsed["parameters"]["value"], 75)

    def test_parse_file_and_folder_creation(self):
        full_req = "Create a folder called JARVIS on my Desktop and create a text file inside it"
        steps = IntentParser.parse_full_request(full_req)
        self.assertGreaterEqual(len(steps), 2)
        self.assertEqual(steps[0]["tool_name"], "create_folder")
        self.assertIn("JARVIS", steps[0]["parameters"]["path"].upper())
        self.assertEqual(steps[1]["tool_name"], "create_file")

    def test_parse_office_excel_and_word(self):
        # Excel
        excel_step = IntentParser.parse_clause("create an Excel table, calculate the total, and save it")
        self.assertIsNotNone(excel_step)
        self.assertEqual(excel_step["tool_name"], "create_excel")
        self.assertTrue(excel_step["parameters"]["include_summary_row"])

        # Word
        word_step = IntentParser.parse_clause("create a Word report and save it")
        self.assertIsNotNone(word_step)
        self.assertEqual(word_step["tool_name"], "create_word")

    def test_telugu_english_command_planning(self):
        # "Chrome open chey"
        from app.voice.speech_to_text import SpeechToTextEngine
        normalized = SpeechToTextEngine.normalize_mixed_language("JARVIS, Chrome open chey")
        self.assertEqual(normalized, "open chrome")

        step = IntentParser.parse_clause(normalized)
        self.assertIsNotNone(step)
        self.assertEqual(step["tool_name"], "launch_app")
        self.assertEqual(step["parameters"]["app_name"], "chrome")

    def test_end_to_end_planner_task_generation(self):
        task = self.planner.create_plan("Open Chrome and then open Notepad")
        self.assertEqual(len(task.steps), 2)
        self.assertEqual(task.steps[0].tool_name, "launch_app")
        self.assertEqual(task.steps[1].tool_name, "launch_app")


if __name__ == "__main__":
    unittest.main()
