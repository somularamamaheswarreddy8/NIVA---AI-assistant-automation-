"""
Tests for File Explorer Control and Document Management in JARVIS.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.automation.file_manager import FileManager
from app.automation.office_automation import OfficeAutomation
from app.interruption.checkpoints import CheckpointManager


class TestFileManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="jarvis_test_files_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_folder_and_file_verification(self):
        target_folder = os.path.join(self.test_dir, "JARVIS_Subdir")
        folder_res = FileManager.create_folder(target_folder)
        self.assertTrue(folder_res["success"])
        self.assertTrue(os.path.exists(target_folder))
        self.assertTrue(os.path.isdir(target_folder))

        target_file = os.path.join(target_folder, "test_doc.txt")
        file_res = FileManager.create_file(target_file, "JARVIS autonomous verification content.")
        self.assertTrue(file_res["success"])
        self.assertTrue(os.path.exists(target_file))

        # Test reading file
        read_res = FileManager.read_file(target_file)
        self.assertTrue(read_res["success"])
        self.assertIn("JARVIS autonomous", read_res["content"])

    def test_create_and_read_excel(self):
        xlsx_path = os.path.join(self.test_dir, "test_sheet.xlsx")
        headers = ["Item", "Cost", "Quantity"]
        rows = [["Laptop", 1200, 2], ["Monitor", 300, 3]]

        res = OfficeAutomation.create_excel_sheet(
            path=xlsx_path,
            sheet_title="Inventory",
            headers=headers,
            rows=rows,
            include_summary_row=True
        )
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(xlsx_path))

        # Read back
        read_res = FileManager.read_file(xlsx_path)
        self.assertTrue(read_res["success"])
        self.assertGreaterEqual(len(read_res["content"]), 2)

    def test_create_word_document(self):
        docx_path = os.path.join(self.test_dir, "test_doc.docx")
        res = OfficeAutomation.create_word_document(
            path=docx_path,
            title="JARVIS Research Report",
            paragraphs=["Paragraph 1: Testing autonomous agent docx generation.", "Paragraph 2: Results confirmed."]
        )
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(docx_path))

        read_res = FileManager.read_file(docx_path)
        self.assertTrue(read_res["success"])
        self.assertIn("Testing autonomous agent", read_res["content"])

    def test_undo_file_creation(self):
        chk_mgr = CheckpointManager()
        temp_file = os.path.join(self.test_dir, "undo_me.txt")
        FileManager.create_file(temp_file, "Temporary")
        self.assertTrue(os.path.exists(temp_file))

        chk_mgr.register_file_creation("task_1", "step_1", temp_file)
        undo_msg = chk_mgr.undo_last()
        self.assertIn("Successfully reverted", undo_msg)
        self.assertFalse(os.path.exists(temp_file))


if __name__ == "__main__":
    unittest.main()
