"""
Main Desktop Application Window for JARVIS.
Futuristic, responsive AI operator console built with PySide6.
"""

from datetime import datetime
import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QProgressBar, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget
)

from app.config import ASSISTANT_NAME
from app.core.assistant import JarvisAssistant
from app.core.task_state import StepStatus, Task, TaskStatus, TaskStep
from app.gui.dialogs import PermissionConfirmationDialog, SettingsDialog
from app.gui.styles import DARK_THEME_QSS
from app.gui.waveform import WaveformVisualizer

logger = logging.getLogger(f"{ASSISTANT_NAME}.GUI")


class MainWindow(QMainWindow):
    """Primary GUI Window for the NIVA Autonomous Assistant."""

    # Thread-safe Qt Signals for GUI updates from background threads
    signal_waveform_amplitude = Signal(float)
    signal_status_update = Signal(str)
    signal_task_update = Signal(object)
    signal_dialogue_logged = Signal(str, str)
    signal_transcript_update = Signal(str)

    def __init__(self, assistant: JarvisAssistant):
        super().__init__()
        self.assistant = assistant
        self.setWindowTitle(f"{ASSISTANT_NAME} — Universal Autonomous AI Computer Control System")
        self.resize(1180, 780)
        self.setMinimumSize(960, 640)

        # Apply dark theme styling
        self.setStyleSheet(DARK_THEME_QSS)

        # Setup GUI Components
        self._init_ui()

        # Connect assistant signals to UI slots
        self._connect_signals()

        # Wire GUI permission confirmation dialog to assistant
        self.assistant.permissions.set_confirmation_callback(self._ask_user_permission)

        # Trigger formalized startup lifecycle sequence
        QTimer.singleShot(100, self._run_startup_sequence)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. Top Header Bar
        # -------------------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)

        # Title & Branding
        brand_layout = QVBoxLayout()
        spaced_title = " ".join(ASSISTANT_NAME.upper())
        title_label = QLabel(spaced_title)
        title_label.setObjectName("headerTitle")
        subtitle_label = QLabel("UNIVERSAL AUTONOMOUS COMPUTER CONTROL AGENT")
        subtitle_label.setStyleSheet("color: #64748B; font-size: 11px; letter-spacing: 1px;")
        brand_layout.addWidget(title_label)
        brand_layout.addWidget(subtitle_label)
        header_layout.addLayout(brand_layout)

        header_layout.addStretch()

        # Status Indicators
        self.status_badge = QLabel("IDLE")
        self.status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.status_badge)

        self.ai_badge = QLabel(f"AI: {self.assistant.llm_provider.provider.upper()}")
        self.ai_badge.setStyleSheet("color: #94A3B8; font-size: 11px; margin-right: 12px;")
        header_layout.addWidget(self.ai_badge)

        # Control Buttons
        self.mic_btn = QPushButton("🎤 Mic: ON")
        self.mic_btn.setStyleSheet("background-color: #064E3B; color: #34D399; font-weight: bold; border: 1px solid #10B981; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        self.mic_btn.clicked.connect(self._toggle_mic)
        header_layout.addWidget(self.mic_btn)

        self.wake_btn = QPushButton()
        self.wake_btn.setObjectName("wakeBtn")
        self.wake_btn.clicked.connect(self._toggle_wake_word)
        self._update_wake_btn()
        header_layout.addWidget(self.wake_btn)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.clicked.connect(self._pause_task)
        header_layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton("▶ Resume")
        self.resume_btn.setObjectName("resumeBtn")
        self.resume_btn.clicked.connect(self._resume_task)
        header_layout.addWidget(self.resume_btn)

        self.stop_btn = QPushButton("⛔ STOP")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumWidth(90)
        self.stop_btn.clicked.connect(self._emergency_stop)
        header_layout.addWidget(self.stop_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(self.settings_btn)

        main_layout.addWidget(header_card)

        # -------------------------------------------------------------
        # 2. Main Content Splitter (Left: Controls/Task, Right: Dialogue)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # Left Column (Waveform + Task Plan + Progress)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        # Waveform Card
        wave_card = QFrame()
        wave_card.setObjectName("card")
        wave_layout = QVBoxLayout(wave_card)
        wave_layout.setContentsMargins(12, 10, 12, 10)
        wave_title = QLabel("LIVE AUDIO SPECTRUM")
        wave_title.setObjectName("sectionTitle")
        wave_layout.addWidget(wave_title)

        self.waveform = WaveformVisualizer()
        wave_layout.addWidget(self.waveform)
        left_layout.addWidget(wave_card)

        # Task Progress Card
        task_card = QFrame()
        task_card.setObjectName("card")
        task_layout = QVBoxLayout(task_card)
        task_layout.setContentsMargins(14, 12, 14, 12)

        self.task_title_label = QLabel("ACTIVE TASK: NONE")
        self.task_title_label.setObjectName("sectionTitle")
        task_layout.addWidget(self.task_title_label)

        self.outcome_banner = QLabel("STATUS: IDLE")
        self.outcome_banner.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 4px 8px; background: #0F172A; border-radius: 4px;")
        self.outcome_banner.setWordWrap(True)
        task_layout.addWidget(self.outcome_banner)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        task_layout.addWidget(self.progress_bar)

        # Steps list
        steps_header = QLabel("EXECUTION STEPS:")
        steps_header.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px; margin-top: 6px;")
        task_layout.addWidget(steps_header)

        self.steps_list = QListWidget()
        task_layout.addWidget(self.steps_list)

        left_layout.addWidget(task_card)

        # Quick Action Chips
        chips_layout = QHBoxLayout()
        quick_actions = [
            ("🌐 Open Chrome", "Open Chrome"),
            ("📁 Clean Downloads", "Organize my Downloads folder"),
            ("📊 Create Excel Report", "Create an Excel table comparing three AI tools and calculate the total"),
            ("📶 Bluetooth Off", "Turn Bluetooth off"),
            ("🛑 Undo", "undo"),
        ]
        for label, cmd in quick_actions:
            chip_btn = QPushButton(label)
            chip_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; border-radius: 4px;")
            chip_btn.clicked.connect(lambda checked=False, c=cmd: self._send_command(c))
            chips_layout.addWidget(chip_btn)

        left_layout.addLayout(chips_layout)
        splitter.addWidget(left_widget)

        # Right Column (Dialogue History & Direct Prompt Input)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Live Speech Recognition & Transcript Card
        transcript_card = QFrame()
        transcript_card.setObjectName("card")
        transcript_layout = QHBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(12, 8, 12, 8)
        transcript_icon = QLabel("🎙️ LIVE TRANSCRIPT:")
        transcript_icon.setStyleSheet("color: #64748B; font-weight: bold; font-size: 11px;")
        transcript_layout.addWidget(transcript_icon)
        self.live_transcript_label = QLabel("Microphone Ready. Say 'NIVA' or speak a command...")
        self.live_transcript_label.setStyleSheet("color: #00E5FF; font-weight: 500; font-size: 11px;")
        transcript_layout.addWidget(self.live_transcript_label)
        transcript_layout.addStretch()
        right_layout.addWidget(transcript_card)

        dialogue_card = QFrame()
        dialogue_card.setObjectName("card")
        dialogue_layout = QVBoxLayout(dialogue_card)
        dialogue_layout.setContentsMargins(14, 12, 14, 12)

        history_title = QLabel("INTERACTION & AUDIT LOG")
        history_title.setObjectName("sectionTitle")
        dialogue_layout.addWidget(history_title)

        self.dialogue_history = QTextEdit()
        self.dialogue_history.setReadOnly(True)
        dialogue_layout.addWidget(self.dialogue_history)

        right_layout.addWidget(dialogue_card)

        # Input Row
        input_card = QFrame()
        input_card.setObjectName("card")
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(10, 8, 10, 8)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Speak or type any command (e.g. 'Open Chrome, search Python tutorials, and create an Excel sheet')...")
        self.command_input.returnPressed.connect(self._on_input_submitted)
        input_layout.addWidget(self.command_input)

        self.send_btn = QPushButton("Execute")
        self.send_btn.clicked.connect(self._on_input_submitted)
        input_layout.addWidget(self.send_btn)

        self.override_btn = QPushButton("⚡ Override")
        self.override_btn.setObjectName("pauseBtn")
        self.override_btn.setToolTip("Immediately stop active task and switch to this command")
        self.override_btn.clicked.connect(self._on_override_submitted)
        input_layout.addWidget(self.override_btn)

        right_layout.addWidget(input_card)

        splitter.addWidget(right_widget)
        splitter.setSizes([480, 700])
        main_layout.addWidget(splitter)

    def _update_wake_btn(self):
        enabled = getattr(self.assistant.wake_detector, "enabled", False)
        wake_phrase = getattr(self.assistant.wake_detector, "wake_word", "niva").upper()
        if enabled:
            self.wake_btn.setText(f"🔔 Wake Word: ON ('{wake_phrase}')")
            self.wake_btn.setStyleSheet("background-color: #065F46; color: #34D399; font-weight: bold; border: 1px solid #10B981; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
        else:
            self.wake_btn.setText("🔔 Wake Word: OFF (Always Listen)")
            self.wake_btn.setStyleSheet("background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-size: 11px;")

    def _toggle_wake_word(self):
        new_state = not self.assistant.wake_detector.enabled
        self.assistant.wake_detector.enabled = new_state
        self.assistant.db.set_setting("WAKE_WORD_ENABLED", new_state)
        self._update_wake_btn()
        status_txt = f"Wake-word requirement {'ENABLED' if new_state else 'DISABLED (Continuous Direct Listening)'}."
        self._log_dialogue("system", status_txt)

    def _connect_signals(self):
        """Connect background thread signals to Qt UI slots."""
        self.signal_waveform_amplitude.connect(self.waveform.set_amplitude)
        self.signal_status_update.connect(self._update_status_badge)
        self.signal_task_update.connect(self._update_task_ui)
        self.signal_dialogue_logged.connect(self._append_dialogue_message)
        self.signal_transcript_update.connect(self._update_live_transcript)

        # Wire assistant callbacks to emit Qt signals
        self.assistant.on_task_updated = lambda t: self.signal_task_update.emit(t)
        self.assistant.on_message_logged = lambda r, txt: self.signal_dialogue_logged.emit(r, txt)
        self.assistant.voice_listener.on_waveform_data = lambda amp: self.signal_waveform_amplitude.emit(amp)
        self.assistant.voice_listener.on_status_change = lambda s: self.signal_status_update.emit(s)
        self.assistant.voice_listener.on_transcript_preview = lambda txt: self.signal_transcript_update.emit(txt)
        self.assistant.voice_listener.on_error = lambda err: self._handle_audio_error(err)
        if hasattr(self.assistant, "tts"):
            self.assistant.tts.on_speaking_started = lambda txt: self.signal_status_update.emit("SPEAKING")
            self.assistant.tts.on_speaking_finished = lambda txt: self.signal_status_update.emit("LISTENING" if self.assistant.voice_listener.mic_enabled else "MUTED")
            self.assistant.tts.on_error = lambda err: self._handle_audio_error(err)

    def _handle_audio_error(self, err_msg: str):
        self.signal_dialogue_logged.emit("error", err_msg)
        self.signal_transcript_update.emit(f"⚠️ {err_msg}")

    @Slot(str)
    def _update_live_transcript(self, text: str):
        if text:
            self.live_transcript_label.setText(f"\"{text}\"")

    @Slot(str)
    def _update_status_badge(self, status: str):
        s = str(status).upper()
        self.status_badge.setText(s)
        if s in ["STARTING", "INITIALIZING"]:
            self.status_badge.setStyleSheet("background-color: #1E3A8A; color: #93C5FD; border: 1px solid #3B82F6; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        elif s in ["ASKING_PERMISSION", "PERMISSION"]:
            self.status_badge.setStyleSheet("background-color: #78350F; color: #FCD34D; border: 1px solid #F59E0B; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        elif s in ["LISTENING", "ACTIVE"]:
            self.status_badge.setStyleSheet("background-color: #064E3B; color: #34D399; border: 1px solid #10B981; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        elif s in ["SPEAKING"]:
            self.status_badge.setStyleSheet("background-color: #4C1D95; color: #C4B5FD; border: 1px solid #8B5CF6; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        elif s in ["PROCESSING_SPEECH", "PLANNING", "RUNNING", "PROCESSING"]:
            self.status_badge.setStyleSheet("background-color: #0A2540; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        elif s in ["STOPPED", "MUTED", "PAUSED"]:
            self.status_badge.setStyleSheet("background-color: #382405; color: #FBBF24; border: 1px solid #F59E0B; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        elif s in ["NO_MIC", "PERMISSION_DENIED", "ERROR", "MIC_ERROR"]:
            self.status_badge.setStyleSheet("background-color: #450A0A; color: #EF4444; border: 1px solid #EF4444; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        else:
            self.status_badge.setStyleSheet("background-color: #111E38; color: #94A3B8; border: 1px solid #203358; border-radius: 6px; padding: 4px 10px; font-weight: 600;")

    @Slot(object)
    def _update_task_ui(self, task: Task):
        if not task:
            return

        self.task_title_label.setText(f"TASK: {task.user_prompt[:45]}...")
        self.progress_bar.setValue(task.progress_percentage)
        self._update_status_badge(task.status.value)

        # Update outcome banner
        if task.status == TaskStatus.COMPLETED:
            self.outcome_banner.setText("STATUS: ✅ Task completed successfully.")
            self.outcome_banner.setStyleSheet("color: #34D399; font-size: 11px; padding: 4px 8px; background: #064E3B; border-radius: 4px; font-weight: bold;")
        elif task.status == TaskStatus.FAILED:
            self.outcome_banner.setText(f"STATUS: ❌ {task.error_message or 'Execution failed.'}")
            self.outcome_banner.setStyleSheet("color: #EF4444; font-size: 11px; padding: 4px 8px; background: #450A0A; border-radius: 4px; font-weight: bold;")
        elif getattr(task, "needs_clarification", False):
            self.outcome_banner.setText(f"CLARIFICATION: ❓ {task.clarification_question}")
            self.outcome_banner.setStyleSheet("color: #FBBF24; font-size: 11px; padding: 4px 8px; background: #382405; border-radius: 4px; font-weight: bold;")
        elif task.status == TaskStatus.RUNNING:
            self.outcome_banner.setText(f"STATUS: ⚡ Running step {task.current_step_index + 1} of {len(task.steps)}")
            self.outcome_banner.setStyleSheet("color: #00E5FF; font-size: 11px; padding: 4px 8px; background: #0A2540; border-radius: 4px;")
        else:
            self.outcome_banner.setText(f"STATUS: {task.status.value}")
            self.outcome_banner.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 4px 8px; background: #0F172A; border-radius: 4px;")

        # Refresh steps list
        self.steps_list.clear()
        for idx, step in enumerate(task.steps):
            status_symbol = {
                StepStatus.PENDING: "⏳",
                StepStatus.IN_PROGRESS: "⚡",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
            }.get(step.status, "•")

            item_text = f"{status_symbol} Step {idx + 1}: {step.description} [{step.tool_name}]"
            item = QListWidgetItem(item_text)

            if step.status == StepStatus.COMPLETED:
                item.setForeground(QColor("#34D399"))
            elif step.status == StepStatus.IN_PROGRESS:
                item.setForeground(QColor("#00E5FF"))
            elif step.status == StepStatus.FAILED:
                item.setForeground(QColor("#EF4444"))

            self.steps_list.addItem(item)

    @Slot(str, str)
    def _append_dialogue_message(self, role: str, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "user": "#38BDF8",       # Cyan/Blue
            "assistant": "#34D399",  # Mint/Green
            "system": "#94A3B8",     # Slate
            "error": "#EF4444",      # Red
        }
        color = color_map.get(role, "#CBD5E1")
        prefix = {
            "user": "USER",
            "assistant": ASSISTANT_NAME.upper(),
            "system": "SYSTEM",
            "error": "ERROR"
        }.get(role, "INFO")

        html_snippet = f"<div style='margin-bottom: 6px;'><span style='color: #64748B;'>[{timestamp}]</span> <b style='color: {color};'>{prefix}:</b> <span style='color: #F8FAFC;'>{text}</span></div>"
        self.dialogue_history.append(html_snippet)

    def _on_input_submitted(self):
        cmd = self.command_input.text().strip()
        if not cmd:
            return
        self.command_input.clear()
        self._send_command(cmd)

    def _on_override_submitted(self):
        cmd = self.command_input.text().strip()
        if not cmd:
            return
        self.command_input.clear()
        self._log_dialogue("user", f"[OVERRIDE] {cmd}")
        self.assistant.interruption.execute_override(cmd)

    def _send_command(self, cmd_text: str):
        self._log_dialogue("user", cmd_text)
        self.assistant.process_command(cmd_text)

    def _emergency_stop(self):
        logger.warning("UI: Emergency STOP clicked.")
        self.assistant.interruption.execute_stop()

    def _pause_task(self):
        logger.info("UI: Pause clicked.")
        self.assistant.interruption.execute_pause()

    def _resume_task(self):
        logger.info("UI: Resume clicked.")
        self.assistant.interruption.execute_resume()

    def _prompt_microphone_permission(self) -> bool:
        """Displays the microphone access permission dialog."""
        from app.gui.dialogs import MicrophoneAccessDialog
        self._update_status_badge("ASKING_PERMISSION")
        dlg = MicrophoneAccessDialog(self)
        granted = (dlg.exec() == MicrophoneAccessDialog.Accepted)
        return granted

    def _run_startup_sequence(self):
        """Executes full startup sequence with audio greeting and permission check."""
        self._update_status_badge("STARTING")
        res = self.assistant.startup_lifecycle(on_permission_needed=self._prompt_microphone_permission)
        st = res.get("status", "LISTENING")

        if st == "NO_MIC":
            self.mic_btn.setText("❌ No Mic")
            self.mic_btn.setStyleSheet("background-color: #450A0A; color: #EF4444; font-weight: bold; border: 1px solid #EF4444; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
            self._update_status_badge("NO_MIC")
            self.live_transcript_label.setText("No microphone device detected. Connect a microphone or type below.")
        elif st == "PERMISSION_DENIED":
            self.mic_btn.setText("🔇 Mic: OFF")
            self.mic_btn.setStyleSheet("background-color: #450A0A; color: #EF4444; font-weight: bold; border: 1px solid #EF4444; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
            self._update_status_badge("PERMISSION_DENIED")
            self.live_transcript_label.setText("Microphone permission denied. Click 'Mic' or open Windows Settings to enable.")
        elif st == "LISTENING":
            self.mic_btn.setText("🎤 Mic: ON")
            self.mic_btn.setStyleSheet("background-color: #064E3B; color: #34D399; font-weight: bold; border: 1px solid #10B981; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
            self.live_transcript_label.setText("Microphone Ready. Listening for your command...")

    def _toggle_mic(self):
        from app.voice.permission_manager import MicrophonePermissionManager
        perm_state = MicrophonePermissionManager.get_permission_state(self.assistant.db)

        if perm_state == "denied":
            # Re-request permission interactively
            granted = self._prompt_microphone_permission()
            if granted:
                MicrophonePermissionManager.set_permission_state(self.assistant.db, "granted")
                self.assistant.voice_listener.mic_enabled = True
                if not self.assistant.voice_listener.is_listening:
                    self.assistant.start_voice_system()
                self.mic_btn.setText("🎤 Mic: ON")
                self.mic_btn.setStyleSheet("background-color: #064E3B; color: #34D399; font-weight: bold; border: 1px solid #10B981; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
                self._update_status_badge("LISTENING")
                self.live_transcript_label.setText("Microphone enabled. Listening for your command...")
                self._log_dialogue("system", "Microphone access granted. Now listening.")
                self.assistant.tts.speak("Microphone enabled.")
            else:
                MicrophonePermissionManager.open_windows_microphone_settings()
            return

        enabled = self.assistant.voice_listener.toggle_microphone()
        if enabled:
            self.mic_btn.setText("🎤 Mic: ON")
            self.mic_btn.setStyleSheet("background-color: #064E3B; color: #34D399; font-weight: bold; border: 1px solid #10B981; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
            self._update_status_badge("LISTENING")
            self.live_transcript_label.setText("Microphone enabled. Listening for your command...")
            self._log_dialogue("system", "Microphone enabled and listening.")
        else:
            self.mic_btn.setText("🔇 Mic: MUTED")
            self.mic_btn.setStyleSheet("background-color: #450A0A; color: #EF4444; font-weight: bold; border: 1px solid #EF4444; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
            self._update_status_badge("MUTED")
            self.live_transcript_label.setText("Microphone Muted. Click 'Mic' to unmute.")
            self._log_dialogue("system", "Microphone muted.")

    def _open_settings(self):
        dlg = SettingsDialog(self.assistant.db, self)
        if dlg.exec():
            # Refresh AI badge
            provider = self.assistant.db.get_setting("LLM_PROVIDER", "offline_nlp")
            self.ai_badge.setText(f"AI: {str(provider).upper()}")
            # Refresh assistant name and wake word dynamically
            new_name = self.assistant.db.get_setting("ASSISTANT_NAME", "NIVA")
            new_wake = self.assistant.db.get_setting("WAKE_WORD", "niva")
            wake_en = self.assistant.db.get_setting("WAKE_WORD_ENABLED", False)
            self.assistant.wake_detector.set_wake_word(new_wake)
            self.assistant.wake_detector.enabled = wake_en
            self._update_wake_btn()
            self.setWindowTitle(f"{new_name} — Universal Autonomous AI Computer Control System")

    def _ask_user_permission(self, title: str, details: str) -> bool:
        """Invoked synchronously from safety permission manager."""
        dlg = PermissionConfirmationDialog(title, details, self)
        return dlg.exec() == PermissionConfirmationDialog.Accepted

    def _log_dialogue(self, role: str, text: str):
        self.signal_dialogue_logged.emit(role, text)

    def closeEvent(self, event):
        """Clean shutdown when closing window."""
        self.assistant.shutdown()
        event.accept()
