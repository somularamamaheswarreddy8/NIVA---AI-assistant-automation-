"""
20,000+ Command Dataset Generator for NIVA Autonomous Agent.
Generates richly varied, synthetically labeled command utterances covering English,
Telugu-English code-mixed (te-en), and colloquial Telugu-Latin (te-Latn) speech.

Categories covered:
1. Application launching and closing (Windows installed apps, Start Menu, aliases)
2. Browser and YouTube tasks (search, search follow-ups with 'there', video playback)
3. Ordinal search result navigation (first, second, third, etc.)
4. Browser page scrolling (page down, page up, scroll down one page)
5. Email tasks (reading, drafting, sending with confirmation)
6. Form filling and data entry (with confirmation on submission)
7. Windows Settings (Bluetooth, Wi-Fi, volume, brightness, mute)
8. Visible UI clicking (accessible UI Automation elements, buttons, links)
9. Interruption & control (STOP, PAUSE, RESUME, OVERRIDE, UNDO)
10. Conversational greetings, presence checks, and identity
"""

import json
import os
import random

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "niva_commands_dataset.jsonl")


def generate_20k_dataset():
    print("Generating comprehensive 20,000+ command dataset for NIVA...")

    records = []
    # Read existing records if any
    existing_utterances = set()
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        records.append(data)
                        existing_utterances.add(data["utterance"].lower().strip())
                    except Exception:
                        pass
    print(f"Loaded {len(records)} existing records from dataset.")

    def add_rec(utt, lang, intent, entities, tool, risk="SAFE", req_confirm=False, grp="grp_cmd"):
        clean_u = utt.strip()
        if clean_u.lower() in existing_utterances or not clean_u:
            return
        existing_utterances.add(clean_u.lower())
        records.append({
            "utterance": clean_u,
            "language_mix": lang,
            "intent": intent,
            "entities": entities,
            "expected_tool": tool,
            "risk_level": risk,
            "requires_confirmation": req_confirm,
            "paraphrase_group": grp,
            "is_synthetic": True,
            "data_source": "synthetic_niva_augmented_v2"
        })

    # Vocabulary & Template Components
    prefixes_en = ["", "please ", "can you ", "niva ", "hey niva ", "ok niva ", "i want you to ", "could you ", "assist me to "]
    prefixes_te = ["", "niva ", "konchem ", "please ", "urgent ga ", "ventane ", "dayachesi "]
    suffixes_en = ["", " now", " for me", " please", " right now"]
    suffixes_te = ["", " ra", " brother", " tondaraga", " ventane"]

    apps = [
        ("chrome", "launch_app", "Google Chrome", ["chrome", "google chrome", "the browser", "chrome browser", "googlechrome"]),
        ("notepad", "launch_app", "Notepad", ["notepad", "text editor", "note pad", "notepad app"]),
        ("calculator", "launch_app", "Calculator", ["calculator", "calc", "calculator app", "math calculator"]),
        ("vscode", "launch_app", "Visual Studio Code", ["vscode", "vs code", "code", "visual studio code", "code editor"]),
        ("excel", "launch_app", "Microsoft Excel", ["excel", "microsoft excel", "excel sheet", "spreadsheet"]),
        ("word", "launch_app", "Microsoft Word", ["word", "microsoft word", "word doc", "word document"]),
        ("powerpoint", "launch_app", "PowerPoint", ["powerpoint", "ppt", "slides", "microsoft powerpoint"]),
        ("terminal", "launch_app", "Terminal", ["terminal", "windows terminal", "command prompt", "cmd", "powershell"]),
        ("edge", "launch_app", "Microsoft Edge", ["edge", "microsoft edge", "ms edge", "edge browser"]),
        ("paint", "launch_app", "MS Paint", ["paint", "mspaint", "paint app", "drawing app"]),
        ("settings", "open_settings_page", "Windows Settings", ["settings", "windows settings", "pc settings", "system settings"]),
        ("explorer", "launch_app", "File Explorer", ["file explorer", "explorer", "files", "file manager"])
    ]

    # 1. APPLICATION LAUNCHING & CLOSING (English, Telugu-English, Telugu)
    print("Generating Application Control utterances...")
    for app_id, tool_name, display_name, aliases in apps:
        for alias in aliases:
            for p in prefixes_en:
                for s in suffixes_en:
                    # Open
                    add_rec(f"{p}open {alias}{s}", "en", "app_launch", {"app_name": app_id}, tool_name, grp=f"launch_{app_id}")
                    add_rec(f"{p}launch {alias}{s}", "en", "app_launch", {"app_name": app_id}, tool_name, grp=f"launch_{app_id}")
                    add_rec(f"{p}start {alias}{s}", "en", "app_launch", {"app_name": app_id}, tool_name, grp=f"launch_{app_id}")
                    add_rec(f"{p}switch to {alias}{s}", "en", "app_switch", {"app_name": app_id}, "control_window", grp=f"switch_{app_id}")
                    # Close
                    add_rec(f"{p}close {alias}{s}", "en", "app_close", {"app_name": app_id}, "close_app", grp=f"close_{app_id}")
                    add_rec(f"{p}quit {alias}{s}", "en", "app_close", {"app_name": app_id}, "close_app", grp=f"close_{app_id}")
                    add_rec(f"{p}kill {alias}{s}", "en", "app_kill_force", {"app_name": app_id}, "close_app", risk="MODERATE", req_confirm=True, grp=f"kill_{app_id}")

            for pt in prefixes_te:
                for st in suffixes_te:
                    add_rec(f"{pt}{alias} open chey{st}", "te-en", "app_launch", {"app_name": app_id}, tool_name, grp=f"launch_{app_id}")
                    add_rec(f"{pt}{alias} theeyi{st}", "te-Latn", "app_launch", {"app_name": app_id}, tool_name, grp=f"launch_{app_id}")
                    add_rec(f"{pt}{alias} close chey{st}", "te-en", "app_close", {"app_name": app_id}, "close_app", grp=f"close_{app_id}")
                    add_rec(f"{pt}{alias} aapu{st}", "te-Latn", "app_close", {"app_name": app_id}, "close_app", grp=f"close_{app_id}")
                    add_rec(f"{pt}{alias} ki switch avvu{st}", "te-en", "app_switch", {"app_name": app_id}, "control_window", grp=f"switch_{app_id}")

    # 2. BROWSER AND YOUTUBE TASKS & ORDINAL NAVIGATION
    print("Generating Browser & YouTube utterances...")
    queries = [
        "python tutorials", "telugu songs", "machine learning course", "data structures",
        "latest tech news", "artificial intelligence lecture", "react js crash course",
        "django web development", "power bi dashboard", "windows 11 tips", "best coding songs",
        "lo-fi study music", "system design interview", "cloud computing aws", "sql tutorial"
    ]
    ordinals = [
        ("first", 1), ("second", 2), ("third", 3), ("fourth", 4), ("fifth", 5),
        ("1st", 1), ("2nd", 2), ("3rd", 3), ("4th", 4), ("5th", 5),
        ("number 1", 1), ("number 2", 2), ("number 3", 3), ("number 4", 4)
    ]

    for q in queries:
        for p in prefixes_en:
            for s in suffixes_en:
                add_rec(f"{p}search youtube for {q}{s}", "en", "browser_search_youtube", {"query": q, "engine": "youtube"}, "browser_search", grp="yt_search")
                add_rec(f"{p}search for {q} on youtube{s}", "en", "browser_search_youtube", {"query": q, "engine": "youtube"}, "browser_search", grp="yt_search")
                add_rec(f"{p}open youtube and search {q}{s}", "en", "compound_multistep", {"query": q, "engine": "youtube"}, "browser_search", grp="yt_search")
                add_rec(f"{p}google {q}{s}", "en", "browser_search_google", {"query": q, "engine": "google"}, "browser_search", grp="google_search")
                add_rec(f"{p}search google for {q}{s}", "en", "browser_search_google", {"query": q, "engine": "google"}, "browser_search", grp="google_search")
                # Deictic follow-up searches referring to current context
                add_rec(f"{p}now search {q} there{s}", "en", "browser_search_there", {"query": q, "deictic_target": "there"}, "browser_search", grp="search_there")
                add_rec(f"{p}search {q} there{s}", "en", "browser_search_there", {"query": q, "deictic_target": "there"}, "browser_search", grp="search_there")

        for pt in prefixes_te:
            for st in suffixes_te:
                add_rec(f"{pt}youtube lo {q} search chey{st}", "te-en", "browser_search_youtube", {"query": q, "engine": "youtube"}, "browser_search", grp="yt_search")
                add_rec(f"{pt}google lo {q} vetuku{st}", "te-en", "browser_search_google", {"query": q, "engine": "google"}, "browser_search", grp="google_search")
                add_rec(f"{pt}akkada {q} search chey{st}", "te-en", "browser_search_there", {"query": q, "deictic_target": "there"}, "browser_search", grp="search_there")

    # Ordinal selections & video playback
    for word, idx in ordinals:
        for p in prefixes_en:
            for s in suffixes_en:
                add_rec(f"{p}play the {word} video{s}", "en", "browser_open_result", {"result_index": idx, "media_type": "video"}, "browser_open_result", grp="ord_result")
                add_rec(f"{p}play {word} result{s}", "en", "browser_open_result", {"result_index": idx, "media_type": "video"}, "browser_open_result", grp="ord_result")
                add_rec(f"{p}open the {word} result{s}", "en", "browser_open_result", {"result_index": idx}, "browser_open_result", grp="ord_result")
                add_rec(f"{p}open the {word} website{s}", "en", "browser_open_result", {"result_index": idx}, "browser_open_result", grp="ord_result")
                add_rec(f"{p}click the {word} result{s}", "en", "browser_open_result", {"result_index": idx}, "browser_open_result", grp="ord_result")

        for pt in prefixes_te:
            for st in suffixes_te:
                add_rec(f"{pt}{word} video play chey{st}", "te-en", "browser_open_result", {"result_index": idx, "media_type": "video"}, "browser_open_result", grp="ord_result")
                add_rec(f"{pt}{word} result open chey{st}", "te-en", "browser_open_result", {"result_index": idx}, "browser_open_result", grp="ord_result")

    # 3. BROWSER SCROLLING (Page Down, Page Up, Scroll Down)
    print("Generating Browser Scrolling utterances...")
    scroll_cmds = [
        ("scroll down one page", "down", "page", "browser_scroll_down"),
        ("scroll down", "down", "page", "browser_scroll_down"),
        ("go page down", "down", "page", "browser_scroll_down"),
        ("page down", "down", "page", "browser_scroll_down"),
        ("scroll down a bit", "down", "half_page", "browser_scroll_down"),
        ("scroll up one page", "up", "page", "browser_scroll_up"),
        ("scroll up", "up", "page", "browser_scroll_up"),
        ("go page up", "up", "page", "browser_scroll_up"),
        ("page up", "up", "page", "browser_scroll_up"),
    ]
    for phrase, direction, amount, intent_name in scroll_cmds:
        for p in prefixes_en:
            for s in suffixes_en:
                add_rec(f"{p}{phrase}{s}", "en", intent_name, {"direction": direction, "amount": amount}, "browser_scroll", grp="browser_scroll")
        for pt in prefixes_te:
            for st in suffixes_te:
                d_te = "kindaki" if direction == "down" else "paiki"
                add_rec(f"{pt}page {d_te} scroll chey{st}", "te-en", intent_name, {"direction": direction, "amount": amount}, "browser_scroll", grp="browser_scroll")

    # 4. EMAIL AUTOMATION (Reading, Drafting, Sending with confirmation)
    print("Generating Email Automation utterances...")
    recipients = ["prof.sharma@university.edu", "recruiter@techcorp.com", "manager@company.com", "john@example.com", "somu@college.edu"]
    subjects = ["Project Review Schedule", "Technical Interview", "Monthly Progress Report", "Meeting Discussion", "Leave Application"]
    bodies = ["Here is the updated documentation.", "I will be available for the meeting.", "Please find attached files.", "Let us connect tomorrow."]

    for p in prefixes_en:
        for s in suffixes_en:
            add_rec(f"{p}read my email{s}", "en", "email_read", {}, "email_read", grp="email_read")
            add_rec(f"{p}read the latest email{s}", "en", "email_read", {}, "email_read", grp="email_read")
            add_rec(f"{p}read selected email aloud{s}", "en", "email_read", {}, "email_read", grp="email_read")
            add_rec(f"{p}summarize my unread emails{s}", "en", "email_read", {}, "email_read", grp="email_read")
            add_rec(f"{p}open my email client{s}", "en", "email_open", {}, "email_open", grp="email_open")
            add_rec(f"{p}open gmail{s}", "en", "email_open", {"client": "gmail"}, "email_open", grp="email_open")

    for r in recipients:
        for sub in subjects:
            for b in bodies:
                for p in ["", "please ", "can you ", "niva "]:
                    add_rec(f"{p}draft email to {r} with subject {sub} and message {b}", "en", "email_draft", {"recipient": r, "subject": sub, "body": b}, "email_draft", grp="email_draft")
                    add_rec(f"{p}send email to {r} with subject {sub} and message {b}", "en", "email_send", {"recipient": r, "subject": sub, "body": b}, "email_send", risk="CRITICAL", req_confirm=True, grp="email_send")
                    add_rec(f"{p}email {r} regarding {sub}", "en", "email_draft", {"recipient": r, "subject": sub}, "email_draft", grp="email_draft")

    for pt in prefixes_te:
        for st in suffixes_te:
            add_rec(f"{pt}naa email chaduvi cheppu{st}", "te-en", "email_read", {}, "email_read", grp="email_read")
            add_rec(f"{pt}email client open chey{st}", "te-en", "email_open", {}, "email_open", grp="email_open")
            add_rec(f"{pt}gmail theeyi{st}", "te-en", "email_open", {"client": "gmail"}, "email_open", grp="email_open")

    # 5. FORM FILLING & DATA ENTRY (with Confirmation)
    print("Generating Form Filling utterances...")
    sample_forms = [
        {"name": "John Doe", "email": "john@example.com", "phone": "9876543210"},
        {"name": "Somu", "email": "somu@college.edu", "city": "Hyderabad"},
        {"username": "student_ai", "roll_number": "2026AI01", "grade": "A+"},
        {"feedback": "System is highly responsive and robust", "rating": "5"}
    ]
    for form in sample_forms:
        desc_parts = [f"{k} as {v}" for k, v in form.items()]
        desc_str = ", ".join(desc_parts)
        for p in prefixes_en:
            add_rec(f"{p}fill form with {desc_str}", "en", "form_fill_structured", {"fields": form}, "fill_form", grp="form_fill")
            add_rec(f"{p}enter details {desc_str} into form", "en", "form_fill_structured", {"fields": form}, "fill_form", grp="form_fill")
            add_rec(f"{p}submit the form", "en", "form_submit", {}, "fill_form", risk="MODERATE", req_confirm=True, grp="form_submit")
            add_rec(f"{p}clear all form fields", "en", "form_clear_fields", {}, "fill_form", grp="form_fill")

    # 6. WINDOWS SETTINGS (Bluetooth, Wi-Fi, Volume, Brightness, Mute)
    print("Generating Windows Settings utterances...")
    settings_data = [
        ("bluetooth", "on", "setting_bluetooth_on", "set_setting", ["turn bluetooth on", "enable bluetooth", "switch on bluetooth", "bluetooth on chey"]),
        ("bluetooth", "off", "setting_bluetooth_off", "set_setting", ["turn bluetooth off", "disable bluetooth", "switch off bluetooth", "bluetooth off chey"]),
        ("wifi", "on", "setting_wifi_on", "set_setting", ["turn wifi on", "enable wifi", "switch on wifi", "wifi on chey"]),
        ("wifi", "off", "setting_wifi_off", "set_setting", ["turn wifi off", "disable wifi", "switch off wifi", "wifi off chey"]),
        ("volume", 50, "setting_volume_set", "set_setting", ["set volume to 50", "volume 50 percent", "change volume to 50"]),
        ("volume", 80, "setting_volume_increase", "set_setting", ["increase volume", "volume up", "sound penchu", "volume penchu"]),
        ("volume", 20, "setting_volume_decrease", "set_setting", ["decrease volume", "volume down", "sound tagginchu", "volume tagginchu"]),
        ("mute", True, "setting_volume_mute", "set_setting", ["mute audio", "mute sound", "mute computer", "sound aapu"]),
        ("mute", False, "setting_volume_unmute", "set_setting", ["unmute audio", "unmute sound", "turn sound back on"]),
        ("brightness", 80, "setting_brightness_increase", "set_setting", ["increase brightness", "screen brighter", "brightness penchu"]),
        ("brightness", 30, "setting_brightness_decrease", "set_setting", ["decrease brightness", "dim screen", "brightness tagginchu"]),
    ]
    for s_name, s_val, s_intent, s_tool, s_phrases in settings_data:
        for phrase in s_phrases:
            for p in ["", "please ", "can you ", "niva ", "hey niva "]:
                for s in ["", " now", " please"]:
                    lang = "te-en" if any(w in phrase for w in ["chey", "penchu", "tagginchu", "aapu"]) else "en"
                    add_rec(f"{p}{phrase}{s}", lang, s_intent, {"setting": s_name, "value": s_val}, s_tool, grp="settings")

    # 7. VISIBLE CLICKS & ACCESSIBLE UI AUTOMATION
    print("Generating Accessible UI Click utterances...")
    elements = [
        ("Search", "Button", ["click search", "click the search button", "press search", "search meeda click chey"]),
        ("Save", "Button", ["click save", "press save", "click the save button", "save button meeda click chey"]),
        ("OK", "Button", ["click ok", "press ok button", "tap ok"]),
        ("Submit", "Button", ["click submit", "press submit button"]),
        ("Cancel", "Button", ["click cancel", "tap cancel button"]),
        ("Close", "Button", ["click close button", "close window"]),
        ("File", "MenuItem", ["click file menu", "click file"]),
        ("Downloads", "ListItem", ["click downloads", "select downloads"]),
    ]
    for el_name, c_type, el_phrases in elements:
        for phrase in el_phrases:
            for p in ["", "please ", "can you ", "niva "]:
                lang = "te-en" if "chey" in phrase else "en"
                add_rec(f"{p}{phrase}", lang, "mouse_click_element", {"element_name": el_name, "control_type": c_type}, "uia_click", grp="uia_click")

    # 8. INTERRUPTION, STOP, PAUSE, RESUME, OVERRIDE, UNDO
    print("Generating Interruption & Control utterances...")
    interruptions = [
        ("stop", "interruption_stop", "stop", ["stop", "stop now", "emergency stop", "halt", "cancel task", "aapu", "aapey", "vaddu"]),
        ("pause", "interruption_pause", "pause", ["pause", "pause task", "wait a second", "hold on", "koncham aagu", "agandi"]),
        ("resume", "interruption_resume", "resume", ["resume", "continue", "resume task", "keep going", "malli chey", "continue chey"]),
        ("undo", "interruption_undo", "undo", ["undo", "undo that", "revert last action", "venakki teesko"]),
        ("override", "interruption_override", "override", ["stop open notepad instead", "cancel that open calculator", "abort switch to chrome"])
    ]
    for name, intent_name, action_name, phrases in interruptions:
        for phrase in phrases:
            for p in ["", "niva ", "hey niva "]:
                lang = "te-Latn" if any(w in phrase for w in ["aapu", "aapey", "vaddu", "aagu", "agandi", "teesko"]) else "en"
                add_rec(f"{p}{phrase}", lang, intent_name, {"action": action_name}, "interruption", risk="SAFE", grp="interruption")

    # 9. CONVERSATIONAL GREETINGS, PRESENCE, & IDENTITY
    print("Generating Conversational utterances...")
    conv_items = [
        ("hello", "conversational_greeting", ["hello", "hi", "hey", "howdy", "hello niva", "hi niva", "hey niva", "namaste", "namaskaram", "ela unnavu", "bagunnava"]),
        ("how are you", "conversational_greeting", ["how are you", "how are you doing", "how is it going", "how are you niva"]),
        ("presence", "conversational_presence", ["can you hear me", "are you there", "are you listening", "mic test", "testing", "can you speak", "talk to me", "vinipistunda", "unnava"]),
        ("identity", "conversational_identity", ["who are you", "what is your name", "tell me about yourself", "who made you", "who built you", "what can you do", "nuvvu evaru", "nee peru enti", "em cheyagalavu"])
    ]
    for cat, intent_name, phrases in conv_items:
        for phrase in phrases:
            for p in ["", "niva ", "hey niva "]:
                lang = "te-en" if any(w in phrase for w in ["namaste", "namaskaram", "ela", "bagunnava", "vinipistunda", "unnava", "nuvvu", "peru"]) else "en"
                add_rec(f"{p}{phrase}", lang, intent_name, {}, "none", grp="conversation")

    # Write all records to dataset
    print(f"Total dataset size generated: {len(records):,} records.")
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"Successfully saved {len(records):,} records to {DATASET_PATH}!")
    return len(records)


if __name__ == "__main__":
    generate_20k_dataset()
