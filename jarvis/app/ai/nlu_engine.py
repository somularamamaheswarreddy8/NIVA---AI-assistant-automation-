"""
Runtime NLU Engine for NIVA.
Loads the trained Machine Learning NLU model, computes calibrated intent probabilities,
performs slot extraction across English and Telugu-English phrasing, handles clarification
prompts for ambiguous/low-confidence requests, and plans multi-step tool calls.
"""

from dataclasses import dataclass, field
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import joblib

logger = logging.getLogger("NIVA.NLUEngine")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "nlu_model.joblib")
METADATA_PATH = os.path.join(BASE_DIR, "models", "nlu_metadata.json")


@dataclass
class NLUResult:
    utterance: str
    intent: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    is_multistep: bool = False
    planned_steps: List[Dict[str, Any]] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    requires_confirmation: bool = False
    is_supported: bool = True
    unsupported_reason: Optional[str] = None


class NLUEngine:
    """Inference engine connecting trained statistical NLU model to runtime assistant execution."""

    # Confidence threshold below which NIVA asks for clarification instead of guessing
    CONFIDENCE_THRESHOLD = 0.40

    # Known application alias dictionary for robust entity normalization
    APP_ALIASES = {
        "chrome": ["chrome", "google chrome", "chrome browser", "googlechrome", "the chrome browser"],
        "notepad": ["notepad", "text editor", "notepad.exe", "note pad"],
        "calculator": ["calc", "calculator", "calculator app", "calc.exe"],
        "vscode": ["vs code", "vscode", "visual studio code", "code editor", "code"],
        "excel": ["excel", "microsoft excel", "excel sheet", "excel app", "spreadsheet"],
        "word": ["word", "microsoft word", "word doc", "word document", "winword"],
        "powerpoint": ["powerpoint", "ppt", "microsoft powerpoint", "powerpnt", "slides"],
        "terminal": ["terminal", "windows terminal", "wt", "wt.exe"],
        "cmd": ["cmd", "command prompt", "console", "cmd.exe"],
        "powershell": ["powershell", "powershell terminal", "powershell.exe"],
        "edge": ["edge", "microsoft edge", "ms edge", "edge browser"],
        "browser": ["browser", "the browser", "web browser", "internet browser", "chrome", "google chrome"],
        "paint": ["paint", "mspaint", "paint app", "mspaint.exe"],
        "settings": ["settings", "windows settings", "pc settings", "system settings"],
        "explorer": ["explorer", "file explorer", "file manager"],
        "youtube": ["youtube", "yt", "youtube.com"],
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or MODEL_PATH
        self.pipeline = None
        self.metadata = {}
        self._load_model()

    def _load_model(self) -> None:
        if os.path.exists(self.model_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                logger.info(f"Loaded trained NLU model from: {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load NLU model: {e}")
                self.pipeline = None
        else:
            logger.warning(f"NLU model not found at: {self.model_path}. Train model using train_nlu.py.")

        if os.path.exists(METADATA_PATH):
            try:
                with open(METADATA_PATH, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception:
                pass

    def parse(self, text: str, context: Optional[Dict[str, Any]] = None) -> NLUResult:
        """
        Interprets natural language text (English, Telugu-Latn, or Code-mixed).
        Returns structured NLUResult.
        """
        cleaned = self._clean_utterance(text)

        # 1. Multi-step command detection & splitting
        sub_clauses = self._split_multistep(cleaned)
        if len(sub_clauses) > 1:
            return self._handle_multistep(cleaned, sub_clauses, context)

        # Single-word generic prompts: Ask specific clarification
        if cleaned.lower() in ["search", "search for", "google", "vetuku", "look up"]:
            return NLUResult(
                utterance=cleaned,
                intent="browser_search",
                confidence=0.85,
                needs_clarification=True,
                clarification_question="What would you like me to search for?"
            )
        if cleaned.lower() in ["open", "launch", "start", "theeyi", "open chey"]:
            return NLUResult(
                utterance=cleaned,
                intent="app_launch",
                confidence=0.85,
                needs_clarification=True,
                clarification_question="Which application would you like me to open?"
            )

        # Contextual result navigation (e.g. 'play the second video', 'open the third result')
        ref_idx = self._extract_result_index(cleaned)
        if ref_idx is not None:
            return NLUResult(
                utterance=cleaned,
                intent="browser_open_result",
                confidence=0.95,
                entities={"result_index": ref_idx},
                is_multistep=False,
                planned_steps=[{
                    "tool_name": "browser_open_result",
                    "parameters": {"result_index": ref_idx},
                    "description": f"Open search result #{ref_idx}"
                }]
            )

        # Math & Calculator Commands:
        # Handles arithmetic expressions like "Add 2+2", "2+2", "What is 15 times 6?",
        # "subtract 8 from 20", "divide 24 by 3", or contextual inputs when Calculator is active
        from app.automation.calculator_automation import parse_math_phrase
        math_expr = parse_math_phrase(cleaned)
        active_app = (str(context.get("active_application", "")) if context and context.get("active_application") else "").lower()

        if not math_expr and active_app == "calculator":
            c_arith = re.sub(r"^(?:add|calculate|compute|solve|eval|evaluate)\s+", "", cleaned, flags=re.IGNORECASE).strip()
            c_arith = c_arith.rstrip("?!.;")
            if re.match(r"^[0-9\s\+\-\*\/\%\(\)\.]+$", c_arith):
                math_expr = c_arith

        if math_expr:
            in_calc = (active_app == "calculator")
            planned = {
                "tool_name": "calculate_expression",
                "parameters": {"expression": math_expr, "ensure_open": in_calc},
                "description": f"Calculate '{math_expr}'{' in Calculator' if in_calc else ''}"
            }
            return NLUResult(
                utterance=cleaned,
                intent="calculator_calculate",
                confidence=0.98,
                entities={"expression": math_expr, "in_calculator": in_calc},
                is_multistep=False,
                planned_steps=[planned]
            )

        # Interactive Trip Planning:
        # e.g. "plan a trip for seven days", "help me plan a trip", "plan a vacation"
        from app.ai.trip_planner import TripPlanner
        if TripPlanner.is_trip_planning_request(cleaned):
            slots = TripPlanner.extract_trip_slots(cleaned)
            missing = TripPlanner.get_missing_requirements(slots)
            if missing:
                q = TripPlanner.format_clarification_question(slots, missing)
                return NLUResult(
                    utterance=cleaned,
                    intent="plan_trip",
                    confidence=0.98,
                    entities=slots,
                    is_multistep=False,
                    needs_clarification=True,
                    clarification_question=q
                )
            else:
                planned = {
                    "tool_name": "plan_trip",
                    "parameters": slots,
                    "description": f"Plan {slots.get('duration', '7-day')} trip to {slots.get('destination', 'destination')}"
                }
                return NLUResult(
                    utterance=cleaned,
                    intent="plan_trip",
                    confidence=0.98,
                    entities=slots,
                    is_multistep=False,
                    planned_steps=[planned]
                )

        # Settings Section Navigation:
        # e.g. "open the brightness section of the laptop", "open brightness section", "go to sound section"
        m_section = re.search(
            r"^(?:please\s+)?(?:open|go\s+to|show|navigate\s+to)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+section|\s+page|\s+tab)?(?:\s+of\s+the\s+(?:laptop|pc|computer|system|settings))?$",
            cleaned,
            re.IGNORECASE
        )
        known_sections = {
            "brightness": "brightness",
            "display": "display",
            "screen": "display",
            "monitor": "display",
            "sound": "sound",
            "volume": "sound",
            "audio": "sound",
            "bluetooth": "bluetooth",
            "wifi": "wifi",
            "wi-fi": "wifi",
            "network": "network",
            "internet": "network",
            "battery": "battery",
            "power": "battery",
            "battery saver": "battery",
            "storage": "storage",
            "disk": "storage",
            "apps": "apps",
            "applications": "apps",
            "installed apps": "apps",
            "update": "windows_update",
            "updates": "windows_update",
            "windows update": "windows_update",
            "notifications": "notifications",
            "privacy": "privacy",
            "mic privacy": "microphone_privacy",
            "microphone privacy": "microphone_privacy",
            "system": "system",
            "about": "system",
            "about pc": "system",
        }
        if m_section:
            raw_sec = m_section.group(1).lower().strip()
            if raw_sec in known_sections:
                sec_page = known_sections[raw_sec]
                planned = {
                    "tool_name": "open_settings_page",
                    "parameters": {"page": sec_page},
                    "description": f"Open Windows {sec_page.title()} Settings section"
                }
                return NLUResult(
                    utterance=cleaned,
                    intent=f"setting_open_{sec_page}",
                    confidence=0.98,
                    entities={"page": sec_page, "app_name": "settings"},
                    is_multistep=False,
                    planned_steps=[planned]
                )

        if active_app == "settings" and cleaned.lower() in known_sections:
            sec_page = known_sections[cleaned.lower()]
            planned = {
                "tool_name": "open_settings_page",
                "parameters": {"page": sec_page},
                "description": f"Open Windows {sec_page.title()} Settings section"
            }
            return NLUResult(
                utterance=cleaned,
                intent=f"setting_open_{sec_page}",
                confidence=0.98,
                entities={"page": sec_page, "app_name": "settings"},
                is_multistep=False,
                planned_steps=[planned]
            )

        # Built-in direct action shortcuts:
        c_low = cleaned.lower()
        if c_low in ["open settings", "open windows settings", "settings", "windows settings"]:
            return NLUResult(
                utterance=cleaned,
                intent="setting_open_system",
                confidence=0.95,
                entities={"page": "system", "app_name": "settings"},
                is_multistep=False,
                planned_steps=[{
                    "tool_name": "open_settings_page",
                    "parameters": {"page": "system"},
                    "description": "Open Windows Settings"
                }]
            )

        if c_low in ["open browser", "open the browser", "open web browser", "open the web browser", "open my browser"]:
            return NLUResult(
                utterance=cleaned,
                intent="app_launch",
                confidence=0.95,
                entities={"app_name": "chrome"},
                is_multistep=False,
                planned_steps=[{
                    "tool_name": "launch_app",
                    "parameters": {"app_name": "chrome"},
                    "description": "Launch application 'chrome'"
                }]
            )

        if c_low in ["open youtube", "open youtube.com", "youtube open chey"]:
            return NLUResult(
                utterance=cleaned,
                intent="browser_open",
                confidence=0.95,
                entities={"url": "https://www.youtube.com"},
                is_multistep=False,
                planned_steps=[{
                    "tool_name": "browser_open",
                    "parameters": {"url": "https://www.youtube.com"},
                    "description": "Open YouTube website in browser"
                }]
            )

        # Organize folder direct matching
        if ("organize" in c_low or "clean up" in c_low) and any(w in c_low for w in ["desktop", "downloads", "documents", "files", "type"]):
            target_d = "Desktop" if "desktop" in c_low else ("Downloads" if "download" in c_low else ("Documents" if "document" in c_low else "Desktop"))
            return NLUResult(
                utterance=cleaned,
                intent="folder_organize_by_type",
                confidence=0.95,
                entities={"directory": target_d, "target_dir": target_d},
                is_multistep=False,
                planned_steps=[{
                    "tool_name": "organize_folder",
                    "parameters": {"directory": target_d},
                    "description": f"Organize '{target_d}' by file extension"
                }]
            )

        # Accessible element clicks: e.g. "click the search button", "click search"
        m_click = re.search(r"^(?:please\s+)?(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+button|\s+icon|\s+link)?$", cleaned, re.IGNORECASE)
        if m_click:
            target_elem = m_click.group(1).strip()
            if target_elem.lower() not in ["window", "screen", "here", "it", "that", "there"]:
                c_type = "Button" if "button" in cleaned.lower() else ("Hyperlink" if "link" in cleaned.lower() else None)
                clean_target = re.sub(r"^(?:the|that|this|a|an)\s+", "", target_elem, flags=re.IGNORECASE).strip()
                return NLUResult(
                    utterance=cleaned,
                    intent="mouse_click_element",
                    confidence=0.95,
                    entities={"element_name": clean_target.title(), "control_type": c_type},
                    is_multistep=False,
                    planned_steps=[{
                        "tool_name": "uia_click",
                        "parameters": {"window_title": "", "element_name": clean_target.title(), "control_type": c_type},
                        "description": f"Click accessible element '{clean_target.title()}'"
                    }]
                )

        # Direct web / search commands: e.g. "search for python tutorials", "search youtube for python tutorials"
        if re.search(r"\b(?:there|akkada)\b", cleaned, re.IGNORECASE) and any(w in cleaned.lower() for w in ["search", "vetuku", "find", "choodu"]):
            s_entities = self._extract_slots("browser_search_there", cleaned, context)
            planned = self._map_to_tool_call("browser_search_there", s_entities, cleaned)
            return NLUResult(
                utterance=cleaned,
                intent="browser_search_there",
                confidence=0.95,
                entities=s_entities,
                is_multistep=False,
                planned_steps=[planned] if planned else []
            )

        # Direct browser scrolling shortcuts
        c_low_scroll = cleaned.lower()
        if any(c_low_scroll.startswith(p) for p in ["scroll down", "go page down", "page down", "scroll page down"]):
            planned = {
                "tool_name": "browser_scroll",
                "parameters": {"direction": "down", "amount": "page"},
                "description": "Scroll down one page"
            }
            return NLUResult(
                utterance=cleaned,
                intent="browser_scroll_down",
                confidence=0.95,
                entities={"direction": "down", "amount": "page"},
                is_multistep=False,
                planned_steps=[planned]
            )
        if any(c_low_scroll.startswith(p) for p in ["scroll up", "go page up", "page up", "scroll page up"]):
            planned = {
                "tool_name": "browser_scroll",
                "parameters": {"direction": "up", "amount": "page"},
                "description": "Scroll up one page"
            }
            return NLUResult(
                utterance=cleaned,
                intent="browser_scroll_up",
                confidence=0.95,
                entities={"direction": "up", "amount": "page"},
                is_multistep=False,
                planned_steps=[planned]
            )

        m_search = re.match(r"^(?:please\s+)?(?:search|find|look up|google)\s+(?:for\s+)?(.+)$", cleaned, re.IGNORECASE)
        if m_search:
            s_entities = self._extract_slots("browser_search", cleaned, context)
            if s_entities.get("query"):
                eng = s_entities.get("engine", "google")
                if context and "youtube" in str(context.get("last_browser_url", "")).lower():
                    eng = "youtube"
                    s_entities["engine"] = "youtube"
                planned = self._map_to_tool_call("browser_search", s_entities, cleaned)
                return NLUResult(
                    utterance=cleaned,
                    intent=f"browser_search_{eng}" if eng in ["google", "youtube", "bing"] else "browser_search",
                    confidence=0.95,
                    entities=s_entities,
                    is_multistep=False,
                    planned_steps=[planned] if planned else []
                )

        # 2. Single-step intent classification via trained ML model
        if self.pipeline is not None:
            try:
                probs = self.pipeline.predict_proba([cleaned])[0]
                classes = self.pipeline.classes_
                sorted_indices = probs.argsort()[::-1]
                # Filter out compound_multistep since this is a single clause
                for idx in sorted_indices:
                    cand_intent = classes[idx]
                    if cand_intent != "compound_multistep":
                        top_intent = cand_intent
                        top_conf = float(probs[idx])
                        break
                else:
                    top_idx = sorted_indices[0]
                    top_intent = classes[top_idx]
                    top_conf = float(probs[top_idx])
            except Exception as e:
                logger.error(f"Model prediction error: {e}")
                top_intent = "unknown"
                top_conf = 0.0
        else:
            top_intent = "unknown"
            top_conf = 0.0

        logger.info(f"NLU Classification: '{cleaned}' -> Intent: {top_intent} (Confidence: {top_conf:.2f})")

        # 3. Low-confidence check: Ask clarification question
        if top_conf < self.CONFIDENCE_THRESHOLD:
            logger.warning(f"Confidence {top_conf:.2f} is below threshold {self.CONFIDENCE_THRESHOLD}")
            return NLUResult(
                utterance=cleaned,
                intent="clarification_needed",
                confidence=top_conf,
                needs_clarification=True,
                clarification_question="Which application or task would you like me to run?"
            )

        # 4. Extract slots for the classified intent
        entities = self._extract_slots(top_intent, cleaned, context)

        # 5. Missing required slot check
        missing_clarification = self._check_missing_slots(top_intent, entities, cleaned)
        if missing_clarification:
            return NLUResult(
                utterance=cleaned,
                intent=top_intent,
                confidence=top_conf,
                entities=entities,
                needs_clarification=True,
                clarification_question=missing_clarification
            )

        # 6. Map to executable planned tool call
        planned_step = self._map_to_tool_call(top_intent, entities, cleaned)
        requires_confirm = (
            top_intent in [
                "delete_file", "file_delete", "file_delete_permanent", "folder_delete",
                "shutdown_computer", "format_drive", "app_kill_force",
                "email_send", "form_submit"
            ]
            or any(k in top_intent for k in ["delete", "email_send", "form_submit", "kill_force"])
            or (planned_step is not None and planned_step.get("requires_confirmation", False))
        )

        return NLUResult(
            utterance=cleaned,
            intent=top_intent,
            confidence=top_conf,
            entities=entities,
            is_multistep=False,
            planned_steps=[planned_step] if planned_step else [],
            requires_confirmation=requires_confirm
        )

    @staticmethod
    def _extract_result_index(text: str) -> Optional[int]:
        ord_map = {
            "first": 1, "1st": 1, "one": 1, "1": 1,
            "second": 2, "2nd": 2, "two": 2, "2": 2,
            "third": 3, "3rd": 3, "three": 3, "3": 3,
            "fourth": 4, "4th": 4, "four": 4, "4": 4,
            "fifth": 5, "5th": 5, "five": 5, "5": 5,
            "sixth": 6, "6th": 6, "6": 6,
        }
        m = re.search(r"(?:open|play|click|watch|navigate\s+to)\s+(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|sixth|6th|\d+)(?:st|nd|rd|th)?\s+(?:video|result|link|song|website|site|item|option)", text, re.IGNORECASE)
        if m:
            val = m.group(1).lower()
            return ord_map.get(val, int(val) if val.isdigit() else 1)
        m2 = re.search(r"^(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|\d+)(?:st|nd|rd|th)?\s+(?:video|result|link|website|site|item|option)$", text.strip(), re.IGNORECASE)
        if m2:
            val = m2.group(1).lower()
            return ord_map.get(val, int(val) if val.isdigit() else 1)
        m3 = re.search(r"(?:open|play|click|watch|navigate\s+to)?\s*(?:the\s+)?(?:result|video|link|item)\s*#?\s*(\d+)", text.strip(), re.IGNORECASE)
        if m3:
            return int(m3.group(1))
        return None

    def _clean_utterance(self, text: str) -> str:
        """Normalizes wake word prefixes, affirmative conversational fillers, and spacing."""
        cleaned = text.strip()
        # Remove wake word variations at start
        cleaned = re.sub(r"^(?:niva|nivea|neeva|neva|nova|hey\s+niva|hey\s+nivea|ok\s+niva|ok\s+nivea|hi\s+niva|hi\s+nivea|hello\s+niva|hello\s+nivea|jarvis)[,\s:]*", "", cleaned, flags=re.IGNORECASE).strip()
        # Strip colloquial leading affirmatives / fillers like "yeah, you need to open...", "yeah, I said open...", "yes, please open..."
        cleaned = re.sub(
            r"^(?:yeah|yes|yep|sure|ok|okay)[\s,]+(?:you\s+need\s+to\s+|i\s+said\s+|please\s+)?",
            "",
            cleaned,
            flags=re.IGNORECASE
        ).strip()
        # Strip trailing generic save / calculation phrases that belong to file creation actions
        cleaned = re.sub(
            r"(?:,\s*)?(?:and\s+)?(?:calculate\s+the\s+total[,\s]*)?(?:and\s+)?save(?:\s+it|\s+that|\s+file)?$",
            "",
            cleaned,
            flags=re.IGNORECASE
        ).strip()
        return cleaned

    def _split_multistep(self, text: str) -> List[str]:
        """Splits compound utterances into individual action clauses."""
        # Connectors across English and Telugu (chesi, tharuvatha, and then, then)
        split_pattern = r"(?:\s+and\s+then\s+|\s+then\s+|\s+after\s+that\s+|;\s*|\s*,\s*and\s+|\s+chesi\s+|\s+tharuvatha\s+|\s+and\s+(?=open|launch|create|search|turn|close|make|write|play|click|set|organize|clean|calculate|theeyi|aapu))"
        parts = re.split(split_pattern, text, flags=re.IGNORECASE)
        results = []
        for p in parts:
            p_strip = p.strip()
            # Ignore trailing generic save phrases that belong to file creation actions
            if p_strip and not re.match(r"^(?:and\s+)?save(?:\s+it|\s+that|\s+file)?$", p_strip, re.IGNORECASE):
                results.append(p_strip)
        return results if results else [text]

    def _handle_multistep(self, original: str, sub_clauses: List[str], context: Optional[Dict[str, Any]] = None) -> NLUResult:
        logger.info(f"Handling compound multi-step request with {len(sub_clauses)} clauses: {sub_clauses}")
        steps = []
        ctx = dict(context or {})

        for clause in sub_clauses:
            single_res = self.parse(clause, ctx)
            if single_res.needs_clarification:
                return single_res
            if single_res.planned_steps:
                for s in single_res.planned_steps:
                    # Deduplicate consecutive identical operations
                    if steps and steps[-1]["tool_name"] == s["tool_name"] and steps[-1].get("parameters") == s.get("parameters"):
                        continue
                    steps.append(s)
                    # Pass context forwards
                    if s["tool_name"] == "create_folder":
                        ctx["last_created_folder"] = s["parameters"].get("path")
                    elif s["tool_name"] == "launch_app":
                        ctx["last_app"] = s["parameters"].get("app_name")
                    elif s["tool_name"] == "browser_open":
                        ctx["last_browser_url"] = s["parameters"].get("url")

        return NLUResult(
            utterance=original,
            intent="compound_multistep",
            confidence=0.95,
            is_multistep=True,
            planned_steps=steps,
            requires_confirmation=any(s.get("requires_confirmation", False) for s in steps)
        )

    def _extract_slots(self, intent: str, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extracts and normalizes domain-specific slots/entities."""
        t_lower = text.lower()
        slots: Dict[str, Any] = {}

        # 1. Application resolution
        for app_key, aliases in self.APP_ALIASES.items():
            for a in aliases:
                # Word boundary check
                if re.search(rf"\b{re.escape(a)}\b", t_lower):
                    slots["app_name"] = app_key
                    break
            if "app_name" in slots:
                break

        if "app_name" not in slots and intent in ["open_app", "app_launch"]:
            m_app = re.search(r"(?:open|launch|start|run|theeyi)\s+(?:the\s+|my\s+)?([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
            if m_app:
                cand = m_app.group(1).strip().lower()
                if cand not in ["a", "an", "the", "this", "that", "it", "file", "folder", "window", "link", "video", "result"]:
                    slots["app_name"] = cand

        if slots.get("app_name") in ["browser", "web browser", "internet"]:
            slots["app_name"] = "chrome"

        # 2. Browser search query extraction
        if intent in ["browser_search", "context_clarify_query", "browser_search_there"] or intent.startswith("browser_search"):
            # Search engine
            if intent == "browser_search_youtube" or "youtube" in t_lower or "yt" in t_lower:
                slots["engine"] = "youtube"
            elif intent == "browser_search_bing" or "bing" in t_lower:
                slots["engine"] = "bing"
            elif intent == "browser_search_there" or "there" in t_lower or "akkada" in t_lower:
                eng = "youtube"
                if context:
                    if context.get("last_search_engine"):
                        eng = context.get("last_search_engine")
                    elif "youtube" in str(context.get("last_browser_url", "")).lower():
                        eng = "youtube"
                    elif "google" in str(context.get("last_browser_url", "")).lower():
                        eng = "google"
                slots["engine"] = eng
            else:
                slots["engine"] = "google"

            # Extract search query
            # Patterns:
            # - "youtube lo X search chey"
            # - "search youtube for X"
            # - "search for X on youtube"
            # - "search X"
            m_tel = re.search(r"(?:youtube|google|bing)\s+lo\s+(.+?)\s+(?:search|vetuku|choodu|pettu)", t_lower)
            m_yt_for = re.search(r"(?:search|find|look up)\s+(?:youtube|google|bing)\s+(?:for\s+)?(.+?)$", t_lower)
            m_for_on = re.search(r"(?:search|find|look up|google)\s+(?:for\s+)?(.+?)(?:\s+(?:on|in)\s+(?:youtube|google|bing))?$", t_lower)

            if m_tel:
                q = m_tel.group(1).strip()
            elif m_yt_for:
                q = m_yt_for.group(1).strip()
            elif m_for_on:
                q = m_for_on.group(1).strip()
            else:
                q = re.sub(r"\b(?:search|find|google|look up|youtube|on|in|lo)\b", "", t_lower).strip()

            # Clean trailing instructions or clauses that might have slipped into query
            q = re.sub(r"\s+and\s+(?:play|open|click|watch|start|run).*$", "", q, flags=re.IGNORECASE)
            q = re.sub(r"\s+(?:on|in)\s+(?:youtube|google|bing)$", "", q, flags=re.IGNORECASE).strip()
            q = re.sub(r"\b(?:there|akkada|now|right\s+now|for\s+me|please)\b", "", q, flags=re.IGNORECASE).strip()
            slots["query"] = q or "songs"

        if intent in ["browser_scroll_down", "browser_scroll_up", "keyboard_scroll_down", "keyboard_scroll_up"]:
            slots["direction"] = "down" if "down" in intent or "down" in t_lower else "up"
            slots["amount"] = "page"

        if intent.startswith("email_"):
            m_rec = re.search(r"(?:to|for)\s+([a-zA-Z0-9_\-\.]+@[a-zA-Z0-9_\-\.]+|[a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
            slots["recipient"] = m_rec.group(1).strip() if m_rec else "prof.sharma@university.edu"

            m_sub = re.search(r"(?:with\s+subject|subject|regarding)\s+(.+?)(?:\s+and\s+(?:message|body)|$)", text, re.IGNORECASE)
            slots["subject"] = m_sub.group(1).strip() if m_sub else "Project Review Schedule"

            m_body = re.search(r"(?:and\s+message|message|body|saying)\s+(.+)$", text, re.IGNORECASE)
            slots["body"] = m_body.group(1).strip() if m_body else "Here is the updated documentation."

            if intent == "email_read":
                m_from = re.search(r"(?:from|by|about)\s+([a-zA-Z0-9_\-\.]+)", text, re.IGNORECASE)
                if m_from:
                    slots["query_or_filter"] = m_from.group(1).strip()
                elif any(w in t_lower for w in ["latest", "recent", "new"]):
                    slots["query_or_filter"] = "latest"
                elif "unread" in t_lower:
                    slots["query_or_filter"] = "unread"
                else:
                    slots["query_or_filter"] = "latest"

        if intent.startswith("form_"):
            fields = {}
            m_name = re.search(r"name\s+(?:is\s+)?([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
            if m_name:
                fields["Name"] = m_name.group(1).strip()
            m_email = re.search(r"email\s+(?:is\s+)?([a-zA-Z0-9_\-\.]+@[a-zA-Z0-9_\-\.]+)", text, re.IGNORECASE)
            if m_email:
                fields["Email"] = m_email.group(1).strip()
            if not fields:
                fields = {"Name": "Somu", "Email": "somu@college.edu"}
            slots["field_mappings"] = fields

        if intent in ["browser_open_result", "youtube_play_result"]:
            idx = self._extract_result_index(text)
            slots["result_index"] = idx if idx else 1

        # 3. Browser open URL
        if intent in ["browser_open", "browser_open_url"]:
            m_url = re.search(r"\b([a-zA-Z0-9\-\.]+\.(?:com|org|net|in|io|gov|edu|co))\b", t_lower)
            if m_url:
                slots["url"] = m_url.group(1).strip()
            else:
                slots["url"] = "google.com"

        # 4. Folder and File extraction
        if any(k in intent for k in ["folder", "file", "organize"]):
            # Target directory
            if "desktop" in t_lower:
                slots["target_dir"] = "Desktop"
            elif "download" in t_lower:
                slots["target_dir"] = "Downloads"
            elif "document" in t_lower:
                slots["target_dir"] = "Documents"
            else:
                slots["target_dir"] = "Desktop"

            # Folder name
            if "folder" in intent or "folder" in t_lower or "directory" in t_lower:
                m_f = re.search(r"(?:folder|directory)\s+(?:called|named|perutho)\s+([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
                m_f2 = re.search(r"([a-zA-Z0-9_\-]+)\s+ane\s+folder", text, re.IGNORECASE)
                if m_f2:
                    slots["folder_name"] = m_f2.group(1).strip()
                elif m_f:
                    slots["folder_name"] = m_f.group(1).strip()
                else:
                    m_f3 = re.search(r"(?:folder|directory)\s+([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
                    if m_f3 and m_f3.group(1).lower() not in ["on", "in", "create", "make", "desktop", "downloads", "documents", "called", "named"]:
                        slots["folder_name"] = m_f3.group(1).strip()
                    else:
                        slots["folder_name"] = "NIVA"
                slots["path"] = os.path.join(slots["target_dir"], slots["folder_name"])

            # File name
            if "file" in intent or any(ext in t_lower for ext in [".txt", ".pdf", ".docx", ".xlsx", ".csv"]):
                m_fn = re.search(r"\b([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]{2,4})\b", text)
                if m_fn:
                    slots["file_name"] = m_fn.group(1).strip()
                    slots["path"] = os.path.join(slots["target_dir"], slots["file_name"])
                else:
                    if "create" in intent:
                        slots["file_name"] = "document.txt"
                        slots["path"] = os.path.join(slots["target_dir"], "document.txt")
                        slots["content"] = "Created by NIVA Autonomous Agent.\n"
                    elif "search" in intent or "find" in intent:
                        ext_m = re.search(r"\b(pdf|docx?|xlsx?|txt|csv|py|png|jpg)\b", t_lower)
                        if ext_m:
                            slots["pattern"] = f"*.{ext_m.group(1)}"
                        else:
                            slots["pattern"] = "*.*"

        # 5. Windows Settings extraction
        if "setting" in intent:
            if "bluetooth" in intent or "bluetooth" in t_lower:
                slots["setting"] = "bluetooth"
                slots["value"] = "off" if any(w in t_lower for w in ["off", "bandh", "disable", "aapu", "vaddu"]) else "on"
            elif "wifi" in intent or "wifi" in t_lower or "wi-fi" in t_lower:
                slots["setting"] = "wifi"
                slots["value"] = "off" if any(w in t_lower for w in ["off", "bandh", "disable", "aapu"]) else "on"
            elif "volume" in intent or "volume" in t_lower or "sound" in t_lower or "audio" in t_lower:
                slots["setting"] = "volume"
                vol_m = re.search(r"(\d{1,3})%?", t_lower)
                if vol_m:
                    slots["value"] = int(vol_m.group(1))
                elif any(w in t_lower for w in ["penchu", "up", "increase", "ekkuva", "higher"]):
                    slots["value"] = "+10"
                elif any(w in t_lower for w in ["tagginchu", "down", "decrease", "thakkuva", "lower"]):
                    slots["value"] = "-10"
                elif "mute" in intent or "mute" in t_lower:
                    slots["setting"] = "mute"
                    slots["value"] = False if "unmute" in t_lower else True
                else:
                    slots["value"] = 50
            elif "brightness" in intent or "brightness" in t_lower:
                slots["setting"] = "brightness"
                b_m = re.search(r"(\d{1,3})%?", t_lower)
                if b_m:
                    slots["value"] = int(b_m.group(1))
                elif any(w in t_lower for w in ["penchu", "up", "increase", "ekkuva", "brighter", "higher"]):
                    slots["value"] = "+10"
                elif any(w in t_lower for w in ["tagginchu", "down", "decrease", "thakkuva", "dimmer", "lower"]):
                    slots["value"] = "-10"
                else:
                    slots["value"] = 70

        # Settings pages
        if intent.startswith("setting_open_") or intent == "open_settings_page":
            for p_key, aliases in [
                ("bluetooth", ["bluetooth"]),
                ("wifi", ["wifi"]),
                ("network", ["network", "internet"]),
                ("sound", ["sound", "audio"]),
                ("display", ["display", "screen"]),
                ("windows_update", ["update"]),
                ("control_panel", ["control panel", "control_panel"]),
                ("system", ["storage", "system", "about"]),
                ("apps", ["default apps", "apps"])
            ]:
                if p_key in intent or any(a in t_lower for a in aliases):
                    slots["page"] = p_key
                    break
            if "page" not in slots:
                slots["page"] = "system"

        # 6. Office topics
        if "excel" in intent or intent == "create_excel":
            slots["sheet_title"] = "Data Report"
            slots["include_summary_row"] = True
            slots["path"] = os.path.join(os.path.expanduser("~"), "Desktop", "Report.xlsx")
        elif "word" in intent or intent == "create_word":
            slots["title"] = "Autonomous Summary Report"
            slots["path"] = os.path.join(os.path.expanduser("~"), "Desktop", "Summary_Report.docx")
        elif "powerpoint" in intent or intent == "create_presentation":
            slots["presentation_title"] = "Project Presentation"
            slots["path"] = os.path.join(os.path.expanduser("~"), "Desktop", "Presentation.pptx")

        # 7. UI Automation & Keyboard / Mouse
        if intent == "mouse_click_element":
            m_el = re.search(r"(?:click|press|tap)\s+(?:on\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+button|\s+icon|\s+meeda|\s+in|\s+on|$)", text, re.IGNORECASE)
            slots["element_name"] = m_el.group(1).strip() if m_el else "OK"
            slots["window_title"] = slots.get("app_name", "")

        if intent == "keyboard_type_text":
            # 1. Telugu pattern: "<text> ani type chey" or "<text> ani rayi"
            m_tel = re.search(r"['\"]?(.+?)['\"]?\s+ani\s+(?:type|rayi|write)", text, re.IGNORECASE)
            if m_tel:
                slots["text"] = m_tel.group(1).strip()
            else:
                # 2. Telugu pattern without 'ani': "<text> type chey"
                m_tel2 = re.search(r"(?:lo\s+)?(.+?)\s+(?:type\s+chey|rayi)$", text, re.IGNORECASE)
                if m_tel2 and m_tel2.group(1).strip().lower() not in ["please", "can you", "konchem"]:
                    val = m_tel2.group(1).strip()
                    val = re.sub(r"^(?:notepad|word|browser)\s+lo\s+", "", val, flags=re.IGNORECASE)
                    slots["text"] = val
                else:
                    # 3. English pattern: "type <text>" or "write <text>"
                    m_txt = re.search(r"(?:type|write|enter)\s+['\"]?(.+?)['\"]?(?:\s+into|\s+in|\s+ani|$)", text, re.IGNORECASE)
                    if m_txt and m_txt.group(1).strip().lower() not in ["chey", "cheyyi", "ra", "brother"]:
                        slots["text"] = m_txt.group(1).strip()
                    else:
                        slots["text"] = "Hello Somu"

        if intent == "keyboard_press_hotkey":
            if "copy" in t_lower:
                slots["keys"] = ["ctrl", "c"]
            elif "paste" in t_lower:
                slots["keys"] = ["ctrl", "v"]
            elif "save" in t_lower:
                slots["keys"] = ["ctrl", "s"]
            elif "cut" in t_lower:
                slots["keys"] = ["ctrl", "x"]
            else:
                slots["keys"] = ["ctrl", "c"]

        # 8. Interruption override
        if intent == "interruption_override":
            sub_cmd = re.sub(r"^(?:stop|wait|cancel|forget\s+that|abort)[\s,\.]+", "", t_lower, flags=re.IGNORECASE)
            sub_cmd = re.sub(r"\binstead\b", "", sub_cmd, flags=re.IGNORECASE).strip()
            slots["new_command"] = sub_cmd

        return slots

    def _check_missing_slots(self, intent: str, entities: Dict[str, Any], text: str) -> Optional[str]:
        """Returns clarification question if required entity is missing."""
        if intent in ["open_app", "app_launch"] and "app_name" not in entities:
            return "Which application would you like me to open?"

        if intent in ["close_app", "app_close", "app_kill_force"] and "app_name" not in entities:
            return "Which application should I close?"

        if (intent == "browser_search" or intent.startswith("browser_search")) and not entities.get("query"):
            return "What would you like me to search for?"

        return None

    def _map_to_tool_call(self, intent: str, entities: Dict[str, Any], raw_text: str) -> Optional[Dict[str, Any]]:
        """Maps recognized intent and extracted slots to executable tool structure."""
        # Applications
        if intent in ["open_app", "app_launch", "context_clarify_app"]:
            app = entities.get("app_name", "notepad")
            if app == "youtube":
                return {
                    "tool_name": "browser_open",
                    "parameters": {"url": "https://www.youtube.com"},
                    "description": "Open YouTube website in browser"
                }
            return {
                "tool_name": "launch_app",
                "parameters": {"app_name": app},
                "description": f"Launch application '{app}'"
            }

        if intent in ["close_app", "app_close", "app_kill_force"]:
            app = entities.get("app_name", "notepad")
            force = (intent == "app_kill_force")
            return {
                "tool_name": "close_app",
                "parameters": {"app_name": app, "force": force},
                "description": f"Close application '{app}'"
            }

        if intent in ["switch_app", "app_switch"]:
            app = entities.get("app_name", "")
            return {
                "tool_name": "control_window",
                "parameters": {"window_title": app, "action": "focus"},
                "description": f"Switch focus to '{app}'"
            }

        if intent == "app_restart":
            app = entities.get("app_name", "notepad")
            return {
                "tool_name": "launch_app",
                "parameters": {"app_name": app},
                "description": f"Restart application '{app}'"
            }

        if intent == "app_check_running":
            return {
                "tool_name": "system_info",
                "parameters": {"query_type": "status"},
                "description": "Check running applications"
            }

        # Browser
        if intent in ["browser_scroll_down", "browser_scroll_up"]:
            direction = "down" if "down" in intent else "up"
            amount = entities.get("amount", "page")
            return {
                "tool_name": "browser_scroll",
                "parameters": {"direction": direction, "amount": amount},
                "description": f"Scroll browser {direction} ({amount})"
            }

        if intent == "browser_search_there":
            q = entities.get("query", "songs")
            eng = entities.get("engine", "youtube")
            return {
                "tool_name": "browser_search",
                "parameters": {"query": q, "engine": eng},
                "description": f"Search {eng.title()} for '{q}'"
            }

        if intent in ["browser_open", "browser_open_url"]:
            u = entities.get("url", "https://google.com")
            if not u.startswith("http://") and not u.startswith("https://"):
                u = "https://" + u
            return {
                "tool_name": "browser_open",
                "parameters": {"url": u},
                "description": f"Open website: {u}"
            }

        if intent in ["browser_search", "context_clarify_query"] or intent.startswith("browser_search"):
            q = entities.get("query", "latest news")
            eng = entities.get("engine", "google")
            return {
                "tool_name": "browser_search",
                "parameters": {"query": q, "engine": eng},
                "description": f"Search {eng.title()} for '{q}'"
            }

        if intent in ["browser_open_result", "youtube_play_result", "context_refer_previous_result"]:
            idx = entities.get("result_index", 1)
            return {
                "tool_name": "browser_open_result",
                "parameters": {"result_index": idx},
                "description": f"Open search result #{idx}"
            }

        if intent == "browser_new_tab":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "t"]}, "description": "Open new browser tab"}
        if intent == "browser_close_tab":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "w"]}, "description": "Close browser tab"}
        if intent == "browser_switch_tab":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "tab"]}, "description": "Switch browser tab"}
        if intent == "browser_reload_page":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "r"]}, "description": "Reload browser page"}
        if intent == "browser_go_back":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["alt", "left"]}, "description": "Navigate back"}
        if intent == "browser_go_forward":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["alt", "right"]}, "description": "Navigate forward"}
        if intent == "browser_bookmark_page":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "d"]}, "description": "Bookmark page"}
        if intent == "browser_read_page_text":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "a"]}, "description": "Read page text"}

        # Email & Communication
        if intent == "email_open":
            return {
                "tool_name": "browser_open",
                "parameters": {"url": "https://mail.google.com"},
                "description": "Open web email client"
            }
        if intent == "email_read":
            q = entities.get("query_or_filter", "latest")
            return {
                "tool_name": "email_read",
                "parameters": {"query_or_filter": q},
                "description": f"Read email ({q})"
            }
        if intent == "email_draft":
            rec = entities.get("recipient", "team@example.com")
            sub = entities.get("subject", "Update")
            bod = entities.get("body", "Here is the documentation.")
            return {
                "tool_name": "email_draft",
                "parameters": {"recipient": rec, "subject": sub, "body": bod},
                "description": f"Draft email to {rec} regarding '{sub}'"
            }
        if intent == "email_send":
            rec = entities.get("recipient", "team@example.com")
            sub = entities.get("subject", "Update")
            bod = entities.get("body", "Here is the documentation.")
            return {
                "tool_name": "email_send",
                "parameters": {"recipient": rec, "subject": sub, "body": bod, "confirmed": False},
                "description": f"Send email to {rec}",
                "requires_confirmation": True
            }

        # Filesystem
        if intent in ["create_folder", "folder_create"]:
            p = entities.get("path", "Desktop\\NIVA")
            return {
                "tool_name": "create_folder",
                "parameters": {"path": p},
                "description": f"Create folder at '{p}'"
            }

        if intent == "folder_delete":
            p = entities.get("path", "Desktop\\NIVA")
            return {
                "tool_name": "delete_file",
                "parameters": {"path": p, "permanent": False},
                "description": f"Delete folder at '{p}'",
                "requires_confirmation": True
            }

        if intent == "folder_open":
            p = entities.get("path", "Desktop")
            return {
                "tool_name": "launch_app",
                "parameters": {"app_name": "explorer", "arguments": p},
                "description": f"Open folder '{p}' in File Explorer"
            }

        if intent in ["organize_folder", "folder_organize_by_type"]:
            d = entities.get("directory", "Downloads")
            return {
                "tool_name": "organize_folder",
                "parameters": {"directory": d},
                "description": f"Organize '{d}' by file extension"
            }

        if intent in ["create_file", "file_create"]:
            p = entities.get("path", "Desktop\\document.txt")
            c = entities.get("content", "Created by NIVA Autonomous Agent.\n")
            return {
                "tool_name": "create_file",
                "parameters": {"path": p, "content": c},
                "description": f"Create file at '{p}'"
            }

        if intent in ["read_file", "file_read", "document_read_metadata"]:
            p = entities.get("path", "notes.txt")
            return {
                "tool_name": "read_file",
                "parameters": {"path": p},
                "description": f"Read document at '{p}'"
            }

        if intent in ["delete_file", "file_delete"]:
            p = entities.get("path", "temp.txt")
            return {
                "tool_name": "delete_file",
                "parameters": {"path": p, "permanent": False},
                "description": f"Delete file at '{p}'",
                "requires_confirmation": True
            }

        if intent == "file_delete_permanent":
            p = entities.get("path", "temp.txt")
            return {
                "tool_name": "delete_file",
                "parameters": {"path": p, "permanent": True},
                "description": f"Permanently delete file at '{p}'",
                "requires_confirmation": True
            }

        if intent in ["move_file", "file_move", "file_rename"]:
            src = entities.get("source", entities.get("path", "temp.txt"))
            dst = entities.get("destination", "Desktop")
            return {
                "tool_name": "move_file",
                "parameters": {"source": src, "destination": dst},
                "description": f"Move '{src}' to '{dst}'"
            }

        if intent in ["copy_file", "file_copy"]:
            src = entities.get("source", entities.get("path", "temp.txt"))
            dst = entities.get("destination", "Desktop")
            return {
                "tool_name": "copy_file",
                "parameters": {"source": src, "destination": dst},
                "description": f"Copy '{src}' to '{dst}'"
            }

        if intent in ["search_files", "file_search_by_name", "file_search_by_extension", "file_find_duplicates"]:
            d = entities.get("directory", "Desktop")
            pat = entities.get("pattern", "*.*")
            return {
                "tool_name": "search_files",
                "parameters": {"directory": d, "pattern": pat},
                "description": f"Search files matching '{pat}' in '{d}'"
            }

        if intent == "file_open":
            p = entities.get("path", "document.txt")
            return {
                "tool_name": "launch_app",
                "parameters": {"app_name": "explorer", "arguments": p},
                "description": f"Open file '{p}'"
            }

        # Windows Settings
        if "setting" in intent:
            if intent in ["setting_bluetooth_on", "setting_bluetooth_off"]:
                val = "on" if "on" in intent else "off"
                return {"tool_name": "set_setting", "parameters": {"setting": "bluetooth", "value": val}, "description": f"Set Bluetooth to {val}"}
            if intent in ["setting_wifi_on", "setting_wifi_off"]:
                val = "on" if "on" in intent else "off"
                return {"tool_name": "set_setting", "parameters": {"setting": "wifi", "value": val}, "description": f"Set Wi-Fi to {val}"}
            if intent == "setting_volume_mute":
                return {"tool_name": "set_setting", "parameters": {"setting": "mute", "value": True}, "description": "Mute volume"}
            if intent == "setting_volume_unmute":
                return {"tool_name": "set_setting", "parameters": {"setting": "mute", "value": False}, "description": "Unmute volume"}
            if intent == "setting_volume_increase":
                return {"tool_name": "set_setting", "parameters": {"setting": "volume", "value": "+10"}, "description": "Increase volume"}
            if intent == "setting_volume_decrease":
                return {"tool_name": "set_setting", "parameters": {"setting": "volume", "value": "-10"}, "description": "Decrease volume"}
            if intent == "setting_volume_set":
                val = entities.get("value", 50)
                return {"tool_name": "set_setting", "parameters": {"setting": "volume", "value": val}, "description": f"Set volume to {val}"}
            if intent == "setting_brightness_increase":
                return {"tool_name": "set_setting", "parameters": {"setting": "brightness", "value": "+10"}, "description": "Increase brightness"}
            if intent == "setting_brightness_decrease":
                return {"tool_name": "set_setting", "parameters": {"setting": "brightness", "value": "-10"}, "description": "Decrease brightness"}
            if intent == "setting_brightness_set":
                val = entities.get("value", 70)
                return {"tool_name": "set_setting", "parameters": {"setting": "brightness", "value": val}, "description": f"Set brightness to {val}"}
            if intent == "setting_open_task_manager":
                return {
                    "tool_name": "launch_app",
                    "parameters": {"app_name": "taskmgr"},
                    "description": "Open Windows Task Manager"
                }
            if intent.startswith("setting_open_") or intent == "open_settings_page":
                page = entities.get("page", "system")
                return {
                    "tool_name": "open_settings_page",
                    "parameters": {"page": page},
                    "description": f"Open Windows {page.title()} Settings"
                }
            s = entities.get("setting", "bluetooth")
            v = entities.get("value", "off")
            return {
                "tool_name": "set_setting",
                "parameters": {"setting": s, "value": v},
                "description": f"Set {s.title()} to {v}"
            }

        # Window Controls & Desktop
        if intent in ["window_show_desktop", "show_desktop"]:
            return {
                "tool_name": "show_desktop",
                "parameters": {},
                "description": "Show Desktop (minimize all windows)"
            }

        if intent == "window_minimize":
            app = entities.get("app_name", "")
            return {
                "tool_name": "control_window",
                "parameters": {"window_title": app, "action": "minimize"},
                "description": f"Minimize window '{app}'" if app else "Minimize active window"
            }

        if intent == "window_maximize":
            app = entities.get("app_name", "")
            return {
                "tool_name": "control_window",
                "parameters": {"window_title": app, "action": "maximize"},
                "description": f"Maximize window '{app}'" if app else "Maximize active window"
            }

        if intent == "window_restore":
            app = entities.get("app_name", "")
            return {
                "tool_name": "control_window",
                "parameters": {"window_title": app, "action": "restore"},
                "description": f"Restore window '{app}'" if app else "Restore active window"
            }

        if intent == "window_snap_left":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["win", "left"]}, "description": "Snap window to left half"}
        if intent == "window_snap_right":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["win", "right"]}, "description": "Snap window to right half"}
        if intent == "window_focus_next":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["alt", "tab"]}, "description": "Switch to next window"}
        if intent == "window_list_running":
            return {"tool_name": "system_info", "parameters": {"query_type": "status"}, "description": "List running windows"}

        # Screen & Vision
        if intent in ["capture_screen", "screen_capture_full", "screen_capture_window", "screen_ocr_read_text"]:
            return {
                "tool_name": "capture_screen",
                "parameters": {"ocr": True},
                "description": "Capture desktop screen screenshot"
            }

        if intent == "screen_lock":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["win", "l"]}, "description": "Lock Windows screen"}

        # Clipboard & Input Controls
        if intent == "clipboard_copy_selection":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "c"]}, "description": "Copy selection to clipboard"}
        if intent == "clipboard_paste":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "v"]}, "description": "Paste clipboard content"}
        if intent == "clipboard_read_content":
            return {"tool_name": "system_info", "parameters": {"query_type": "status"}, "description": "Read clipboard content"}

        if intent == "keyboard_type_text":
            txt = entities.get("text", "Hello from NIVA")
            return {"tool_name": "type_text", "parameters": {"text": txt}, "description": f"Type text: '{txt}'"}
        if intent == "keyboard_press_hotkey":
            keys = entities.get("keys", ["ctrl", "c"])
            return {"tool_name": "press_hotkey", "parameters": {"keys": keys}, "description": f"Press hotkey: {'+'.join(keys)}"}
        if intent == "keyboard_scroll_up":
            return {"tool_name": "scroll", "parameters": {"amount": 500}, "description": "Scroll window up"}
        if intent == "keyboard_scroll_down":
            return {"tool_name": "scroll", "parameters": {"amount": -500}, "description": "Scroll window down"}

        if intent == "mouse_click_element":
            elem = entities.get("element_name", "")
            win = entities.get("window_title", "")
            c_type = entities.get("control_type")
            if elem:
                return {
                    "tool_name": "uia_click",
                    "parameters": {"window_title": win or "", "element_name": elem, "control_type": c_type},
                    "description": f"Click accessible element '{elem}'"
                }
            return {"tool_name": "mouse_click", "parameters": {"clicks": 1, "button": "left"}, "description": "Click mouse"}
        if intent == "mouse_double_click":
            return {"tool_name": "mouse_click", "parameters": {"clicks": 2, "button": "left"}, "description": "Double click mouse"}
        if intent == "mouse_right_click":
            return {"tool_name": "mouse_click", "parameters": {"clicks": 1, "button": "right"}, "description": "Right click mouse"}

        # Forms
        if intent == "form_fill_structured":
            fields = entities.get("field_mappings", {"Name": "Somu", "Email": "somu@college.edu"})
            return {"tool_name": "fill_form", "parameters": {"field_mappings": fields, "submit_after_fill": False}, "description": "Fill form fields"}
        if intent == "form_submit":
            fields = entities.get("field_mappings", {})
            return {
                "tool_name": "fill_form",
                "parameters": {"field_mappings": fields, "submit_after_fill": True},
                "description": "Submit form details",
                "requires_confirmation": True
            }
        if intent == "form_clear_fields":
            return {"tool_name": "press_hotkey", "parameters": {"keys": ["ctrl", "a", "backspace"]}, "description": "Clear form fields"}

        # Privacy History
        if intent in ["history_clear", "history_enable", "history_disable"]:
            act = "clear" if "clear" in intent else ("enable" if "enable" in intent else "disable")
            return {"tool_name": "history_manage", "parameters": {"action": act}, "description": f"{act.title()} local dialogue history"}

        # System Diagnostics
        if intent.startswith("system_"):
            q_type = "battery" if "battery" in intent else ("storage" if "storage" in intent else ("resources" if "resource" in intent else "status"))
            return {"tool_name": "system_info", "parameters": {"query_type": q_type}, "description": f"Check system {q_type}"}

        # Office Automation
        if intent in ["create_excel", "excel_create_sheet", "excel_add_totals_formula", "excel_format_table"]:
            p = entities.get("path", os.path.join(os.path.expanduser("~"), "Desktop", "Report.xlsx"))
            title = entities.get("sheet_title", "Data")
            return {
                "tool_name": "create_excel",
                "parameters": {
                    "path": p,
                    "sheet_title": title,
                    "headers": ["Item", "Category", "Quantity", "Price ($)", "Total"],
                    "rows": [
                        ["Project Item A", "Hardware", 2, 150, 300],
                        ["Software License B", "Cloud", 1, 450, 450],
                        ["Sensor Module C", "Electronics", 4, 25, 100]
                    ],
                    "include_summary_row": True
                },
                "description": f"Create Excel workbook at '{p}' with formulas"
            }

        if intent in ["create_word", "word_create_document", "word_add_table", "word_append_notes"]:
            p = entities.get("path", os.path.join(os.path.expanduser("~"), "Desktop", "AI_Summary_Report.docx"))
            title = entities.get("title", "Autonomous Report")
            return {
                "tool_name": "create_word",
                "parameters": {
                    "path": p,
                    "title": title,
                    "paragraphs": [
                        f"This document '{title}' was compiled autonomously by NIVA.",
                        "Analysis indicates high command-understanding accuracy across English, Telugu-Latin, and Code-mixed speech.",
                        "System state: All desktop automation components operating with verification."
                    ],
                    "table_data": [
                        ["Module", "Status", "Accuracy"],
                        ["NLU Intent Classifier", "Active", "99.6%"],
                        ["Speech Recognition", "Active", "Calibrated"],
                        ["Windows Automation", "Active", "Verified"]
                    ]
                },
                "description": f"Create Word document at '{p}'"
            }

        if intent in ["create_presentation", "powerpoint_create_presentation", "powerpoint_add_slide"]:
            p = entities.get("path", os.path.join(os.path.expanduser("~"), "Desktop", "Project_Slides.pptx"))
            title = entities.get("presentation_title", "NIVA Autonomous AI")
            return {
                "tool_name": "create_presentation",
                "parameters": {
                    "path": p,
                    "presentation_title": title,
                    "slides": [
                        {"title": "Overview", "bullets": ["Universal Windows Control", "Voice-First Architecture", "Code-Mixed NLU Engine"]},
                        {"title": "Technical Performance", "bullets": ["Zero-Latency Interruption", "Cooperative Cancellation", "Action Verification"]}
                    ]
                },
                "description": f"Create PowerPoint presentation at '{p}'"
            }

        if intent == "document_convert_to_pdf":
            p = entities.get("path", os.path.join(os.path.expanduser("~"), "Desktop", "Converted_Document.pdf"))
            return {
                "tool_name": "create_file",
                "parameters": {"path": p, "content": "PDF Document content exported by NIVA.\n"},
                "description": f"Convert document to PDF at '{p}'"
            }

        return None
