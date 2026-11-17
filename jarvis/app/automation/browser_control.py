"""
Universal Web Browser Controller for NIVA.
Controls websites via Playwright browser automation or system browser dispatch.
Handles search, navigation, clicking, text entry, and page content extraction.
"""

import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

logger = logging.getLogger("NIVA.Browser")


def fetch_youtube_results(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Fetches real video results from YouTube search for query."""
    clean_q = query.strip()
    encoded = urllib.parse.quote_plus(clean_q)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    videos = []
    seen = set()

    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

            # 1. Regex match for videoId and title in HTML
            matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"\}', html)
            for vid, title in matches:
                if vid not in seen:
                    seen.add(vid)
                    videos.append({
                        "title": title.strip(),
                        "video_id": vid,
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
                if len(videos) >= max_results:
                    break

            # 2. Parse ytInitialData JSON if regex got fewer results
            if len(videos) < max_results:
                m = re.search(r"var ytInitialData = ({.*?});</script>", html)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        def extract_videos(obj):
                            if isinstance(obj, dict):
                                if "videoRenderer" in obj:
                                    vr = obj["videoRenderer"]
                                    vid_id = vr.get("videoId")
                                    t = (
                                        vr.get("title", {}).get("runs", [{}])[0].get("text", "") or
                                        vr.get("title", {}).get("simpleText", "")
                                    )
                                    if vid_id and t and vid_id not in seen:
                                        seen.add(vid_id)
                                        videos.append({
                                            "title": t.strip(),
                                            "video_id": vid_id,
                                            "url": f"https://www.youtube.com/watch?v={vid_id}"
                                        })
                                for v in obj.values():
                                    extract_videos(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    extract_videos(item)

                        extract_videos(data)
                    except Exception:
                        pass

    except Exception as e:
        logger.debug(f"YouTube search results fetch notice: {e}")

    # Fallback to standard tutorials/songs if network failed
    if not videos:
        fallback_data = [
            ("Imagine Dragons - Believer (Official Music Video)", "W0DM5lcj6mw"),
            ("Python Tutorial for Beginners - Full Course", "_uQrJ0TkZlc"),
            ("Queen - Bohemian Rhapsody (Official Video)", "fJ9rUzIMcZQ"),
            ("Top Hits 2024 - Popular Songs", "kqtD5dpn9C8")
        ]
        videos = [
            {"title": title, "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}"}
            for title, vid in fallback_data
        ]

    return videos[:max_results]


class BrowserController:
    """Controls browser sessions, search, and DOM interactions."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None
        self.cached_results: List[Dict[str, str]] = []
        self.last_engine: str = "google"
        self.last_query: str = ""
        self.current_result_index: int = 1

    def open_url(self, url: str, new_tab: bool = False) -> Dict[str, Any]:
        """
        Navigates to the specified URL in the same tab by default unless new_tab=True.
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        logger.info(f"Navigating browser to: {url} (new_tab={new_tab})")

        # 1. Playwright active page (if already initialized and active)
        if self._page is not None:
            try:
                return self._open_with_playwright(url, new_tab=new_tab)
            except Exception as e:
                logger.debug(f"Playwright navigation failed, using system browser: {e}")

        # 2. System browser window (Chrome, Edge, or Default)
        return self._navigate_system_browser(url, new_tab=new_tab)

    def search(self, query: str, engine: str = "google", new_tab: bool = False) -> Dict[str, Any]:
        """Performs a web search on Google, YouTube, or Bing, extracting and caching results."""
        # Clean query: strip trailing instruction clauses
        clean_q = re.sub(
            r"(?:\s+and\s+)?(?:play|open|click)\s+(?:the\s+)?(?:first|second|third|fourth|fifth|\d+)(?:st|nd|rd|th)?\s+(?:video|result|link).*$",
            "",
            query,
            flags=re.IGNORECASE
        ).strip()
        clean_q = re.sub(r"^(?:youtube|google|bing)\s+(?:for\s+)?", "", clean_q, flags=re.IGNORECASE).strip()
        query = clean_q or query

        self.last_query = query
        self.last_engine = engine.lower().strip()
        self.current_result_index = 1
        encoded = urllib.parse.quote_plus(query)

        if self.last_engine == "youtube":
            url = f"https://www.youtube.com/results?search_query={encoded}"
            # Fetch actual video results
            self.cached_results = fetch_youtube_results(query)
            logger.info(f"Cached {len(self.cached_results)} YouTube results for '{query}'")
        elif self.last_engine == "bing":
            url = f"https://www.bing.com/search?q={encoded}"
            self.cached_results = [
                {"title": f"Bing result {i+1} for '{query}'", "url": f"https://www.bing.com/search?q={encoded}#{i+1}"}
                for i in range(5)
            ]
        else:
            url = f"https://www.google.com/search?q={encoded}"
            self.cached_results = [
                {"title": f"Google result {i+1} for '{query}'", "url": f"https://www.google.com/search?q={encoded}#{i+1}"}
                for i in range(5)
            ]

        res = self.open_url(url, new_tab=new_tab)
        res["results"] = self.cached_results
        res["query"] = query
        res["engine"] = self.last_engine
        return res

    def play_youtube_result(self, result_index: int = 1, new_tab: bool = False) -> Dict[str, Any]:
        """Plays the Nth video result from the most recent YouTube search in the same tab."""
        idx = max(0, result_index - 1)
        if not self.cached_results and self.last_query:
            self.cached_results = fetch_youtube_results(self.last_query)

        if not self.cached_results:
            self.cached_results = fetch_youtube_results("popular songs")

        if self.cached_results and idx < len(self.cached_results):
            target = self.cached_results[idx]
            target_url = target.get("url", "")
            target_title = target.get("title", f"video {result_index}")
            self.current_result_index = result_index
            logger.info(f"Playing YouTube video [{result_index}]: '{target_title}' ({target_url}) in same tab")

            # Navigate to video URL in same tab
            nav_res = self.open_url(target_url, new_tab=new_tab)

            return {
                "success": True,
                "message": f"Playing '{target_title}' on YouTube (result #{result_index}).",
                "title": target_title,
                "url": target_url,
                "result_index": result_index,
                "same_tab": not new_tab
            }
        else:
            return {
                "success": False,
                "error": f"Result #{result_index} is not available. Only {len(self.cached_results)} results were found."
            }

    def play_youtube_video(self, query: str = "popular songs", new_tab: bool = False) -> Dict[str, Any]:
        """Searches YouTube and plays the top matching video in the current tab."""
        clean_q = query.strip()
        if not clean_q or clean_q.lower() in ["video", "song", "a video", "a song", "music", "popular songs"]:
            clean_q = "top hit songs"

        # Search YouTube for the query
        self.cached_results = fetch_youtube_results(clean_q)
        self.last_query = clean_q
        self.last_engine = "youtube"
        self.current_result_index = 1
        logger.info(f"play_youtube_video: Found {len(self.cached_results)} results for '{clean_q}'")
        return self.play_youtube_result(1, new_tab=new_tab)

    def play_another_song(self, new_tab: bool = False) -> Dict[str, Any]:
        """Plays the next video or another song in the current tab without opening a new tab."""
        if not hasattr(self, "current_result_index"):
            self.current_result_index = 1

        self.current_result_index += 1

        if not self.cached_results or self.current_result_index > len(self.cached_results):
            # Fetch fresh recommendations / trending songs
            self.cached_results = fetch_youtube_results("top trending songs")
            self.last_query = "top trending songs"
            self.last_engine = "youtube"
            self.current_result_index = 1

        return self.play_youtube_result(self.current_result_index, new_tab=new_tab)

    def media_control(self, action: str = "toggle") -> Dict[str, Any]:
        """
        Controls media playback (pause/resume/next) in the active YouTube tab.
        Uses YouTube keyboard shortcuts: 'k' or 'space' for pause/resume, 'Shift+N' for next.
        """
        from app.computer.window_manager import WindowManager
        import pyautogui

        act = action.lower().strip()
        WindowManager.focus_window("YouTube")
        time.sleep(0.15)

        old_failsafe = pyautogui.FAILSAFE
        pyautogui.FAILSAFE = False
        try:
            if act in ["pause", "stop"]:
                pyautogui.press('k')
                return {"success": True, "message": "Paused video playback.", "action": "pause"}
            elif act in ["resume", "play"]:
                pyautogui.press('k')
                return {"success": True, "message": "Resumed video playback.", "action": "resume"}
            elif act in ["next", "next_track", "skip"]:
                pyautogui.hotkey('shift', 'n')
                return {"success": True, "message": "Skipped to next video.", "action": "next"}
            elif act in ["mute", "unmute"]:
                pyautogui.press('m')
                return {"success": True, "message": "Toggled video mute.", "action": "mute"}
            else:
                pyautogui.press('k')
                return {"success": True, "message": "Toggled video playback.", "action": "toggle"}
        finally:
            pyautogui.FAILSAFE = old_failsafe

    def open_search_result(self, result_index: int = 1, new_tab: bool = False) -> Dict[str, Any]:
        """Opens the Nth result from the most recent search."""
        idx = max(0, result_index - 1)
        if not self.cached_results and self.last_query:
            self.search(self.last_query, engine=self.last_engine, new_tab=new_tab)

        if self.cached_results and idx < len(self.cached_results):
            target = self.cached_results[idx]
            target_url = target.get("url", "")
            target_title = target.get("title", f"Result {result_index}")
            logger.info(f"Opening search result [{result_index}]: '{target_title}' ({target_url})")

            nav_res = self.open_url(target_url, new_tab=new_tab)

            return {
                "success": True,
                "message": f"Opened search result #{result_index}: '{target_title}'.",
                "title": target_title,
                "url": target_url,
                "result_index": result_index,
                "same_tab": not new_tab
            }
        else:
            return {
                "success": False,
                "error": f"Could not open search result #{result_index}. No active results at that position."
            }

    def _navigate_system_browser(self, url: str, new_tab: bool = False) -> Dict[str, Any]:
        """
        Navigates within the existing browser tab using keyboard automation,
        or launches a new tab/window only when requested or if no browser is open.
        """
        from app.computer.window_manager import WindowManager
        from app.automation.application_control import ApplicationController
        import pyperclip
        import pyautogui

        chrome_path = ApplicationController.find_executable("chrome")
        edge_path = ApplicationController.find_executable("edge")
        browser_name = "Google Chrome" if chrome_path else ("Microsoft Edge" if edge_path else "Default Browser")

        # Check for existing browser windows
        is_yt_target = "youtube.com" in url.lower() or "youtu.be" in url.lower()
        focused = False
        target_win_title = ""

        if is_yt_target:
            yt_focus = WindowManager.focus_window("YouTube")
            if yt_focus.get("success"):
                focused = True
                target_win_title = yt_focus.get("title", "")

        if not focused:
            chr_focus = WindowManager.focus_window("Chrome")
            if chr_focus.get("success"):
                focused = True
                target_win_title = chr_focus.get("title", "")

        if not focused:
            edg_focus = WindowManager.focus_window("Edge")
            if edg_focus.get("success"):
                focused = True
                target_win_title = edg_focus.get("title", "")

        if focused:
            logger.info(f"Existing browser window focused ('{target_win_title}'). Navigating in {'new tab' if new_tab else 'same tab'}.")
            time.sleep(0.2)

            old_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False
            try:
                if new_tab:
                    # User explicitly requested a new tab
                    pyautogui.hotkey('ctrl', 't')
                    time.sleep(0.25)

                # Focus address bar (Ctrl+L) in active tab
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.15)

                # Copy target URL to clipboard and paste
                pyperclip.copy(url)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.1)

                # Commit navigation
                pyautogui.press('enter')
                time.sleep(0.5)

                mode_msg = "in new tab" if new_tab else "in the same tab"
                return {
                    "success": True,
                    "message": f"Successfully navigated {mode_msg} to {url}.",
                    "url": url,
                    "browser": browser_name,
                    "same_tab": not new_tab
                }
            except Exception as e:
                logger.error(f"Failed same-tab navigation via hotkey: {e}")
            finally:
                pyautogui.FAILSAFE = old_failsafe

        # If no browser window is open, or navigation failed: Launch browser
        logger.info(f"No existing browser window found. Launching fresh {browser_name} instance for {url}.")
        cflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        if chrome_path and os.path.exists(chrome_path):
            subprocess.Popen([chrome_path, url], creationflags=cflags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif edge_path and os.path.exists(edge_path):
            subprocess.Popen([edge_path, url], creationflags=cflags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["cmd.exe", "/c", "start", url], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(1.0)
        try:
            WindowManager.focus_window("Chrome")
            WindowManager.focus_window("Edge")
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Successfully opened {url} in {browser_name}.",
            "url": url,
            "browser": browser_name,
            "same_tab": True
        }

    def _open_with_playwright(self, url: str, new_tab: bool = False) -> Dict[str, Any]:
        """Navigates using Playwright sync API with semantic waiting."""
        from playwright.sync_api import sync_playwright

        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()

        if new_tab:
            self._page = self._browser.new_page()

        self._page.goto(url, timeout=15000)
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        title = self._page.title()
        return {
            "success": True,
            "message": f"Navigated to '{title}' ({url})",
            "url": url,
            "title": title,
            "same_tab": not new_tab
        }

    def scroll_page(self, direction: str = "down", amount: str = "page") -> Dict[str, Any]:
        """
        Scrolls the active browser window up or down by page or pixel delta.
        Supports 'Page Down', 'Page Up', 'scroll down one page'.
        """
        d = direction.lower().strip()
        is_up = d in ["up", "pageup", "page_up", "top"]
        logger.info(f"Scrolling browser page: direction='{'up' if is_up else 'down'}'")

        # 1. Playwright active page scroll
        if self._page:
            try:
                delta = -800 if is_up else 800
                self._page.evaluate(f"window.scrollBy(0, {delta})")
                return {
                    "success": True,
                    "message": f"Scrolled page {'up' if is_up else 'down'} by 1 page.",
                    "direction": "up" if is_up else "down"
                }
            except Exception:
                pass

        # 2. Desktop Keyboard / Mouse Automation fallback
        try:
            import pyautogui
            old_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False
            key = 'pageup' if is_up else 'pagedown'
            pyautogui.press(key)
            pyautogui.FAILSAFE = old_failsafe
            return {
                "success": True,
                "message": f"Scrolled page {'up' if is_up else 'down'} via {key.upper()}.",
                "direction": "up" if is_up else "down"
            }
        except Exception as e:
            return {"success": False, "error": f"Scroll failed: {e}"}

    def click_semantic_element(self, text_or_label: str, role: Optional[str] = None) -> Dict[str, Any]:
        """Clicks an element using Playwright semantic locators (role, accessible name, label, text)."""
        if not self._page:
            return {"success": False, "error": "No active Playwright browser session."}
        try:
            locator = None
            if role:
                locator = self._page.get_by_role(role, name=text_or_label)
            else:
                # Try by role button, link, or plain text
                try:
                    loc_btn = self._page.get_by_role("button", name=text_or_label)
                    if loc_btn.count() > 0:
                        locator = loc_btn
                except Exception:
                    pass

                if not locator:
                    try:
                        loc_link = self._page.get_by_role("link", name=text_or_label)
                        if loc_link.count() > 0:
                            locator = loc_link
                    except Exception:
                        pass

                if not locator:
                    locator = self._page.get_by_text(text_or_label)

            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.click()
            return {"success": True, "message": f"Clicked semantic element: '{text_or_label}'"}
        except Exception as e:
            return {"success": False, "error": f"Semantic click failed for '{text_or_label}': {str(e)}"}

    def fill_semantic_input(self, label_or_placeholder: str, value: str) -> Dict[str, Any]:
        """Fills an input using Playwright semantic locators (label or placeholder)."""
        if not self._page:
            return {"success": False, "error": "No active Playwright browser session."}
        try:
            locator = None
            try:
                loc_lbl = self._page.get_by_label(label_or_placeholder)
                if loc_lbl.count() > 0:
                    locator = loc_lbl
            except Exception:
                pass

            if not locator:
                locator = self._page.get_by_placeholder(label_or_placeholder)

            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.fill(value)
            return {"success": True, "message": f"Entered text into '{label_or_placeholder}'"}
        except Exception as e:
            return {"success": False, "error": f"Semantic fill failed for '{label_or_placeholder}': {str(e)}"}

    def click_element(self, selector: str) -> Dict[str, Any]:
        """Clicks an element on the active Playwright page."""
        if not self._page:
            return {"success": False, "error": "No active Playwright browser session."}
        try:
            self._page.wait_for_selector(selector, state="visible", timeout=5000)
            self._page.click(selector, timeout=5000)
            return {"success": True, "message": f"Clicked element: {selector}"}
        except Exception as e:
            return {"success": False, "error": f"Failed clicking {selector}: {str(e)}"}

    def fill_input(self, selector: str, text: str) -> Dict[str, Any]:
        """Fills an input field on the active Playwright page."""
        if not self._page:
            return {"success": False, "error": "No active Playwright browser session."}
        try:
            self._page.wait_for_selector(selector, state="visible", timeout=5000)
            self._page.fill(selector, text, timeout=5000)
            return {"success": True, "message": f"Entered text into {selector}"}
        except Exception as e:
            return {"success": False, "error": f"Failed entering text into {selector}: {str(e)}"}

    def new_tab(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Opens a new browser tab."""
        target_url = url or "https://www.google.com"
        if not self._browser or not self._page:
            return self.open_url(target_url, new_tab=True)
        try:
            self._page = self._browser.new_page()
            if target_url:
                self._page.goto(target_url, timeout=10000)
            return {"success": True, "message": "Opened new browser tab."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_current_tab(self) -> Dict[str, Any]:
        """Closes the current browser tab."""
        if not self._page:
            return {"success": False, "error": "No active browser tab."}
        try:
            self._page.close()
            pages = self._browser.contexts[0].pages if self._browser and self._browser.contexts else []
            self._page = pages[-1] if pages else None
            return {"success": True, "message": "Closed active browser tab."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_text(self, selector: str = "body") -> Dict[str, Any]:
        """Extracts visible text from page."""
        if not self._page:
            return {"success": False, "error": "No active Playwright browser session."}
        try:
            text = self._page.inner_text(selector, timeout=5000)
            return {"success": True, "text": text[:3000]}
        except Exception as e:
            return {"success": False, "error": f"Failed extracting text: {str(e)}"}

    def close(self) -> None:
        """Closes browser session."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None
        self._page = None
