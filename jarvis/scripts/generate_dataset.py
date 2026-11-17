"""
Comprehensive Synthetic Dataset Generator for NIVA Voice Assistant.
Generates >= 5,000 varied command utterances across >= 100 useful intents
spanning English, Latin-script Telugu (Tanglish), and Telugu-English code-mixed phrasing.

Schema per record:
- utterance (str)
- language_mix ("en" | "te-Latn" | "te-en")
- intent (str, 1 of 111 unique intents)
- entities (dict of extracted slots)
- expected_tool (str, mapped tool in ToolRegistry)
- risk_level ("SAFE" | "MODERATE" | "SENSITIVE" | "DANGEROUS")
- requires_confirmation (bool)
- paraphrase_group (str, for group-based cross-validation)
- is_synthetic (True)
"""

import json
import os
import random
from typing import Any, Dict, List

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "niva_commands_dataset.jsonl")

# Common entities
APPS = [
    ("chrome", "Chrome", ["google chrome", "chrome browser", "chrome"]),
    ("notepad", "Notepad", ["notepad text editor", "notepad"]),
    ("calculator", "Calculator", ["calc", "calculator", "calculator app"]),
    ("vscode", "VS Code", ["vs code", "code editor", "visual studio code", "vscode"]),
    ("excel", "Excel", ["microsoft excel", "excel sheet", "excel app", "excel"]),
    ("word", "Word", ["microsoft word", "word doc", "word document", "word"]),
    ("powerpoint", "PowerPoint", ["microsoft powerpoint", "powerpoint slides", "ppt", "powerpoint"]),
    ("terminal", "Windows Terminal", ["terminal", "windows terminal", "wt"]),
    ("cmd", "Command Prompt", ["cmd", "command prompt", "console"]),
    ("powershell", "PowerShell", ["powershell terminal", "powershell"]),
    ("edge", "Microsoft Edge", ["edge browser", "ms edge", "edge"]),
    ("paint", "Paint", ["mspaint", "paint app", "paint"]),
    ("settings", "Windows Settings", ["pc settings", "windows settings", "settings"]),
    ("explorer", "File Explorer", ["file manager", "file explorer", "explorer"]),
    ("spotify", "Spotify", ["spotify music", "spotify"]),
    ("vlc", "VLC", ["vlc media player", "vlc player", "vlc"]),
]

FOLDERS = [
    "AI Projects", "College", "Final Year", "Work", "Personal", "Research",
    "Dataset", "Reports", "Submissions", "Codebase", "Downloads", "Desktop",
    "Documents", "Photos", "Invoices", "Study Materials", "Testing", "NIVA"
]

TARGET_DIRS = [
    ("Desktop", ["Desktop", "desktop meeda", "my desktop", "on desktop"]),
    ("Downloads", ["Downloads", "downloads lo", "my downloads", "in downloads"]),
    ("Documents", ["Documents", "documents lo", "my documents", "in documents"]),
]

FILE_NAMES = [
    "notes.txt", "summary.docx", "report.pdf", "data.xlsx", "todo.txt",
    "project_plan.docx", "budget.xlsx", "test.py", "main.py", "presentation.pptx",
    "script.bat", "config.json", "resume.docx", "analysis.pdf", "paper.docx"
]

SEARCH_QUERIES = [
    "Python tutorials", "machine learning basics", "best laptops in 2026",
    "data structures algorithms", "React js crash course", "Hyderabad weather today",
    "Telugu latest news", "DeepSeek vs ChatGPT", "how to build an AI agent",
    "PySide6 GUI tutorial", "Windows automation with Python", "operating systems lecture",
    "Telugu songs playlist", "IPL match highlights", "quantum computing overview"
]

SETTINGS_PAGES = [
    ("bluetooth", ["bluetooth settings", "bluetooth configuration", "bluetooth page"]),
    ("wifi", ["wifi settings", "network settings", "wifi page"]),
    ("sound", ["sound settings", "audio settings", "volume settings"]),
    ("display", ["display settings", "screen resolution settings", "monitor settings"]),
    ("windows_update", ["windows update", "system update settings", "update page"]),
    ("control_panel", ["control panel", "windows control panel"]),
    ("apps", ["installed apps", "default apps", "apps settings"]),
    ("system", ["system settings", "about pc", "device specs"]),
    ("storage", ["storage settings", "disk clean settings", "storage sense"]),
]


def make_record(utterance: str, lang: str, intent: str, entities: Dict[str, Any], tool: str, risk: str, confirm: bool, grp: str) -> Dict[str, Any]:
    return {
        "utterance": utterance.strip(),
        "language_mix": lang,
        "intent": intent,
        "entities": entities,
        "expected_tool": tool,
        "risk_level": risk,
        "requires_confirmation": confirm,
        "paraphrase_group": grp,
        "is_synthetic": True
    }


