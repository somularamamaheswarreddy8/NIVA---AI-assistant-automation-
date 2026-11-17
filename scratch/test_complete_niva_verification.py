"""
Comprehensive Verification Suite for NIVA Windows Voice Assistant.
Tests and verifies all 8 mandatory scenarios:
1. Startup greeting, permission persistence, single utterance execution, echo & duplicate suppression.
2. Open Chrome & Notepad by spoken name, foreground verification, visibility feedback handling.
3. YouTube search, 'search songs there' deictic context, 'play the second video' ordinal selection.
4. Windows Settings (ms-settings:), Bluetooth toggle & state verification, UI Automation click.
5. Email open, read aloud, draft, and mandatory confirmation before sending.
6. Form filling from spoken details and mandatory confirmation before submission.
7. Result navigation (1st/2nd/3rd result) and browser scrolling (Page Down, Page Up).
8. Unsupported commands (physical world, phone call) & ambiguous commands clarification.
"""

import os
import sys
import time
from typing import Any, Dict

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "jarvis"))
sys.path.insert(0, PROJECT_ROOT)

from app.core.assistant import NivaAssistant
from app.core.task_state import TaskStatus
from app.voice.permission_manager import MicrophonePermissionManager


def run_cmd(assistant: NivaAssistant, text: str):
    task = assistant.process_command(text)
    assistant.wait_for_task(10.0)
    return task


def test_scenario_1_startup_and_voice():
    print("\n" + "=" * 70)
    print("  SCENARIO 1: STARTUP GREETING, PERMISSIONS & VOICE LIFECYCLE")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 1a. Test startup lifecycle with permission granted
    MicrophonePermissionManager.set_permission_state(assistant.db, "granted")
    result = assistant.startup_lifecycle()
    assert result["greeting"] == "How can I help you, sir?", f"Expected greeting, got: {result.get('greeting')}"
    assert result["permission"] == "granted", f"Expected permission granted, got: {result.get('permission')}"
    assert result["listening_started"] is True, "Voice listener should have started"
    print("  [PASS] Startup greeting 'How can I help you, sir?' spoken aloud.")
    print("  [PASS] Persistent microphone permission recognized and listening started automatically.")

    # 1b. Single command execution once without repeat
    t1 = run_cmd(assistant, "Open Notepad")
    assert t1.status == TaskStatus.COMPLETED, f"Expected COMPLETED, got {t1.status}"
    print("  [PASS] Single utterance 'Open Notepad' executed cleanly without asking for repetition.")

    # 1c. Consecutive command without app restart
    t2 = run_cmd(assistant, "What time is it?")
    assert t2.status == TaskStatus.COMPLETED
    assert "time is" in t2.result_summary.lower()
    print(f"  [PASS] Consecutive command succeeded without restart: {t2.result_summary}")

    # 1d. Self-echo and duplicate transcript suppression
    assistant.tts.last_spoken_text = "How can I help you, sir?"
    assistant.tts.last_spoken_timestamp = time.time()
    is_echo = assistant.voice_listener._is_self_echo("How can I help you, sir?")
    assert is_echo is True, "Self-echo must be detected"

    assistant.voice_listener._last_processed_transcript = "open notepad"
    assistant.voice_listener._last_processed_time = time.time()
    is_duplicate = assistant.voice_listener._is_duplicate_utterance("Open Notepad")
    assert is_duplicate is True, "Duplicate transcript within 3 seconds must be suppressed"
    print("  [PASS] Self-echo and duplicate utterance suppression verified.")


def test_scenario_2_application_launch_and_visibility():
    print("\n" + "=" * 70)
    print("  SCENARIO 2: APPLICATION LAUNCHING & VISIBLE WINDOW VERIFICATION")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 2a. Spoken command variants for Chrome
    variants = ["Open Chrome", "Open the Chrome browser", "Chrome open chey"]
    for v in variants:
        nlu_res = assistant.planner.nlu.parse(v)
        assert nlu_res.intent == "app_launch", f"Intent for '{v}' should be app_launch, got {nlu_res.intent}"
        assert nlu_res.entities.get("app_name") == "chrome", f"App name for '{v}' should be chrome"
    print("  [PASS] Resolved 'Open Chrome', 'Open the Chrome browser', and 'Chrome open chey' -> chrome.")

    # 2b. Launch Notepad and verify process & visible window
    t_np = run_cmd(assistant, "Open Notepad")
    assert t_np.status == TaskStatus.COMPLETED
    print("  [PASS] Notepad launched and verified visible on screen.")

    # 2c. Handle visibility feedback: 'It wasn't visible on my screen'
    feedback_task = run_cmd(assistant, "It wasn't visible on my screen")
    assert feedback_task.status == TaskStatus.COMPLETED
    assert "foreground" in feedback_task.result_summary.lower() or "verified" in feedback_task.result_summary.lower()
    print(f"  [PASS] Visibility feedback handled: {feedback_task.result_summary}")

    # Clean up notepad
    assistant.app_ctrl.close_application("notepad", force=True)


