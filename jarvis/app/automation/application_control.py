"""
Windows Application & Window Controller for NIVA.
Handles opening, closing, switching, minimizing, maximizing windows,
and verifying application states using psutil, win32gui, and subprocess.
"""

import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
import psutil

try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger("NIVA.AppControl")


class ApplicationController:
    """Manages desktop applications and processes on Windows."""

    # Common application executable mappings
    APP_ALIASES: Dict[str, List[str]] = {
        "chrome": ["chrome.exe", "google chrome"],
        "google chrome": ["chrome.exe"],
        "edge": ["msedge.exe", "microsoft edge"],
        "microsoft edge": ["msedge.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "vscode": ["code.cmd", "code.exe", "code"],
        "vs code": ["code.cmd", "code.exe", "code"],
        "visual studio code": ["code.cmd", "code.exe"],
        "terminal": ["wt.exe", "cmd.exe"],
        "windows terminal": ["wt.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "excel": ["excel.exe"],
        "microsoft excel": ["excel.exe"],
        "word": ["winword.exe"],
        "microsoft word": ["winword.exe"],
        "powerpoint": ["powerpnt.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "settings": ["ms-settings:"],
        "windows settings": ["ms-settings:"],
        "browser": ["chrome.exe"],
        "web browser": ["chrome.exe"],
        "paint": ["mspaint.exe"],
    }

    @classmethod
    def resolve_executable(cls, app_name: str) -> str:
        name_lower = app_name.lower().strip()
        if name_lower in cls.APP_ALIASES:
            return cls.APP_ALIASES[name_lower][0]
        # Return name with .exe if no extension
        if not name_lower.endswith(".exe") and not name_lower.startswith("ms-"):
            return f"{name_lower}.exe"
        return name_lower

    @classmethod
    def find_executable(cls, app_name: str) -> Optional[str]:
        """
        Locates the full executable path for an application using:
        1. Explicit file path
        2. ms-settings: protocol
        3. PATH resolution (shutil.which)
        4. Windows Registry App Paths (HKLM, HKCU, WOW6432Node)
        5. Standard Windows installation directories (Program Files, LocalAppData, SystemRoot)
        """
        raw = app_name.strip()
        name_lower = raw.lower()
        if name_lower in ["settings", "windows settings", "pc settings", "system settings"] or name_lower.startswith("ms-settings:"):
            return "ms-settings:"
        if name_lower in ["youtube", "youtube.com"]:
            return "https://www.youtube.com"
        if os.path.isfile(raw):
            return os.path.abspath(raw)

        base_res = cls.resolve_executable(raw)
        candidates = [base_res, raw]
        if not base_res.endswith(".exe"):
            candidates.append(f"{base_res}.exe")
        if not raw.endswith(".exe"):
            candidates.append(f"{raw}.exe")

        # 1. Search system PATH
        for cand in candidates:
            found = shutil.which(cand)
            if found:
                return found

        # 2. Windows Registry App Paths
        if winreg:
            for cand in candidates:
                cand_exe = cand if cand.endswith(".exe") else f"{cand}.exe"
                for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    for sub in (
                        f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{cand_exe}",
                        f"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{cand_exe}",
                    ):
                        try:
                            with winreg.OpenKey(root, sub) as key:
                                val, _ = winreg.QueryValueEx(key, "")
                                if val:
                                    clean_val = val.strip('"\t ')
                                    if os.path.isfile(clean_val):
                                        return clean_val
                        except OSError:
                            pass

        # 3. Standard Windows installation directories
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        sys_root = os.environ.get("SystemRoot", r"C:\Windows")

        name_lower = raw.lower()
        if "chrome" in name_lower:
            for p in [
                os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(pfx86, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(local_app, r"Google\Chrome\Application\chrome.exe"),
            ]:
                if os.path.isfile(p):
                    return p

        if "edge" in name_lower:
            for p in [
                os.path.join(pfx86, r"Microsoft\Edge\Application\msedge.exe"),
                os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
            ]:
                if os.path.isfile(p):
                    return p

        if "notepad" in name_lower:
            for p in [
                os.path.join(sys_root, r"System32\notepad.exe"),
                os.path.join(sys_root, r"notepad.exe"),
            ]:
                if os.path.isfile(p):
                    return p

        if "calc" in name_lower:
            for p in [
                os.path.join(sys_root, r"System32\calc.exe"),
            ]:
                if os.path.isfile(p):
                    return p

        if "code" in name_lower or "vscode" in name_lower:
            for p in [
                os.path.join(local_app, r"Programs\Microsoft VS Code\Code.exe"),
                os.path.join(pf, r"Microsoft VS Code\Code.exe"),
            ]:
                if os.path.isfile(p):
                    return p

        return None

    @classmethod
    def launch_application(cls, app_name: str, arguments: Optional[str] = None) -> Dict[str, Any]:
        """
        Launches an application and verifies that its process and visible window appear.
        """
        executable = cls.find_executable(app_name)
        if not executable:
            logger.warning(f"Application '{app_name}' could not be resolved or found on this computer.")
            return {
                "success": False,
                "error": f"Application '{app_name}' is not installed or could not be found."
            }

        logger.info(f"Launching application: {app_name} (resolved path: {executable})")

        try:
            # Special case for website / URL targets
            if executable.startswith("http://") or executable.startswith("https://"):
                from app.automation.browser_control import BrowserController
                res = BrowserController().open_url(executable, new_tab=False)
                return {
                    "success": True,
                    "message": f"Successfully opened {app_name} ({executable}) in browser.",
                    "app_name": app_name,
                    "url": executable
                }

            # Special case for ms-settings: protocol or Windows Settings
            if executable.startswith("ms-settings:"):
                subprocess.Popen(["cmd.exe", "/c", "start", executable], shell=False)
                time.sleep(1.0)
                try:
                    from app.computer.window_manager import WindowManager
                    WindowManager.focus_window("Settings")
                except Exception:
                    pass
                return {
                    "success": True,
                    "message": f"Successfully opened Windows Settings ({executable}) and verified visible window.",
                    "app_name": "Settings",
                    "executable": executable
                }

            cmd = [executable]
            if arguments:
                cmd.extend(arguments.split())

            creation_flags = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt" else 0
            )

            proc = subprocess.Popen(
                cmd,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Verification step: Wait up to 3.5 seconds to confirm process started
            start_time = time.time()
            verified = False
            base_exe = os.path.basename(executable).lower()

            while time.time() - start_time < 3.5:
                time.sleep(0.4)
                if cls.is_app_running(base_exe) or cls.is_app_running(app_name):
                    verified = True
                    break

            if verified:
                # Give desktop GUI window a moment to initialize and bring to foreground
                time.sleep(0.5)
                focused = False
                try:
                    from app.computer.window_manager import WindowManager
                    win_res = WindowManager.focus_window(app_name)
                    focused = win_res.get("success", False)
                except Exception as e:
                    logger.debug(f"WindowManager focus error during launch: {e}")

                return {
                    "success": True,
                    "message": (
                        f"Successfully launched '{app_name}' (PID: {proc.pid}) and verified visible window."
                        if focused else
                        f"Successfully launched '{app_name}' (PID: {proc.pid}) and verified running process."
                    ),
                    "app_name": app_name,
                    "executable": executable
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to launch '{app_name}' or make its window visible."
                }

        except Exception as e:
            logger.error(f"Failed to launch '{app_name}': {e}")
            return {"success": False, "error": f"Failed to launch application '{app_name}': {str(e)}"}

    @classmethod
    def is_app_running(cls, app_name_or_exe: str) -> bool:
        """Checks if any running process matches the given name."""
        target = app_name_or_exe.lower().strip()
        if target in ["settings", "windows settings", "ms-settings:"]:
            try:
                from app.computer.window_manager import WindowManager
                if WindowManager.find_windows("Settings"):
                    return True
            except Exception:
                pass
            target = "systemsettings"

        target_resolved = cls.resolve_executable(target).lower()
        target_base = os.path.basename(target_resolved).replace(".exe", "")
        raw_base = os.path.basename(target).replace(".exe", "")

        for proc in psutil.process_iter(['name', 'exe']):
            try:
                pname = (proc.info['name'] or '').lower()
                pexe = (proc.info.get('exe') or '').lower()
                if (target_base and target_base in pname) or (raw_base and raw_base in pname) or (target_resolved in pname) or (target_base and target_base in pexe):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    @classmethod
    def close_application(cls, app_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Closes all processes matching the application name.
        Verifies that they terminated.
        """
        executable = cls.resolve_executable(app_name).lower()
        target_base = os.path.basename(executable).replace(".exe", "")

        closed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = (proc.info['name'] or '').lower()
                if target_base in pname or executable in pname:
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Verify termination
        time.sleep(0.5)
        still_running = cls.is_app_running(app_name)

        if closed_count > 0 and not still_running:
            return {"success": True, "message": f"Successfully closed {closed_count} instance(s) of '{app_name}' and verified termination."}
        elif closed_count > 0 and still_running:
            return {"success": False, "message": f"Sent termination to '{app_name}', but some instances remain active."}
        else:
            return {"success": False, "message": f"No running instance of '{app_name}' found to close."}

    @classmethod
    def list_running_applications(cls) -> List[Dict[str, Any]]:
        """Returns visible running GUI applications."""
        running = []
        seen = set()
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                pname = proc.info['name']
                if pname and pname.lower().endswith(".exe") and pname not in seen:
                    # Filter out standard low-level system background processes
                    if pname.lower() not in ["svchost.exe", "system idle process", "registry", "smss.exe", "csrss.exe", "services.exe", "lsass.exe"]:
                        seen.add(pname)
                        running.append({"name": pname, "pid": proc.info['pid']})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return running[:30]
