import sys
sys.path.insert(0, 'jarvis')
import time
import win32gui, ctypes, pywinauto

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
if hdesk:
    user32.SetThreadDesktop(hdesk)

from app.automation.calculator_automation import CalculatorAutomation
hwnd = CalculatorAutomation.find_calculator_window(auto_launch=True)

app = pywinauto.Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)

t0 = time.time()
# Single descendants traversal:
controls = {}
for ctrl in win.descendants():
    try:
        aid = ctrl.automation_id()
        if aid:
            controls[aid] = ctrl
    except Exception:
        pass
t1 = time.time()
print(f"Descendants traversal took: {t1-t0:.3f}s. Found {len(controls)} controls.")

# Now invoke using cached controls:
t2 = time.time()
controls['clearButton'].invoke()
controls['num2Button'].invoke()
controls['plusButton'].invoke()
controls['num2Button'].invoke()
controls['equalButton'].invoke()
t3 = time.time()
print(f"5 button invokes took: {t3-t2:.3f}s")

res = controls['CalculatorResults'].window_text()
print(f"Result text: '{res}'")
