from __future__ import annotations

from typing import Dict


LANGUAGES = ("ru", "pl", "en")
LANGUAGE_NAMES = {
    "ru": "Русский",
    "pl": "Polski",
    "en": "English",
}


_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        "app.subtitle": "RU → PL  ·  PL → RU",
        "section.incoming": "ВХОДЯЩИЕ ⟶ ПОЛЬСКИЙ",
        "section.outgoing": "ОТПРАВКА ⟶ РУССКИЙ",
        "input.placeholder": "Напиши по-польски — Ctrl+Enter переведёт и скопирует в буфер",
        "button.translate_copy": "ПЕРЕВЕСТИ И СКОПИРОВАТЬ",
        "button.clear": "Очистить",
        "tooltip.calibrate": "Калибровать область чата",
        "tooltip.minimize": "Свернуть",
        "tooltip.close": "Закрыть",
        "tooltip.lang": "Язык интерфейса",
        "tooltip.theme": "Тема оформления",
        "status.ready": "Готов",
        "status.ocr_active": "OCR активен",
        "status.loading_models": "Загружаю OCR-модели…",
        "status.copied": "Скопировано в буфер — вставь в чат (T → Ctrl+V)",
        "status.translating": "Перевожу…",
        "status.uncalibrated": "Чат не откалиброван — нажми «Калибровать»",
        "status.calibration_cancelled": "Калибровка отменена",
        "status.region": "Регион: {w}×{h}",
        "status.error_prefix": "Ошибка: {msg}",
        "status.ocr_error_prefix": "OCR: {msg}",
    },
    "pl": {
        "app.subtitle": "RU → PL  ·  PL → RU",
        "section.incoming": "PRZYCHODZĄCE ⟶ POLSKI",
        "section.outgoing": "WYSYŁANE ⟶ ROSYJSKI",
        "input.placeholder": "Wpisz po polsku — Ctrl+Enter przetłumaczy i skopiuje do schowka",
        "button.translate_copy": "PRZETŁUMACZ I SKOPIUJ",
        "button.clear": "Wyczyść",
        "tooltip.calibrate": "Kalibruj obszar czatu",
        "tooltip.minimize": "Minimalizuj",
        "tooltip.close": "Zamknij",
        "tooltip.lang": "Język interfejsu",
        "tooltip.theme": "Motyw",
        "status.ready": "Gotowy",
        "status.ocr_active": "OCR aktywny",
        "status.loading_models": "Ładuję modele OCR…",
        "status.copied": "Skopiowano do schowka — wklej w czat (T → Ctrl+V)",
        "status.translating": "Tłumaczę…",
        "status.uncalibrated": "Czat nie skalibrowany — naciśnij «Kalibruj»",
        "status.calibration_cancelled": "Kalibracja anulowana",
        "status.region": "Obszar: {w}×{h}",
        "status.error_prefix": "Błąd: {msg}",
        "status.ocr_error_prefix": "OCR: {msg}",
    },
    "en": {
        "app.subtitle": "RU → PL  ·  PL → RU",
        "section.incoming": "INCOMING ⟶ POLISH",
        "section.outgoing": "OUTGOING ⟶ RUSSIAN",
        "input.placeholder": "Type in Polish — Ctrl+Enter translates and copies to clipboard",
        "button.translate_copy": "TRANSLATE & COPY",
        "button.clear": "Clear",
        "tooltip.calibrate": "Calibrate chat region",
        "tooltip.minimize": "Minimize",
        "tooltip.close": "Close",
        "tooltip.lang": "Interface language",
        "tooltip.theme": "Theme",
        "status.ready": "Ready",
        "status.ocr_active": "OCR active",
        "status.loading_models": "Loading OCR models…",
        "status.copied": "Copied to clipboard — paste in chat (T → Ctrl+V)",
        "status.translating": "Translating…",
        "status.uncalibrated": "Chat not calibrated — press «Calibrate»",
        "status.calibration_cancelled": "Calibration cancelled",
        "status.region": "Region: {w}×{h}",
        "status.error_prefix": "Error: {msg}",
        "status.ocr_error_prefix": "OCR: {msg}",
    },
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Look up a translated string. Falls back to the Russian table, then
    to the key itself, so the UI never crashes on a missing entry."""
    table = _TRANSLATIONS.get(lang) or _TRANSLATIONS["ru"]
    s = table.get(key) or _TRANSLATIONS["ru"].get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, IndexError):
            return s
    return s
