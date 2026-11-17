import sys
import os

sys.path.insert(0, os.path.join(os.getcwd(), 'jarvis'))

from app.core.assistant import NivaAssistant
from app.voice.wake_word import WakeWordDetector
from app.voice.listener import VoiceListener

assistant = NivaAssistant()

print("=== 1. WAKE WORD TEST ===")
detector = WakeWordDetector(enabled=True)
is_only = detector.is_wake_word_only("NIVA")
triggered, cmd = detector.check_wake_word("NIVA, open Chrome")
print(f"Wake word alone is_wake_word_only('NIVA'): {is_only}")
print(f"check_wake_word('NIVA, open Chrome'): triggered={triggered}, cmd='{cmd}'")
assert is_only is True, "Wake word alone should be detected"
assert triggered is True and cmd.lower() == "open chrome", f"Wake word + command failed: {cmd}"

greeting_resp = assistant._answer_conversational_question("NIVA")
print(f"Assistant response to wake word: '{greeting_resp}'")
assert greeting_resp == "How can I help you, sir?", f"Unexpected wake reply: {greeting_resp}"

print("\n=== 2. YOUTUBE SEARCH & PLAY SECOND VIDEO ===")
task_yt = assistant.process_command("Search YouTube for Python tutorials and play the second video")
print(f"Task steps ({len(task_yt.steps)}):")
for s in task_yt.steps:
    print(f"  - {s.tool_name}: {s.parameters}")
assert len(task_yt.steps) == 2, f"Expected 2 steps, got {len(task_yt.steps)}"
assert task_yt.steps[0].tool_name == "browser_search"
assert "play" not in task_yt.steps[0].parameters.get("query", "").lower(), "Query contained trailing instruction"
assert task_yt.steps[1].tool_name == "browser_open_result"
assert task_yt.steps[1].parameters.get("result_index") == 2

print("\n=== 3. CONTEXTUAL FOLLOW-UP ('OK NOW') ===")
assistant.context.last_search_query = "Python tutorials"
assistant.context.last_search_engine = "youtube"
ok_now_resp = assistant._answer_conversational_question("ok now")
print(f"Response to 'ok now': '{ok_now_resp}'")
assert "Which application" not in ok_now_resp, "NIVA asked which app to open!"
assert "Python tutorials" in ok_now_resp, "NIVA did not reference search context"

print("\n=== 4. WINDOWS SETTINGS ===")
task_sett = assistant.process_command("Open Settings and turn Bluetooth off")
print(f"Task steps ({len(task_sett.steps)}):")
for s in task_sett.steps:
    print(f"  - {s.tool_name}: {s.parameters}")
assert len(task_sett.steps) == 2, f"Expected 2 steps, got {len(task_sett.steps)}"
assert task_sett.steps[0].tool_name == "open_settings_page"
assert task_sett.steps[1].tool_name == "set_setting"

print("\n=== 5. CLICK ACCESSIBLE ELEMENT ===")
task_click = assistant.process_command("Click the search button")
print(f"Task steps ({len(task_click.steps)}):")
for s in task_click.steps:
    print(f"  - {s.tool_name}: {s.parameters}")
assert len(task_click.steps) == 1
assert task_click.steps[0].tool_name == "uia_click"
assert task_click.steps[0].parameters.get("element_name") == "Search"

print("\n=== 6. ORDINAL SEARCH RESULT FOLLOW-UP ===")
task_ord = assistant.process_command("Open the third result")
print(f"Task steps ({len(task_ord.steps)}):")
for s in task_ord.steps:
    print(f"  - {s.tool_name}: {s.parameters}")
assert len(task_ord.steps) == 1
assert task_ord.steps[0].tool_name == "browser_open_result"
assert task_ord.steps[0].parameters.get("result_index") == 3

print("\nALL 6 VERIFICATION TEST CASES PASSED PERFECTLY!")
