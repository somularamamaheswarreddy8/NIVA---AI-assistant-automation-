"""
Live Verification of New Interactive & In-App Capabilities:
1. Multi-turn trip planning dialogue:
   - "plan a trip for seven days" -> asks for missing info (destination, people, budget)
   - "We are 4 people going to Goa with 50000 budget" -> generates itinerary, creates file on Desktop, opens it!
2. In-app settings navigation:
   - "open the brightness section of the laptop" -> opens ms-settings:display, brings to foreground, reports verified outcome.
   - "open the sound section" -> opens ms-settings:sound, brings to foreground.
   - When settings is active: "bluetooth" -> navigates to ms-settings:bluetooth.
"""

import os
import sys
import time
sys.path.insert(0, 'jarvis')

from app.core.assistant import NivaAssistant
from app.core.task_state import TaskStatus

print("=" * 70)
print("TESTING INTERACTIVE TRIP PLANNING & IN-APP SETTINGS NAVIGATION")
print("=" * 70)

assistant = NivaAssistant(safe_mode=False)

# -------------------------------------------------------------
# Test 1: Trip Planning Multi-Turn Interaction
# -------------------------------------------------------------
print("\n>>> TEST 1: Trip Planning Initiation")
prompt1 = "plan a trip for seven days"
t1 = assistant.process_command(prompt1)
print("  Status:", t1.status.value)
print("  Needs Clarification:", t1.needs_clarification)
print("  Question Asked:", t1.clarification_question)
assert t1.needs_clarification is True
assert "destination" in t1.clarification_question.lower()
assert "people" in t1.clarification_question.lower() or "how many" in t1.clarification_question.lower()
assert "budget" in t1.clarification_question.lower()
print("  -> PASSED: Successfully asked for destination, people count, and budget!")

print("\n>>> TEST 2: Trip Planning Slot-Filling Follow-Up")
prompt2 = "We are 4 people going to Goa with 50000 budget"
t2 = assistant.process_command(prompt2)
print("  Status:", t2.status.value)
print("  Summary:", t2.result_summary)
assert t2.status == TaskStatus.COMPLETED
assert "Goa" in t2.result_summary
assert "4" in t2.result_summary
assert "50,000" in t2.result_summary

# Verify itinerary file on Desktop
desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
itin_file = os.path.join(desktop_dir, "Trip_Itinerary_Goa.txt")
print("  Checking itinerary file on disk:", itin_file)
assert os.path.exists(itin_file), f"Expected file to exist: {itin_file}"
with open(itin_file, "r", encoding="utf-8") as f:
    content = f.read()
    assert "7-DAY TRIP ITINERARY: GOA" in content
    assert "Day 1:" in content
    assert "Day 7:" in content
    assert "ESTIMATED BUDGET BREAKDOWN:" in content
print(f"  -> PASSED: Itinerary document created and verified ({len(content)} bytes)!")

# -------------------------------------------------------------
# Test 3: In-App Settings Section Navigation (Brightness)
# -------------------------------------------------------------
print("\n>>> TEST 3: 'open the brightness section of the laptop'")
prompt3 = "open the brightness section of the laptop"
t3 = assistant.process_command(prompt3)
assistant.wait_for_task(timeout=10)
print("  Status:", t3.status.value)
print("  Summary:", t3.result_summary)
assert t3.status == TaskStatus.COMPLETED
assert "brightness" in t3.result_summary.lower() or "display" in t3.result_summary.lower()
print("  -> PASSED: Successfully navigated to Brightness section in Settings!")

# -------------------------------------------------------------
# Test 4: In-App Settings Section Navigation (Sound)
# -------------------------------------------------------------
print("\n>>> TEST 4: 'open the sound section'")
prompt4 = "open the sound section"
t4 = assistant.process_command(prompt4)
assistant.wait_for_task(timeout=10)
print("  Status:", t4.status.value)
print("  Summary:", t4.result_summary)
assert t4.status == TaskStatus.COMPLETED
assert "sound" in t4.result_summary.lower()
print("  -> PASSED: Successfully navigated to Sound section in Settings!")

# -------------------------------------------------------------
# Test 5: Contextual In-App Navigation when Settings is active
# -------------------------------------------------------------
print("\n>>> TEST 5: Contextual navigation 'bluetooth' while in Settings")
assistant.context.update_active_app("settings", "Settings")
prompt5 = "bluetooth"
t5 = assistant.process_command(prompt5)
assistant.wait_for_task(timeout=10)
print("  Status:", t5.status.value)
print("  Summary:", t5.result_summary)
assert t5.status == TaskStatus.COMPLETED
assert "bluetooth" in t5.result_summary.lower()
print("  -> PASSED: Successfully navigated to Bluetooth section while in Settings!")

print("\n" + "=" * 70)
print("ALL NEW INTERACTIVE & IN-APP CAPABILITIES VERIFIED SUCCESSFULLY!")
print("=" * 70)
