import ctypes
import time
import pywinauto

user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW("Default", 0, False, 0x0100)
user32.SetThreadDesktop(hdesk)

import win32gui
hwnds = []
win32gui.EnumWindows(lambda h, l: l.append(h) if "calculator" in win32gui.GetWindowText(h).lower() else None, hwnds)
print("Calculator HWNDs:", hwnds)

for h in hwnds:
    try:
        app = pywinauto.Application(backend="uia").connect(handle=h)
        top = app.window(handle=h)
        print(f"Top window: {top.window_text()}")
        for i, child in enumerate(top.children()):
            print(f"  Child {i}: text='{child.window_text()}', class='{child.class_name()}', id='{child.automation_id()}'")
            for j, sub in enumerate(child.children()):
                print(f"    Sub {j}: text='{sub.window_text()}', id='{sub.automation_id()}'")
                for k, leaf in enumerate(sub.children()):
                    print(f"      Leaf {k}: text='{leaf.window_text()}', id='{leaf.automation_id()}'")
    except Exception as e:
        print("Error on", h, e)
