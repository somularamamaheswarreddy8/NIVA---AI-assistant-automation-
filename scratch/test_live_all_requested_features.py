"""
Live Machine Verification for all NIVA Target Workflows:
1. Contextual Calculator: "Open Calculator" -> "Add 2+2" -> Verify display is 4.
2. Natural math queries: "What is 15 times 6?", "subtract 8 from 20", "divide 24 by 3".
3. Bluetooth control: "Turn Bluetooth off" -> verify Windows reports Off.
4. Bluetooth control: "Turn Bluetooth on" -> verify Windows reports On.
5. Volume control: "Increase the volume.", "Decrease the volume.", "Set the volume to 40 percent.", "Mute", "Unmute".
6. Brightness control: "Set brightness to 60 percent.", "Increase brightness.", "Decrease brightness."
7. Limitation reporting: Verify unsupported hardware/driver queries report honest limitations.
"""

import sys
import time
sys.path.insert(0, 'jarvis')

from app.core.assistant import NivaAssistant
from app.core.task_state import TaskStatus
from app.automation.windows_settings import WindowsSettingsController as WSC

print("=" * 70)
print("STARTING LIVE NIVA WORKFLOW VERIFICATION ON WINDOWS LAPTOP")
print("=" * 70)

assistant = NivaAssistant(safe_mode=False)

def run_test(prompt: str, timeout: float = 25.0):
    print(f"\n[COMMAND] -> \"{prompt}\"")
    t0 = time.time()
    task = assistant.process_command(prompt)
    assistant.wait_for_task(timeout=timeout)
    t1 = time.time()
    
    print(f"  Status: {task.status.value}")
    print(f"  Summary: {task.result_summary}")
    for i, step in enumerate(task.steps):
        print(f"  Step {i}: tool={step.tool_name}, status={step.status.value}, result={step.result}, error={step.error}")
    print(f"  Elapsed: {t1-t0:.2f}s")
    assert task.status == TaskStatus.COMPLETED, f"Task '{prompt}' failed with status {task.status}: {task.error_message}"
    return task

results = []

# -------------------------------------------------------------
# Workflow 1: "Open Calculator" -> "Add 2+2" (Verify displayed 4)
# -------------------------------------------------------------
print("\n>>> TESTING WORKFLOW 1: Open Calculator -> Add 2+2")
t1 = run_test("Open Calculator", timeout=15)
assert assistant.context.active_application == "calculator", f"Expected active app 'calculator', got '{assistant.context.active_application}'"

t2 = run_test("Add 2+2", timeout=25)
calc_step = t2.steps[0]
assert "4" in str(calc_step.result) or "4" in str(t2.result_summary), f"Expected 4 in result, got {calc_step.result}"
print(">>> WORKFLOW 1 PASSED: Displayed 4 verified in Calculator app!")
results.append(("Workflow 1: Open Calculator -> Add 2+2 (Display 4)", True))

# -------------------------------------------------------------
# Additional Math Queries
# -------------------------------------------------------------
print("\n>>> TESTING NATURAL MATH QUERIES")
tm1 = run_test("What is 15 times 6?", timeout=15)
assert "90" in str(tm1.steps[0].result) or "90" in str(tm1.result_summary)
print(">>> 'What is 15 times 6?' PASSED: Result 90")

tm2 = run_test("subtract 8 from 20", timeout=15)
assert "12" in str(tm2.steps[0].result) or "12" in str(tm2.result_summary)
print(">>> 'subtract 8 from 20' PASSED: Result 12")

tm3 = run_test("divide 24 by 3", timeout=15)
assert "8" in str(tm3.steps[0].result) or "8" in str(tm3.result_summary)
print(">>> 'divide 24 by 3' PASSED: Result 8")
results.append(("Natural Math Queries: 15*6, 20-8, 24/3", True))

# -------------------------------------------------------------
# Workflow 2: Turn Bluetooth Off -> Verify Windows reports Off
# -------------------------------------------------------------
print("\n>>> TESTING WORKFLOW 2: Turn Bluetooth off")
t_btoff = run_test("Turn Bluetooth off", timeout=15)
actual_bt = WSC.get_bluetooth_state()
print(f"Windows reported Bluetooth state: '{actual_bt}'")
assert actual_bt.lower() == "off", f"Expected Bluetooth Off, got '{actual_bt}'"
print(">>> WORKFLOW 2 PASSED: Bluetooth is Off and verified via WinRT!")
results.append(("Workflow 2: Turn Bluetooth off (Verified Off)", True))

