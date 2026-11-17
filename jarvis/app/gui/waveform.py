"""
Animated Audio Waveform Visualizer Widget for JARVIS GUI.
Draws dynamic sine oscillations and spectrum bars representing voice activity.
"""

import math
import random
from PySide6.QtCore import QPointF, QRect, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class WaveformVisualizer(QWidget):
    """Futuristic holographic waveform visualizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(65)
        self.amplitude: float = 0.2
        self.target_amplitude: float = 0.2
        self.phase: float = 0.0

        # Animation refresh timer (30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(33)

    def set_amplitude(self, amp: float) -> None:
        """Sets target amplitude [0.0, 1.0]."""
        self.target_amplitude = max(0.1, min(1.0, float(amp)))

    def _animate(self) -> None:
        # Smooth interpolation towards target amplitude
        self.amplitude += (self.target_amplitude - self.amplitude) * 0.15
        self.phase += 0.08
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        mid_y = height / 2.0

        # Draw subtle background glow
        bg_rect = QRect(0, 0, width, height)
        painter.fillRect(bg_rect, QColor(10, 17, 32))

        # Draw central reference line
        ref_pen = QPen(QColor(26, 42, 70), 1, Qt.DashLine)
        painter.setPen(ref_pen)
        painter.drawLine(0, int(mid_y), width, int(mid_y))

        # Waveform 1: Cyan primary wave
        cyan_pen = QPen(QColor(0, 229, 255, 220), 2)
        painter.setPen(cyan_pen)
        path1 = QPainterPath()
        path1.moveTo(0, mid_y)

        steps = 60
        dx = width / steps
        for i in range(steps + 1):
            x = i * dx
            # Composite harmonic oscillation
            sin_val = math.sin((i * 0.15) + self.phase) * math.cos((i * 0.05) - self.phase)
            y = mid_y + (sin_val * (height * 0.4) * self.amplitude)
            path1.lineTo(x, y)

        painter.drawPath(path1)

        # Waveform 2: Electric Blue secondary harmonic wave
        blue_pen = QPen(QColor(0, 120, 255, 140), 1.5)
        painter.setPen(blue_pen)
        path2 = QPainterPath()
        path2.moveTo(0, mid_y)

        for i in range(steps + 1):
            x = i * dx
            sin_val2 = math.sin((i * 0.22) - (self.phase * 1.3))
            y2 = mid_y + (sin_val2 * (height * 0.28) * self.amplitude)
            path2.lineTo(x, y2)

        painter.drawPath(path2)
