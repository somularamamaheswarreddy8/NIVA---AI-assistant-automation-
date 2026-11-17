import sys
import time
import ctypes
import re
import win32gui
import win32con
import pywinauto

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
if hdesk:
    user32.SetThreadDesktop(hdesk)

hwnds = []
def enum_cb(h, _):
    if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "ApplicationFrameWindow" and "calculator" in win32gui.GetWindowText(h).lower():
        hwnds.append(h)

win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
if not hwnds:
    print("Calculator window not found!")
    sys.exit(1)

hwnd = hwnds[0]
user32.ShowWindow(hwnd, win32con.SW_RESTORE)
user32.SetForegroundWindow(hwnd)
time.sleep(0.3)

app = pywinauto.Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
res_ctrl = win.child_window(auto_id="CalculatorResults")

VK_MAP = {
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    '+': 0x6B,
    '-': 0x6D,
    '*': 0x6A,
    '/': 0x6F,
    '.': 0x6E,
    '=': 0x0D,
}

def press_vk(vk):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.01)
    user32.keybd_event(vk, 0, 2, 0)
    time.sleep(0.01)

def calc_expr(expr):
    press_vk(0x1B) # Esc
    time.sleep(0.05)
    for ch in expr:
        if ch in VK_MAP:
            press_vk(VK_MAP[ch])
        elif ch == ' ':
            continue
    press_vk(0x0D) # Enter / Equals
    time.sleep(0.15)
    raw = res_ctrl.window_text()
    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", raw.replace(",", ""))
    val = float(m.group(0)) if "." in m.group(0) else int(m.group(0))
    return val, raw

tests = ["2+2", "15*6", "20-8", "24/3", "3.5+2.5"]
for t in tests:
    t0 = time.time()
    val, raw = calc_expr(t)
    t1 = time.time()
    print(f"Expr: {t} -> Result: {val} (raw: '{raw}') in {t1-t0:.3f}s")
