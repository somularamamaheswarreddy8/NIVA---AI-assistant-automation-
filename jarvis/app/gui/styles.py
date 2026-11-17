"""
Futuristic JARVIS UI Theme and Stylesheets for PySide6.
Dark holographic aesthetic with cyan, electric blue, and neon accents.
"""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #080D1A;
}

QWidget {
    color: #E2E8F0;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #0D1527;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #1E293B;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #00E5FF;
}

/* Cards & Containers */
QFrame#card {
    background-color: #0E1726;
    border: 1px solid #1A2744;
    border-radius: 10px;
}

QFrame#card:hover {
    border: 1px solid #00B0FF;
}

/* Labels */
QLabel#headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #00E5FF;
    letter-spacing: 2px;
}

QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel#statusBadge {
    background-color: #0A2540;
    color: #00E5FF;
    border: 1px solid #00E5FF;
    border-radius: 6px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 11px;
}

/* Buttons */
QPushButton {
    background-color: #111E38;
    color: #E2E8F0;
    border: 1px solid #203358;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #192D54;
    border-color: #00E5FF;
    color: #00E5FF;
}

QPushButton:pressed {
    background-color: #0C1628;
}

/* Emergency STOP Button */
QPushButton#stopBtn {
    background-color: #450A0A;
    color: #FF4444;
    border: 1px solid #EF4444;
    font-weight: bold;
    letter-spacing: 1px;
}

QPushButton#stopBtn:hover {
    background-color: #DC2626;
    color: #FFFFFF;
    border-color: #F87171;
}

/* Pause Button */
QPushButton#pauseBtn {
    background-color: #382405;
    color: #FBBF24;
    border: 1px solid #F59E0B;
}

QPushButton#pauseBtn:hover {
    background-color: #D97706;
    color: #FFFFFF;
}

/* Resume Button */
QPushButton#resumeBtn {
    background-color: #064E3B;
    color: #34D399;
    border: 1px solid #10B981;
}

QPushButton#resumeBtn:hover {
    background-color: #059669;
    color: #FFFFFF;
}

/* Mic Toggle Button Active */
QPushButton#micActive {
    background-color: #0C2B4E;
    color: #38BDF8;
    border: 1px solid #38BDF8;
}

/* Input Fields */
QLineEdit {
    background-color: #0C1527;
    border: 1px solid #1E2D4A;
    border-radius: 8px;
    padding: 10px 14px;
    color: #F8FAFC;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #00E5FF;
    background-color: #0F1B33;
}

/* Progress Bar */
QProgressBar {
    background-color: #0C1527;
    border: 1px solid #1E2D4A;
    border-radius: 6px;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077B6, stop:1 #00E5FF);
    border-radius: 5px;
}

/* Lists and Trees */
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item {
    background-color: #0B1322;
    border: 1px solid #16243E;
    border-radius: 6px;
    padding: 8px;
    margin-bottom: 6px;
}

QListWidget::item:selected {
    border: 1px solid #00E5FF;
    background-color: #101E36;
}

/* Text Edit / Conversation Logs */
QTextEdit {
    background-color: #0A1120;
    border: 1px solid #16243E;
    border-radius: 8px;
    padding: 8px;
    color: #CBD5E1;
}
"""