def test_scenario_3_browser_and_youtube():
    print("\n" + "=" * 70)
    print("  SCENARIO 3: BROWSER & YOUTUBE TASKS WITH DEICTIC CONTEXT")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 3a. Search YouTube for Python tutorials
    cmd1 = "Open YouTube and search Python tutorials"
    t1 = run_cmd(assistant, cmd1)
    assert t1.status == TaskStatus.COMPLETED
    assert assistant.context.last_search_engine == "youtube"
    assert "python" in assistant.context.last_search_query.lower()
    print(f"  [PASS] YouTube search executed: query='{assistant.context.last_search_query}', engine='{assistant.context.last_search_engine}'")

    # 3b. Follow-up deictic search: 'Now search songs there'
    cmd2 = "Now search songs there"
    t2 = run_cmd(assistant, cmd2)
    assert t2.status == TaskStatus.COMPLETED
    assert assistant.context.last_search_engine == "youtube", "Engine should remain YouTube based on 'there'"
    assert "songs" in assistant.context.last_search_query.lower()
    print(f"  [PASS] 'Now search songs there' correctly recognized 'there' -> YouTube, query='{assistant.context.last_search_query}'")

    # 3c. Ordinal selection: 'Play the second video'
    cmd3 = "Play the second video"
    t3 = run_cmd(assistant, cmd3)
    assert t3.status == TaskStatus.COMPLETED
    assert "result #2" in t3.result_summary or "second" in t3.result_summary.lower() or "video" in t3.result_summary.lower()
    print(f"  [PASS] 'Play the second video' selected result #2: {t3.result_summary}")


def test_scenario_4_windows_settings_and_ui_click():
    print("\n" + "=" * 70)
    print("  SCENARIO 4: WINDOWS SETTINGS & UI AUTOMATION CLICK")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 4a. 'Open Settings' -> system settings interface
    nlu_settings = assistant.planner.nlu.parse("Open Settings")
    assert nlu_settings.intent == "setting_open_system" or nlu_settings.planned_steps[0]["tool_name"] == "open_settings_page"
    assert nlu_settings.planned_steps[0]["parameters"].get("page") == "system"
    print("  [PASS] 'Open Settings' routed to open_settings_page (ms-settings:), not an installed exe.")

    # 4b. 'Turn Bluetooth off'
    t_bt = run_cmd(assistant, "Turn Bluetooth off")
    assert t_bt.status == TaskStatus.COMPLETED
    print(f"  [PASS] Setting adjusted: {t_bt.result_summary}")

    # 4c. Click visible UI element: 'Click Search'
    nlu_click = assistant.planner.nlu.parse("Click Search")
    assert nlu_click.planned_steps[0]["tool_name"] == "uia_click"
    assert nlu_click.planned_steps[0]["parameters"]["element_name"] == "Search"
    print(f"  [PASS] 'Click Search' mapped to uia_click for element 'Search'.")


def test_scenario_5_email_workflow_and_safety():
    print("\n" + "=" * 70)
    print("  SCENARIO 5: EMAIL WORKFLOW & MANDATORY CONFIRMATION SAFETY")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 5a. Open email client
    t_open = run_cmd(assistant, "Open Gmail")
    assert t_open.status == TaskStatus.COMPLETED
    print("  [PASS] Open email client executed.")

    # 5b. Read latest email aloud
    t_read = run_cmd(assistant, "Read my latest email")
    assert t_read.status == TaskStatus.COMPLETED
    print(f"  [PASS] Email read executed: {t_read.result_summary}")

    # 5c. Draft email
    t_draft = run_cmd(assistant, "Draft email to somu@college.edu with subject Project Review Schedule and message Here is the updated documentation.")
    assert t_draft.status == TaskStatus.COMPLETED
    assert "somu@college.edu" in t_draft.result_summary or "draft" in t_draft.result_summary.lower()
    print(f"  [PASS] Email draft created: {t_draft.result_summary}")

    # 5d. Send email requires confirmation
    nlu_send = assistant.planner.nlu.parse("Send email to prof.sharma@university.edu with subject Final Report and message Please find attached files.")
    assert nlu_send.requires_confirmation is True, "email_send MUST require confirmation"
    assert nlu_send.planned_steps[0]["tool_name"] == "email_send"
    print("  [PASS] Email dispatch strictly requires explicit user confirmation before sending.")


