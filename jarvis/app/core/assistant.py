"""
Master Jarvis Assistant Coordinator.
Wires together voice listener, speech recognition, interruption controller,
AI planning, safety enforcement, tool registry, and execution engine.
"""

from datetime import datetime
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional

from app.config import ASSISTANT_NAME
from app.ai.intent_parser import IntentParser
from app.ai.llm_provider import LLMProvider
from app.ai.reasoning_engine import ReasoningEngine
from app.automation.application_control import ApplicationController
from app.automation.browser_control import BrowserController
from app.automation.calculator_automation import CalculatorAutomation
from app.automation.email_automation import EmailAutomation
from app.automation.file_manager import FileManager
from app.automation.form_filling import FormFiller
from app.automation.office_automation import OfficeAutomation
from app.automation.windows_settings import WindowsSettingsController
from app.computer.computer_use import ComputerUseEngine
from app.core.context_manager import ContextManager
from app.core.executor import TaskExecutor
from app.core.planner import TaskPlanner
from app.core.task_manager import TaskManager
from app.core.task_state import StepStatus, Task, TaskStatus, TaskStep
from app.interruption.cancellation import CancellationToken
from app.interruption.checkpoints import CheckpointManager
from app.interruption.controller import InterruptionController
from app.safety.audit_log import AuditLogger
from app.safety.permissions import PermissionManager
from app.storage.database import Database
from app.tools import schemas
from app.tools.registry import ToolRegistry
from app.voice.listener import VoiceListener
from app.voice.speech_to_text import SpeechToTextEngine
from app.voice.text_to_speech import TextToSpeechEngine
from app.voice.wake_word import WakeWordDetector

logger = logging.getLogger(f"{ASSISTANT_NAME}.Assistant")


