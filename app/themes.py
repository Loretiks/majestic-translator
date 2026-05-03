from __future__ import annotations

from typing import Dict


THEMES = ("majestic", "dark", "light")
THEME_NAMES = {
    "majestic": "Majestic",
    "dark": "Dark",
    "light": "Light",
}


_PALETTES: Dict[str, Dict[str, str]] = {
    "majestic": {
        "card_bg": "rgba(15, 17, 28, 240)",
        "card_border": "rgba(255, 209, 102, 60)",
        "feed_bg": "rgba(8, 9, 16, 200)",
        "feed_border": "rgba(255, 209, 102, 30)",
        "input_bg": "rgba(8, 9, 16, 220)",
        "input_border": "rgba(255, 209, 102, 60)",
        "input_border_focus": "#FFD166",
        "scroll_handle": "rgba(255, 209, 102, 90)",
        "preview_bg": "rgba(8, 9, 16, 180)",
        "preview_border": "rgba(255, 209, 102, 40)",
        "ghost_border": "rgba(255, 209, 102, 50)",
        "selection_bg": "rgba(255, 209, 102, 90)",
        "title": "#FFD166",
        "subtitle": "#6E7591",
        "section": "#FFD166",
        "text_primary": "#E8ECF7",
        "text_secondary": "#9099B0",
        "text_muted": "#6E7591",
        "text_dim": "#4A5070",
        "accent": "#FFD166",
        "accent_hover": "#FFE08A",
        "accent_pressed": "#E5BB57",
        "accent_text": "#0A0C16",
        "accent_dim": "#9099B0",
        "ok": "#66E0A3",
        "error": "#FF6B6B",
        "preview_text": "#FFD166",
        "popup_bg": "#0F111C",
    },
    "dark": {
        "card_bg": "rgba(24, 26, 32, 245)",
        "card_border": "rgba(80, 92, 110, 140)",
        "feed_bg": "rgba(15, 17, 22, 230)",
        "feed_border": "rgba(80, 92, 110, 80)",
        "input_bg": "rgba(15, 17, 22, 230)",
        "input_border": "rgba(80, 92, 110, 140)",
        "input_border_focus": "#5AC8FA",
        "scroll_handle": "rgba(120, 140, 170, 140)",
        "preview_bg": "rgba(15, 17, 22, 200)",
        "preview_border": "rgba(80, 92, 110, 120)",
        "ghost_border": "rgba(120, 140, 170, 100)",
        "selection_bg": "rgba(90, 200, 250, 80)",
        "title": "#EAECEF",
        "subtitle": "#8C95A6",
        "section": "#5AC8FA",
        "text_primary": "#EAECEF",
        "text_secondary": "#A0A8B5",
        "text_muted": "#7A8392",
        "text_dim": "#5A6373",
        "accent": "#5AC8FA",
        "accent_hover": "#7DD7FB",
        "accent_pressed": "#3FA9D6",
        "accent_text": "#0E1116",
        "accent_dim": "#8C95A6",
        "ok": "#66E0A3",
        "error": "#FF6B6B",
        "preview_text": "#5AC8FA",
        "popup_bg": "#16181E",
    },
    "light": {
        "card_bg": "rgba(248, 249, 251, 245)",
        "card_border": "rgba(180, 190, 210, 200)",
        "feed_bg": "rgba(255, 255, 255, 245)",
        "feed_border": "rgba(200, 210, 225, 230)",
        "input_bg": "rgba(255, 255, 255, 250)",
        "input_border": "rgba(180, 190, 210, 230)",
        "input_border_focus": "#3B82F6",
        "scroll_handle": "rgba(150, 165, 190, 180)",
        "preview_bg": "rgba(238, 244, 252, 240)",
        "preview_border": "rgba(180, 190, 210, 230)",
        "ghost_border": "rgba(180, 190, 210, 230)",
        "selection_bg": "rgba(59, 130, 246, 80)",
        "title": "#1F2937",
        "subtitle": "#6B7280",
        "section": "#3B82F6",
        "text_primary": "#111827",
        "text_secondary": "#4B5563",
        "text_muted": "#6B7280",
        "text_dim": "#9CA3AF",
        "accent": "#3B82F6",
        "accent_hover": "#60A5FA",
        "accent_pressed": "#2563EB",
        "accent_text": "#FFFFFF",
        "accent_dim": "#6B7280",
        "ok": "#16A34A",
        "error": "#DC2626",
        "preview_text": "#1D4ED8",
        "popup_bg": "#FFFFFF",
    },
}