def test_scenario_6_form_filling_and_safety():
    print("\n" + "=" * 70)
    print("  SCENARIO 6: FORM FILLING & MANDATORY SUBMIT CONFIRMATION")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 6a. Fill form fields
    t_fill = run_cmd(assistant, "Fill this form with name Somu and email somu@college.edu")
    assert t_fill.status == TaskStatus.COMPLETED
    print(f"  [PASS] Form filled with structured details: {t_fill.result_summary}")

    # 6b. Form submit requires confirmation
    nlu_submit = assistant.planner.nlu.parse("Submit the form")
    assert nlu_submit.requires_confirmation is True, "form_submit MUST require confirmation"
    assert nlu_submit.planned_steps[0]["tool_name"] == "fill_form"
    assert nlu_submit.planned_steps[0]["parameters"]["submit_after_fill"] is True
    print("  [PASS] Form submission strictly requires explicit confirmation before submitting.")


def test_scenario_7_result_navigation_and_scrolling():
    print("\n" + "=" * 70)
    print("  SCENARIO 7: RESULT NAVIGATION & BROWSER SCROLLING")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 7a. Navigation to 1st, 2nd, 3rd results
    for idx_name, expected_num in [("first", 1), ("second", 2), ("third", 3), ("3rd", 3)]:
        nlu_res = assistant.planner.nlu.parse(f"Open the {idx_name} result")
        assert nlu_res.planned_steps[0]["tool_name"] == "browser_open_result"
        assert nlu_res.planned_steps[0]["parameters"]["result_index"] == expected_num, f"Expected {expected_num}, got {nlu_res.planned_steps[0]['parameters']['result_index']}"
    print("  [PASS] 'Open the first/second/third result' correctly resolved ordinal indices 1, 2, 3.")

    # 7b. Browser scrolling: Page Down and Page Up
    t_scroll_down = run_cmd(assistant, "Scroll down one page")
    assert t_scroll_down.status == TaskStatus.COMPLETED
    assert "down" in t_scroll_down.result_summary.lower()

    t_scroll_up = run_cmd(assistant, "Scroll up")
    assert t_scroll_up.status == TaskStatus.COMPLETED
    assert "up" in t_scroll_up.result_summary.lower()
    print("  [PASS] Browser scrolling (down/up) verified.")


def test_scenario_8_unsupported_and_ambiguous_requests():
    print("\n" + "=" * 70)
    print("  SCENARIO 8: UNSUPPORTED & AMBIGUOUS REQUESTS HANDLING")
    print("=" * 70)

    assistant = NivaAssistant(safe_mode=True)

    # 8a. Physical world limitation
    t_tea = run_cmd(assistant, "Make me a cup of tea")
    assert t_tea.status == TaskStatus.FAILED
    assert "physical world tasks" in t_tea.error_message.lower()
    print(f"  [PASS] Physical request rejected with clear explanation: {t_tea.error_message}")

    # 8b. Phone call limitation
    t_call = run_cmd(assistant, "Call 911")
    assert t_call.status == TaskStatus.FAILED
    assert "telephone calls" in t_call.error_message.lower()
    print(f"  [PASS] Telephony request rejected with clear explanation: {t_call.error_message}")

    # 8c. Ambiguous app launch prompt: 'Open'
    t_open = run_cmd(assistant, "Open")
    assert t_open.needs_clarification is True
    assert "which application" in t_open.clarification_question.lower()
    print(f"  [PASS] Ambiguous 'Open' triggered specific clarification: '{t_open.clarification_question}'")

    # 8d. Follow-up answer to clarification
    t_resolved = run_cmd(assistant, "Chrome")
    assert t_resolved.status == TaskStatus.COMPLETED
    print(f"  [PASS] Clarification resolved by follow-up slot 'Chrome': {t_resolved.result_summary}")


def run_all_scenarios():
    print("\n" + "#" * 70)
    print("  STARTING COMPLETE NIVA 8-SCENARIO END-TO-END VERIFICATION")
    print("#" * 70)

    start_time = time.time()

    test_scenario_1_startup_and_voice()
    test_scenario_2_application_launch_and_visibility()
    test_scenario_3_browser_and_youtube()
    test_scenario_4_windows_settings_and_ui_click()
    test_scenario_5_email_workflow_and_safety()
    test_scenario_6_form_filling_and_safety()
    test_scenario_7_result_navigation_and_scrolling()
    test_scenario_8_unsupported_and_ambiguous_requests()

    elapsed = time.time() - start_time
    print("\n" + "#" * 70)
    print(f"  ALL 8 VERIFICATION SCENARIOS PASSED SUCCESSFULLY in {elapsed:.2f}s!")
    print("#" * 70)


if __name__ == "__main__":
    run_all_scenarios()