# -------------------------------------------------------------
# Workflow 3: Turn Bluetooth On -> Verify Windows reports On
# -------------------------------------------------------------
print("\n>>> TESTING WORKFLOW 3: Turn Bluetooth on")
t_bton = run_test("Turn Bluetooth on", timeout=15)
actual_bt2 = WSC.get_bluetooth_state()
print(f"Windows reported Bluetooth state: '{actual_bt2}'")
assert actual_bt2.lower() == "on", f"Expected Bluetooth On, got '{actual_bt2}'"
print(">>> WORKFLOW 3 PASSED: Bluetooth is On and verified via WinRT!")
results.append(("Workflow 3: Turn Bluetooth on (Verified On)", True))

# -------------------------------------------------------------
# Workflow 4: Volume Control (Increase, Decrease, Set, Mute, Unmute)
# -------------------------------------------------------------
print("\n>>> TESTING WORKFLOW 4: System Volume & Mute Controls")
init_vol = WSC.get_volume()
print(f"Initial system volume: {init_vol}%")

t_v_set = run_test("Set the volume to 40 percent.", timeout=15)
v40 = WSC.get_volume()
print(f"Verified system volume: {v40}%")
assert abs(v40 - 40) <= 2, f"Expected 40%, got {v40}%"

t_v_inc = run_test("Increase the volume.", timeout=15)
v_inc = WSC.get_volume()
print(f"Verified volume after increase (+10%): {v_inc}%")
assert v_inc > v40, f"Expected volume to increase from {v40}%, got {v_inc}%"

t_v_dec = run_test("Decrease the volume.", timeout=15)
v_dec = WSC.get_volume()
print(f"Verified volume after decrease (-10%): {v_dec}%")
assert v_dec < v_inc, f"Expected volume to decrease from {v_inc}%, got {v_dec}%"

t_mute = run_test("Mute", timeout=15)
assert WSC.get_mute() is True, "Expected audio to be muted"

t_unmute = run_test("Unmute.", timeout=15)
assert WSC.get_mute() is False, "Expected audio to be unmuted"

# Restore original volume
if init_vol is not None:
    WSC.set_volume(init_vol)
print(">>> WORKFLOW 4 PASSED: Volume set, increase, decrease, mute, unmute all verified!")
results.append(("Workflow 4: Volume & Mute Controls (Verified CoreAudio)", True))

# -------------------------------------------------------------
# Workflow 5: Brightness Control (Set to 60%, verify, restore)
# -------------------------------------------------------------
print("\n>>> TESTING WORKFLOW 5: Display Brightness Controls")
init_b = WSC.get_brightness()
print(f"Initial display brightness: {init_b}%")

t_b60 = run_test("Set brightness to 60 percent.", timeout=15)
b60 = WSC.get_brightness()
print(f"Verified display brightness: {b60}%")
assert b60 == 60, f"Expected 60%, got {b60}%"

t_b_inc = run_test("Increase brightness.", timeout=15)
b_inc = WSC.get_brightness()
print(f"Verified brightness after increase (+10%): {b_inc}%")
assert b_inc == 70 or b_inc > b60, f"Expected >60%, got {b_inc}%"

t_b_dec = run_test("Decrease brightness.", timeout=15)
b_dec = WSC.get_brightness()
print(f"Verified brightness after decrease (-10%): {b_dec}%")
assert b_dec < b_inc, f"Expected <{b_inc}%, got {b_dec}%"

# Restore initial
if init_b is not None:
    WSC.set_brightness(init_b)
print(">>> WORKFLOW 5 PASSED: Brightness set, increase, decrease verified via WMI!")
results.append(("Workflow 5: Brightness Controls (Verified WMI)", True))

# -------------------------------------------------------------
# Workflow 6: Limitation Reporting for Unsupported Actions
# -------------------------------------------------------------
print("\n>>> TESTING WORKFLOW 6: Honest Limitation Reporting")
t_unsupported = assistant.process_command("Order a pizza for me right now")
assistant.wait_for_task(timeout=10)
print(f"Unsupported status: {t_unsupported.status.value}, reason: {t_unsupported.unsupported_reason or t_unsupported.error_message}")
assert t_unsupported.status in [TaskStatus.FAILED, TaskStatus.AWAITING_CONFIRMATION] or t_unsupported.unsupported_reason is not None
print(">>> WORKFLOW 6 PASSED: Unsupported action reported limitation honestly!")
results.append(("Workflow 6: Limitation Reporting (No false claims)", True))

print("\n" + "=" * 70)
print("SUMMARY OF LIVE WORKFLOW VERIFICATION:")
for name, passed in results:
    print(f"  [PASS] {name}" if passed else f"  [FAIL] {name}")
print("=" * 70)
