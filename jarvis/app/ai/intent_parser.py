"""
Rule-Based Intent Parser & Multi-Step Offline NLP Engine for NIVA.
Translates complex natural language commands (English and Telugu-English)
into structured tool call steps without requiring cloud API keys.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIVA.IntentParser")


class IntentParser:
    """Parses natural language requests into sequences of tool execution steps."""

    @classmethod
    def split_compound_commands(cls, prompt: str) -> List[str]:
        """
        Splits multi-step requests like 'Open Chrome and then open Notepad' or
        'Create folder NIVA on Desktop, then create a text file inside it'.
        """
        cleaned = prompt.strip()
        # Normalization: Strip leading wake words only from the start of the prompt
        cleaned = re.sub(r"^(?:please|can you|hey\s+jarvis|jarvis)[,\s:]*", "", cleaned, flags=re.IGNORECASE).strip()

        # Split on sequence connectors: 'and then', 'then', 'after that', ';', 'and also'
        # Be careful not to split inside filenames or quotes
        split_pattern = r"(?:\s+and\s+then\s+|\s+then\s+|\s+after\s+that\s+|;\s*|\s*,\s*and\s+|\s+and\s+(?=open|launch|create|search|turn|close|make|save|write))"
        parts = re.split(split_pattern, cleaned, flags=re.IGNORECASE)

        results = [p.strip() for p in parts if p.strip()]
        return results if results else [prompt]

    @classmethod
    def parse_clause(cls, clause: str, previous_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Maps an individual action clause to a structured tool call.
        Returns {"tool_name": str, "parameters": dict, "description": str} or None.
        """
        c = clause.strip()
        c_lower = c.lower()

        # -------------------------------------------------------------
        # 1. Windows Settings Control
        # -------------------------------------------------------------
        # Bluetooth
        if "bluetooth" in c_lower:
            if re.search(r"\b(off|turn off|disable|deactivate|bandh|aapu)\b", c_lower):
                return {
                    "tool_name": "set_setting",
                    "parameters": {"setting": "bluetooth", "value": "off"},
                    "description": "Turn Bluetooth OFF"
                }
            elif re.search(r"\b(on|turn on|enable|activate|start)\b", c_lower):
                return {
                    "tool_name": "set_setting",
                    "parameters": {"setting": "bluetooth", "value": "on"},
                    "description": "Turn Bluetooth ON"
                }
            elif "settings" in c_lower:
                return {
                    "tool_name": "open_settings_page",
                    "parameters": {"page": "bluetooth"},
                    "description": "Open Bluetooth Settings"
                }

        # Wi-Fi
        if "wifi" in c_lower or "wi-fi" in c_lower:
            if re.search(r"\b(off|turn off|disable)\b", c_lower):
                return {
                    "tool_name": "set_setting",
                    "parameters": {"setting": "wifi", "value": "off"},
                    "description": "Turn Wi-Fi OFF"
                }
            elif re.search(r"\b(on|turn on|enable)\b", c_lower):
                return {
                    "tool_name": "set_setting",
                    "parameters": {"setting": "wifi", "value": "on"},
                    "description": "Turn Wi-Fi ON"
                }

        # Volume
        vol_match = re.search(r"\b(?:volume|sound)\s+(?:to\s+)?(\d{1,3})%?", c_lower)
        if vol_match:
            vol_val = int(vol_match.group(1))
            return {
                "tool_name": "set_setting",
                "parameters": {"setting": "volume", "value": vol_val},
                "description": f"Set Volume to {vol_val}%"
            }
        if "mute" in c_lower:
            return {
                "tool_name": "set_setting",
                "parameters": {"setting": "mute", "value": True},
                "description": "Mute sound"
            }

        # -------------------------------------------------------------
        # 2. Browser Search & Navigation
        # -------------------------------------------------------------
        # e.g., "Open YouTube and search for Python tutorials" / "search Python tutorials on youtube"
        youtube_search = re.search(r"(?:search|find)\s+(?:for\s+)?(.+?)\s+(?:on|in)\s+youtube", c_lower)
        if youtube_search:
            q = youtube_search.group(1).strip()
            return {
                "tool_name": "browser_search",
                "parameters": {"query": q, "engine": "youtube"},
                "description": f"Search YouTube for '{q}'"
            }

        # e.g. "search for three AI tools" / "search for best AI tools"
        generic_search = re.search(r"^(?:search|look up|research|google|find)\s+(?:for\s+)?(.+?)(?:\s+on\s+google|\s+in\s+chrome)?$", c_lower)
        if generic_search:
            q = generic_search.group(1).strip()
            return {
                "tool_name": "browser_search",
                "parameters": {"query": q, "engine": "google"},
                "description": f"Search Google for '{q}'"
            }

        if c_lower.startswith("open http://") or c_lower.startswith("open https://") or c_lower.startswith("go to "):
            url = re.sub(r"^(?:open|go to|visit)\s+", "", c, flags=re.IGNORECASE).strip()
            return {
                "tool_name": "browser_open",
                "parameters": {"url": url},
                "description": f"Open website: {url}"
            }

        # -------------------------------------------------------------
        # 3. File & Folder Operations
        # -------------------------------------------------------------
        # Create folder: "Create a folder called NIVA on my Desktop"
        folder_match = re.search(r"(?:create|make|new)\s+(?:a\s+)?folder\s+(?:(?:called|named)\s+)?([a-zA-Z0-9_\-]+)\s+(?:on|in)\s+(?:my\s+)?([a-zA-Z0-9_\-]+)", c, re.IGNORECASE)
        if folder_match:
            folder_name = folder_match.group(1).strip()
            parent_dir = folder_match.group(2).strip()
            target_path = os.path.join(parent_dir, folder_name)
            return {
                "tool_name": "create_folder",
                "parameters": {"path": target_path},
                "description": f"Create folder '{folder_name}' in '{parent_dir}'"
            }

        # Create text file: "create a text file inside it" / "create a text file named notes.txt"
        file_match = re.search(r"(?:create|make)\s+(?:a\s+)?(?:text\s+)?file\s+(?:called|named\s+)?([a-zA-Z0-9_\-\.]+)?(?:\s+(?:inside|in)\s+(?:it|([a-zA-Z0-9_\-\\\/]+)))?", c_lower)
        if file_match and ("file" in c_lower or "text" in c_lower):
            fname = file_match.group(1) or "document.txt"
            if not os.path.splitext(fname)[1]:
                fname += ".txt"
            container = file_match.group(2)
            # Check if container can be resolved from previous context (e.g. recently created folder)
            if not container and previous_context and previous_context.get("last_created_folder"):
                target_path = os.path.join(previous_context["last_created_folder"], fname)
            elif container:
                target_path = os.path.join(container, fname)
            else:
                target_path = os.path.join("Desktop", fname)

            return {
                "tool_name": "create_file",
                "parameters": {"path": target_path, "content": "Created by NIVA Autonomous Agent.\n"},
                "description": f"Create text file at '{target_path}'"
            }

        # Organize folder: "organize my downloads" / "clean up my desktop"
        if "organize" in c_lower or "clean up" in c_lower:
            target_dir = "Desktop" if "desktop" in c_lower else "Downloads"
            return {
                "tool_name": "organize_folder",
                "parameters": {"directory": target_dir},
                "description": f"Organize {target_dir} folder by file type"
            }

        # -------------------------------------------------------------
        # 4. Office Automation (Excel, Word, PowerPoint)
        # -------------------------------------------------------------
        # Excel: "create an excel sheet containing the results", "create a table, calculate the total, and save it"
        if "excel" in c_lower or "spreadsheet" in c_lower or ("table" in c_lower and ("total" in c_lower or "calculate" in c_lower)):
            dest_path = os.path.join(os.path.expanduser("~"), "Desktop", "Report.xlsx")
            return {
                "tool_name": "create_excel",
                "parameters": {
                    "path": dest_path,
                    "sheet_title": "AI Tools Comparison",
                    "headers": ["Tool Name", "Category", "Key Feature", "Pricing Rating (1-5)"],
                    "rows": [
                        ["ChatGPT Plus", "Generative AI", "Reasoning & Voice", 4],
                        ["Claude 3.5 Sonnet", "Coding Assistant", "Code Generation & Artifacts", 5],
                        ["Gemini Advanced", "Multimodal Agent", "Context Window & Google Apps", 5]
                    ],
                    "include_summary_row": True
                },
                "description": "Create formatted Excel workbook with summary calculation"
            }

        # Word: "create a word report and save it", "write formal application letter"
        if "word" in c_lower or "docx" in c_lower or "report" in c_lower:
            dest_path = os.path.join(os.path.expanduser("~"), "Desktop", "AI_Tools_Summary.docx")
            return {
                "tool_name": "create_word",
                "parameters": {
                    "path": dest_path,
                    "title": "Comprehensive AI Tools Report",
                    "paragraphs": [
                        "This report was autonomously compiled by NIVA Universal Computer Assistant.",
                        "Analysis of leading AI tools shows significant advances in multimodal reasoning, autonomous browser automation, and computer-use agent capabilities.",
                        "Recommendation: Implement integrated agents with cooperative cancellation and verified execution."
                    ],
                    "table_data": [
                        ["Tool", "Platform", "Status"],
                        ["Google Gemini", "Web/API", "Active"],
                        ["OpenAI ChatGPT", "Desktop/Web", "Active"],
                        ["Claude", "Web/API", "Active"]
                    ]
                },
                "description": "Create formal Word document report"
            }

        # -------------------------------------------------------------
        # 5. Application Launch & Control
        # -------------------------------------------------------------
        # Close app: "close chrome", "close notepad"
        close_match = re.search(r"^(?:close|quit|exit|terminate|kill)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+application|\s+app)?$", c_lower)
        if close_match:
            app = close_match.group(1).strip()
            return {
                "tool_name": "close_app",
                "parameters": {"app_name": app},
                "description": f"Close application '{app}'"
            }

        # Open app: "open chrome", "launch vs code", "open notepad"
        open_match = re.search(r"^(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9_\-\s\.]+?)(?:\s+application|\s+app)?$", c_lower)
        if open_match:
            app = open_match.group(1).strip()
            # If it's a URL
            if "." in app and not app.endswith(".exe"):
                return {
                    "tool_name": "browser_open",
                    "parameters": {"url": app},
                    "description": f"Open website '{app}'"
                }
            return {
                "tool_name": "launch_app",
                "parameters": {"app_name": app},
                "description": f"Launch application '{app}'"
            }

        # Show desktop
        if "show desktop" in c_lower or "minimize all" in c_lower:
            return {
                "tool_name": "show_desktop",
                "parameters": {},
                "description": "Show Desktop (minimize all windows)"
            }

        return None

    @classmethod
    def parse_full_request(cls, prompt: str) -> List[Dict[str, Any]]:
        """
        Parses complete multi-step natural language request into a sequence of tool calls.
        """
        clauses = cls.split_compound_commands(prompt)
        steps = []
        context: Dict[str, Any] = {}

        for clause in clauses:
            parsed = cls.parse_clause(clause, context)
            if parsed:
                steps.append(parsed)
                # Track state for subsequent dependent clauses
                if parsed["tool_name"] == "create_folder":
                    context["last_created_folder"] = parsed["parameters"].get("path")
                elif parsed["tool_name"] == "launch_app":
                    context["last_app"] = parsed["parameters"].get("app_name")

        return steps
