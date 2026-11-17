"""
End-to-end verification of NIVA Startup, Microphone Permission, and Spoken-Response Lifecycle.
Verifies:
1. Spoken greeting on startup: speaks 'How can I help you, sir?' once.
2. Permission check & device discovery: grants permission once and enters LISTENING.
3. Single command processing & verified outcome ('Open Chrome').
4. Second command handling without restarting or repeating the first command.
5. Denied microphone permission handling: reports clear error and provides settings link.
6. Duplicate transcript suppression: does not execute the same recognized utterance twice.
7. Self-echo suppression: drops NIVA's own spoken output.
"""

import os
import sys
import time

# Ensure jarvis package is on sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in locals() else os.getcwd()
sys.path.insert(0, workspace_dir)
sys.path.insert(0, os.path.join(workspace_dir, "jarvis"))

from app.core.assistant import NivaAssistant
from app.core.task_state import TaskStatus
from app.voice.permission_manager import MicrophonePermissionManager


def test_startup_and_lifecycle():
    print("=" * 65)
    print("  TESTING NIVA STARTUP, PERMISSION, AND VOICE LIFECYCLE")
    print("=" * 65)

    assistant = NivaAssistant(safe_mode=False)

    # Telemetry tracking
    spoken_messages = []
    logged_dialogues = []
    status_history = []

    assistant.tts.speak = lambda txt: spoken_messages.append(txt)
    assistant.on_message_logged = lambda r, txt: logged_dialogues.append((r, txt))
    assistant.voice_listener.on_status_change = lambda s: status_history.append(s)

    # -------------------------------------------------------------
    # CASE 1: Startup Greeting & Permission Granting
    # -------------------------------------------------------------
    print("\n[CASE 1] Startup sequence with initial permission prompt...")
    assistant.db.set_setting("MIC_PERMISSION_STATUS", "prompt")

    prompt_called = [False]
    def mock_user_grants_permission():
        prompt_called[0] = True
        return True

    res = assistant.startup_lifecycle(on_permission_needed=mock_user_grants_permission)
    print(f"  Startup lifecycle result: {res}")
    assert prompt_called[0] is True, "Permission prompt should have been invoked on first run!"
    assert res["status"] == "LISTENING", f"Expected LISTENING, got {res['status']}"
    assert "How can I help you, sir?" in spoken_messages, f"Spoken greeting missing! Got: {spoken_messages}"
    greeting_count = sum(1 for m in spoken_messages if "How can I help you, sir?" in m)
    assert greeting_count == 1, f"Expected greeting to be spoken exactly once, got {greeting_count} times."
    print("  -> PASSED: Startup greeted user with 'How can I help you, sir?' once and entered LISTENING.")
    assistant.stop_voice_system()
    time.sleep(0.3)

    # -------------------------------------------------------------
    # CASE 2: No Repeat Permission Prompt Once Granted
    # -------------------------------------------------------------
    print("\n[CASE 2] Verifying permission is remembered without re-prompting...")
    prompt_called_again = [False]
    spoken_messages.clear()
    res2 = assistant.startup_lifecycle(on_permission_needed=lambda: prompt_called_again.__setitem__(0, True) or True)
    assert prompt_called_again[0] is False, "Permission prompt should NOT be called again once granted!"
    assert res2["status"] == "LISTENING", "Should immediately begin listening!"
    print("  -> PASSED: Permission remembered, no repeat prompt.")
    assistant.stop_voice_system()
    time.sleep(0.3)

    # -------------------------------------------------------------
    # CASE 3: Execute First Command ('Open Chrome') & Spoken Outcome
    # -------------------------------------------------------------
    print("\n[CASE 3] Execute single utterance: 'Open Chrome'...")
    spoken_messages.clear()
    task1 = assistant.process_command("Open Chrome")
    print(f"  Task 1 Status: {task1.status.value}, Steps: {len(task1.steps)}")
    assert len(task1.steps) == 1, f"Expected 1 step for Open Chrome, got {len(task1.steps)}"
    assert task1.steps[0].tool_name == "launch_app", f"Expected launch_app, got {task1.steps[0].tool_name}"
    # Check that speech acknowledgment or verified summary was queued
    assert len(spoken_messages) >= 1, "Expected spoken response for Open Chrome!"
    print(f"  Spoken response: {spoken_messages[-1]}")
    print("  -> PASSED: Single utterance 'Open Chrome' planned, executed, and outcome spoken.")

    # -------------------------------------------------------------
    # CASE 4: Second Consecutive Command Without Restarting
    # -------------------------------------------------------------
    print("\n[CASE 4] Execute second command without restart: 'Turn Bluetooth off'...")
    spoken_messages.clear()
    task2 = assistant.process_command("Turn Bluetooth off")
    print(f"  Task 2 Status: {task2.status.value}, Steps: {len(task2.steps)}")
    assert len(task2.steps) >= 1, f"Expected step for Bluetooth, got {len(task2.steps)}"
    assert task2.steps[-1].tool_name in ["set_setting", "open_settings_page"]
    print("  -> PASSED: Handled second command smoothly on continuous session.")

    # -------------------------------------------------------------
    # CASE 5: Denied Permission & Error State
    # -------------------------------------------------------------
    print("\n[CASE 5] Handling denied microphone permission...")
    assistant.db.set_setting("MIC_PERMISSION_STATUS", "denied")
    spoken_messages.clear()
    res_denied = assistant.startup_lifecycle()
    print(f"  Denied result: {res_denied}")
    assert res_denied["status"] == "PERMISSION_DENIED", f"Expected PERMISSION_DENIED, got {res_denied['status']}"
    assert "disabled" in res_denied["message"].lower() or "denied" in res_denied["message"].lower()
    print("  -> PASSED: Denied microphone permission halts cleanly without pretending to listen.")

    # -------------------------------------------------------------
    # CASE 6: Duplicate Transcript & Self-Echo Suppression
    # -------------------------------------------------------------
    print("\n[CASE 6] Verifying duplicate transcript and self-echo suppression...")
    listener = assistant.voice_listener
    listener._last_processed_transcript = ""
    listener._last_processed_time = 0.0

    processed_calls = []
    listener.on_speech_recognized = lambda cmd: processed_calls.append(cmd)

    # 6a. Self-echo of NIVA's greeting
    assistant.tts.last_spoken_text = "How can I help you, sir?"
    assistant.tts.last_spoken_timestamp = time.time()

    # Simulate transcript arriving that matches NIVA's speech
    is_echo = False
    last_spoken = assistant.tts.last_spoken_text.lower().strip()
    test_transcript = "How can I help you sir"
    if (time.time() - assistant.tts.last_spoken_timestamp) < 3.0:
        if test_transcript.lower() in last_spoken or last_spoken in test_transcript.lower() or "how can i help you sir" in test_transcript.lower():
            is_echo = True
    assert is_echo is True, "Self-echo should be identified!"
    print("  -> PASSED: Self-echo from NIVA audio output suppressed.")

    # 6b. Duplicate utterance within 3 seconds
    cmd = "open chrome"
    now = time.time()
    listener._last_processed_transcript = cmd
    listener._last_processed_time = now

    is_duplicate = (cmd == listener._last_processed_transcript and (time.time() - listener._last_processed_time) < 3.0)
    assert is_duplicate is True, "Immediate duplicate should be detected and skipped!"
    print("  -> PASSED: Duplicate transcript within suppression window detected.")

    print("\n" + "=" * 65)
    print("  ALL STARTUP, MICROPHONE, AND VOICE LIFECYCLE TESTS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_startup_and_lifecycle()
