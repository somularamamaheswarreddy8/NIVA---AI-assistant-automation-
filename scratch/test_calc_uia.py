import subprocess
import time
import pywinauto
from pywinauto import Desktop

print("1. Launching Calculator...")
subprocess.Popen(["calc.exe"], shell=True)
time.sleep(2)

print("2. Connecting to Calculator via UIA...")
desktop = Desktop(backend="uia")
calc_win = None
for w in desktop.windows():
    try:
        t = w.window_text()
        if "calculator" in t.lower() or "calc" in t.lower():
            calc_win = w
            print(f"Found window: {t}")
            break
    except Exception as e:
        pass

if not calc_win:
    print("Could not find Calculator window!")
    exit(1)

calc_win.set_focus()
time.sleep(0.5)

print("3. Inspecting descendants...")
desc = calc_win.descendants()
print(f"Total descendants: {len(desc)}")

# Look for display elements
for d in desc:
    try:
        auto_id = d.automation_id()
        name = d.window_text()
        c_type = d.control_type()
        if any(k in auto_id.lower() for k in ["result", "display", "calculatorresults"]) or any(k in name.lower() for k in ["display is", "display"]):
            print(f"DISPLAY CANDIDATE: Name='{name}', AutomationId='{auto_id}', ControlType='{c_type}'")
    except Exception:
        pass

# Send keys 2 + 2 =
print("4. Sending keys '2+2=' ...")
calc_win.type_keys("2{+}2{=}", set_foreground=True)
time.sleep(1)

# Read display again
print("5. Reading display after calculation:")
for d in calc_win.descendants():
    try:
        auto_id = d.automation_id()
        name = d.window_text()
        if "calculatorresults" in auto_id.lower() or "display is" in name.lower():
            print(f"-> Result text: '{name}', AutomationId: '{auto_id}'")
    except Exception:
        pass
