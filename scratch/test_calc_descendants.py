import ctypes
import time
import win32gui
import pywinauto

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

if calc_hwnds:
    hwnd = calc_hwnds[0]
    app = pywinauto.Application(backend="uia").connect(handle=hwnd)
    win = app.window(handle=hwnd)
    win.set_focus()
    time.sleep(0.5)

    desc = win.descendants()
    print(f"Total descendants: {len(desc)}")
    for i, d in enumerate(desc):
        try:
            aid = d.automation_id()
            txt = d.window_text()
            ct = d.element_info.control_type
            if aid or txt:
                print(f"[{i}] type={ct} | id='{aid}' | text='{txt}'")
        except Exception as e:
            pass
