from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int

    def as_mss(self) -> dict:
        return {"left": self.x, "top": self.y, "width": self.w, "height": self.h}


@dataclass
class Config:
    chat_region: Optional[Region] = None
    tesseract_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ocr_interval_ms: int = 1000
    overlay_pos: dict = field(default_factory=lambda: {"x": 40, "y": 40})
    overlay_size: dict = field(default_factory=lambda: {"w": 460, "h": 520})
    overlay_opacity: float = 0.94
    source_lang: str = "ru"
    target_lang: str = "pl"
    input_lang: str = "pl"
    input_target_lang: str = "ru"
    # MyMemory email — kept for forward-compat. Currently unused.
    mymemory_email: str = ""
    # UI language: "ru" | "pl" | "en"
    language: str = "ru"
    # Theme: "majestic" | "dark" | "light"
    theme: str = "majestic"

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        region_data = data.pop("chat_region", None)
        cfg = cls(**data)
        if region_data:
            cfg.chat_region = Region(**region_data)
        return cfg

    def save(self) -> None:
        data = asdict(self)
        CONFIG_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
