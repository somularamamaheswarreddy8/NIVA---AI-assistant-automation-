import sys
import time
sys.path.insert(0, 'jarvis')
import win32gui, ctypes, pywinauto
from app.automation.calculator_automation import CalculatorAutomation

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
if hdesk:
    user32.SetThreadDesktop(hdesk)

t0 = time.time()
hwnd = CalculatorAutomation.find_calculator_window(auto_launch=False)
t1 = time.time()
print(f"find_calculator_window took: {t1-t0:.3f}s, hwnd={hwnd}")

app = pywinauto.Application(backend="uia").connect(handle=hwnd)
t2 = time.time()
print(f"pywinauto connect took: {t2-t1:.3f}s")

win = app.window(handle=hwnd)
t3 = time.time()
print(f"app.window took: {t3-t2:.3f}s")

btn = win.child_window(auto_id="clearButton")
btn.invoke()
t4 = time.time()
print(f"clearButton invoke took: {t4-t3:.3f}s")

btn2 = win.child_window(auto_id="num2Button")
btn2.invoke()
t5 = time.time()
print(f"num2Button invoke took: {t5-t4:.3f}s")

btnp = win.child_window(auto_id="plusButton")
btnp.invoke()
t6 = time.time()
print(f"plusButton invoke took: {t6-t5:.3f}s")

btn2.invoke()
t7 = time.time()
print(f"second num2Button invoke took: {t7-t6:.3f}s")

btneq = win.child_window(auto_id="equalButton")
btneq.invoke()
t8 = time.time()
print(f"equalButton invoke took: {t8-t7:.3f}s")

res = win.child_window(auto_id="CalculatorResults")
txt = res.window_text()
t9 = time.time()
print(f"read CalculatorResults took: {t9-t8:.3f}s, text='{txt}'")