def generate_all_intents() -> List[Dict[str, Any]]:
    records = []

    # =========================================================================
    # DOMAIN 1: APPLICATION LIFECYCLE & WINDOW MANAGEMENT (15 Intents)
    # =========================================================================

    # 1. app_launch
    for app_id, app_name, aliases in APPS:
        grp = f"grp_launch_{app_id}"
        for alias in aliases:
            # English
            for t in ["open {a}", "launch {a}", "start {a}", "please open {a}", "can you launch {a}", "run {a} now"]:
                records.append(make_record(t.format(a=alias), "en", "app_launch", {"app_name": app_id}, "launch_app", "SAFE", False, grp))
            # Telugu / Code-mixed
            for t in ["{a} open chey", "{a} theeyi", "{a} open cheyyi brother", "{a} start chey ra", "{a} launch chey please", "{a} theeyi brother"]:
                records.append(make_record(t.format(a=alias), "te-en", "app_launch", {"app_name": app_id}, "launch_app", "SAFE", False, grp))

    # 2. app_close
    for app_id, app_name, aliases in APPS:
        grp = f"grp_close_{app_id}"
        for alias in aliases:
            for t in ["close {a}", "exit {a}", "quit {a}", "please close {a}", "shut down {a}"]:
                records.append(make_record(t.format(a=alias), "en", "app_close", {"app_name": app_id}, "close_app", "SAFE", False, grp))
            for t in ["{a} close chey", "{a} aapu", "{a} bandh cheyyi", "{a} moosiveyi", "{a} close cheyyara"]:
                records.append(make_record(t.format(a=alias), "te-en", "app_close", {"app_name": app_id}, "close_app", "SAFE", False, grp))

    # 3. app_kill_force
    for app_id, app_name, aliases in APPS[:6]:
        grp = f"grp_kill_{app_id}"
        for alias in aliases:
            for t in ["force kill {a}", "terminate {a} immediately", "force close {a}"]:
                records.append(make_record(t.format(a=alias), "en", "app_kill_force", {"app_name": app_id, "force": True}, "close_app", "SENSITIVE", True, grp))
            for t in ["{a} ni force close chey", "{a} kill cheyyi", "{a} process kill chey"]:
                records.append(make_record(t.format(a=alias), "te-en", "app_kill_force", {"app_name": app_id, "force": True}, "close_app", "SENSITIVE", True, grp))

    # 4. app_switch
    for app_id, app_name, aliases in APPS[:8]:
        grp = f"grp_switch_{app_id}"
        for alias in aliases:
            for t in ["switch to {a}", "bring {a} to front", "focus on {a}", "switch window to {a}"]:
                records.append(make_record(t.format(a=alias), "en", "app_switch", {"app_name": app_id}, "control_window", "SAFE", False, grp))
            for t in ["{a} ki switch avvu", "{a} window ki vellu", "{a} screen meedhaki theeyi"]:
                records.append(make_record(t.format(a=alias), "te-en", "app_switch", {"app_name": app_id}, "control_window", "SAFE", False, grp))

    # 5. app_restart
    for app_id, app_name, aliases in APPS[:6]:
        grp = f"grp_restart_{app_id}"
        for alias in aliases:
            for t in ["restart {a}", "relaunch {a}", "close and reopen {a}"]:
                records.append(make_record(t.format(a=alias), "en", "app_restart", {"app_name": app_id}, "launch_app", "SAFE", False, grp))
            for t in ["{a} restart chey", "{a} close chesi malli open chey"]:
                records.append(make_record(t.format(a=alias), "te-en", "app_restart", {"app_name": app_id}, "launch_app", "SAFE", False, grp))

    # 6. app_check_running
    for app_id, app_name, aliases in APPS[:6]:
        alias = aliases[0]
        grp = f"grp_check_running_{app_id}"
        for t in ["is {a} running", "check if {a} is open", "is {a} active right now"]:
            records.append(make_record(t.format(a=alias), "en", "app_check_running", {"app_name": app_id}, "system_info", "SAFE", False, grp))
        for t in ["{a} run avthunda", "{a} open lo unda choodu"]:
            records.append(make_record(t.format(a=alias), "te-en", "app_check_running", {"app_name": app_id}, "system_info", "SAFE", False, grp))

    # 7. window_minimize
    for t, l in [("minimize window", "en"), ("minimize this app", "en"), ("minimize current window", "en"),
                ("window minimize chey", "te-en"), ("deeni kindhaki pettu", "te-Latn"), ("minimize cheyyi", "te-en")]:
        records.append(make_record(t, l, "window_minimize", {"action": "minimize"}, "control_window", "SAFE", False, "grp_win_minimize"))

    # 8. window_maximize
    for t, l in [("maximize window", "en"), ("maximize this screen", "en"), ("make window full screen", "en"),
                ("window maximize chey", "te-en"), ("full screen cheyyi", "te-en"), ("peddadi chey window", "te-Latn")]:
        records.append(make_record(t, l, "window_maximize", {"action": "maximize"}, "control_window", "SAFE", False, "grp_win_maximize"))

    # 9. window_restore
    for t, l in [("restore window", "en"), ("unmaximize window", "en"), ("restore window size", "en"),
                ("window normal size chey", "te-en"), ("restore cheyyi", "te-en")]:
        records.append(make_record(t, l, "window_restore", {"action": "restore"}, "control_window", "SAFE", False, "grp_win_restore"))

    # 10. window_snap_left
    for t, l in [("snap window to left", "en"), ("split window left", "en"), ("dock window to the left side", "en"),
                ("left ki snap chey", "te-en"), ("window left side pettu", "te-en")]:
        records.append(make_record(t, l, "window_snap_left", {"action": "snap_left"}, "control_window", "SAFE", False, "grp_win_snap_left"))

    # 11. window_snap_right
    for t, l in [("snap window to right", "en"), ("split window right", "en"), ("dock window right side", "en"),
                ("right ki snap chey", "te-en"), ("window right side pettu", "te-en")]:
        records.append(make_record(t, l, "window_snap_right", {"action": "snap_right"}, "control_window", "SAFE", False, "grp_win_snap_right"))

    # 12. window_show_desktop
    for t, l in [("show desktop", "en"), ("minimize all windows", "en"), ("go to desktop", "en"),
                ("desktop chupinchu", "te-Latn"), ("anni minimize chesi desktop ki vellu", "te-en")]:
        records.append(make_record(t, l, "window_show_desktop", {}, "show_desktop", "SAFE", False, "grp_win_desktop"))

    # 13. window_list_running
    for t, l in [("list open windows", "en"), ("what apps are open", "en"), ("show active windows", "en"),
                ("open lo unna windows chupinchu", "te-en"), ("active apps list chey", "te-en")]:
        records.append(make_record(t, l, "window_list_running", {}, "control_window", "SAFE", False, "grp_win_list"))

    # 14. window_focus_next
    for t, l in [("switch to next window", "en"), ("alt tab", "en"), ("next app please", "en"),
                ("next window ki vellu", "te-en"), ("tarvatha window ki switch avvu", "te-en")]:
        records.append(make_record(t, l, "window_focus_next", {}, "control_window", "SAFE", False, "grp_win_next"))

    # 15. screen_lock
    for t, l in [("lock computer", "en"), ("lock screen", "en"), ("lock my pc", "en"),
                ("pc lock chey", "te-en"), ("screen lock cheyyi brother", "te-en")]:
        records.append(make_record(t, l, "screen_lock", {}, "control_window", "MODERATE", False, "grp_win_lock"))


    # =========================================================================
    # DOMAIN 2: FILE & FOLDER OPERATIONS (15 Intents)
    # =========================================================================

    # 16. folder_create
    for f in FOLDERS:
        grp = f"grp_mkdir_{f}"
        for t in [f"create a folder called {f}", f"make a new directory named {f}", f"create folder {f} on Desktop"]:
            records.append(make_record(t, "en", "folder_create", {"folder_name": f, "path": f"Desktop\\{f}"}, "create_folder", "MODERATE", False, grp))
        for t in [f"Desktop meeda {f} ane folder create chey", f"{f} folder tayaru cheyyi", f"{f} ane kotha folder pettu"]:
            records.append(make_record(t, "te-en", "folder_create", {"folder_name": f, "path": f"Desktop\\{f}"}, "create_folder", "MODERATE", False, grp))

    # 17. folder_open
    for f in ["Downloads", "Documents", "Desktop", "Pictures", "Music"]:
        grp = f"grp_open_folder_{f}"
        for t in [f"open {f} folder", f"show my {f}", f"open {f} in explorer"]:
            records.append(make_record(t, "en", "folder_open", {"folder": f}, "launch_app", "SAFE", False, grp))
        for t in [f"{f} folder open chey", f"{f} theeyi brother", f"{f} folder loki vellu"]:
            records.append(make_record(t, "te-en", "folder_open", {"folder": f}, "launch_app", "SAFE", False, grp))

    # 18. folder_delete
    for f in ["TempFolder", "OldProject", "TestDir"]:
        grp = f"grp_rmdir_{f}"
        for t in [f"delete folder {f}", f"remove directory {f}", f"delete the {f} folder"]:
            records.append(make_record(t, "en", "folder_delete", {"path": f}, "delete_file", "SENSITIVE", True, grp))
        for t in [f"{f} folder delete chey", f"{f} directory ni theesiveyi"]:
            records.append(make_record(t, "te-en", "folder_delete", {"path": f}, "delete_file", "SENSITIVE", True, grp))

    # 19. file_create
    for fn in FILE_NAMES[:6]:
        grp = f"grp_mkfile_{fn}"
        for t in [f"create a file named {fn}", f"make a new text file {fn}", f"create file {fn} on desktop"]:
            records.append(make_record(t, "en", "file_create", {"file_name": fn, "path": f"Desktop\\{fn}"}, "create_file", "MODERATE", False, grp))
        for t in [f"Desktop lo {fn} file create chey", f"{fn} ane file rayi"]:
            records.append(make_record(t, "te-en", "file_create", {"file_name": fn, "path": f"Desktop\\{fn}"}, "create_file", "MODERATE", False, grp))

    # 20. file_open
    for fn in FILE_NAMES[:6]:
        grp = f"grp_openfile_{fn}"
        for t in [f"open {fn}", f"launch {fn}", f"open the file {fn}"]:
            records.append(make_record(t, "en", "file_open", {"file_name": fn}, "read_file", "SAFE", False, grp))
        for t in [f"{fn} open chey", f"{fn} file theeyi"]:
            records.append(make_record(t, "te-en", "file_open", {"file_name": fn}, "read_file", "SAFE", False, grp))

    # 21. file_read
    for fn in FILE_NAMES[:6]:
        grp = f"grp_readfile_{fn}"
        for t in [f"read {fn}", f"read content of {fn}", f"what is inside {fn}"]:
            records.append(make_record(t, "en", "file_read", {"file_name": fn}, "read_file", "SAFE", False, grp))
        for t in [f"{fn} chaduvu", f"{fn} lo em undo cheppu"]:
            records.append(make_record(t, "te-en", "file_read", {"file_name": fn}, "read_file", "SAFE", False, grp))

    # 22. file_delete
    for fn in ["temp.txt", "scratch.log", "old_draft.docx"]:
        grp = f"grp_delfile_{fn}"
        for t in [f"delete file {fn}", f"remove {fn}", f"delete {fn} from desktop"]:
            records.append(make_record(t, "en", "file_delete", {"path": fn, "permanent": False}, "delete_file", "SENSITIVE", True, grp))
        for t in [f"{fn} delete chey", f"{fn} file ni remove cheyyi"]:
            records.append(make_record(t, "te-en", "file_delete", {"path": fn, "permanent": False}, "delete_file", "SENSITIVE", True, grp))

    # 23. file_delete_permanent
    for fn in ["shred_me.txt", "unneeded.tmp"]:
        grp = f"grp_shred_{fn}"
        for t in [f"permanently delete {fn}", f"destroy {fn} completely", f"wipe {fn} permanently"]:
            records.append(make_record(t, "en", "file_delete_permanent", {"path": fn, "permanent": True}, "delete_file", "DANGEROUS", True, grp))
        for t in [f"{fn} ni permanent ga delete chey", f"recycle bin lekunda {fn} delete cheyyi"]:
            records.append(make_record(t, "te-en", "file_delete_permanent", {"path": fn, "permanent": True}, "delete_file", "DANGEROUS", True, grp))

    # 24. file_rename
    for t, l in [("rename file old.txt to new.txt", "en"), ("change file name of data.csv to archive.csv", "en"),
                ("file peru marchu", "te-Latn"), ("old.txt ni new.txt ga rename chey", "te-en")]:
        records.append(make_record(t, l, "file_rename", {"source": "old.txt", "destination": "new.txt"}, "move_file", "MODERATE", False, "grp_rename"))

    # 25. file_move
    for t, l in [("move all PDFs from Downloads into a new folder", "en"), ("move report.pdf to Desktop", "en"),
                ("Downloads lo unna PDFs anni oka kotha folder loki move chey", "te-en"), ("file ni move chey", "te-en")]:
        records.append(make_record(t, l, "file_move", {"source": "Downloads", "destination": "Desktop"}, "move_file", "MODERATE", False, "grp_move"))

    # 26. file_copy
    for t, l in [("copy file report.docx to Documents", "en"), ("duplicate notes.txt to Desktop", "en"),
                ("report.docx ni copy cheyyi", "te-en"), ("file copy chesi desktop meeda pettu", "te-en")]:
        records.append(make_record(t, l, "file_copy", {"source": "report.docx", "destination": "Desktop"}, "move_file", "MODERATE", False, "grp_copy"))

    # 27. file_search_by_name
    for t, l in [("search for file report.docx", "en"), ("find my resume file", "en"), ("look for file budget.xlsx", "en"),
                ("resume file vetuku", "te-Latn"), ("budget.xlsx ekkada undo find chey", "te-en")]:
        records.append(make_record(t, l, "file_search_by_name", {"pattern": "*resume*"}, "search_files", "SAFE", False, "grp_search_name"))

    # 28. file_search_by_extension
    for ext in ["pdf", "docx", "xlsx", "py", "png"]:
        grp = f"grp_searchext_{ext}"
        for t in [f"find all {ext} files", f"search for *.{ext} in Downloads", f"list all {ext} documents"]:
            records.append(make_record(t, "en", "file_search_by_extension", {"pattern": f"*.{ext}"}, "search_files", "SAFE", False, grp))
        for t in [f"Downloads lo unna {ext} files anni chupinchu", f"anni {ext} files vetuku"]:
            records.append(make_record(t, "te-en", "file_search_by_extension", {"pattern": f"*.{ext}"}, "search_files", "SAFE", False, grp))

    # 29. folder_organize_by_type
    for d in ["Downloads", "Desktop", "Documents"]:
        grp = f"grp_organize_{d}"
        for t in [f"organize my {d} folder", f"clean up my {d} by file type", f"group files in {d}"]:
            records.append(make_record(t, "en", "folder_organize_by_type", {"directory": d}, "organize_folder", "MODERATE", False, grp))
        for t in [f"{d} lo unna files organize chey", f"{d} folder clean chesi categorize cheyyi"]:
            records.append(make_record(t, "te-en", "folder_organize_by_type", {"directory": d}, "organize_folder", "MODERATE", False, grp))

    # 30. file_find_duplicates
    for t, l in [("find duplicate files in Downloads", "en"), ("check for duplicate files", "en"),
                ("Downloads lo unna duplicate files vetuku", "te-en"), ("duplicates find chey", "te-en")]:
        records.append(make_record(t, l, "file_find_duplicates", {"directory": "Downloads"}, "search_files", "SAFE", False, "grp_duplicates"))


    # =========================================================================
    # DOMAIN 3: BROWSER NAVIGATION & WEB SEARCH (12 Intents)
    # =========================================================================

    # 31. browser_open_url
    for u in ["google.com", "github.com", "youtube.com", "wikipedia.org", "reddit.com"]:
        grp = f"grp_url_{u}"
        for t in [f"open website {u}", f"navigate to {u}", f"go to {u}"]:
            records.append(make_record(t, "en", "browser_open_url", {"url": u}, "browser_open", "SAFE", False, grp))
        for t in [f"{u} open chey", f"{u} website ki vellu", f"{u} theeyi browser lo"]:
            records.append(make_record(t, "te-en", "browser_open_url", {"url": u}, "browser_open", "SAFE", False, grp))

    # 32. browser_search_google
    for q in SEARCH_QUERIES:
        grp = f"grp_google_{q[:10]}"
        for t in [f"google {q}", f"search {q} on google", f"look up {q}"]:
            records.append(make_record(t, "en", "browser_search_google", {"query": q, "engine": "google"}, "browser_search", "SAFE", False, grp))
        for t in [f"google lo {q} search chey", f"{q} gurinchi google lo choodu"]:
            records.append(make_record(t, "te-en", "browser_search_google", {"query": q, "engine": "google"}, "browser_search", "SAFE", False, grp))

    # 33. browser_search_youtube
    for q in SEARCH_QUERIES:
        grp = f"grp_yt_{q[:10]}"
        for t in [f"search for {q} on youtube", f"open youtube and search {q}", f"find {q} videos on youtube"]:
            records.append(make_record(t, "en", "browser_search_youtube", {"query": q, "engine": "youtube"}, "browser_search", "SAFE", False, grp))
        for t in [f"youtube lo {q} search chey", f"youtube lo {q} pettu", f"{q} videos youtube lo vetuku"]:
            records.append(make_record(t, "te-en", "browser_search_youtube", {"query": q, "engine": "youtube"}, "browser_search", "SAFE", False, grp))

    # 34. browser_search_bing
    for q in SEARCH_QUERIES[:5]:
        grp = f"grp_bing_{q[:10]}"
        for t in [f"search {q} on bing", f"bing search {q}"]:
            records.append(make_record(t, "en", "browser_search_bing", {"query": q, "engine": "bing"}, "browser_search", "SAFE", False, grp))
        for t in [f"bing lo {q} search chey"]:
            records.append(make_record(t, "te-en", "browser_search_bing", {"query": q, "engine": "bing"}, "browser_search", "SAFE", False, grp))

    # 35. browser_new_tab
    for t, l in [("open a new tab in browser", "en"), ("new tab please", "en"), ("open another tab", "en"),
                ("kotha tab open chey", "te-Latn"), ("browser lo new tab theeyi", "te-en")]:
        records.append(make_record(t, l, "browser_new_tab", {}, "browser_open", "SAFE", False, "grp_new_tab"))

    # 36. browser_close_tab
    for t, l in [("close this tab", "en"), ("close current browser tab", "en"), ("shut this tab", "en"),
                ("ee tab close chey", "te-en"), ("tab moosiveyi", "te-Latn")]:
        records.append(make_record(t, l, "browser_close_tab", {}, "control_window", "SAFE", False, "grp_close_tab"))

    # 37. browser_switch_tab
    for t, l in [("switch tab", "en"), ("go to next tab", "en"), ("previous tab please", "en"),
                ("next tab ki vellu", "te-en"), ("tab switch cheyyi", "te-en")]:
        records.append(make_record(t, l, "browser_switch_tab", {}, "control_window", "SAFE", False, "grp_switch_tab"))

    # 38. browser_reload_page
    for t, l in [("reload page", "en"), ("refresh browser page", "en"), ("reload this website", "en"),
                ("page refresh chey", "te-en"), ("malli load cheyyi website", "te-en")]:
        records.append(make_record(t, l, "browser_reload_page", {}, "browser_open", "SAFE", False, "grp_reload"))

    # 39. browser_go_back
    for t, l in [("go back in browser", "en"), ("previous web page", "en"), ("back button", "en"),
                ("browser lo venakki vellu", "te-en"), ("back page theeyi", "te-en")]:
        records.append(make_record(t, l, "browser_go_back", {}, "press_hotkey", "SAFE", False, "grp_back"))

    # 40. browser_go_forward
    for t, l in [("go forward in browser", "en"), ("next page in history", "en"), ("forward button", "en"),
                ("mundhuki vellu browser lo", "te-Latn"), ("forward chey", "te-en")]:
        records.append(make_record(t, l, "browser_go_forward", {}, "press_hotkey", "SAFE", False, "grp_forward"))

    # 41. browser_bookmark_page
    for t, l in [("bookmark this page", "en"), ("save this website to bookmarks", "en"),
                ("ee page bookmark chey", "te-en"), ("bookmarks lo add cheyyi", "te-en")]:
        records.append(make_record(t, l, "browser_bookmark_page", {}, "press_hotkey", "SAFE", False, "grp_bookmark"))

    # 42. browser_read_page_text
    for t, l in [("read this webpage", "en"), ("summarize webpage text", "en"), ("what does this page say", "en"),
                ("ee website chaduvu", "te-en"), ("page meeda unna content cheppu", "te-en")]:
        records.append(make_record(t, l, "browser_read_page_text", {}, "browser_open", "SAFE", False, "grp_read_page"))


    # =========================================================================
    # DOMAIN 4: WINDOWS SETTINGS & HARDWARE CONTROLS (15 Intents)
    # =========================================================================

    # 43. setting_bluetooth_on
    for t, l in [("turn bluetooth on", "en"), ("enable bluetooth", "en"), ("switch on bluetooth", "en"),
                ("bluetooth on chey", "te-Latn"), ("bluetooth start cheyyi brother", "te-en"), ("bluetooth pettu", "te-Latn")]:
        records.append(make_record(t, l, "setting_bluetooth_on", {"setting": "bluetooth", "value": "on"}, "set_setting", "SAFE", False, "grp_bt_on"))

    # 44. setting_bluetooth_off
    for t, l in [("turn bluetooth off", "en"), ("disable bluetooth", "en"), ("switch off bluetooth", "en"),
                ("bluetooth off chey", "te-Latn"), ("bluetooth bandh cheyyi", "te-Latn"), ("bluetooth aapu brother", "te-en")]:
        records.append(make_record(t, l, "setting_bluetooth_off", {"setting": "bluetooth", "value": "off"}, "set_setting", "SAFE", False, "grp_bt_off"))

    # 45. setting_wifi_on
    for t, l in [("turn wifi on", "en"), ("enable wifi", "en"), ("connect to wifi", "en"),
                ("wifi on chey", "te-Latn"), ("wifi start cheyyi brother", "te-en"), ("wireless on chey", "te-en")]:
        records.append(make_record(t, l, "setting_wifi_on", {"setting": "wifi", "value": "on"}, "set_setting", "SAFE", False, "grp_wifi_on"))

    # 46. setting_wifi_off
    for t, l in [("turn wifi off", "en"), ("disable wifi", "en"), ("disconnect wifi", "en"),
                ("wifi off chey", "te-Latn"), ("wifi bandh cheyyi", "te-Latn"), ("wifi aapu", "te-Latn")]:
        records.append(make_record(t, l, "setting_wifi_off", {"setting": "wifi", "value": "off"}, "set_setting", "SAFE", False, "grp_wifi_off"))

    # 47. setting_volume_set
    for v in [20, 50, 75, 80, 100]:
        grp = f"grp_vol_{v}"
        for t in [f"set volume to {v}%", f"change volume to {v} percent", f"make volume {v}"]:
            records.append(make_record(t, "en", "setting_volume_set", {"setting": "volume", "value": v}, "set_setting", "SAFE", False, grp))
        for t in [f"volume {v} ki pettu", f"sound {v} percent chey brother"]:
            records.append(make_record(t, "te-en", "setting_volume_set", {"setting": "volume", "value": v}, "set_setting", "SAFE", False, grp))

    # 48. setting_volume_increase
    for t, l in [("increase volume", "en"), ("turn up the sound", "en"), ("make it louder", "en"),
                ("volume penchu", "te-Latn"), ("sound konchem ekkuva chey", "te-Latn"), ("sound penchara", "te-Latn")]:
        records.append(make_record(t, l, "setting_volume_increase", {"setting": "volume", "value": "up"}, "set_setting", "SAFE", False, "grp_vol_up"))

    # 49. setting_volume_decrease
    for t, l in [("decrease volume", "en"), ("turn down sound", "en"), ("make it quieter", "en"),
                ("volume tagginchu", "te-Latn"), ("sound thakkuva cheyyi", "te-Latn"), ("sound tagginchara", "te-Latn")]:
        records.append(make_record(t, l, "setting_volume_decrease", {"setting": "volume", "value": "down"}, "set_setting", "SAFE", False, "grp_vol_down"))

    # 50. setting_volume_mute
    for t, l in [("mute sound", "en"), ("mute audio", "en"), ("silence the computer", "en"),
                ("sound mute chey", "te-en"), ("mothamm silent cheyyi", "te-Latn")]:
        records.append(make_record(t, l, "setting_volume_mute", {"setting": "mute", "value": True}, "set_setting", "SAFE", False, "grp_mute"))

    # 51. setting_volume_unmute
    for t, l in [("unmute sound", "en"), ("unmute audio", "en"), ("turn sound back on", "en"),
                ("unmute chey", "te-en"), ("sound malli pettu", "te-Latn")]:
        records.append(make_record(t, l, "setting_volume_unmute", {"setting": "mute", "value": False}, "set_setting", "SAFE", False, "grp_unmute"))

    # 52. setting_brightness_set
    for b in [30, 50, 70, 90, 100]:
        grp = f"grp_bright_{b}"
        for t in [f"set brightness to {b}%", f"make brightness {b} percent"]:
            records.append(make_record(t, "en", "setting_brightness_set", {"setting": "brightness", "value": b}, "set_setting", "SAFE", False, grp))
        for t in [f"brightness {b} ki pettu", f"screen light {b} percent chey"]:
            records.append(make_record(t, "te-en", "setting_brightness_set", {"setting": "brightness", "value": b}, "set_setting", "SAFE", False, grp))

    # 53. setting_brightness_increase
    for t, l in [("increase brightness", "en"), ("make screen brighter", "en"), ("turn up screen light", "en"),
                ("brightness penchu", "te-Latn"), ("screen light ekkuva chey", "te-en")]:
        records.append(make_record(t, l, "setting_brightness_increase", {"setting": "brightness", "value": "up"}, "set_setting", "SAFE", False, "grp_bright_up"))

    # 54. setting_brightness_decrease
    for t, l in [("decrease brightness", "en"), ("dim the screen", "en"), ("lower screen brightness", "en"),
                ("brightness tagginchu", "te-Latn"), ("screen light thakkuva chey", "te-en")]:
        records.append(make_record(t, l, "setting_brightness_decrease", {"setting": "brightness", "value": "down"}, "set_setting", "SAFE", False, "grp_bright_down"))

    # 55. setting_open_sound_settings
    for t, l in [("open sound settings", "en"), ("show audio configuration page", "en"),
                ("sound settings theeyi", "te-en"), ("audio settings open chey", "te-en")]:
        records.append(make_record(t, l, "setting_open_sound_settings", {"page": "sound"}, "open_settings_page", "SAFE", False, "grp_page_sound"))

    # 56. setting_open_display_settings
    for t, l in [("open display settings", "en"), ("show screen resolution page", "en"),
                ("display settings open chey", "te-en"), ("screen settings theeyi", "te-en")]:
        records.append(make_record(t, l, "setting_open_display_settings", {"page": "display"}, "open_settings_page", "SAFE", False, "grp_page_display"))

    # 57. setting_open_network_settings
    for t, l in [("open network settings", "en"), ("show internet settings page", "en"),
                ("network settings open chey", "te-en"), ("internet settings theeyi", "te-en")]:
        records.append(make_record(t, l, "setting_open_network_settings", {"page": "wifi"}, "open_settings_page", "SAFE", False, "grp_page_network"))


    # =========================================================================
    # DOMAIN 5: SYSTEM SETTINGS PAGES & UTILITIES (10 Intents)
    # =========================================================================

    # 58. setting_open_bluetooth_page
    for t, l in [("open bluetooth settings", "en"), ("show paired bluetooth devices", "en"),
                ("bluetooth settings theeyi", "te-en"), ("bluetooth page open chey", "te-en")]:
        records.append(make_record(t, l, "setting_open_bluetooth_page", {"page": "bluetooth"}, "open_settings_page", "SAFE", False, "grp_page_bt"))

    # 59. setting_open_windows_update
    for t, l in [("open windows update", "en"), ("check for windows updates", "en"),
                ("windows update open chey", "te-en"), ("system updates theeyi", "te-en")]:
        records.append(make_record(t, l, "setting_open_windows_update", {"page": "windows_update"}, "open_settings_page", "SAFE", False, "grp_page_update"))

    # 60. setting_open_control_panel
    for t, l in [("open control panel", "en"), ("launch classic control panel", "en"),
                ("control panel theeyi", "te-en"), ("control panel open chey", "te-en")]:
        records.append(make_record(t, l, "setting_open_control_panel", {"page": "control_panel"}, "open_settings_page", "SAFE", False, "grp_page_cp"))

    # 61. setting_open_task_manager
    for t, l in [("open task manager", "en"), ("launch task manager", "en"),
                ("task manager theeyi", "te-en"), ("task manager open chey brother", "te-en")]:
        records.append(make_record(t, l, "setting_open_task_manager", {"app_name": "taskmgr"}, "launch_app", "SAFE", False, "grp_taskmgr"))

    # 62. setting_open_system_about
    for t, l in [("open system specs", "en"), ("about this pc", "en"), ("show system specifications", "en"),
                ("system details chupinchu", "te-en"), ("pc specs theeyi", "te-en")]:
        records.append(make_record(t, l, "setting_open_system_about", {"page": "system"}, "open_settings_page", "SAFE", False, "grp_page_about"))

    # 63. setting_open_default_apps
    for t, l in [("open default apps settings", "en"), ("manage default applications", "en"),
                ("default apps open chey", "te-en")]:
        records.append(make_record(t, l, "setting_open_default_apps", {"page": "apps"}, "open_settings_page", "SAFE", False, "grp_page_apps"))

    # 64. setting_open_storage_settings
    for t, l in [("open storage settings", "en"), ("show disk space settings", "en"),
                ("storage settings open chey", "te-en"), ("disk settings theeyi", "te-en")]:
        records.append(make_record(t, l, "setting_open_storage_settings", {"page": "storage"}, "open_settings_page", "SAFE", False, "grp_page_storage"))

    # 65. system_battery_status
    for t, l in [("what is my battery level", "en"), ("check battery status", "en"), ("how much charge is left", "en"),
                ("battery entha undi", "te-Latn"), ("charge entha undo choodu", "te-en")]:
        records.append(make_record(t, l, "system_battery_status", {"query_type": "battery"}, "system_info", "SAFE", False, "grp_sys_battery"))

    # 66. system_storage_status
    for t, l in [("how much free disk space is left", "en"), ("check drive storage", "en"), ("storage status", "en"),
                ("drive lo entha space undi", "te-en"), ("free disk space cheppu", "te-en")]:
        records.append(make_record(t, l, "system_storage_status", {"query_type": "storage"}, "system_info", "SAFE", False, "grp_sys_storage"))

    # 67. system_resource_usage
    for t, l in [("check cpu usage", "en"), ("what is ram consumption", "en"), ("system performance", "en"),
                ("cpu usage entha", "te-en"), ("ram entha vaaduthondi", "te-en")]:
        records.append(make_record(t, l, "system_resource_usage", {"query_type": "resources"}, "system_info", "SAFE", False, "grp_sys_resources"))


    # =========================================================================
    # DOMAIN 6: OFFICE SUITE AUTOMATION (10 Intents)
    # =========================================================================

    # 68. excel_create_sheet
    for top in ["expenses", "marks", "salaries", "budget", "sales"]:
        grp = f"grp_excel_{top}"
        for t in [f"create an excel sheet for {top}", f"make an excel spreadsheet containing {top}", f"create an excel table for {top}"]:
            records.append(make_record(t, "en", "excel_create_sheet", {"sheet_title": top}, "create_excel", "MODERATE", False, grp))
        for t in [f"excel lo {top} table pettu", f"excel lo {top} create chey", f"{top} gurinchi spreadsheet tayaru chey"]:
            records.append(make_record(t, "te-en", "excel_create_sheet", {"sheet_title": top}, "create_excel", "MODERATE", False, grp))

    # 69. excel_add_totals_formula
    for t, l in [("calculate total in excel sheet", "en"), ("add sum formula to excel table", "en"), ("compute total expenses in excel", "en"),
                ("excel lo total calculate chey", "te-en"), ("sum formula pettu excel lo", "te-en"), ("total sum cheyyi brother", "te-en")]:
        records.append(make_record(t, l, "excel_add_totals_formula", {"include_summary_row": True}, "create_excel", "MODERATE", False, "grp_excel_formula"))

    # 70. excel_format_table
    for t, l in [("format excel table with headers and borders", "en"), ("style the spreadsheet table", "en"),
                ("excel table format chey", "te-en"), ("table style cheyyi", "te-en")]:
        records.append(make_record(t, l, "excel_format_table", {}, "create_excel", "MODERATE", False, "grp_excel_format"))

    # 71. word_create_document
    for top in ["AI Project Summary", "Research Overview", "Formal Letter", "Meeting Notes"]:
        grp = f"grp_word_{top[:8]}"
        for t in [f"create a word document titled {top}", f"write a word report for {top}", f"make a docx file about {top}"]:
            records.append(make_record(t, "en", "word_create_document", {"title": top}, "create_word", "MODERATE", False, grp))
        for t in [f"word lo {top} document rayi", f"{top} gurinchi word report cheyyi"]:
            records.append(make_record(t, "te-en", "word_create_document", {"title": top}, "create_word", "MODERATE", False, grp))

    # 72. word_add_table
    for t, l in [("add a table into the word document", "en"), ("insert comparison table in word", "en"),
                ("word document lo table pettu", "te-en"), ("table insert chey word lo", "te-en")]:
        records.append(make_record(t, l, "word_add_table", {}, "create_word", "MODERATE", False, "grp_word_table"))

    # 73. word_append_notes
    for t, l in [("append summary to word document", "en"), ("add notes to existing word report", "en"),
                ("word doc lo notes add chey", "te-en"), ("document lo inkonchem rayi", "te-en")]:
        records.append(make_record(t, l, "word_append_notes", {}, "create_word", "MODERATE", False, "grp_word_append"))

    # 74. powerpoint_create_presentation
    for top in ["Artificial Intelligence", "Autonomous Systems", "Cloud Computing"]:
        grp = f"grp_ppt_{top[:6]}"
        for t in [f"create a presentation on {top}", f"generate slides for {top} in powerpoint", f"make a ppt deck on {top}"]:
            records.append(make_record(t, "en", "powerpoint_create_presentation", {"presentation_title": top}, "create_presentation", "MODERATE", False, grp))
        for t in [f"powerpoint lo {top} meeda slides chey", f"{top} gurinchi ppt tayaru chey"]:
            records.append(make_record(t, "te-en", "powerpoint_create_presentation", {"presentation_title": top}, "create_presentation", "MODERATE", False, grp))

    # 75. powerpoint_add_slide
    for t, l in [("add a new slide to presentation", "en"), ("insert bullet slide in powerpoint", "en"),
                ("kotha slide add chey ppt lo", "te-en"), ("slide pettu powerpoint lo", "te-en")]:
        records.append(make_record(t, l, "powerpoint_add_slide", {}, "create_presentation", "MODERATE", False, "grp_ppt_addslide"))

    # 76. document_convert_to_pdf
    for t, l in [("convert report to pdf", "en"), ("export document as pdf", "en"), ("save docx as pdf", "en"),
                ("document ni pdf ga export chey", "te-en"), ("pdf convert cheyyi", "te-en")]:
        records.append(make_record(t, l, "document_convert_to_pdf", {}, "create_word", "MODERATE", False, "grp_doc_pdf"))

    # 77. document_read_metadata
    for t, l in [("read document properties", "en"), ("how many pages in this report", "en"),
                ("document metadata chaduvu", "te-en"), ("enno pages undo cheppu", "te-en")]:
        records.append(make_record(t, l, "document_read_metadata", {}, "read_file", "SAFE", False, "grp_doc_meta"))


    # =========================================================================
    # DOMAIN 7: COMPUTER USE, UI AUTOMATION & PERIPHERALS (10 Intents)
    # =========================================================================

    # 78. screen_capture_full
    for t, l in [("take a screenshot", "en"), ("capture full screen", "en"), ("take desktop screenshot", "en"),
                ("screenshot theeyi", "te-Latn"), ("screen photo theeyi", "te-Latn"), ("screen capture chey", "te-en")]:
        records.append(make_record(t, l, "screen_capture_full", {"ocr": False}, "capture_screen", "SAFE", False, "grp_scr_full"))

    # 79. screen_capture_window
    for t, l in [("screenshot active window", "en"), ("capture current app window", "en"),
                ("ee window screenshot theeyi", "te-en"), ("active window capture chey", "te-en")]:
        records.append(make_record(t, l, "screen_capture_window", {}, "capture_screen", "SAFE", False, "grp_scr_win"))

    # 80. screen_ocr_read_text
    for t, l in [("read text on my screen", "en"), ("what text is on the display", "en"), ("extract text via ocr", "en"),
                ("screen meeda unna text chaduvu", "te-Latn"), ("display text decode chey", "te-en")]:
        records.append(make_record(t, l, "screen_ocr_read_text", {"ocr": True}, "capture_screen", "SAFE", False, "grp_scr_ocr"))

    # 81. mouse_click_element
    for elem in ["Save", "Cancel", "Submit", "Next", "File", "Edit"]:
        grp = f"grp_click_{elem}"
        for t in [f"click the {elem} button", f"press {elem} via UI automation", f"click on {elem}"]:
            records.append(make_record(t, "en", "mouse_click_element", {"element_name": elem}, "uia_click", "SAFE", False, grp))
        for t in [f"{elem} button meeda click chey", f"{elem} press cheyyi"]:
            records.append(make_record(t, "te-en", "mouse_click_element", {"element_name": elem}, "uia_click", "SAFE", False, grp))

    # 82. mouse_double_click
    for t, l in [("double click here", "en"), ("double click icon", "en"),
                ("double click chey", "te-en"), ("rendu sarlu click cheyyi", "te-Latn")]:
        records.append(make_record(t, l, "mouse_double_click", {"clicks": 2}, "mouse_click", "SAFE", False, "grp_double_click"))

    # 83. mouse_right_click
    for t, l in [("right click", "en"), ("open context menu with right click", "en"),
                ("right click chey", "te-en"), ("context menu open cheyyi", "te-en")]:
        records.append(make_record(t, l, "mouse_right_click", {"button": "right"}, "mouse_click", "SAFE", False, "grp_right_click"))

    # 84. keyboard_type_text
    for t, l in [("type hello world", "en"), ("type my name here", "en"), ("enter text into field", "en"),
                ("type chey text", "te-en"), ("ee text rayi", "te-en")]:
        records.append(make_record(t, l, "keyboard_type_text", {"text": "hello"}, "type_text", "SAFE", False, "grp_type"))

    # 85. keyboard_press_hotkey
    for t, l in [("press ctrl c", "en"), ("press alt tab", "en"), ("press win d", "en"), ("press ctrl v", "en"),
                ("ctrl c press chey", "te-en"), ("hotkey enter cheyyi", "te-en")]:
        records.append(make_record(t, l, "keyboard_press_hotkey", {"keys": ["ctrl", "c"]}, "press_hotkey", "SAFE", False, "grp_hotkey"))

    # 86. keyboard_scroll_down
    for t, l in [("scroll down", "en"), ("scroll the page down", "en"), ("move down", "en"),
                ("kindhaki scroll chey", "te-Latn"), ("scroll down cheyyi brother", "te-en")]:
        records.append(make_record(t, l, "keyboard_scroll_down", {"amount": -300}, "scroll", "SAFE", False, "grp_scroll_down"))

    # 87. keyboard_scroll_up
    for t, l in [("scroll up", "en"), ("scroll page upwards", "en"), ("move up", "en"),
                ("paiki scroll chey", "te-Latn"), ("scroll up cheyyi brother", "te-en")]:
        records.append(make_record(t, l, "keyboard_scroll_up", {"amount": 300}, "scroll", "SAFE", False, "grp_scroll_up"))


    # =========================================================================
    # DOMAIN 8: FORM FILLING & CLIPBOARD (6 Intents)
    # =========================================================================

    # 88. form_fill_structured
    for t, l in [("fill this form with my details", "en"), ("enter name and email into fields", "en"), ("fill out registration form", "en"),
                ("ee form fill chey", "te-en"), ("form lo details enter cheyyi", "te-en")]:
        records.append(make_record(t, l, "form_fill_structured", {"field_mappings": {}}, "fill_form", "MODERATE", False, "grp_form_fill"))

    # 89. form_clear_fields
    for t, l in [("clear form fields", "en"), ("reset the form", "en"), ("erase all inputs", "en"),
                ("form fields clear chey", "te-en"), ("mothamm erase cheyyi", "te-Latn")]:
        records.append(make_record(t, l, "form_clear_fields", {}, "fill_form", "MODERATE", False, "grp_form_clear"))

    # 90. form_submit
    for t, l in [("submit the form", "en"), ("click submit button on this page", "en"),
                ("form submit chey", "te-en"), ("application submit cheyyi brother", "te-en")]:
        records.append(make_record(t, l, "form_submit", {"submit_after_fill": True}, "fill_form", "SENSITIVE", True, "grp_form_submit"))

    # 91. clipboard_copy_selection
    for t, l in [("copy selected text", "en"), ("copy to clipboard", "en"),
                ("select chesindi copy chey", "te-en"), ("clipboard loki copy cheyyi", "te-en")]:
        records.append(make_record(t, l, "clipboard_copy_selection", {}, "press_hotkey", "SAFE", False, "grp_clip_copy"))

    # 92. clipboard_paste
    for t, l in [("paste clipboard text", "en"), ("paste here", "en"),
                ("paste chey", "te-en"), ("copy chesindi paste cheyyi", "te-en")]:
        records.append(make_record(t, l, "clipboard_paste", {}, "press_hotkey", "SAFE", False, "grp_clip_paste"))

    # 93. clipboard_read_content
    for t, l in [("what is in my clipboard", "en"), ("read clipboard text", "en"),
                ("clipboard lo em undo cheppu", "te-en")]:
        records.append(make_record(t, l, "clipboard_read_content", {}, "press_hotkey", "SAFE", False, "grp_clip_read"))


    # =========================================================================
    # DOMAIN 9: TASK INTERRUPTION, CONTROLS & PRIVACY (10 Intents)
    # =========================================================================

    # 94. interruption_stop
    stop_items = [
        ("stop", "en"), ("stop now", "en"), ("cancel this task", "en"), ("abort", "en"),
        ("don't continue", "en"), ("halt", "en"), ("terminate action", "en"), ("kill task", "en"),
        ("aapu", "te-Latn"), ("aapey", "te-Latn"), ("aagandi", "te-Latn"), ("vaddu", "te-Latn"),
        ("urgent ga aapu", "te-Latn"), ("aapey brother", "te-en"), ("stop chey", "te-en"),
        ("aapu immediate ga", "te-en"), ("pani aapeyyi", "te-Latn"), ("task cancel chey", "te-en")
    ]
    for core, lang in stop_items:
        for pre in ["", "niva ", "please ", "just "]:
            records.append(make_record(f"{pre}{core}", lang, "interruption_stop", {}, "interruption_stop", "SAFE", False, "grp_stop"))

    # 95. interruption_pause
    pause_items = [
        ("pause", "en"), ("wait a second", "en"), ("hold on", "en"), ("stand by", "en"),
        ("koncham aagu", "te-Latn"), ("konchem aagu", "te-Latn"), ("aagu", "te-Latn"), ("agandi", "te-Latn"),
        ("wait chey brother", "te-en"), ("pause chey", "te-en")
    ]
    for core, lang in pause_items:
        for pre in ["", "niva ", "please "]:
            records.append(make_record(f"{pre}{core}", lang, "interruption_pause", {}, "interruption_pause", "SAFE", False, "grp_pause"))

    # 96. interruption_resume
    resume_items = [
        ("resume", "en"), ("continue task", "en"), ("keep going", "en"), ("carry on", "en"),
        ("malli chey", "te-Latn"), ("kaniyyi", "te-Latn"), ("continue cheyyi", "te-en"),
        ("malli start chey", "te-en"), ("resume chey brother", "te-en")
    ]
    for core, lang in resume_items:
        for pre in ["", "niva ", "now "]:
            records.append(make_record(f"{pre}{core}", lang, "interruption_resume", {}, "interruption_resume", "SAFE", False, "grp_resume"))

    # 97. interruption_override
    for app in ["notepad", "calculator", "chrome", "edge"]:
        for t, l in [(f"stop open {app} instead", "en"), (f"forget that launch {app}", "en"),
                    (f"cancel that open {app} instead", "en"), (f"aapu {app} theeyi", "te-Latn"),
                    (f"adhey vaddu {app} open chey", "te-en")]:
            records.append(make_record(t, l, "interruption_override", {"new_command": f"open {app}"}, "interruption_override", "SAFE", False, f"grp_override_{app}"))

    # 98. interruption_undo
    for t, l in [("undo", "en"), ("undo that", "en"), ("revert last action", "en"), ("take it back", "en"),
                ("venakki teesko", "te-Latn"), ("undo chey", "te-en"), ("chesindi cancel cheyyi", "te-en")]:
        records.append(make_record(t, l, "interruption_undo", {}, "interruption_undo", "SAFE", False, "grp_undo"))

    # 99. system_status
    for t, l in [("what are you doing", "en"), ("status update", "en"), ("how much work remaining", "en"), ("are you finished", "en"),
                ("em chesthunnav", "te-Latn"), ("status enti", "te-en"), ("work aipoinda", "te-Latn"), ("progress cheppu niva", "te-en")]:
        records.append(make_record(t, l, "system_status", {}, "system_status", "SAFE", False, "grp_status"))

    # 100. history_clear
    for t, l in [("clear history", "en"), ("erase all task records", "en"), ("wipe dialogue history", "en"),
                ("history clear chey", "te-en"), ("mothamm records delete cheyyi", "te-en")]:
        records.append(make_record(t, l, "history_clear", {"action": "clear"}, "history_manage", "SENSITIVE", False, "grp_hist_clear"))

    # 101. history_disable
    for t, l in [("disable history storage", "en"), ("turn off conversation recording", "en"), ("don't save my history", "en"),
                ("history recording aapey", "te-en"), ("history save cheyyoddu", "te-en")]:
        records.append(make_record(t, l, "history_disable", {"action": "disable"}, "history_manage", "SAFE", False, "grp_hist_disable"))

    # 102. history_enable
    for t, l in [("enable history storage", "en"), ("turn on conversation logging", "en"),
                ("history save cheyyi", "te-en"), ("history recording on chey", "te-en")]:
        records.append(make_record(t, l, "history_enable", {"action": "enable"}, "history_manage", "SAFE", False, "grp_hist_enable"))

    # 103. system_explain_capabilities
    for t, l in [("what can you do", "en"), ("explain your capabilities", "en"), ("what features are supported", "en"),
                ("nuvvu em cheyagalao cheppu", "te-Latn"), ("supported actions enti niva", "te-en")]:
        records.append(make_record(t, l, "system_explain_capabilities", {}, "system_info", "SAFE", False, "grp_explain_caps"))


    # =========================================================================
    # DOMAIN 10: CONVERSATIONAL CONTEXT, CORRECTIONS & CLARIFICATIONS (8 Intents)
    # =========================================================================

    # 104. context_refer_previous_result
    for t, l in [("open the second result", "en"), ("click the first link", "en"), ("choose the second one", "en"),
                ("rendava result open chey", "te-Latn"), ("second link meeda click cheyyi", "te-en")]:
        records.append(make_record(t, l, "context_refer_previous_result", {"index": 2}, "browser_open", "SAFE", False, "grp_ctx_result"))

    # 105. context_specify_target_location
    for loc in ["on Desktop", "in Downloads", "inside Documents"]:
        for t, l in [(f"save it {loc}", "en"), (f"put it {loc}", "en"), (f"{loc} pettu", "te-en"), (f"{loc} save cheyyi", "te-en")]:
            records.append(make_record(t, l, "context_specify_target_location", {"target_dir": loc}, "create_file", "SAFE", False, f"grp_ctx_loc_{loc[:4]}"))

    # 106. context_correct_parameter
    for t, l in [("no make it 80 percent", "en"), ("actually set it to 50", "en"), ("correction make it chrome", "en"),
                ("kaadhu 80 pettu", "te-Latn"), ("correct chesi chrome open chey", "te-en")]:
        records.append(make_record(t, l, "context_correct_parameter", {}, "set_setting", "SAFE", False, "grp_ctx_correct"))

    # 107. context_clarify_app
    for app in ["Google Chrome", "Calculator", "Notepad", "VS Code", "Microsoft Excel"]:
        for t in [app, f"I meant {app}", f"{app} please", f"{app} app"]:
            records.append(make_record(t, "en", "context_clarify_app", {"app_name": app.lower()}, "launch_app", "SAFE", False, f"grp_clarify_{app[:4]}"))

    # 108. context_clarify_query
    for q in ["Python tutorials", "machine learning course", "weather today"]:
        for t in [q, f"I want {q}", f"about {q}", f"{q} topic"]:
            records.append(make_record(t, "en", "context_clarify_query", {"query": q}, "browser_search", "SAFE", False, f"grp_clarify_q_{q[:4]}"))

    # 109. context_confirm_yes
    for t, l in [("yes", "en"), ("yes proceed", "en"), ("confirm", "en"), ("authorize", "en"), ("go ahead", "en"),
                ("avunu", "te-Latn"), ("avunu chey", "te-Latn"), ("confirm cheyyi", "te-en"), ("sare chey", "te-Latn")]:
        records.append(make_record(t, l, "context_confirm_yes", {"confirmed": True}, "system_status", "SAFE", False, "grp_confirm_yes"))

    # 110. context_confirm_no
    for t, l in [("no", "en"), ("cancel", "en"), ("don't do it", "en"), ("deny permission", "en"),
                ("vaddu", "te-Latn"), ("kaadhu", "te-Latn"), ("aapey vaddu", "te-Latn"), ("cancel cheyyi", "te-en")]:
        records.append(make_record(t, l, "context_confirm_no", {"confirmed": False}, "system_status", "SAFE", False, "grp_confirm_no"))

    # 111. compound_multistep
    compound_samples = [
        ("Open Chrome and then open Notepad", "en"),
        ("Launch Calculator and then open VS Code", "en"),
        ("First browser open chey, tarvatha YouTube lo Python tutorials search chey", "te-en"),
        ("Desktop meeda AI folder create chesi and then open Chrome", "te-en"),
        ("Create an Excel table comparing three AI tools, calculate total, and save it", "en"),
        ("Open Chrome, search for the best AI tools, and create an Excel sheet", "en"),
        ("Downloads folder open chesi anni PDFs organize chey", "te-en"),
        ("Bluetooth off chesi sound 80 percent ki set chey", "te-en"),
        ("Take a screenshot of my screen and save it on Desktop", "en"),
        ("Open Word, write project summary report, and convert to PDF", "en"),
        ("Clean up my Desktop and organize my files by type", "en"),
        ("Excel lo ee month expenses table create chesi total calculate chey", "te-en"),
        ("Search for three AI tools, compare them, create a Word report, and save it", "en"),
        ("Open YouTube and search for Python tutorials", "en"),
    ]
    for utt, lang in compound_samples:
        records.append(make_record(utt, lang, "compound_multistep", {}, "compound_multistep", "MODERATE", False, "grp_multistep"))

    # Multiplier variations to reach >= 5,000 diverse utterances
    # Add variations with politeness markers, prefixes, and punctuation
    augmented = []
    prefixes_en = ["please ", "can you ", "could you ", "niva ", "hey niva "]
    prefixes_te = ["konchem ", "brother ", "niva ", "hey niva "]

    for r in list(records):
        utt = r["utterance"]
        lang = r["language_mix"]
        if lang == "en":
            for p in prefixes_en[:2]:
                if not utt.lower().startswith(p):
                    aug_r = dict(r)
                    aug_r["utterance"] = f"{p}{utt}".strip()
                    augmented.append(aug_r)
        elif lang in ["te-Latn", "te-en"]:
            for p in prefixes_te[:2]:
                if not utt.lower().startswith(p):
                    aug_r = dict(r)
                    aug_r["utterance"] = f"{p}{utt}".strip()
                    augmented.append(aug_r)

    records.extend(augmented)
    return records


def main():
    print("Generating comprehensive synthetic NIVA command dataset (111 intents)...")
    os.makedirs(DATA_DIR, exist_ok=True)
    records = generate_all_intents()

    # Deduplicate while preserving order
    seen = set()
    unique_records = []
    for r in records:
        key = r["utterance"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_records.append(r)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in unique_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    unique_intents = set(r["intent"] for r in unique_records)
    print(f"Total unique synthetic utterances: {len(unique_records)}")
    print(f"Total unique intents covered: {len(unique_intents)}")
    print(f"Dataset successfully saved to: {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE):,} bytes.")


if __name__ == "__main__":
    main()
