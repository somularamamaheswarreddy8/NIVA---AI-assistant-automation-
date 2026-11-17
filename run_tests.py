"""
Comprehensive Test Runner for JARVIS.
Discovers and executes all unit and integration test suites.
"""

import os
import sys
import unittest

# Ensure jarvis package is on sys.path
workspace_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.path.abspath(".")
jarvis_dir = os.path.join(workspace_dir, "jarvis")
sys.path.insert(0, jarvis_dir)

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Import and add test modules
    import jarvis.tests.test_planner as tp
    import jarvis.tests.test_interruption as ti
    import jarvis.tests.test_safety as ts
    import jarvis.tests.test_voice as tv
    import jarvis.tests.test_files as tf
    import jarvis.tests.test_desktop as td
    import jarvis.tests.test_nlu as tn
    import jarvis.tests.test_conversational_and_verification as tcv

    suite.addTests(loader.loadTestsFromModule(tp))
    suite.addTests(loader.loadTestsFromModule(ti))
    suite.addTests(loader.loadTestsFromModule(ts))
    suite.addTests(loader.loadTestsFromModule(tv))
    suite.addTests(loader.loadTestsFromModule(tf))
    suite.addTests(loader.loadTestsFromModule(td))
    suite.addTests(loader.loadTestsFromModule(tn))
    suite.addTests(loader.loadTestsFromModule(tcv))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
