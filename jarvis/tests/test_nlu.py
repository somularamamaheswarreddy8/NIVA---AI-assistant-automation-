"""
Comprehensive tests for NIVA's statistical NLU engine, slot extractors,
multilingual Telugu-English intent classification, multi-step decomposition,
and clarification handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.nlu_engine import NLUEngine
from app.core.planner import TaskPlanner
from app.tools.registry import ToolRegistry


class TestNLUEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nlu = NLUEngine()
        cls.assertIsNotNone(cls.nlu.pipeline, "NLU model pipeline should be loaded from joblib.")

    def test_model_loaded(self):
        self.assertIsNotNone(self.nlu.pipeline)
        self.assertGreater(len(self.nlu.metadata.get("intents", [])), 20)

    def test_english_commands(self):
        cases = [
            ("Launch Google Chrome browser", "app_launch"),
            ("Close Notepad text editor", "app_close"),
            ("Search for machine learning tutorials on Google", "browser_search_google"),
            ("Create a new folder called FinalProjects on Desktop", "folder_create"),
            ("Create an Excel spreadsheet with expense data", "excel_create_sheet"),
            ("Turn Bluetooth off", "setting_bluetooth_off"),
            ("Set volume to 80 percent", "setting_volume_set"),
            ("Take a screenshot of my screen", "screen_capture_full"),
        ]
        for utterance, expected_intent in cases:
            res = self.nlu.parse(utterance)
            self.assertEqual(res.intent, expected_intent, f"Failed on: '{utterance}' (got {res.intent})")
            self.assertGreaterEqual(res.confidence, 0.40)
            self.assertTrue(len(res.planned_steps) > 0, f"No tool calls planned for: '{utterance}'")

    def test_telugu_latin_and_codemixed_commands(self):
        cases = [
            ("Chrome theeyi ra", "app_launch"),
            ("Notepad open cheyyi brother", "app_launch"),
            ("Bluetooth bandh chey", "setting_bluetooth_off"),
            ("Sound penchu", "setting_volume_increase"),
            ("Excel lo monthly expenses create chey", "excel_create_sheet"),
            ("YouTube lo Python tutorials search chey", "browser_search_youtube"),
            ("Desktop meeda AI Projects ane folder create chey", "folder_create"),
            ("Screen screenshot theeyi", "screen_capture_full"),
        ]
        for utterance, expected_intent in cases:
            res = self.nlu.parse(utterance)
            self.assertEqual(res.intent, expected_intent, f"Failed on Telugu/code-mixed: '{utterance}' (got {res.intent})")
            self.assertTrue(len(res.planned_steps) > 0, f"No tool calls planned for: '{utterance}'")

    def test_slot_extraction(self):
        # App name
        res_chrome = self.nlu.parse("Google Chrome launch chey")
        self.assertEqual(res_chrome.entities.get("app_name"), "chrome")

        res_calc = self.nlu.parse("Open calculator")
        self.assertEqual(res_calc.entities.get("app_name"), "calculator")

        # Search query and engine
        res_search = self.nlu.parse("YouTube lo Telugu songs search chey")
        self.assertEqual(res_search.entities.get("engine"), "youtube")
        self.assertIn("telugu", res_search.entities.get("query", "").lower())

        # Folder name
        res_folder = self.nlu.parse("Create a folder called TestReports on Desktop")
        self.assertIn("TestReports", res_folder.entities.get("path", ""))

        # Settings volume
        res_vol = self.nlu.parse("Volume 70% ki set chey")
        self.assertEqual(res_vol.entities.get("value"), 70)

    def test_missing_slot_clarification(self):
        # "open" without app name should ask clarification
        res = self.nlu.parse("open")
        self.assertTrue(res.needs_clarification)
        self.assertIn("Which application", res.clarification_question)

        # "search" without query should ask clarification
        res2 = self.nlu.parse("search")
        self.assertTrue(res2.needs_clarification)
        self.assertIn("search for", res2.clarification_question.lower())

    def test_low_confidence_clarification(self):
        # Gibberish string should result in low confidence clarification
        res = self.nlu.parse("xyzqqwwrr123 arbitrary nonsense gibberish")
        self.assertTrue(res.needs_clarification)

    def test_compound_multistep(self):
        res = self.nlu.parse("Open Chrome and then open Notepad")
        self.assertTrue(res.is_multistep)
        self.assertEqual(len(res.planned_steps), 2)
        self.assertEqual(res.planned_steps[0]["tool_name"], "launch_app")
        self.assertEqual(res.planned_steps[1]["tool_name"], "launch_app")

    def test_interruption_classification(self):
        res_stop = self.nlu.parse("aapu immediate ga")
        self.assertEqual(res_stop.intent, "interruption_stop")

        res_pause = self.nlu.parse("koncham aagu")
        self.assertEqual(res_pause.intent, "interruption_pause")

        res_resume = self.nlu.parse("malli chey")
        self.assertEqual(res_resume.intent, "interruption_resume")

    def test_planner_integration(self):
        registry = ToolRegistry()
        planner = TaskPlanner(tool_registry=registry)

        # 1. Normal command
        task = planner.create_plan("Chrome theeyi")
        self.assertFalse(task.needs_clarification)
        self.assertEqual(len(task.steps), 1)
        self.assertEqual(task.steps[0].tool_name, "launch_app")
        self.assertEqual(task.steps[0].parameters["app_name"], "chrome")

        # 2. Clarification command
        task_clarify = planner.create_plan("open")
        self.assertTrue(task_clarify.needs_clarification)
        self.assertIsNotNone(task_clarify.clarification_question)
        self.assertEqual(len(task_clarify.steps), 0)


if __name__ == "__main__":
    unittest.main()
