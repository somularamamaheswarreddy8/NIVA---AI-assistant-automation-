import sys
import time
import ctypes
import win32gui
import win32con

user32 = ctypes.windll.user32
hdesk = user32.OpenInputDesktop(0, False, 0x0100) or user32.OpenDesktopW("Default", 0, False, 0x0100)
if hdesk:
    user32.SetThreadDesktop(hdesk)

hwnds = []
def enum_cb(h, _):
    if win32gui.IsWindowVisible(h) and win32gui.GetClassName(h) == "ApplicationFrameWindow" and "calculator" in win32gui.GetWindowText(h).lower():
        hwnds.append(h)

win32gui.EnumDesktopWindows(hdesk, enum_cb, None)
if hwnds:
    hwnd = hwnds[0]
    user32.ShowWindow(hwnd, win32con.SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    
    # Try keybd_event
    VK_ESCAPE = 0x1B
    VK_2 = ord('2')
    VK_ADD = 0x6B  # Numpad +
    VK_RETURN = 0x0D

    def press_key(vk):
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.02)

    t0 = time.time()
    press_key(VK_ESCAPE)
    press_key(VK_2)
    # OEM_PLUS is 0xBB (needs shift? or numpad + 0x6B)
    press_key(VK_ADD)
    press_key(VK_2)
    press_key(VK_RETURN)
    t1 = time.time()
    print(f"Key events sent in: {t1-t0:.3f}s")
    
    time.sleep(0.2)
    import pywinauto
    app = pywinauto.Application(backend="uia").connect(handle=hwnd)
    win = app.window(handle=hwnd)
    res = win.child_window(auto_id="CalculatorResults")
    print("Result text:", res.window_text())
