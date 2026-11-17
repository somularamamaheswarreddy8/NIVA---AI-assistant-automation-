import ctypes
import time
import win32gui
import win32con
import pyautogui

user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
if hdesk:
    user32.SetThreadDesktop(hdesk)

calc_hwnds = []
def enum_cb(h, _):
    if win32gui.IsWindowVisible(h):
        txt = win32gui.GetWindowText(h)
        if "calculator" in txt.lower():
            calc_hwnds.append(h)

win32gui.EnumWindows(enum_cb, None)
print("Found Calculator hwnds:", calc_hwnds)

if not calc_hwnds:
    print("Launching calc.exe...")
    import subprocess
    subprocess.Popen(["calc.exe"])
    time.sleep(2)
    win32gui.EnumWindows(enum_cb, None)
    print("Found Calculator hwnds after launch:", calc_hwnds)

if calc_hwnds:
    hwnd = calc_hwnds[0]
    print(f"Bringing Calculator ({hwnd}) to foreground...")
    user32.ShowWindow(hwnd, win32con.SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)

    # Press Escape to clear
    pyautogui.press('esc')
    time.sleep(0.2)
    
    # Type 2 + 2 =
    pyautogui.typewrite('2+2=', interval=0.1)
    time.sleep(0.5)
    
    # Copy result with Ctrl+C
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    
    # Read clipboard
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        print("COPIED RESULT FROM CALCULATOR CLIPBOARD:", repr(data))
    finally:
        win32clipboard.CloseClipboard()
