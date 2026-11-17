"""
Dialogs for JARVIS GUI: Settings Configuration and Safety Authorization Prompts.
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QTextEdit, QVBoxLayout
)

from app.config import ASSISTANT_NAME
from app.storage.database import Database


class SettingsDialog(QDialog):
    """Configuration panel for AI API keys, voice synthesis, assistant identity, and privacy controls."""

    def __init__(self, db: Database, parent=None, assistant=None):
        super().__init__(parent)
        self.db = db
        self.assistant = assistant or getattr(parent, "assistant", None)
        current_name = self.db.get_setting("ASSISTANT_NAME", os.getenv("ASSISTANT_NAME", ASSISTANT_NAME))
        self.setWindowTitle(f"{current_name} - System Configuration")
        self.resize(520, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Assistant Name Configuration
        self.name_edit = QLineEdit()
        self.name_edit.setText(str(self.db.get_setting("ASSISTANT_NAME", os.getenv("ASSISTANT_NAME", ASSISTANT_NAME))))
        form.addRow("Assistant Name:", self.name_edit)

        # Wake Word Configuration
        self.wake_word_edit = QLineEdit()
        self.wake_word_edit.setText(str(self.db.get_setting("WAKE_WORD", os.getenv("WAKE_WORD", "niva"))))
        form.addRow("Wake Word Phrase:", self.wake_word_edit)

        self.wake_check = QCheckBox("Enable Wake Word Activation")
        self.wake_check.setChecked(bool(self.db.get_setting("WAKE_WORD_ENABLED", False)))
        form.addRow("Wake Word Active:", self.wake_check)

        # Microphone Permissions & Settings
        from app.voice.permission_manager import MicrophonePermissionManager
        mic_perm_row = QHBoxLayout()
        current_perm = str(self.db.get_setting("MIC_PERMISSION_STATUS", "granted")).lower()
        perm_color = "#34D399" if current_perm == "granted" else "#EF4444"
        self.mic_perm_lbl = QLabel(current_perm.upper())
        self.mic_perm_lbl.setStyleSheet(f"font-weight: bold; color: {perm_color};")
        mic_perm_row.addWidget(self.mic_perm_lbl)

        win_mic_btn = QPushButton("Open Windows Mic Settings")
        win_mic_btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        win_mic_btn.clicked.connect(lambda: MicrophonePermissionManager.open_windows_microphone_settings())
        mic_perm_row.addWidget(win_mic_btn)
        form.addRow("Microphone Permission:", mic_perm_row)

        # Speech & Language Provider
        self.stt_combo = QComboBox()
        self.stt_combo.addItems(["Google Speech API (Online)", "Local Offline Recognizer"])
        cur_stt = self.db.get_setting("STT_PROVIDER", "Google Speech API (Online)")
        stt_idx = self.stt_combo.findText(cur_stt)
        if stt_idx >= 0:
            self.stt_combo.setCurrentIndex(stt_idx)
        form.addRow("Speech-to-Text Provider:", self.stt_combo)

        # TTS Spoken Output Controls
        self.voice_out_check = QCheckBox("Enable Spoken Audio Output (TTS)")
        self.voice_out_check.setChecked(bool(self.db.get_setting("TTS_ENABLED", True)))
        form.addRow("Spoken Audio Output:", self.voice_out_check)

        # TTS Voice Selection
        self.voice_combo = QComboBox()
        available_voices = []
        if self.assistant and hasattr(self.assistant, "tts"):
            available_voices = self.assistant.tts.list_voices()
        if available_voices:
            saved_voice = str(self.db.get_setting("TTS_VOICE_ID", ""))
            for v in available_voices:
                v_name = v.get("name", "Voice")
                v_id = v.get("id", "")
                self.voice_combo.addItem(v_name, v_id)
            if saved_voice:
                for idx in range(self.voice_combo.count()):
                    if self.voice_combo.itemData(idx) == saved_voice:
                        self.voice_combo.setCurrentIndex(idx)
                        break
        else:
            self.voice_combo.addItem("Default System Voice", "")
        form.addRow("TTS Voice:", self.voice_combo)

        # TTS Volume
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(self.db.get_setting("TTS_VOLUME", 100)))
        form.addRow("TTS Volume (0-100):", self.vol_slider)

        # TTS Speech Rate
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(-10, 10)
        self.rate_slider.setValue(int(self.db.get_setting("TTS_RATE", 0)))
        form.addRow("TTS Speech Rate (-10 to 10):", self.rate_slider)

        # LLM Provider
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["offline_nlp", "gemini", "openai", "anthropic", "ollama"])
        current_provider = self.db.get_setting("LLM_PROVIDER", os.getenv("LLM_PROVIDER", "offline_nlp"))
        idx = self.provider_combo.findText(current_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        form.addRow("AI Reasoning Engine:", self.provider_combo)

        # Gemini API Key
        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.Password)
        self.gemini_key_edit.setText(str(self.db.get_setting("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))))
        form.addRow("Google Gemini Key:", self.gemini_key_edit)

        # OpenAI API Key
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        self.openai_key_edit.setText(str(self.db.get_setting("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))))
        form.addRow("OpenAI Key:", self.openai_key_edit)

        # Ollama URL
        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setText(str(self.db.get_setting("OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))))
        form.addRow("Ollama Endpoint:", self.ollama_url_edit)

        # Safe Mode
        self.safe_mode_check = QCheckBox("Enforce Safety Confirmations for Sensitive Actions")
        self.safe_mode_check.setChecked(bool(self.db.get_setting("SAFE_MODE", True)))
        form.addRow("Safety Guardrails:", self.safe_mode_check)

        # Privacy Controls
        self.history_check = QCheckBox("Enable Local Task and Dialogue History")
        self.history_check.setChecked(bool(self.db.is_history_enabled()))
        form.addRow("History Storage:", self.history_check)

        self.clear_history_btn = QPushButton("🗑️ Clear Local History Now")
        self.clear_history_btn.setStyleSheet("background-color: #450A0A; color: #EF4444; font-weight: bold; padding: 4px 8px;")
        self.clear_history_btn.clicked.connect(self._clear_history)
        form.addRow("Privacy Action:", self.clear_history_btn)

        layout.addLayout(form)

        # Dialog Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._save_settings)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _clear_history(self):
        res = self.db.clear_history()
        if res.get("success"):
            self.clear_history_btn.setText("✅ History Cleared!")
            self.clear_history_btn.setEnabled(False)

    def _save_settings(self):
        new_name = self.name_edit.text().strip() or "NIVA"
        new_wake_word = self.wake_word_edit.text().strip() or "niva"
        wake_en = self.wake_check.isChecked()
        stt_prov = self.stt_combo.currentText()
        provider = self.provider_combo.currentText()
        gemini_k = self.gemini_key_edit.text().strip()
        openai_k = self.openai_key_edit.text().strip()
        ollama_u = self.ollama_url_edit.text().strip()
        tts_en = self.voice_out_check.isChecked()
        voice_id = str(self.voice_combo.currentData() or "")
        vol = self.vol_slider.value()
        rate = self.rate_slider.value()
        safe_en = self.safe_mode_check.isChecked()
        hist_en = self.history_check.isChecked()

        # Update DB and env
        self.db.set_setting("ASSISTANT_NAME", new_name)
        self.db.set_setting("WAKE_WORD", new_wake_word)
        self.db.set_setting("WAKE_WORD_ENABLED", wake_en)
        self.db.set_setting("STT_PROVIDER", stt_prov)
        self.db.set_setting("TTS_ENABLED", tts_en)
        self.db.set_setting("TTS_VOICE_ID", voice_id)
        self.db.set_setting("TTS_VOLUME", vol)
        self.db.set_setting("TTS_RATE", rate)
        self.db.set_setting("LLM_PROVIDER", provider)
        self.db.set_setting("GEMINI_API_KEY", gemini_k)
        self.db.set_setting("OPENAI_API_KEY", openai_k)
        self.db.set_setting("OLLAMA_BASE_URL", ollama_u)
        self.db.set_setting("SAFE_MODE", safe_en)
        self.db.set_history_enabled(hist_en)

        os.environ["ASSISTANT_NAME"] = new_name
        os.environ["WAKE_WORD"] = new_wake_word
        os.environ["LLM_PROVIDER"] = provider
        os.environ["GEMINI_API_KEY"] = gemini_k
        os.environ["OPENAI_API_KEY"] = openai_k
        os.environ["OLLAMA_BASE_URL"] = ollama_u

        # Update live assistant components
        if self.assistant:
            if hasattr(self.assistant, "tts"):
                self.assistant.tts.set_speaking_enabled(tts_en)
                self.assistant.tts.set_volume(vol)
                self.assistant.tts.set_rate(rate)
                if voice_id:
                    self.assistant.tts.set_voice(voice_id)

        self.accept()
        os.environ["OPENAI_API_KEY"] = openai_k
        os.environ["OLLAMA_BASE_URL"] = ollama_u

        self.accept()


class MicrophoneAccessDialog(QDialog):
    """Explains why microphone access is needed and requests user authorization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{ASSISTANT_NAME} — Microphone Access Required")
        self.resize(500, 300)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        icon_title = QLabel("🎙️ Microphone Access Required")
        icon_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00E5FF;")
        layout.addWidget(icon_title)

        expl = QLabel(
            f"<b>{ASSISTANT_NAME}</b> uses your microphone to transcribe voice instructions, "
            "answer your questions hands-free, and automate computer tasks.<br><br>"
            "Audio is processed in real time and is never recorded or stored permanently.<br>"
            "You can mute the microphone or toggle access at any time using the <b>🎤 Mic</b> button."
        )
        expl.setWordWrap(True)
        expl.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.5;")
        layout.addWidget(expl)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        settings_btn = QPushButton("⚙ Windows Settings")
        settings_btn.setStyleSheet("background-color: #1E293B; color: #94A3B8; padding: 8px 12px; border-radius: 6px;")
        settings_btn.clicked.connect(self._open_windows_settings)
        btn_layout.addWidget(settings_btn)

        deny_btn = QPushButton("Deny")
        deny_btn.setStyleSheet("background-color: #450A0A; color: #EF4444; padding: 8px 16px; border-radius: 6px;")
        deny_btn.clicked.connect(self.reject)
        btn_layout.addWidget(deny_btn)

        allow_btn = QPushButton("Grant Permission")
        allow_btn.setStyleSheet("background-color: #064E3B; color: #34D399; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        allow_btn.clicked.connect(self.accept)
        btn_layout.addWidget(allow_btn)

        layout.addLayout(btn_layout)

    def _open_windows_settings(self):
        from app.voice.permission_manager import MicrophonePermissionManager
        MicrophonePermissionManager.open_windows_microphone_settings()


class PermissionConfirmationDialog(QDialog):
    """Prompts the user to authorize or block a sensitive action."""

    def __init__(self, action_title: str, details_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{ASSISTANT_NAME} - Safety Authorization Required")
        self.resize(460, 280)
        self._init_ui(action_title, details_text)

    def _init_ui(self, title: str, details: str):
        layout = QVBoxLayout(self)

        title_lbl = QLabel(f"⚠️ {title}")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #F59E0B;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(f"{ASSISTANT_NAME} is requesting permission to execute the following sensitive action:")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        details_box = QTextEdit()
        details_box.setReadOnly(True)
        details_box.setText(details)
        layout.addWidget(details_box)

        btn_layout = QHBoxLayout()
        deny_btn = QPushButton("Block Action")
        deny_btn.setStyleSheet("background-color: #450A0A; color: #EF4444;")
        deny_btn.clicked.connect(self.reject)

        allow_btn = QPushButton("Authorize Action")
        allow_btn.setStyleSheet("background-color: #064E3B; color: #10B981; font-weight: bold;")
        allow_btn.clicked.connect(self.accept)

        btn_layout.addWidget(deny_btn)
        btn_layout.addWidget(allow_btn)
        layout.addLayout(btn_layout)
