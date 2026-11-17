"""
Pydantic schemas and strict parameter validation for all JARVIS tools.
Guarantees structured tool calls with type safety.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Application & Window Schemas
# -------------------------------------------------------------
class LaunchAppParams(BaseModel):
    app_name: str = Field(..., description="Name or executable of the application to launch (e.g. 'chrome', 'notepad', 'calc', 'excel', 'code')")
    arguments: Optional[str] = Field(None, description="Optional command-line arguments to pass")


class CloseAppParams(BaseModel):
    app_name: str = Field(..., description="Name or process of the application to close")
    force: bool = Field(False, description="Whether to terminate forcibly if not responding")


class WindowControlParams(BaseModel):
    window_title: Optional[str] = Field(None, description="Title or part of the title of the target window")
    action: Literal["focus", "minimize", "maximize", "restore", "close"] = Field("focus", description="Action to perform on the window")


# -------------------------------------------------------------
# File & Directory Schemas
# -------------------------------------------------------------
class CreateFolderParams(BaseModel):
    path: str = Field(..., description="Target folder path to create (supports ~ and Desktop/Downloads references)")


class CreateFileParams(BaseModel):
    path: str = Field(..., description="Path of the file to create")
    content: str = Field("", description="Initial text content of the file")


class ReadFileParams(BaseModel):
    path: str = Field(..., description="Path of the file to read (supports .txt, .docx, .pdf, .xlsx, .csv)")
    max_lines: int = Field(200, description="Maximum number of lines or rows to retrieve")


class FileMoveCopyParams(BaseModel):
    source: str = Field(..., description="Source file or folder path")
    destination: str = Field(..., description="Destination directory or file path")
    overwrite: bool = Field(False, description="Whether to overwrite existing destination")


class DeleteFileParams(BaseModel):
    path: str = Field(..., description="Target path to delete")
    permanent: bool = Field(False, description="If False, moves to Recycle Bin where possible; if True, permanently deletes")


class SearchFilesParams(BaseModel):
    directory: str = Field("Desktop", description="Directory to search (e.g., 'Desktop', 'Downloads', 'Documents', or absolute path)")
    pattern: str = Field("*.*", description="File name pattern or extension (e.g., '*.pdf', '*report*', '*.py')")
    recursive: bool = Field(True, description="Whether to search subdirectories")


class OrganizeFolderParams(BaseModel):
    directory: str = Field("Downloads", description="Directory to organize by file extension")
    dry_run: bool = Field(False, description="Simulate without actually moving files")


# -------------------------------------------------------------
# Windows Settings Schemas
# -------------------------------------------------------------
class WindowsSettingParams(BaseModel):
    setting: Literal["bluetooth", "wifi", "volume", "mute", "brightness"] = Field(..., description="The setting to adjust")
    value: Union[str, int, float, bool] = Field(..., description="Target state: 'on', 'off', True, False, integer 0-100, or relative step like '+10' / '-10'")


class OpenSettingsPageParams(BaseModel):
    page: str = Field("system", description="Settings category to open")
    page_name: Optional[str] = Field(None, description="Settings category alias")


class CalculateExpressionParams(BaseModel):
    expression: str = Field(..., description="Mathematical expression or calculation phrase (e.g. '2+2', '15*6', 'subtract 8 from 20')")
    ensure_open: bool = Field(False, description="Whether to launch Calculator if not already open")


class PlanTripParams(BaseModel):
    destination: Optional[str] = Field("Goa", description="Destination for the trip")
    duration: Optional[str] = Field("7 days", description="Duration of the trip")
    duration_days: Optional[int] = Field(7, description="Duration in number of days")
    people: Optional[int] = Field(2, description="Number of travelers")
    budget: Optional[str] = Field("50,000 INR", description="Budget for the trip")


# -------------------------------------------------------------
# Mouse & Keyboard Schemas
# -------------------------------------------------------------
class MouseClickParams(BaseModel):
    x: Optional[int] = Field(None, description="X screen coordinate (if None, clicks at current cursor position)")
    y: Optional[int] = Field(None, description="Y screen coordinate (if None, clicks at current cursor position)")
    button: Literal["left", "right", "middle"] = Field("left", description="Mouse button to click")
    clicks: int = Field(1, description="Number of clicks (1 for single, 2 for double)")


class TypeTextParams(BaseModel):
    text: str = Field(..., description="Text string to type into the currently active element")
    press_enter: bool = Field(False, description="Whether to press Enter after typing")
    interval: float = Field(0.02, description="Delay between individual keystrokes in seconds")


class HotkeyParams(BaseModel):
    keys: List[str] = Field(..., description="Sequence of keys to press simultaneously (e.g. ['ctrl', 'c'], ['win', 'd'], ['alt', 'tab'])")


class ScrollParams(BaseModel):
    amount: int = Field(..., description="Scroll units (positive scrolls up, negative scrolls down)")


# -------------------------------------------------------------
# Browser Automation Schemas
# -------------------------------------------------------------
class BrowserOpenParams(BaseModel):
    url: str = Field(..., description="Website URL to navigate to")
    new_tab: bool = Field(False, description="Whether to open in a new tab instead of navigating the current tab")


class BrowserSearchParams(BaseModel):
    query: str = Field(..., description="Search query string")
    engine: Literal["google", "youtube", "bing"] = Field("google", description="Search engine to use")
    new_tab: bool = Field(False, description="Whether to open in a new tab instead of navigating the current tab")


class BrowserOpenResultParams(BaseModel):
    result_index: int = Field(1, description="1-based index of search result or video to open or play")
    new_tab: bool = Field(False, description="Whether to open in a new tab instead of navigating the current tab")


class PlayVideoParams(BaseModel):
    query: str = Field("popular songs", description="Song or video title, or search query to play on YouTube")
    new_tab: bool = Field(False, description="Whether to open in a new tab instead of navigating the current tab")


class PlayAnotherVideoParams(BaseModel):
    new_tab: bool = Field(False, description="Whether to open in a new tab instead of navigating the current tab")


class MediaControlParams(BaseModel):
    action: Literal["play", "pause", "resume", "stop", "next", "toggle", "mute", "unmute"] = Field("toggle", description="Media playback action")


class BrowserScrollParams(BaseModel):
    direction: Literal["up", "down", "pageup", "pagedown"] = Field("down", description="Scroll direction: 'up', 'down', 'pageup', 'pagedown'")
    amount: Literal["page", "half_page", "line"] = Field("page", description="Amount of scrolling to perform")


class EmailReadParams(BaseModel):
    query_or_filter: Optional[str] = Field(None, description="Optional search term or sender name to locate email")


class EmailDraftParams(BaseModel):
    recipient: str = Field(..., description="Recipient email address or name")
    subject: str = Field("No Subject", description="Subject of the email draft")
    body: str = Field(..., description="Body message of the email")


class EmailSendParams(BaseModel):
    recipient: str = Field(..., description="Recipient email address or name")
    subject: str = Field("No Subject", description="Subject of the email")
    body: str = Field(..., description="Body message of the email")
    confirmed: bool = Field(False, description="Mandatory confirmation flag before dispatching email")


class BrowserActionParams(BaseModel):
    selector: str = Field(..., description="CSS selector, text, or accessibility label of the target element")
    action: Literal["click", "type", "extract_text", "wait_for"] = Field("click", description="Action to perform")
    value: Optional[str] = Field(None, description="Text value to enter if action is 'type'")


# -------------------------------------------------------------
# Office Automation Schemas
# -------------------------------------------------------------
class CreateExcelParams(BaseModel):
    path: str = Field(..., description="Path to save the generated .xlsx file")
    sheet_title: str = Field("Data", description="Name of the worksheet")
    headers: List[str] = Field(..., description="Column header strings")
    rows: List[List[Any]] = Field(..., description="Table row records")
    include_summary_row: bool = Field(False, description="Whether to append a total/sum formula row for numerical columns")


class CreateWordParams(BaseModel):
    path: str = Field(..., description="Path to save the generated .docx file")
    title: str = Field("Document", description="Title heading")
    paragraphs: List[str] = Field(..., description="Body paragraph texts")
    table_data: Optional[List[List[str]]] = Field(None, description="Optional embedded table data")


class CreatePowerPointParams(BaseModel):
    path: str = Field(..., description="Path to save the generated .pptx file")
    presentation_title: str = Field(..., description="Presentation Title")
    slides: List[Dict[str, Any]] = Field(..., description="List of slides, each with 'title' and 'bullets' (list of strings)")


# -------------------------------------------------------------
# Form Filling Schemas
# -------------------------------------------------------------
class FillFormParams(BaseModel):
    field_mappings: Dict[str, str] = Field(..., description="Key-value mapping of field label / selector to value")
    submit_after_fill: bool = Field(False, description="Whether to click the submit button after filling all fields")


# -------------------------------------------------------------
# Microsoft UI Automation Schemas
# -------------------------------------------------------------
class UIAClickParams(BaseModel):
    window_title: Optional[str] = Field("", description="Target window title substring to locate (empty for active window)")
    element_name: str = Field(..., description="Accessible element name or label (e.g. 'File', 'Save', 'OK', 'Close', 'Search')")
    control_type: Optional[str] = Field(None, description="Optional control type (e.g. 'Button', 'MenuItem', 'TabItem')")


class UIASetTextParams(BaseModel):
    window_title: str = Field(..., description="Target window title substring to locate")
    element_name: str = Field(..., description="Accessible name or automation ID of the text field")
    text: str = Field(..., description="Text content to enter into the accessible field")


class UIAListElementsParams(BaseModel):
    window_title: str = Field(..., description="Target window title substring to inspect")


# -------------------------------------------------------------
# System & Privacy Schemas
# -------------------------------------------------------------
class SystemInfoParams(BaseModel):
    query_type: Literal["battery", "storage", "resources", "status"] = Field("status", description="Hardware or resource metric to inspect")


class HistoryActionParams(BaseModel):
    action: Literal["clear", "status", "enable", "disable"] = Field("status", description="Action to perform on local history")


# -------------------------------------------------------------
# Screen Observation Schemas
# -------------------------------------------------------------
class ScreenObservationParams(BaseModel):
    region: Optional[List[int]] = Field(None, description="Optional bounding box [left, top, width, height]")
    ocr: bool = Field(True, description="Whether to extract visible text via OCR")
