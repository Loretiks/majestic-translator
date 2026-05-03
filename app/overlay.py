from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

import pyperclip
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .config import Config, Region
from .i18n import LANGUAGE_NAMES, LANGUAGES, t
from .ocr import ChatOCR
from .region_picker import RegionPicker
from .themes import THEME_NAMES, THEMES, build_qss, status_dot_color
from .translator import Translator
from .workers import ManualTranslateWorker, OcrTranslateWorker


_FEED_MAX_ITEMS = 40


class TitleBar(QWidget):
    """Drag handle for the frameless overlay window. Calls QWindow's
    startSystemMove so the OS handles the drag — smooth, no per-pixel
    Python repaint."""

    def __init__(self, root_window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = root_window
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            wh = self._root.windowHandle()
            if wh is not None:
                wh.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        event.accept()


class FeedItem(QWidget):
    """Compact feed entry: timestamp, translated text, original text.

    All styling is driven by the parent's QSS via objectName selectors,
    so insertion is light (no per-label setStyleSheet)."""

    def __init__(self, original: str, translated: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        time_lbl = QLabel(time.strftime("%H:%M"))
        time_lbl.setObjectName("msgTime")

        translated_lbl = QLabel(translated)
        translated_lbl.setObjectName("msgTrans")
        translated_lbl.setWordWrap(True)

        original_lbl = QLabel(original)
        original_lbl.setObjectName("msgOrig")
        original_lbl.setWordWrap(True)

        layout.addWidget(time_lbl)
        layout.addWidget(translated_lbl)
        layout.addWidget(original_lbl)


class Overlay(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self._lang = cfg.language if cfg.language in LANGUAGES else "ru"
        self._theme = cfg.theme if cfg.theme in THEMES else "majestic"
        self._ocr_worker: Optional[OcrTranslateWorker] = None

        # i18n: list of (widget, setter_method_name, key, fmt_kwargs)
        # used by _retranslate() to update strings on language switch.
        self._i18n_widgets: List[Tuple[QWidget, str, str, dict]] = []
        # Tracks the most recent status text source so we can retranslate
        # on language switch. Either ("key", {fmt}) or ("raw", text).
        self._status_source: Tuple[str, object] = ("key", ("status.ready", {}))

        email = cfg.mymemory_email or None
        self._chat_translator = Translator(cfg.source_lang, cfg.target_lang, email=email)
        self._input_translator = Translator(
            cfg.input_lang, cfg.input_target_lang, email=email
        )
        self._manual = ManualTranslateWorker(self._input_translator)
        self._manual.done.connect(self._on_manual_done)
        self._manual.error.connect(
            lambda e: self._set_status_key("status.error_prefix", ok=False, msg=str(e))
        )

        self._build_ui()
        self._apply_window_flags()
        self._restore_geometry()
        self._apply_theme()

        if cfg.chat_region:
            self._start_ocr()
        else:
            self._set_status_key("status.uncalibrated", ok=False)

    # ---------- window flags ----------

    def _apply_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        # WA_TranslucentBackground enables rounded card corners. The card
        # bakes its own alpha via QSS rgba, so we deliberately do NOT also
        # set windowOpacity — stacking both forces an extra alpha pass per
        # redraw and was a major drag-lag source.
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Majestic Translator")

    def _restore_geometry(self) -> None:
        self.resize(self.cfg.overlay_size["w"], self.cfg.overlay_size["h"])
        self.move(self.cfg.overlay_pos["x"], self.cfg.overlay_pos["y"])

    # ---------- UI construction ----------

    def _build_ui(self) -> None:
        self.setObjectName("root")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("card")
        outer.addWidget(card)

        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)

        v.addWidget(self._build_titlebar())
        v.addWidget(self._build_section_label("section.incoming"))
        v.addWidget(self._build_feed(), stretch=1)
        v.addWidget(self._build_section_label("section.outgoing"))
        v.addLayout(self._build_input_block())
        v.addLayout(self._build_status_bar())

    def _track_i18n(self, widget: QWidget, setter: str, key: str, **fmt) -> QWidget:
        """Register a widget so _retranslate() can update its text/tooltip
        when the UI language changes."""
        self._i18n_widgets.append((widget, setter, key, fmt))
        getattr(widget, setter)(t(key, self._lang, **fmt))
        return widget

    def _build_titlebar(self) -> QWidget:
        bar = TitleBar(self)
        bar.setObjectName("titlebar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        title = QLabel("MAJESTIC TRANSLATOR")
        title.setObjectName("title")
        title.setAttribute(Qt.WA_TransparentForMouseEvents)

        subtitle = QLabel()
        subtitle.setObjectName("subtitle")
        subtitle.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._track_i18n(subtitle, "setText", "app.subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addStretch(1)

        self._calib_btn = QPushButton("⌖")
        self._calib_btn.setObjectName("iconbtn")
        self._calib_btn.clicked.connect(self._calibrate)
        self._track_i18n(self._calib_btn, "setToolTip", "tooltip.calibrate")
        layout.addWidget(self._calib_btn)

        self._min_btn = QPushButton("—")
        self._min_btn.setObjectName("iconbtn")
        self._min_btn.clicked.connect(self.showMinimized)
        self._track_i18n(self._min_btn, "setToolTip", "tooltip.minimize")
        layout.addWidget(self._min_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("iconbtn")
        self._close_btn.clicked.connect(self.close)
        self._track_i18n(self._close_btn, "setToolTip", "tooltip.close")
        layout.addWidget(self._close_btn)

        return bar

    def _build_section_label(self, key: str) -> QLabel:
        lbl = QLabel()
        lbl.setObjectName("sectionLabel")
        self._track_i18n(lbl, "setText", key)
        return lbl

    def _build_feed(self) -> QScrollArea:
        self._feed_container = QWidget()
        self._feed_container.setObjectName("feed")
        self._feed_layout = QVBoxLayout(self._feed_container)
        self._feed_layout.setContentsMargins(4, 4, 4, 4)
        self._feed_layout.setSpacing(2)
        self._feed_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("feedScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._feed_container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll = scroll
        return scroll

    def _build_input_block(self) -> QVBoxLayout:
        wrap = QVBoxLayout()
        wrap.setSpacing(6)

        self._input = QPlainTextEdit()
        self._input.setObjectName("input")
        self._track_i18n(self._input, "setPlaceholderText", "input.placeholder")
        self._input.setFixedHeight(72)
        font = QFont()
        font.setPointSize(10)
        self._input.setFont(font)
        wrap.addWidget(self._input)

        QShortcut(QKeySequence("Ctrl+Return"), self._input, self._submit_input)
        QShortcut(QKeySequence("Ctrl+Enter"), self._input, self._submit_input)

        self._preview = QLabel("")
        self._preview.setObjectName("russianPreview")
        self._preview.setWordWrap(True)
        self._preview.setVisible(False)
        wrap.addWidget(self._preview)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._copy_btn = QPushButton()
        self._copy_btn.setObjectName("primary")
        self._copy_btn.clicked.connect(self._submit_input)
        self._track_i18n(self._copy_btn, "setText", "button.translate_copy")
        row.addWidget(self._copy_btn, stretch=1)

        self._clear_btn = QPushButton()
        self._clear_btn.setObjectName("ghost")
        self._clear_btn.clicked.connect(self._input.clear)
        self._track_i18n(self._clear_btn, "setText", "button.clear")
        row.addWidget(self._clear_btn)
        wrap.addLayout(row)

        return wrap

    def _build_status_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(6)

        self._status_dot = QLabel("●")
        self._status_dot.setObjectName("statusDot")
        bar.addWidget(self._status_dot)

        self._status = QLabel()
        self._status.setObjectName("status")
        bar.addWidget(self._status)
        bar.addStretch(1)

        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("switcher")
        for code in LANGUAGES:
            self._lang_combo.addItem(LANGUAGE_NAMES[code], code)
        self._lang_combo.setCurrentIndex(LANGUAGES.index(self._lang))
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        self._track_i18n(self._lang_combo, "setToolTip", "tooltip.lang")
        bar.addWidget(self._lang_combo)

        self._theme_combo = QComboBox()
        self._theme_combo.setObjectName("switcher")
        for code in THEMES:
            self._theme_combo.addItem(THEME_NAMES[code], code)
        self._theme_combo.setCurrentIndex(THEMES.index(self._theme))
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._track_i18n(self._theme_combo, "setToolTip", "tooltip.theme")
        bar.addWidget(self._theme_combo)

        # Apply initial status text via the standard path.
        self._set_status_key("status.ready", ok=True)
        return bar

    # ---------- theme + language ----------

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_qss(self._theme))
        # The status dot color is per-theme, so refresh it after re-applying.
        self._refresh_status_dot()

    def _refresh_status_dot(self) -> None:
        ok = getattr(self, "_status_ok", True)
        color = status_dot_color(self._theme, ok)
        self._status_dot.setStyleSheet(f"color: {color}; font-size: 13px;")

    def _retranslate(self) -> None:
        for widget, setter, key, fmt in self._i18n_widgets:
            try:
                getattr(widget, setter)(t(key, self._lang, **fmt))
            except Exception:
                pass
        # Re-render whatever the status currently shows in the new language.
        kind, payload = self._status_source
        if kind == "key":
            key, fmt = payload
            self._set_status_key(key, ok=getattr(self, "_status_ok", True), **fmt)
        else:
            self._set_status_raw(str(payload), ok=getattr(self, "_status_ok", True))

    def _on_lang_changed(self, index: int) -> None:
        code = self._lang_combo.itemData(index)
        if code not in LANGUAGES or code == self._lang:
            return
        self._lang = code
        self.cfg.language = code
        self.cfg.save()
        self._retranslate()

    def _on_theme_changed(self, index: int) -> None:
        code = self._theme_combo.itemData(index)
        if code not in THEMES or code == self._theme:
            return
        self._theme = code
        self.cfg.theme = code
        self.cfg.save()
        self._apply_theme()

    # ---------- status helpers ----------

    def _set_status_key(self, key: str, ok: bool = True, **fmt) -> None:
        self._status_source = ("key", (key, fmt))
        self._status_ok = ok
        self._status.setText(t(key, self._lang, **fmt))
        self._refresh_status_dot()

    def _set_status_raw(self, text: str, ok: bool = True) -> None:
        self._status_source = ("raw", text)
        self._status_ok = ok
        self._status.setText(text)
        self._refresh_status_dot()

    # ---------- OCR ----------

    def _start_ocr(self) -> None:
        if self._ocr_worker:
            self._ocr_worker.stop()
        ocr = ChatOCR(self.cfg)
        ocr.set_mask_provider(self._own_window_rects)
        self._ocr_worker = OcrTranslateWorker(
            ocr, self._chat_translator, self.cfg.ocr_interval_ms
        )
        self._ocr_worker.line_ready.connect(self._on_line)
        self._ocr_worker.error.connect(self._on_worker_error)
        self._ocr_worker.status.connect(self._on_worker_status)
        self._ocr_worker.start()

    def _on_worker_status(self, key: str) -> None:
        # Workers emit symbolic keys ("loading_models", "ocr_active") which
        # we map to localized strings via i18n.
        self._set_status_key(f"status.{key}", ok=True)

    def _on_worker_error(self, msg: str) -> None:
        self._set_status_key("status.ocr_error_prefix", ok=False, msg=msg)

    def _own_window_rects(self):
        """Mask the translator's own window from the OCR capture so the
        UI doesn't get fed back as chat text."""
        if not self.isVisible():
            return []
        pad = 6
        g = self.frameGeometry()
        return [(g.x() - pad, g.y() - pad, g.width() + 2 * pad, g.height() + 2 * pad)]

    # ---------- feed ----------

    def _on_line(self, original: str, translated: str) -> None:
        item = FeedItem(original, translated)
        self._feed_layout.insertWidget(self._feed_layout.count() - 1, item)

        max_count = _FEED_MAX_ITEMS + 1
        while self._feed_layout.count() > max_count:
            it = self._feed_layout.takeAt(0)
            if it is None:
                break
            w = it.widget()
            if w is not None:
                w.deleteLater()

        QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------- input ----------

    def _submit_input(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._set_status_key("status.translating", ok=True)
        self._copy_btn.setEnabled(False)
        self._manual.submit(text)

    def _on_manual_done(self, original: str, translated: str) -> None:
        pyperclip.copy(translated)
        self._preview.setText(f"📋 {translated}")
        self._preview.setVisible(True)
        self._set_status_key("status.copied", ok=True)
        self._copy_btn.setEnabled(True)

    # ---------- calibration ----------

    def _calibrate(self) -> None:
        self._picker = RegionPicker()
        self._picker.region_selected.connect(self._on_region)
        self._picker.cancelled.connect(self._on_calibrate_cancelled)
        self.hide()
        self._picker.show()

    def _on_calibrate_cancelled(self) -> None:
        self.show()
        self._set_status_key("status.calibration_cancelled", ok=True)

    def _on_region(self, region: Region) -> None:
        self.cfg.chat_region = region
        self.cfg.save()
        self.show()
        self._set_status_key("status.region", ok=True, w=region.w, h=region.h)
        self._start_ocr()

    # ---------- close ----------

    def closeEvent(self, event):
        if self._ocr_worker:
            self._ocr_worker.stop()
        self.cfg.overlay_pos = {"x": self.x(), "y": self.y()}
        self.cfg.overlay_size = {"w": self.width(), "h": self.height()}
        self.cfg.save()
        super().closeEvent(event)
