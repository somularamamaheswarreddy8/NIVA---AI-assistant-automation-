# NIVA — Universal AI-Powered Autonomous Computer Control System

![NIVA Banner](https://img.shields.io/badge/NIVA-Autonomous%20Computer%20Agent-00E5FF?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%2B-green?style=for-the-badge)
![NLU](https://img.shields.io/badge/NLU-Statistical%20ML%20(99.6%25)-purple?style=for-the-badge)
![UI](https://img.shields.io/badge/UI-PySide6%20Qt-orange?style=for-the-badge)

---

## 1. Overview

**NIVA** (Natural Intelligent Voice Assistant) is an intelligent, voice-first autonomous computer-use agent designed to operate Windows computers like a human user. Rather than functioning as a rigid chatbot or simple macro recorder, NIVA captures natural speech transcripts, classifies intent and extracts entities using a trained statistical Machine Learning NLU model, dynamically plans multi-step workflows, and controls the actual Windows desktop, installed applications, websites, file systems, and system settings.

### Key Highlights
- **Configurable Identity:** Renamed from legacy JARVIS to **NIVA** everywhere in code, UI, wake word, logs, and dialogs. Assistant name is dynamically configurable via `ASSISTANT_NAME` in `.env`.
- **Decoupled Voice Pipeline:** Clean separation of concerns between speech recognition (audio-to-text) and semantic command understanding (statistical NLU model).
- **Comprehensive Multilingual NLU Model:** Trained on **7,960 synthetic, labeled utterances** covering English, Telugu written in Latin script (`te-Latn` / Tanglish), and Telugu-English code-mixed commands across **111 distinct intents**. Achieves **99.50% validation accuracy**.
- **Microsoft UI Automation (UIA) Integration:** Employs `pywinauto` with `backend="uia"` for robust, accessible UI element inspection, invoking controls via InvokePattern and ValuePattern instead of brittle fixed screen coordinates.
- **Reliable Browser Automation:** Supports Playwright semantic locators (by role, label, and text) with explicit `domcontentloaded` waits.
- **Privacy & Local History Controls:** SQLite storage at `~/.niva/niva.db` with user-controlled dialogue history toggle and instant clearing via GUI settings.
- **Natural Language Generalization:** Understands varied wording, spelling, and phrasing (e.g. *"Chrome theeyi ra"*, *"Notepad open cheyyi brother"*, *"Bluetooth bandh chey"*, *"Sound penchu"*, *"Excel lo monthly expenses create chey"*, *"Desktop meeda AI folder create chesi and then open Chrome"*).
- **Interactive Clarification System:** If speech transcription confidence is below calibrated threshold (< 0.40) or required slots (such as app name or search query) are missing, NIVA asks a concise clarification question rather than guessing.
- **Dedicated Real-Time Interruption Controller:** Instant, high-priority hard-stop (**STOP**, **PAUSE**, **RESUME**, **OVERRIDE**, **UNDO**) that triggers immediately on background threads without waiting for external API latency.
- **Universal Windows Desktop Control:** Launches, switches, minimizes, maximizes, and closes applications; inspects and controls Windows Settings (Bluetooth, Wi-Fi, volume, mute, brightness) with real verification.
- **Office & Documents Automation:** Creates styled Microsoft Excel spreadsheets with formulas, formatted Microsoft Word reports, and PowerPoint slide decks.
- **Safety & Permissions Architecture:** Protects against destructive actions (file deletion, formatting, system modifications) with interactive GUI confirmation dialogs and audit logging.

---

## 2. Voice Pipeline Architecture

The complete voice execution pipeline flows strictly through independent, verifiable stages:

```
[System Microphone]
        │  (Audio Stream)
        ▼
[Continuous VoiceListener]  ──► [UI Audio Waveform Spectrum]
        │  (Raw Audio Chunk)
        ▼
[SpeechToTextEngine]        ──► Converts audio to text (Google Speech API / Whisper)
        │  (Raw Transcript)
        ▼
[Interruption Controller]   ──► Fast-path check: STOP / PAUSE / RESUME / OVERRIDE
        │  (Non-interruption prompt)
        ▼
[NLUEngine (Trained ML)]    ──► Intent classification & Slot Extraction (English, Tanglish, Mixed)
        │                       ├─ Calibrated Confidence Score (< 0.40 -> Clarification Question)
        │                       ├─ Slot Normalization (App, Path, URL, Setting, Query)
        │                       └─ Compound Multi-step Decomposition
        ▼
[TaskPlanner]               ──► Resolves conversational context -> Generates TaskStep execution plan
        │  (Structured Task Steps)
        ▼
[Safety / PermissionManager]──► Evaluates safety policy (SAFE, MODERATE, SENSITIVE, DANGEROUS)
        │                       └─ Prompts GUI Authorization Dialog if sensitive/destructive
        ▼
[TaskExecutor]              ──► Dispatches calls to ToolRegistry (App, Windows, Settings, Office, Browser)
        │  (Action Result Verification)
        ▼
[Feedback & Response]       ──► Spoken confirmation (TextToSpeech) + Audit Log + Qt GUI Update
```

---

## 3. Dataset & NLU Model Training

### The Dataset
The project includes a synthetic command-understanding dataset saved at:
`jarvis/data/niva_commands_dataset.jsonl`

- **Total Records:** 7,960 uniquely generated synthetic utterances across 111 intents.
- **Languages Supported:**
  - `en`: Standard and conversational English.
  - `te-Latn`: Telugu transliterated into Latin characters (Tanglish).
  - `te-en`: Telugu-English code-mixed colloquial commands.
- **Schema:**
  ```json
  {
    "utterance": "Excel lo monthly expenses create chey",
    "language_mix": "te-en",
    "intent": "excel_create_sheet",
    "entities": {"sheet_title": "monthly expenses", "include_summary_row": true},
    "risk_level": "SAFE",
    "requires_confirmation": false,
    "expected_tool": "create_excel",
    "paraphrase_group": "grp_excel_create",
    "is_synthetic": true
  }
  ```
- **Supported Intents (111 categories across 11 domains):**
  - *Applications & Window Control:* `app_launch`, `app_close`, `app_switch`, `app_restart`, `app_check_running`, `app_kill_force`, `window_minimize`, `window_maximize`, `window_restore`, `window_show_desktop`, `window_snap_left`, `window_snap_right`, `window_focus_next`, `window_list_running`
  - *Browser Automation:* `browser_open_url`, `browser_search_google`, `browser_search_youtube`, `browser_search_bing`, `browser_new_tab`, `browser_close_tab`, `browser_switch_tab`, `browser_read_page_text`, `browser_reload_page`, `browser_go_back`, `browser_go_forward`, `browser_bookmark_page`
  - *Filesystem Management:* `folder_create`, `folder_delete`, `folder_open`, `folder_organize_by_type`, `file_create`, `file_read`, `file_delete`, `file_delete_permanent`, `file_move`, `file_copy`, `file_rename`, `file_open`, `file_search_by_name`, `file_search_by_extension`, `file_find_duplicates`
  - *Office & Documents:* `excel_create_sheet`, `excel_add_totals_formula`, `excel_format_table`, `word_create_document`, `word_add_table`, `word_append_notes`, `powerpoint_create_presentation`, `powerpoint_add_slide`, `document_convert_to_pdf`, `document_read_metadata`
  - *Windows Settings & Control Panel:* `setting_bluetooth_on`, `setting_bluetooth_off`, `setting_wifi_on`, `setting_wifi_off`, `setting_volume_set`, `setting_volume_increase`, `setting_volume_decrease`, `setting_volume_mute`, `setting_volume_unmute`, `setting_brightness_set`, `setting_brightness_increase`, `setting_brightness_decrease`, `setting_open_bluetooth_page`, `setting_open_network_settings`, `setting_open_sound_settings`, `setting_open_display_settings`, `setting_open_windows_update`, `setting_open_control_panel`, `setting_open_task_manager`, `setting_open_storage_settings`, `setting_open_default_apps`, `setting_open_system_about`
  - *Screen & Vision:* `screen_capture_full`, `screen_capture_window`, `screen_ocr_read_text`, `screen_lock`
  - *Mouse, Keyboard, Clipboard:* `mouse_click_element`, `mouse_double_click`, `mouse_right_click`, `keyboard_type_text`, `keyboard_press_hotkey`, `keyboard_scroll_up`, `keyboard_scroll_down`, `clipboard_copy_selection`, `clipboard_paste`, `clipboard_read_content`
  - *Forms & Structured Input:* `form_fill_structured`, `form_submit`, `form_clear_fields`
  - *Privacy & History:* `history_enable`, `history_disable`, `history_clear`
  - *System Diagnostics:* `system_status`, `system_resource_usage`, `system_battery_status`, `system_storage_status`, `system_explain_capabilities`
  - *Interruption & Context:* `interruption_stop`, `interruption_pause`, `interruption_resume`, `interruption_override`, `interruption_undo`, `context_clarify_app`, `context_clarify_query`, `context_confirm_yes`, `context_confirm_no`, `context_correct_parameter`, `context_specify_target_location`, `context_refer_previous_result`, `compound_multistep`.

### Training Pipeline
A statistical machine learning pipeline is built with scikit-learn using a composite feature extraction union:
1. **Word TF-IDF n-grams** (1 to 3 words) with sublinear term-frequency scaling.
2. **Character-wb TF-IDF n-grams** (2 to 5 character boundaries) to robustly capture Telugu transliteration and spelling variations (`chey`, `cheyyi`, `theeyi`, `thiyi`, `pettu`).
3. **Calibrated Logistic Regression** with $L_2$ regularization for probabilistic confidence scoring.

### Retraining Instructions
To regenerate the dataset or retrain the NLU model at any time:

```bash
# 1. Regenerate synthetic dataset (7,900+ samples across 111 intents)
python jarvis/scripts/generate_dataset.py

# 2. Retrain NLU model and update artifacts
python train_nlu.py
```

Model artifacts are persisted at:
- `jarvis/app/ai/models/nlu_model.joblib` (8.18 MB)
- `jarvis/app/ai/models/nlu_metadata.json`

---

## 4. Runtime Behavior & Interactive Clarification

- **Missing Details:** If the user issues a command missing a required entity (e.g. *"open"* without specifying the application, or *"search"* without specifying the query), NIVA pauses and asks:
  - *"Which application would you like me to open?"*
  - User can respond *"Chrome"*, and NIVA automatically completes the request.
- **Low Confidence:** Unintelligible noise or out-of-domain gibberish is detected when top confidence falls below 0.40. NIVA politely requests clarification instead of executing random actions.
- **Unsupported Commands:** If a user requests a capability not supported by available Windows tools, NIVA explains exactly what capability is missing.
- **Emergency Interruption:** Voice commands like *"NIVA, aapu"*, *"stop now"*, or *"emergency stop"* bypass the AI queue and immediately halt active threads, resetting hardware states.

---

## 5. Verification & Testing

All unit tests and acceptance criteria pass cleanly:

```bash
# Run All Unit Tests (39 unit tests)
python -m unittest discover -s jarvis/tests

# Run NLU-specific tests (multilingual classification, slot extraction, clarifications)
python -m unittest jarvis/tests/test_nlu.py

# Run System Acceptance Tests (14 comprehensive scenarios)
python run_acceptance_tests.py
```

### Acceptance Test Results
- Application Control (`Open Chrome and then open Notepad`): **PASSED**
- Windows Settings (`Turn Bluetooth off`): **PASSED**
- File Management (`Create a folder called NIVA on my Desktop`): **PASSED**
- Browser Automation (`Open YouTube and search for Python tutorials`): **PASSED**
- Form Filling & Data Entry: **PASSED**
- Office Automation (`create an Excel table, calculate the total, and save it`): **PASSED**
- Multi-Application Workflow (`create a Word report and save it`): **PASSED**
- Interruption STOP: **PASSED**
- Interruption PAUSE & RESUME: **PASSED**
- Command OVERRIDE: **PASSED**
- Error Recovery & Safe Reporting: **PASSED**
- Natural Language Instruction (`Clean up Desktop`): **PASSED**
- Code-Mixed Telugu-English (`Excel lo monthly expenses create chey`): **PASSED**
- Interactive Clarification Prompt (`open`): **PASSED**

---

## 6. How to Run NIVA

### Quick Launch
Double-click `run.bat` or run from PowerShell:
```cmd
run.bat
```

### Running with Custom Options
```bash
# Launch GUI mode (Default)
python jarvis/main.py

# Launch Terminal CLI mode
python jarvis/main.py --cli

# Launch without microphone (text input only)
python jarvis/main.py --no-voice
```

---

## 7. Limitations & Verification Notes
- **Operating System:** Designed and verified on Windows 10/11 64-bit with Python 3.11+.
- **Speech Recognition:** Live microphone input uses Google Speech API for transcription; internet connectivity is required for real-time cloud STT unless local Whisper is configured. Command understanding, NLU inference, planning, and execution run **100% offline** locally.
- **Audio Device:** On headless virtual machines without a physical audio recording hardware device, the listener logs a device notice and safely falls back to direct GUI / CLI command entry.