def build_qss(theme: str) -> str:
    """Construct the full QSS stylesheet for the chosen theme palette."""
    p = _PALETTES.get(theme) or _PALETTES["majestic"]
    return f"""
#root {{ background: transparent; }}
#card {{
    background: {p["card_bg"]};
    border: 1px solid {p["card_border"]};
    border-radius: 14px;
}}
#titlebar {{ background: transparent; }}
#title {{
    color: {p["title"]};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
}}
#subtitle {{
    color: {p["subtitle"]};
    font-size: 10px;
    letter-spacing: 1px;
}}
QPushButton#iconbtn {{
    color: {p["accent_dim"]};
    background: transparent;
    border: none;
    font-size: 14px;
    padding: 2px 8px;
}}
QPushButton#iconbtn:hover {{
    color: {p["accent"]};
}}
#sectionLabel {{
    color: {p["section"]};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 4px 0;
}}
#feedScroll, #feed {{
    background: {p["feed_bg"]};
    border: 1px solid {p["feed_border"]};
    border-radius: 10px;
}}
#feed {{ padding: 6px 8px; }}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {p["scroll_handle"]};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#msgTime {{ color: {p["text_dim"]}; font-size: 9px; }}
QLabel#msgTrans {{ color: {p["text_primary"]}; font-size: 13px; font-weight: 500; }}
QLabel#msgOrig {{ color: {p["text_muted"]}; font-size: 11px; }}

QPlainTextEdit#input {{
    background: {p["input_bg"]};
    border: 1px solid {p["input_border"]};
    border-radius: 10px;
    color: {p["text_primary"]};
    font-size: 13px;
    padding: 8px 10px;
    selection-background-color: {p["selection_bg"]};
}}
QPlainTextEdit#input:focus {{
    border: 1px solid {p["input_border_focus"]};
}}
QPushButton#primary {{
    background: {p["accent"]};
    color: {p["accent_text"]};
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1px;
}}
QPushButton#primary:hover {{ background: {p["accent_hover"]}; }}
QPushButton#primary:pressed {{ background: {p["accent_pressed"]}; }}

QPushButton#ghost {{
    background: transparent;
    color: {p["text_secondary"]};
    border: 1px solid {p["ghost_border"]};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
}}
QPushButton#ghost:hover {{
    color: {p["accent"]};
    border: 1px solid {p["accent"]};
}}

#status {{ color: {p["text_muted"]}; font-size: 10px; }}
#russianPreview {{
    color: {p["preview_text"]};
    font-size: 12px;
    background: {p["preview_bg"]};
    border: 1px solid {p["preview_border"]};
    border-radius: 8px;
    padding: 6px 8px;
}}

QComboBox#switcher {{
    color: {p["text_secondary"]};
    background: transparent;
    border: 1px solid {p["ghost_border"]};
    border-radius: 6px;
    padding: 2px 6px 2px 8px;
    font-size: 10px;
    min-width: 70px;
}}
QComboBox#switcher:hover {{
    color: {p["accent"]};
    border: 1px solid {p["accent"]};
}}
QComboBox#switcher::drop-down {{
    border: none;
    width: 14px;
}}
QComboBox#switcher QAbstractItemView {{
    background: {p["popup_bg"]};
    color: {p["text_primary"]};
    border: 1px solid {p["card_border"]};
    selection-background-color: {p["accent"]};
    selection-color: {p["accent_text"]};
    outline: 0;
    padding: 2px;
}}
"""


def status_dot_color(theme: str, ok: bool) -> str:
    p = _PALETTES.get(theme) or _PALETTES["majestic"]
    return p["ok"] if ok else p["error"]
