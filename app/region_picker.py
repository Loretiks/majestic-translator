from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget

from .config import Region


class RegionPicker(QWidget):
    """Fullscreen translucent overlay: drag mouse to select chat region."""

    region_selected = Signal(Region)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        screen_geo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)

        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None

        self._hint = QLabel(
            "Выдели мышью область чата Majestic. ESC — отмена.",
            self,
        )
        self._hint.setStyleSheet(
            "QLabel { color: #FFD166; font-size: 18px; font-weight: 600;"
            " background: rgba(15,17,28,200); padding: 10px 16px;"
            " border: 1px solid #FFD166; border-radius: 6px; }"
        )
        self._hint.adjustSize()
        self._hint.move(40, 40)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._origin is None:
            return
        rect = QRect(self._origin, event.position().toPoint()).normalized()
        if rect.width() < 30 or rect.height() < 20:
            self.cancelled.emit()
            self.close()
            return
        offset = self.geometry().topLeft()
        region = Region(
            x=rect.x() + offset.x(),
            y=rect.y() + offset.y(),
            w=rect.width(),
            h=rect.height(),
        )
        self.region_selected.emit(region)
        self.close()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            pen = QPen(QColor("#FFD166"), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