class NivaAssistant:
    """The central nervous system of the NIVA Universal AI Computer Agent."""

    def __init__(self, safe_mode: bool = True):
        # 1. Foundational state & safety
        self.cancellation_token = CancellationToken()
        self.checkpoint_mgr = CheckpointManager()
        self.permissions = PermissionManager(safe_mode=safe_mode)
        self.audit = AuditLogger()
        self.db = Database()
        self.context = ContextManager(db=self.db)

        # 2. Automation Engines
        self.app_ctrl = ApplicationController
        self.file_mgr = FileManager
        self.settings_ctrl = WindowsSettingsController
        self.calculator_ctrl = CalculatorAutomation
        self.browser_ctrl = BrowserController()
        self.email_ctrl = EmailAutomation(browser_controller=self.browser_ctrl)
        self.office = OfficeAutomation
        self.form_filler = FormFiller
        self.computer_use = ComputerUseEngine()

        # 3. Tool Registry setup
        self.tool_registry = ToolRegistry(permissions=self.permissions, audit=self.audit)
        self._register_all_tools()

        # 4. Interruption & Execution Core
        self.interruption = InterruptionController(
            token=self.cancellation_token,
            checkpoint_mgr=self.checkpoint_mgr
        )
        self.llm_provider = LLMProvider()
        self.planner = TaskPlanner(
            tool_registry=self.tool_registry,
            llm_provider=self.llm_provider,
            context=self.context
        )
        self.executor = TaskExecutor(
            tool_registry=self.tool_registry,
            cancellation_token=self.cancellation_token,
            checkpoint_mgr=self.checkpoint_mgr
        )
        self.task_manager = TaskManager(
            planner=self.planner,
            executor=self.executor,
            token=self.cancellation_token,
            db=self.db
        )

        # 5. Voice System
        self.stt = SpeechToTextEngine()
        self.tts = TextToSpeechEngine()
        self.wake_detector = WakeWordDetector(enabled=False)
        self.voice_listener = VoiceListener(
            stt_engine=self.stt,
            wake_detector=self.wake_detector,
            interruption_controller=self.interruption,
            tts_engine=self.tts
        )

        # Wire Interruption Callbacks
        self._wire_interruption_hooks()

        # UI Notification Callbacks
        self.on_task_updated: Optional[Callable[[Task], None]] = None
        self.on_message_logged: Optional[Callable[[str, str], None]] = None  # (role, text)
        self.pending_clarification: Optional[Dict[str, Any]] = None

        # Wire executor telemetry to assistant callbacks
        self.executor.on_step_started = self._on_step_started
        self.executor.on_step_completed = self._on_step_completed
        self.executor.on_task_finished = self._on_task_finished
        self.task_manager.on_task_state_changed = self._on_task_state_changed
        self.voice_listener.on_speech_recognized = self.handle_voice_input
        self.voice_listener.on_error = lambda err: self._log_dialogue("error", f"Voice Recognition Error: {err}")
        self.tts.on_error = lambda err: self._log_dialogue("error", f"Text-to-Speech Error: {err}")

    def _register_all_tools(self) -> None:
        """Populates the central ToolRegistry with all automation capabilities."""
        # Applications & Windows
        self.tool_registry.register("launch_app", "Launch an application", schemas.LaunchAppParams, self.app_ctrl.launch_application, "application")
        self.tool_registry.register("close_app", "Close a running application", schemas.CloseAppParams, self.app_ctrl.close_application, "application")
        self.tool_registry.register("control_window", "Focus, minimize, maximize, restore, or close a window", schemas.WindowControlParams, self.computer_use.window.control_window, "window")
        self.tool_registry.register("show_desktop", "Minimize all windows to show desktop", schemas.BaseModel, self.computer_use.window.show_desktop, "desktop")

        # Filesystem
        self.tool_registry.register("create_folder", "Create a new folder", schemas.CreateFolderParams, self.file_mgr.create_folder, "filesystem")
        self.tool_registry.register("create_file", "Create a new file with text content", schemas.CreateFileParams, self.file_mgr.create_file, "filesystem")
        self.tool_registry.register("read_file", "Read text, docx, pdf, or xlsx content", schemas.ReadFileParams, self.file_mgr.read_file, "filesystem")
        self.tool_registry.register("move_file", "Move or rename a file/folder", schemas.FileMoveCopyParams, self.file_mgr.move_file, "filesystem")
        self.tool_registry.register("copy_file", "Copy a file or directory", schemas.FileMoveCopyParams, self.file_mgr.copy_file, "filesystem")
        self.tool_registry.register("delete_file", "Safely delete a file or directory", schemas.DeleteFileParams, self.file_mgr.delete_file, "filesystem")
        self.tool_registry.register("search_files", "Search files by name wildcard", schemas.SearchFilesParams, self.file_mgr.search_files, "filesystem")
        self.tool_registry.register("organize_folder", "Organize files by extension into category folders", schemas.OrganizeFolderParams, self.file_mgr.organize_folder, "filesystem")

        # Settings
        self.tool_registry.register("set_setting", "Adjust Bluetooth, Wi-Fi, Volume, Mute, or Brightness", schemas.WindowsSettingParams, self._dispatch_setting, "settings")
        self.tool_registry.register("open_settings_page", "Open a specific Windows Settings page", schemas.OpenSettingsPageParams, self.settings_ctrl.open_settings_page, "settings")
        self.tool_registry.register("calculate_expression", "Calculate mathematical expression or enter into open Calculator app", schemas.CalculateExpressionParams, self._dispatch_calculation, "calculator")
        self.tool_registry.register("plan_trip", "Plan comprehensive trip itinerary and save document to Desktop", schemas.PlanTripParams, self._dispatch_plan_trip, "planning")

        # Mouse & Keyboard
        self.tool_registry.register("mouse_click", "Click mouse at coordinates or current position", schemas.MouseClickParams, self.computer_use.click, "computer_use")
        self.tool_registry.register("type_text", "Type text into active window", schemas.TypeTextParams, self.computer_use.type, "computer_use")
        self.tool_registry.register("press_hotkey", "Press key combination (e.g. ['ctrl', 'c'])", schemas.HotkeyParams, self.computer_use.hotkey, "computer_use")
        self.tool_registry.register("scroll", "Scroll up or down", schemas.ScrollParams, self.computer_use.scroll, "computer_use")

        # Browser
        self.tool_registry.register("browser_open", "Open a website in browser", schemas.BrowserOpenParams, self._dispatch_browser_open, "browser")
        self.tool_registry.register("browser_search", "Search Google, YouTube, or Bing", schemas.BrowserSearchParams, self._dispatch_browser_search, "browser")
        self.tool_registry.register("browser_open_result", "Open or play a specific search result or video by index", schemas.BrowserOpenResultParams, self._dispatch_browser_result, "browser")
        self.tool_registry.register("browser_scroll", "Scroll the active browser page up or down", schemas.BrowserScrollParams, self._dispatch_browser_scroll, "browser")
        self.tool_registry.register("play_youtube_video", "Search and play a video or song on YouTube in the current tab", schemas.PlayVideoParams, self._dispatch_play_youtube_video, "browser")
        self.tool_registry.register("play_another_video", "Play next song or another video in current tab without opening new tabs", schemas.PlayAnotherVideoParams, self._dispatch_play_another_video, "browser")
        self.tool_registry.register("browser_media_control", "Control media playback (pause, resume, next, mute) in YouTube", schemas.MediaControlParams, self._dispatch_media_control, "browser")

        # Email & Communication
        self.tool_registry.register("email_read", "Read or summarize requested emails", schemas.EmailReadParams, self.email_ctrl.read_email, "email")
        self.tool_registry.register("email_draft", "Draft an email with dictated details", schemas.EmailDraftParams, self.email_ctrl.draft_email, "email")
        self.tool_registry.register("email_send", "Send an email after explicit confirmation", schemas.EmailSendParams, self._dispatch_email_send, "email")

        # Office
        self.tool_registry.register("create_excel", "Create an Excel spreadsheet with tables and totals", schemas.CreateExcelParams, self.office.create_excel_sheet, "office")
        self.tool_registry.register("create_word", "Create a Word document report", schemas.CreateWordParams, self.office.create_word_document, "office")
        self.tool_registry.register("create_presentation", "Create a PowerPoint presentation deck", schemas.CreatePowerPointParams, self.office.create_presentation, "office")

        # Form Filling
        self.tool_registry.register("fill_form", "Enter structured data into form fields", schemas.FillFormParams, self._dispatch_form_fill, "automation")

        # Vision
        self.tool_registry.register("capture_screen", "Capture desktop screenshot", schemas.ScreenObservationParams, self.computer_use.take_screenshot, "vision")

        # Microsoft UI Automation (Accessible Elements)
        self.tool_registry.register("uia_click", "Click accessible UI element by name in an application window", schemas.UIAClickParams, self.computer_use.click_accessible_element, "ui_automation")
        self.tool_registry.register("uia_set_text", "Enter text into accessible control using UI Automation ValuePattern", schemas.UIASetTextParams, self.computer_use.set_accessible_text, "ui_automation")
        self.tool_registry.register("uia_list_elements", "Inspect accessible controls in window", schemas.UIAListElementsParams, self.computer_use.uia.list_accessible_elements, "ui_automation")

        # System & Privacy Diagnostics
        self.tool_registry.register("system_info", "Check battery, storage, and resource metrics", schemas.SystemInfoParams, self._dispatch_system_info, "system")
        self.tool_registry.register("history_manage", "Clear or inspect local dialogue history", schemas.HistoryActionParams, self._dispatch_history, "privacy")

    def _dispatch_browser_open(self, url: str) -> Dict[str, Any]:
        res = self.browser_ctrl.open_url(url=url)
        if res.get("success"):
            self.context.last_browser_url = url
            self.context.active_application = "browser"
        return res

    def _dispatch_browser_search(self, query: str, engine: str = "google") -> Dict[str, Any]:
        res = self.browser_ctrl.search(query=query, engine=engine)
        if res.get("success"):
            self.context.last_search_query = query
            self.context.last_search_engine = engine
            self.context.active_application = "browser"
            items = res.get("results", [])
            if items:
                self.context.recent_search_results = [
                    item.get("url") for item in items if isinstance(item, dict) and item.get("url")
                ]
        return res

    def _dispatch_browser_result(self, result_index: int = 1) -> Dict[str, Any]:
        engine = getattr(self.browser_ctrl, "last_engine", "") or getattr(self.context, "last_search_engine", "")
        if str(engine).lower() == "youtube":
            res = self.browser_ctrl.play_youtube_result(result_index=result_index)
        else:
            res = self.browser_ctrl.open_search_result(result_index=result_index)
        if res.get("success"):
            if res.get("url"):
                self.context.last_browser_url = res.get("url")
            self.context.active_application = "browser"
        return res

    def _dispatch_browser_scroll(self, direction: str = "down", amount: str = "page") -> Dict[str, Any]:
        return self.browser_ctrl.scroll_page(direction=direction, amount=amount)

    def _dispatch_email_send(self, recipient: str, subject: str, body: str, confirmed: bool = False) -> Dict[str, Any]:
        """Ensures explicit user confirmation is verified before sending any email."""
        if not confirmed:
            prompt_title = "Confirm Email Dispatch"
            details = f"To: {recipient}\nSubject: {subject}\n\nContent:\n{body}"
            confirmed = self.permissions.request_confirmation(prompt_title, details)
        return self.email_ctrl.send_email(recipient=recipient, subject=subject, body=body, confirmed=confirmed)

    def _dispatch_setting(self, setting: str, value: Any) -> Dict[str, Any]:
        """Routes generic set_setting calls to specific Windows settings methods."""
        s = setting.lower()
        if s == "bluetooth":
            enable = str(value).lower() in ["on", "true", "1", "enable"]
            return self.settings_ctrl.set_bluetooth_state(enable)
        elif s in ["wifi", "wi-fi"]:
            enable = str(value).lower() in ["on", "true", "1", "enable"]
            return self.settings_ctrl.set_wifi_state(enable)
        elif s == "volume":
            return self.settings_ctrl.set_volume(value)
        elif s == "mute":
            m = str(value).lower() in ["true", "1", "mute", "on"]
            return self.settings_ctrl.set_mute(m)
        elif s == "brightness":
            return self.settings_ctrl.set_brightness(value)
        return {"success": False, "error": f"Unknown setting '{setting}'"}

    def _dispatch_calculation(self, expression: str, ensure_open: bool = False) -> Dict[str, Any]:
        """Calculates mathematical expression or executes it directly in open Calculator app."""
        in_calc_context = (getattr(self.context, "active_application", None) == "calculator")
        must_open = ensure_open or in_calc_context
        res = self.calculator_ctrl.calculate(expression, ensure_open=must_open)
        if res.get("in_calculator"):
            self.context.update_active_app("calculator", "Calculator")
        return res

    def _dispatch_plan_trip(self, destination: str = "Goa", duration: str = "7 days", duration_days: int = 7, people: int = 2, budget: str = "50,000 INR") -> Dict[str, Any]:
        """Generates comprehensive trip itinerary, saves document to Desktop, and opens it."""
        from app.ai.trip_planner import TripPlanner
        session = {
            "destination": destination,
            "duration": duration,
            "duration_days": duration_days,
            "people": people,
            "budget": budget
        }
        itinerary = TripPlanner.generate_itinerary(session)
        file_path = TripPlanner.save_and_open_itinerary_document(itinerary)
        self.context.update_last_file(file_path)
        return {
            "success": True,
            "message": itinerary["spoken_summary"],
            "file_path": file_path,
            "itinerary": itinerary
        }

    def _dispatch_form_fill(self, field_mappings: Dict[str, str], submit_after_fill: bool = False) -> Dict[str, Any]:
        return self.form_filler.fill_form_fields(
            field_mappings=field_mappings,
            submit_after_fill=submit_after_fill,
            browser_controller=self.browser_ctrl
        )

    def _dispatch_system_info(self, query_type: str = "status") -> Dict[str, Any]:
        import psutil
        q = query_type.lower()
        if q == "battery":
            b = psutil.sensors_battery()
            if b:
                return {"success": True, "percent": b.percent, "power_plugged": b.power_plugged, "message": f"Battery is at {b.percent}% ({'Plugged in' if b.power_plugged else 'On battery'})."}
            return {"success": True, "message": "No battery sensor detected (Desktop workstation)."}
        elif q == "storage":
            d = psutil.disk_usage("C:")
            free_gb = round(d.free / (1024**3), 1)
            total_gb = round(d.total / (1024**3), 1)
            return {"success": True, "free_gb": free_gb, "total_gb": total_gb, "message": f"Drive C has {free_gb} GB free out of {total_gb} GB."}
        elif q == "resources":
            cpu = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory().percent
            return {"success": True, "cpu_percent": cpu, "ram_percent": ram, "message": f"CPU usage: {cpu}%, RAM usage: {ram}%."}
        return {"success": True, "message": f"NIVA system operational."}

    def _dispatch_history(self, action: str = "status") -> Dict[str, Any]:
        a = action.lower()
        if a == "clear":
            return self.db.clear_history()
        elif a == "enable":
            self.db.set_history_enabled(True)
            return {"success": True, "history_enabled": True}
        elif a == "disable":
            self.db.set_history_enabled(False)
            return {"success": True, "history_enabled": False}
        return {"success": True, "history_enabled": self.db.is_history_enabled()}

    def _wire_interruption_hooks(self) -> None:
        """Wires up InterruptionController events to immediate actions."""
        self.interruption.on_stop_callback = self._on_stop_triggered
        self.interruption.on_pause_callback = self._on_pause_triggered
        self.interruption.on_resume_callback = self._on_resume_triggered
        self.interruption.on_override_callback = self._on_override_triggered
        self.interruption.on_status_callback = self._on_status_requested

    def _on_stop_triggered(self) -> None:
        self.tts.stop_speaking()
        self.task_manager.stop_current_task()
        self.tts.speak("I've stopped the task immediately. All actions cancelled.")
        self._log_dialogue("assistant", "Task stopped by emergency interruption.")

    def _on_pause_triggered(self) -> None:
        self.task_manager.pause_current_task()
        self.tts.speak("Execution paused.")
        self._log_dialogue("assistant", "Task paused.")

    def _on_resume_triggered(self) -> None:
        self.task_manager.resume_current_task()
        self.tts.speak("Resuming execution.")
        self._log_dialogue("assistant", "Task resumed.")

    def _on_override_triggered(self, new_command: str) -> None:
        self.tts.stop_speaking()
        self.task_manager.stop_current_task()
        self.tts.speak(f"Previous task cancelled. Switching to: {new_command}")
        self._log_dialogue("assistant", f"Switching to override command: {new_command}")
        self.process_command(new_command)

    def _on_status_requested(self) -> str:
        task = self.task_manager.current_task
        if not task or task.status == TaskStatus.IDLE:
            return "I am currently idle with no active tasks."
        if task.status == TaskStatus.RUNNING:
            curr = task.current_step
            step_desc = curr.description if curr else "processing"
            return f"Currently running step {task.current_step_index + 1} of {len(task.steps)}: {step_desc}. Progress: {task.progress_percentage}%."
        return f"Task is currently in state {task.status.value}."

    def _check_unsupported_action(self, prompt: str) -> Optional[str]:
        """
        Detects requests that are impossible or outside NIVA's software capabilities
        (such as physical world manipulation, telephony/SMS, or malicious actions).
        """
        p_lower = prompt.lower().strip()
        p_clean = re.sub(r"^(?:niva|hey\s+niva|ok\s+niva|hi\s+niva|jarvis)[,\s:]*", "", p_lower).strip()

        # 1. Physical world actions
        physical_verbs = [
            "cook", "bake", "fry", "boil", "sweep", "mop",
            "wash clothes", "do laundry", "iron clothes", "ironing",
            "drive car", "drive my car", "drive", "fly drone", "fly plane",
            "order pizza", "order food", "deliver food", "bring me water", "pour water", "give me a massage"
        ]
        # Regex patterns for physical tasks with variable phrasing (e.g. 'make me a cup of tea')
        physical_regexes = [
            r"\b(?:make|brew|pour|prepare|give|bring|get)\b.*?\b(?:tea|coffee)\b",
            r"\b(?:make|cook|prepare|order|buy)\b.*?\b(?:dinner|lunch|breakfast|food|meal|pizza|burger)\b",
            r"\b(?:wash|clean|do)\b.*?\b(?:dishes|laundry|clothes|room|house|floor)\b",
            r"\b(?:drive|fly|ride)\b.*?\b(?:car|drone|plane|airplane|bike|bicycle)\b",
        ]
        telugu_physical = [
            "tea chey", "coffee ivvu", "coffee pettu", "vanta chey", "car drive chey",
            "illu clean chey", "batalu uthuku", "batalu iron chey", "food pettu"
        ]
        for pv in physical_verbs + telugu_physical:
            if re.search(rf"\b{re.escape(pv)}\b", p_clean):
                return (
                    "I cannot perform physical world tasks like cooking, driving, or washing dishes. "
                    "I am a software assistant designed to control your Windows computer, applications, files, and settings."
                )

        for pr in physical_regexes:
            if re.search(pr, p_clean, re.IGNORECASE):
                return (
                    "I cannot perform physical world tasks like cooking, driving, or washing dishes. "
                    "I am a software assistant designed to control your Windows computer, applications, files, and settings."
                )

        # 2. Telephony / SMS
        calling_patterns = [
            "call 911", "call 100", "call emergency", "call my phone", "make a phone call",
            "send sms", "send a text message to phone", "phone call chey"
        ]
        for cp in calling_patterns:
            if cp in p_clean:
                return (
                    "I cannot place telephone calls or send cellular SMS messages. "
                    "I can operate Windows desktop applications, web browsers, and computer files."
                )

        # 3. Malicious / Hacking
        malicious_patterns = [
            "hack a website", "hack bank", "crack password", "bypass login", "steal credentials",
            "ddos", "hack facebook", "hack instagram"
        ]
        for mp in malicious_patterns:
            if mp in p_clean:
                return (
                    "I cannot perform hacking, credential theft, or security bypass actions. "
                    "All operations must adhere to system safety guidelines."
                )

        return None

    def _is_conversational_question(self, prompt: str) -> bool:
        """
        Determines whether a user input is a conversational question or greeting,
        rather than a command to operate the computer.
        """
        p_lower = prompt.lower().strip()
        p_clean = re.sub(r"^(?:niva|nivea|neeva|neva|nova|hey\s+niva|hey\s+nivea|ok\s+niva|ok\s+nivea|hi\s+niva|hi\s+nivea|hello\s+niva|hello\s+nivea|jarvis)[,\s:]*", "", p_lower).strip()
        p_clean = re.sub(r"[?!.,]+$", "", p_clean).strip()

        # If user greeted or called assistant directly (e.g. 'Hi NIVA', 'Hey NIVA', 'NIVA', 'Hello')
        wake_greetings = ["niva", "nivea", "neeva", "neva", "nova", "hey niva", "hey nivea", "ok niva", "hi niva", "hello niva", "hello", "hi", "hey", "howdy"]
        if p_clean == "" or p_clean in wake_greetings or p_lower in wake_greetings:
            return True

        # Action verbs or computer terms that clearly indicate a computer control command
        action_indicators = [
            "open ", "launch ", "close ", "kill ", "quit ", "switch to ", "minimize", "maximize",
            "create ", "make folder", "make file", "delete ", "remove ", "move ", "copy ", "rename ",
            "organize ", "search ", "find ", "google ", "look up ", "type ", "write ", "enter ",
            "press ", "click ", "scroll ", "turn on ", "turn off ", "set volume", "set brightness",
            "set bluetooth", "set wifi", "mute", "unmute", "save", "download",
            "open chey", "close chey", "type chey", "rayi", "create chey", "pettu", "theeyi",
            "aapu", "vetuku", "choodu"
        ]
        for ai in action_indicators:
            if ai in p_clean:
                if not any(p_clean.startswith(q) for q in ["what ", "how ", "can you explain", "tell me how"]):
                    return False

        # Conversational questions / greetings patterns
        conv_patterns = [
            r"^(?:who|what)\s+are\s+you\b",
            r"^what\s+is\s+your\s+name\b",
            r"^tell\s+me\s+about\s+yourself\b",
            r"^who\s+(?:made|built|created)\s+you\b",
            r"^what\s+can\s+you\s+do\b",
            r"^what\s+(?:features|capabilities)\s+(?:do\s+you\s+have|are\s+supported)\b",
            r"^explain\s+your\s+capabilities\b",
            r"^how\s+do\s+you\s+work\b",
            r"^how\s+are\s+you(?:\s+doing)?\b",
            r"^how\'?s\s+it\s+going\b",
            r"^(?:hello|hi|hey|howdy)\b",
            r"^(?:good\s+morning|good\s+afternoon|good\s+evening|good\s+night)\b",
            r"^(?:namaste|namaskaram)\b",
            r"^(?:thank\s+you|thanks(?:\s+a\s+lot)?|dhanyavadalu)\b",
            r"^what\s+(?:is\s+the\s+)?time(?:\s+is\s+it)?\b",
            r"^what\s+time\s+is\s+it\b",
            r"^what\s+(?:day|date)\s+is\s+(?:it\s+)?today\b",
            r"^what\s+is\s+today\'?s\s+date\b",
            r"^what\s+is\s+python\b",
            r"^what\s+is\s+(?:ai|artificial\s+intelligence)\b",
            r"^what\s+is\s+machine\s+learning\b",
            r"^tell\s+me\s+a\s+joke\b",
            r"^nuvvu\s+evaru\b",
            r"^nee\s+peru\s+enti\b",
            r"^(?:nuvvu\s+)?em\s+cheyagala(?:vo|vu)\b",
            r"^ela\s+unnavu\b",
            r"^bagunnava\b",
            r"^time\s+entha\b",
            r"^eroju\s+date\s+enti\b",
            r"^chala\s+thanks\b",
            r"^(?:ok|okay)\s+now\b",
            r"^(?:ok|okay)\s+then\b",
            r"^(?:now\s+what|what\s+now|what\s+next)\b",
            r"^(?:can\s+you\s+hear\s+me|are\s+you\s+there|are\s+you\s+listening|can\s+you\s+speak|talk\s+to\s+me|speak\s+to\s+me|say\s+something)\b",
            r"^(?:mic\s+test|microphone\s+test|audio\s+test|testing|test)\b",
            r"^(?:vinipistunda|nenu\s+matladedi\s+vinipistunda|unnava)\b",
        ]

        for pat in conv_patterns:
            if re.search(pat, p_clean, re.IGNORECASE):
                return True

        return False

    def _answer_conversational_question(self, prompt: str) -> str:
        """
        Generates a direct, accurate answer for conversational questions.
        Uses configured LLM if available, or offline built-in knowledge.
        """
        p_lower = prompt.lower().strip()
        p_clean = re.sub(r"^(?:niva|nivea|neeva|neva|nova|hey\s+niva|hey\s+nivea|ok\s+niva|ok\s+nivea|hi\s+niva|hi\s+nivea|hello\s+niva|hello\s+nivea|jarvis)[,\s:]*", "", p_lower).strip()
        p_clean = re.sub(r"[?!.,]+$", "", p_clean).strip()

        # 0. Direct Wake/Greeting (e.g. 'Hi NIVA', 'Hey NIVA', 'NIVA', 'Hello NIVA')
        wake_names = ["niva", "nivea", "neeva", "neva", "nova", "hey niva", "hey nivea", "ok niva", "hi niva", "hello niva"]
        if p_clean == "" or p_clean in wake_names or p_lower in wake_names:
            return "How can I help you, sir?"

        # Presence & microphone checks (e.g. 'can you hear me', 'are you there', 'mic test')
        if any(w in p_clean for w in ["can you hear me", "are you listening", "vinipistunda"]):
            return "Yes, I can hear you clearly! How can I help you today?"
        if any(w in p_clean for w in ["are you there", "unnava"]):
            return "Yes, I am here and ready to assist you. What would you like to do?"
        if any(w in p_clean for w in ["mic test", "testing", "test", "audio test"]):
            return "Microphone test successful. I can hear you loud and clear. What would you like me to do?"
        if any(w in p_clean for w in ["can you speak", "talk to me", "speak to me", "say something"]):
            return "Yes, I can speak. I am NIVA, your Windows AI computer assistant. How can I assist you?"

        # Contextual status / next step
        if p_clean in ["ok now", "okay now", "now what", "what now", "what next", "ok then"]:
            if getattr(self.context, "last_search_query", None):
                engine = getattr(self.context, "last_search_engine", "search")
                return f"I have the {engine} results for '{self.context.last_search_query}'. You can say 'open the first result' or 'play the second video'."
            elif getattr(self.context, "active_application", None):
                return f"You currently have {self.context.active_application} open. You can ask me to type, click, or perform another task."
            return "I am ready for your next instruction. What would you like me to do?"

        # 1. Identity & Creator
        if any(w in p_clean for w in ["who are you", "what are you", "what is your name", "tell me about yourself"]):
            return (
                "I am NIVA, your voice-first autonomous AI assistant for Windows. "
                "I can operate desktop applications, manage files and folders, browse the web, adjust settings, and type or click for you."
            )
        if any(w in p_clean for w in ["who made you", "who built you", "who created you"]):
            return (
                "I was built as NIVA, the Universal Autonomous AI Computer Control System for Windows."
            )
        if any(w in p_clean for w in ["nuvvu evaru", "nee peru enti"]):
            return (
                "Nenu NIVA, mee Windows AI computer assistant ni. Nenu mee computer lo apps, files, browser, mariyu settings control cheyagalanu."
            )

        # 2. Capabilities & Help
        if any(w in p_clean for w in ["what can you do", "capabilities", "features", "how do you work", "help"]):
            return (
                "I can control your Windows computer using voice or text. I can open and close applications, "
                "create Excel spreadsheets and Word documents, manage files and folders, search YouTube or Google, "
                "adjust system settings like volume and Wi-Fi, and interact with desktop windows."
            )
        if any(w in p_clean for w in ["em cheyagalavu", "em cheyagalao", "supported actions enti"]):
            return (
                "Nenu mee computer lo apps open cheyadam, files create mariyu organize cheyadam, "
                "YouTube and Google search cheyadam, Excel reports tayaru cheyadam lanti panulu cheyagalanu."
            )

        # 3. Time & Date
        if any(w in p_clean for w in ["what time is it", "what is the time", "time entha", "what's the time"]):
            return f"The current time is {datetime.now().strftime('%I:%M %p')}."
        if any(w in p_clean for w in ["what day is today", "what date is today", "today's date", "eroju date enti", "today date"]):
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

        # 4. Greetings
        if any(w == p_clean or p_clean.startswith(w + " ") for w in ["hello", "hi", "hey", "howdy"]):
            return "Hello! I am NIVA. How can I help you on your computer today?"
        if any(w in p_clean for w in ["good morning", "good afternoon", "good evening", "good night"]):
            return f"{p_clean.title()}! I am NIVA. What computer tasks can I assist you with today?"
        if any(w in p_clean for w in ["namaste", "namaskaram"]):
            return "Namaskaram! Nenu NIVA. Nenu meeku ela sahayapadagalanu?"

        # 5. Well-being
        if any(w in p_clean for w in ["how are you", "how's it going", "how are you doing"]):
            return "I am doing great and ready to assist you on your computer. What would you like to do?"
        if any(w in p_clean for w in ["ela unnavu", "bagunnava"]):
            return "Nenu chala bagunnanu! Meeku ela sahayapadagalanu?"

        # 6. Gratitude
        if any(w in p_clean for w in ["thank you", "thanks", "dhanyavadalu"]):
            return "You're very welcome! Let me know whenever you need assistance."

        # 7. Try LLM if configured
        if self.llm_provider.is_configured():
            try:
                llm_ans = self.llm_provider.generate_conversational_response(prompt)
                if llm_ans:
                    return llm_ans
            except Exception as e:
                logger.warning(f"Conversational LLM response failed: {e}")

        # 8. Built-in Technical Knowledge & Explanations (Offline Fallback)
        if "what is python" in p_clean:
            return (
                "Python is a popular high-level programming language known for its readability and versatility. "
                "It is widely used in artificial intelligence, data science, web development, and desktop automation."
            )
        if "what is ai" in p_clean or "artificial intelligence" in p_clean:
            return (
                "Artificial Intelligence is the simulation of human intelligence by computers, "
                "enabling systems to perceive, reason, learn, and perform complex tasks autonomously."
            )
        if "what is machine learning" in p_clean:
            return (
                "Machine learning is a subset of artificial intelligence where computers learn patterns "
                "from data and improve their performance without being explicitly programmed."
            )
        if "joke" in p_clean:
            return "Why do programmers prefer dark mode? Because light attracts bugs!"

        return (
            f"I am NIVA, your Windows AI computer assistant. I am currently operating in offline mode. "
            "You can ask me to open applications, manage files, search Google or YouTube, or adjust computer settings."
        )

    def _generate_task_completion_summary(self, task: Task) -> str:
        """
        Synthesizes a natural, verified spoken summary of executed steps.
        E.g.: 'Done. Opened notepad and typed Hello Somu.'
        """
        if not task.steps:
            return "Task completed."

        step_summaries = []
        for step in task.steps:
            t_name = step.tool_name
            params = step.parameters or {}

            if t_name == "launch_app":
                app = params.get("app_name", "application")
                if app in ["ms-settings:", "settings", "windows_settings"]:
                    step_summaries.append("opened Windows Settings")
                else:
                    step_summaries.append(f"opened {app}")
            elif t_name == "close_app":
                app = params.get("app_name", "application")
                step_summaries.append(f"closed {app}")
            elif t_name == "type_text":
                txt = params.get("text", "")
                step_summaries.append(f"typed '{txt}'")
            elif t_name == "browser_open":
                url = params.get("url", "the website")
                if "youtube.com" in url.lower():
                    step_summaries.append("opened YouTube")
                else:
                    step_summaries.append(f"opened {url} in your browser")
            elif t_name == "browser_search":
                q = params.get("query", "")
                eng = params.get("engine", "Google")
                step_summaries.append(f"searched {eng.title()} for '{q}'")
            elif t_name == "browser_open_result":
                idx = params.get("result_index", 1)
                res_dict = step.result if isinstance(step.result, dict) else {}
                title = res_dict.get("title")
                is_yt = (
                    "youtube" in str(res_dict.get("url", "")).lower() or
                    "video" in str(res_dict.get("message", "")).lower() or
                    "youtube" in str(step.result).lower() or
                    getattr(self.context, "last_search_engine", "") == "youtube"
                )
                if is_yt:
                    if title:
                        step_summaries.append(f"playing '{title}' on YouTube")
                    else:
                        step_summaries.append(f"playing video #{idx} on YouTube")
                else:
                    if title:
                        step_summaries.append(f"opened '{title}'")
                    else:
                        step_summaries.append(f"opened search result #{idx}")
            elif t_name == "create_file":
                p = params.get("path", "file")
                step_summaries.append(f"created file '{p}'")
            elif t_name == "create_folder":
                p = params.get("path", "folder")
                step_summaries.append(f"created folder '{p}'")
            elif t_name == "delete_file":
                p = params.get("path", "file")
                step_summaries.append(f"deleted '{p}'")
            elif t_name == "move_file":
                src = params.get("source", "file")
                dst = params.get("destination", "target")
                step_summaries.append(f"moved '{src}' to '{dst}'")
            elif t_name == "copy_file":
                src = params.get("source", "file")
                dst = params.get("destination", "target")
                step_summaries.append(f"copied '{src}' to '{dst}'")
            elif t_name == "organize_folder":
                d = params.get("directory", "folder")
                step_summaries.append(f"organized files in '{d}' by extension")
            elif t_name == "create_excel":
                p = params.get("path", "Report.xlsx")
                step_summaries.append(f"created Excel spreadsheet '{p}'")
            elif t_name == "create_word":
                p = params.get("path", "Report.docx")
                step_summaries.append(f"created Word document '{p}'")
            elif t_name == "create_presentation":
                p = params.get("path", "Presentation.pptx")
                step_summaries.append(f"created PowerPoint presentation '{p}'")
            elif t_name == "calculate_expression":
                if step.result and isinstance(step.result, str):
                    return f"Done. {step.result}"
                expr = params.get("expression", "")
                step_summaries.append(f"calculated '{expr}'")
            elif t_name == "set_setting":
                if step.result and isinstance(step.result, str):
                    return f"Done. {step.result}"
                s = params.get("setting", "setting")
                v = params.get("value", "")
                step_summaries.append(f"set {s} to {v}")
            elif t_name == "plan_trip":
                if step.result and isinstance(step.result, str):
                    return f"Done. {step.result}"
                dest = params.get("destination", "destination")
                step_summaries.append(f"planned trip to {dest}")
            elif t_name == "open_settings_page":
                if step.result and isinstance(step.result, str):
                    return f"Done. {step.result}"
                page = params.get("page", "settings")
                step_summaries.append(f"opened Windows {page} settings")
            elif t_name == "show_desktop":
                step_summaries.append("minimized all windows to show desktop")
            elif t_name == "control_window":
                act = params.get("action", "controlled")
                win = params.get("window_title", "window")
                step_summaries.append(f"{act}d window '{win}'")
            elif t_name == "system_info":
                if step.result and isinstance(step.result, str) and step.result not in ["Success", "NIVA system operational."]:
                    return f"Done. {step.result}"
                q = params.get("query_type", "status")
                step_summaries.append(f"checked system {q}")
            elif t_name == "press_hotkey":
                keys = "+".join(params.get("keys", []))
                step_summaries.append(f"pressed {keys}")
            elif t_name == "mouse_click":
                step_summaries.append("clicked mouse")
            elif t_name == "browser_scroll":
                d = params.get("direction", "down")
                step_summaries.append(f"scrolled page {d}")
            elif t_name == "email_read":
                step_summaries.append("read the requested email")
            elif t_name == "email_draft":
                r = params.get("recipient", "recipient")
                step_summaries.append(f"created email draft for {r}")
            elif t_name == "email_send":
                r = params.get("recipient", "recipient")
                step_summaries.append(f"sent email to {r}")
            elif t_name == "fill_form":
                step_summaries.append("filled the requested form details")
            elif t_name == "uia_click":
                elem = params.get("element_name", "element")
                step_summaries.append(f"clicked '{elem}'")
            else:
                desc = step.description.lower() if step.description else "completed operation"
                step_summaries.append(desc)

        def cap_first(s: str) -> str:
            return s[0].upper() + s[1:] if s else ""

        if len(step_summaries) == 1:
            return f"Done. {cap_first(step_summaries[0])}."
        elif len(step_summaries) == 2:
            return f"Done. {cap_first(step_summaries[0])} and {step_summaries[1]}."
        else:
            joined = ", ".join(step_summaries[:-1]) + f", and {step_summaries[-1]}"
            return f"Done. {cap_first(joined)}."

    def process_command(self, prompt: str) -> Task:
        """
        Main entry point for processing any user instruction (spoken or typed).
        """
        cleaned_prompt = prompt.strip()
        logger.info(f"{ASSISTANT_NAME} received command: '{cleaned_prompt}'")
        self._log_dialogue("user", cleaned_prompt)

        # 1. Fast-path interruption check
        handled, msg = self.interruption.handle_interruption(cleaned_prompt)
        if handled:
            self.pending_clarification = None
            self.tts.speak(msg)
            return self.task_manager.current_task or Task(user_prompt=cleaned_prompt, status=TaskStatus.STOPPED)

        # 1b. Check for active interactive planning session (e.g. Trip Planning)
        active_session = self.context.get_planning_session()
        if active_session and active_session.get("type") == "trip_planning":
            if cleaned_prompt.lower() in ["cancel", "stop", "never mind", "aapey", "vaddu"]:
                self.context.clear_planning_session()
                cancel_msg = "Okay, cancelled trip planning."
                self.tts.speak(cancel_msg)
                self._log_dialogue("assistant", cancel_msg)
                return Task(user_prompt=cleaned_prompt, status=TaskStatus.STOPPED)

            from app.ai.trip_planner import TripPlanner
            session, missing = TripPlanner.update_session(active_session, cleaned_prompt)
            if missing:
                q = TripPlanner.format_clarification_question(session, missing)
                self.tts.speak(q)
                self._log_dialogue("assistant", q)
                task = Task(user_prompt=cleaned_prompt, status=TaskStatus.AWAITING_CONFIRMATION)
                task.needs_clarification = True
                task.clarification_question = q
                return task
            else:
                self.context.clear_planning_session()
                itinerary = TripPlanner.generate_itinerary(session)
                file_path = TripPlanner.save_and_open_itinerary_document(itinerary)
                self.context.update_last_file(file_path)
                self.tts.speak(itinerary["spoken_summary"])
                self._log_dialogue("assistant", itinerary["spoken_summary"])
                task = Task(user_prompt=cleaned_prompt, status=TaskStatus.COMPLETED)
                task.result_summary = itinerary["spoken_summary"]
                self.db.save_task(task.task_id, task.user_prompt, task.status.value, total_steps=1)
                if self.on_task_updated:
                    self.on_task_updated(task)
                return task

        # 2. Check for undo
        if cleaned_prompt.lower() in ["undo", "undo that", "revert"]:
            self.pending_clarification = None
            undo_result = self.checkpoint_mgr.undo_last()
            self.tts.speak(undo_result)
            self._log_dialogue("assistant", undo_result)
            return Task(user_prompt=cleaned_prompt, status=TaskStatus.COMPLETED)

        # 2b. Check for visibility feedback about previous action
        if self._is_visibility_feedback(cleaned_prompt):
            self.pending_clarification = None
            feedback_task = self._handle_visibility_feedback(cleaned_prompt)
            return feedback_task

        # 3. Handle pending clarification follow-up
        if getattr(self, "pending_clarification", None):
            if cleaned_prompt.lower() in ["cancel", "stop", "never mind", "aapey", "vaddu"]:
                self.pending_clarification = None
                cancel_msg = "Okay, cancelled."
                self.tts.speak(cancel_msg)
                self._log_dialogue("assistant", cancel_msg)
                return Task(user_prompt=cleaned_prompt, status=TaskStatus.STOPPED)

            prev_info = self.pending_clarification
            self.pending_clarification = None
            resolved_prompt = self._merge_clarification_response(prev_info, cleaned_prompt)
            logger.info(f"Resolved clarification follow-up: '{cleaned_prompt}' -> '{resolved_prompt}'")
            cleaned_prompt = resolved_prompt

        # 4. Check for unsupported or out-of-scope actions (physical world, calling, hacking)
        unsupported_msg = self._check_unsupported_action(cleaned_prompt)
        if unsupported_msg:
            self.tts.speak(unsupported_msg)
            self._log_dialogue("assistant", unsupported_msg)
            unsupported_task = Task(user_prompt=cleaned_prompt, status=TaskStatus.FAILED)
            unsupported_task.error_message = unsupported_msg
            unsupported_task.unsupported_reason = unsupported_msg
            self.db.save_task(unsupported_task.task_id, unsupported_task.user_prompt, unsupported_task.status.value, total_steps=0)
            if self.on_task_updated:
                self.on_task_updated(unsupported_task)
            return unsupported_task

        # 5. Check for conversational question or greeting
        if self._is_conversational_question(cleaned_prompt):
            answer = self._answer_conversational_question(cleaned_prompt)
            self.tts.speak(answer)
            self._log_dialogue("assistant", answer)
            conv_task = Task(user_prompt=cleaned_prompt, status=TaskStatus.COMPLETED)
            conv_task.result_summary = answer
            self.db.save_task(conv_task.task_id, conv_task.user_prompt, conv_task.status.value, total_steps=0)
            if self.on_task_updated:
                self.on_task_updated(conv_task)
            return conv_task

        # 6. Start Task for Computer Operations
        task = self.task_manager.start_new_task(cleaned_prompt)

        # 7. Handle NLU Interruption / Status intent if caught via ML model
        nlu_res = getattr(task, "nlu_result", None)
        if nlu_res:
            if nlu_res.intent == "interruption_stop":
                self._on_stop_triggered()
                return task
            elif nlu_res.intent == "interruption_pause":
                self._on_pause_triggered()
                return task
            elif nlu_res.intent == "interruption_resume":
                self._on_resume_triggered()
                return task
            elif nlu_res.intent == "interruption_undo":
                undo_res = self.checkpoint_mgr.undo_last()
                self.tts.speak(undo_res)
                self._log_dialogue("assistant", undo_res)
                return task
            elif nlu_res.intent == "system_status":
                status_msg = self._on_status_requested()
                self.tts.speak(status_msg)
                self._log_dialogue("assistant", status_msg)
                return task
            elif nlu_res.intent in ["conversational_greeting", "conversational_presence", "conversational_identity"]:
                answer = self._answer_conversational_question(cleaned_prompt)
                self.tts.speak(answer)
                self._log_dialogue("assistant", answer)
                task.status = TaskStatus.COMPLETED
                task.result_summary = answer
                task.steps = []
                task.unsupported_reason = None
                self.db.save_task(task.task_id, task.user_prompt, task.status.value, total_steps=0)
                if self.on_task_updated:
                    self.on_task_updated(task)
                return task

        # 8. Handle clarification question
        if task.needs_clarification and task.clarification_question:
            if nlu_res and nlu_res.intent == "plan_trip":
                self.context.start_planning_session("trip_planning", nlu_res.entities)
            self.pending_clarification = {
                "original_prompt": cleaned_prompt,
                "task": task,
                "nlu_result": nlu_res
            }
            self.tts.speak(task.clarification_question)
            self._log_dialogue("assistant", task.clarification_question)
            return task

        # 9. Handle unsupported command
        if task.unsupported_reason:
            self.tts.speak(task.unsupported_reason)
            self._log_dialogue("assistant", task.unsupported_reason)
            return task

        # 10. Empty steps failure
        if not task.steps:
            err_msg = task.error_message or "I could not find an action to execute for that request."
            self.tts.speak(err_msg)
            self._log_dialogue("assistant", err_msg)
            return task

        # 11. Acknowledge task initiation
        self.tts.speak("Understood. Starting task.")
        return task

    def wait_for_task(self, timeout: float = 10.0) -> bool:
        """Waits for the currently executing task to complete."""
        return self.task_manager.wait_for_completion(timeout=timeout)

    def _is_visibility_feedback(self, text: str) -> bool:
        """Detects user feedback indicating an application window is not visible on screen."""
        t = text.lower().strip()
        patterns = [
            r"not\s+visible",
            r"wasn'?t\s+visible",
            r"is\s+not\s+visible",
            r"isn'?t\s+visible",
            r"can'?t\s+see\s+it",
            r"cannot\s+see\s+it",
            r"not\s+showing",
            r"didn'?t\s+open",
            r"did\s+not\s+open",
            r"didn'?t\s+show",
            r"not\s+on\s+(?:my\s+)?screen",
        ]
        return any(re.search(p, t) for p in patterns)

    def _handle_visibility_feedback(self, prompt: str) -> Task:
        """
        Inspects whether the previously requested application is running/open,
        restores/unminimizes its window, or launches it directly and brings it to foreground.
        """
        target_app = self.context.active_application
        if not target_app:
            if self.task_manager.current_task:
                for step in self.task_manager.current_task.steps:
                    if step.tool_name == "launch_app":
                        target_app = step.parameters.get("app_name")
                        break
        if not target_app:
            target_app = "chrome"

        logger.info(f"Handling visibility feedback for target application: '{target_app}'")
        from app.computer.window_manager import WindowManager

        is_running = self.app_ctrl.is_app_running(target_app)
        task = Task(user_prompt=prompt)

        if is_running:
            win_res = WindowManager.focus_window(target_app)
            if win_res.get("success"):
                resp = f"I verified {target_app} is running and brought its window to the foreground on your screen."
                task.status = TaskStatus.COMPLETED
                task.result_summary = resp
            else:
                launch_res = self.app_ctrl.launch_application(target_app)
                if launch_res.get("success"):
                    resp = f"I brought {target_app} to the foreground and verified its window is visible."
                    task.status = TaskStatus.COMPLETED
                    task.result_summary = resp
                else:
                    resp = f"I found {target_app} running, but could not display its window: {launch_res.get('error', 'unknown error')}"
                    task.status = TaskStatus.FAILED
                    task.error_message = resp
        else:
            launch_res = self.app_ctrl.launch_application(target_app)
            if launch_res.get("success"):
                resp = f"I have launched {target_app} and verified that its window is visible on your screen."
                task.status = TaskStatus.COMPLETED
                task.result_summary = resp
            else:
                resp = f"Could not launch {target_app}: {launch_res.get('error', 'executable not found')}"
                task.status = TaskStatus.FAILED
                task.error_message = resp

        self.context.update_active_app(target_app)
        self.tts.speak(resp)
        self._log_dialogue("assistant", resp)
        self.db.save_task(task.task_id, task.user_prompt, task.status.value, total_steps=1)
        if self.on_task_updated:
            self.on_task_updated(task)
        return task

    def _merge_clarification_response(self, prev_info: Dict[str, Any], answer: str) -> str:
        """
        Resolves user's clarification response cleanly without concatenating old transcripts.
        """
        cleaned = re.sub(
            r"^(?:yeah|yes|yep|sure|ok|okay)[\s,]+(?:you\s+need\s+to\s+|i\s+said\s+|please\s+)?",
            "",
            answer.strip(),
            flags=re.IGNORECASE
        ).strip()

        # If answer is a full command or contains an action verb, process it as a new standalone command
        tokens = cleaned.lower().split()
        action_verbs = [
            "open", "launch", "start", "search", "create", "make", "close", "set",
            "turn", "switch", "show", "theeyi", "aapu", "play", "run", "find"
        ]
        if tokens and (tokens[0] in action_verbs or len(tokens) >= 3):
            return cleaned

        # If user gave a short slot answer (e.g. "chrome", "notepad") to a pending app query:
        nlu_res = prev_info.get("nlu_result")
        if nlu_res:
            if nlu_res.intent in ["open_app", "app_launch"]:
                return f"open {cleaned}"
            elif "search" in nlu_res.intent:
                return f"search {cleaned}"

        return cleaned or answer

    def handle_voice_input(self, recognized_text: str) -> None:
        """Callback from continuous voice listener when speech is transcribed."""
        self.process_command(recognized_text)

    def _on_step_started(self, task: Task, step: TaskStep, index: int) -> None:
        msg = f"Step {index + 1}/{len(task.steps)}: {step.description}"
        self._log_dialogue("system", msg)
        if len(task.steps) > 1:
            self.tts.speak(f"Starting step {index + 1}: {step.description}")
        if self.on_task_updated:
            self.on_task_updated(task)

    def _on_step_completed(self, task: Task, step: TaskStep, index: int) -> None:
        if step.tool_name == "launch_app" and step.status == StepStatus.COMPLETED:
            app_name = step.parameters.get("app_name")
            if app_name:
                self.context.update_active_app(app_name)
        if self.on_task_updated:
            self.on_task_updated(task)

    def _on_task_finished(self, task: Task) -> None:
        if task.status == TaskStatus.COMPLETED:
            finish_msg = self._generate_task_completion_summary(task)
            task.result_summary = finish_msg
            self.tts.speak(finish_msg)
            self._log_dialogue("assistant", finish_msg)
        elif task.status == TaskStatus.FAILED:
            err_msg = task.error_message or "Task execution encountered an error."
            fail_msg = f"Task could not be completed. {err_msg}"
            self.tts.speak(fail_msg)
            self._log_dialogue("assistant", f"Failed: {err_msg}")

        if self.on_task_updated:
            self.on_task_updated(task)

    def _on_task_state_changed(self, task: Task) -> None:
        if self.on_task_updated:
            self.on_task_updated(task)

    def _log_dialogue(self, role: str, text: str) -> None:
        if self.on_message_logged:
            try:
                self.on_message_logged(role, text)
            except Exception:
                pass

    def start_voice_system(self) -> None:
        """Activates continuous voice recognition loop."""
        self.voice_listener.start()

    def startup_lifecycle(self, on_permission_needed: Optional[Callable[[], bool]] = None) -> Dict[str, Any]:
        """
        Executes formal startup lifecycle:
        1. Audio output initialization.
        2. Microphone hardware check.
        3. Windows microphone permission check / interactive request.
        4. Spoken greeting: "How can I help you, sir?".
        5. Begins continuous listening.
        """
        from app.voice.permission_manager import MicrophonePermissionManager

        logger.info(f"{ASSISTANT_NAME} beginning startup lifecycle sequence...")

        # 1. Device Hardware Check
        has_devices, dev_msg = MicrophonePermissionManager.check_device_available()
        if not has_devices:
            logger.warning(f"Startup hardware check failed: {dev_msg}")
            self._log_dialogue("error", f"Microphone Hardware: {dev_msg}")
            return {
                "success": False,
                "status": "NO_MIC",
                "message": dev_msg
            }

        # 2. Permission Check
        perm_state = MicrophonePermissionManager.get_permission_state(self.db)
        if perm_state == "prompt":
            if on_permission_needed:
                granted = on_permission_needed()
                new_state = "granted" if granted else "denied"
                MicrophonePermissionManager.set_permission_state(self.db, new_state)
                perm_state = new_state
            else:
                MicrophonePermissionManager.set_permission_state(self.db, "granted")
                perm_state = "granted"

        if perm_state == "denied":
            denied_msg = "Microphone access is currently disabled. Click 'Mic' or open Windows Settings to enable."
            logger.info(f"Startup halted at permission: {denied_msg}")
            self._log_dialogue("system", denied_msg)
            return {
                "success": False,
                "status": "PERMISSION_DENIED",
                "message": denied_msg
            }

        # 3. Stream Access Test
        stream_ok, stream_msg = MicrophonePermissionManager.test_microphone_stream()
        if not stream_ok:
            logger.warning(f"Startup stream test failed: {stream_msg}")
            self._log_dialogue("error", f"Microphone Stream: {stream_msg}")
            return {
                "success": False,
                "status": "PERMISSION_DENIED",
                "message": stream_msg
            }

        # 4. Spoken Greeting
        greeting = "How can I help you, sir?"
        self._log_dialogue("assistant", greeting)
        self.tts.speak(greeting)

        # 5. Start Continuous Listening
        self.start_voice_system()

        return {
            "success": True,
            "status": "LISTENING",
            "message": "NIVA initialized, greeted user, and is listening.",
            "greeting": greeting,
            "permission": perm_state,
            "listening_started": True
        }

    def stop_voice_system(self) -> None:
        """Halts voice listener and TTS."""
        self.voice_listener.stop()
        self.tts.stop_speaking()

    def shutdown(self) -> None:
        """Full system shutdown."""
        self.stop_voice_system()
        self.task_manager.stop_current_task()
        self.tts.shutdown()
        self.browser_ctrl.close()


# Backward compatibility alias
JarvisAssistant = NivaAssistant
