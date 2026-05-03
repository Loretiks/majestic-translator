from __future__ import annotations

import logging
import os
import re
from collections import deque
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from .config import Config, Region

# Type alias: a function that returns rectangles in global screen coords
# (x, y, w, h) which must be blanked out before OCR — typically the
# translator's own window so its UI doesn't leak into the chat capture.
MaskProvider = Callable[[], Sequence[Tuple[int, int, int, int]]]

try:
    import mss
except Exception:  # pragma: no cover
    mss = None


_WHITESPACE_RE = re.compile(r"\s+")
_TIMESTAMP_RE = re.compile(r"^\s*\[\d{1,2}[:;.]\d{2}")
_TIMESTAMP_FULL = re.compile(r"\[(\d{1,2}[:;.]\d{1,2}[:;.]\d{1,2})\]")
_HAS_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_NON_ALNUM = re.compile(r"[^a-zа-яё0-9]+", re.IGNORECASE)
_HYPHEN_AT_END = re.compile(r"[-‑–—]\s*$")
_MIN_CONFIDENCE = 0.55
_SIG_BODY_LEN = 25
_SIG_NO_TIMESTAMP_LEN = 50
# If the captured chat region is essentially identical to the previous
# frame (mean per-channel difference below this), skip OCR entirely.
# Bumped well above the noise floor of subtle chat animations (cursor
# blink, time tickers, antialiasing jitter) so the skip actually kicks
# in during active play, not just when the screen is frozen.
_FRAME_DIFF_SKIP = 4.5
# Cap input side fed to the detector — the detection model rescales
# anyway, and a smaller side runs ~2× faster with no real accuracy loss
# on screen-clean text.
_OCR_DET_LIMIT_SIDE = 640


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _signature(text: str) -> str:
    """Robust dedup key.

    For chat messages with a [HH:MM:SS] timestamp (the common case), use
    the timestamp + first SIG_BODY_LEN alphanumeric chars of the body.
    OCR variations in the message body don't break the match because the
    timestamp itself is structurally stable.

    For lines without a timestamp (rare system banners), fall back to a
    longer alphanumeric prefix."""
    m = _TIMESTAMP_FULL.search(text)
    if m:
        ts = m.group(1)
        rest = text[m.end():]
        rest_clean = _NON_ALNUM.sub("", rest.lower())[:_SIG_BODY_LEN]
        return f"{ts}|{rest_clean}"
    cleaned = _NON_ALNUM.sub("", text.lower())
    return cleaned[:_SIG_NO_TIMESTAMP_LEN]


def _silence_paddle() -> None:
    os.environ.setdefault("FLAGS_call_stack_level", "0")
    os.environ.setdefault("GLOG_minloglevel", "3")
    os.environ.setdefault("PADDLE_DISABLE_INFO", "1")
    for name in ("ppocr", "paddle", "paddleocr", "paddlex"):
        logging.getLogger(name).setLevel(logging.ERROR)


class ChatOCR:
    """Captures the chat region, runs PaddleOCR, joins multi-line messages,
    and emits dedup'd new lines for translation."""

    def __init__(self, cfg: Config, history: int = 200) -> None:
        self.cfg = cfg
        self._sct = mss.mss() if mss else None
        self._seen_sigs: deque[str] = deque(maxlen=history)
        self._seen_set: set[str] = set()
        self._engine = None
        self._mask_provider: Optional[MaskProvider] = None
        # Subsampled previous frame, used by the image-diff skip below.
        self._last_thumb: Optional[np.ndarray] = None
        _silence_paddle()

    def set_mask_provider(self, provider: Optional[MaskProvider]) -> None:
        """Register a callback that returns rects (in global screen coords)
        to blank out from the OCR capture before recognition."""
        self._mask_provider = provider

    def _engine_lazy(self):
        if self._engine is not None:
            return self._engine
        from paddleocr import PaddleOCR

        # Mobile detection model — ~3–5× faster than PP-OCRv5_server_det.
        # IMPORTANT: when you set any *_model_name, PaddleOCR silently
        # ignores the `lang` kwarg and falls back to its default Chinese
        # rec model — so the cyrillic rec model MUST be set explicitly.
        # cpu_threads=2 caps the inference thread fan-out (default tries
        # to use every core); text_det_limit_side_len downscales the
        # input before detection for additional speed.
        self._engine = PaddleOCR(
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="eslav_PP-OCRv5_mobile_rec",
            text_det_limit_side_len=_OCR_DET_LIMIT_SIDE,
            text_det_limit_type="max",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            cpu_threads=2,
            device="cpu",
        )

        # Belt-and-braces: clamp paddle's own thread count after init,
        # in case env vars were read too late by some subsystem.
        try:
            import paddle  # noqa: WPS433
            paddle.set_num_threads(2)
        except Exception:
            pass

        return self._engine

    def _grab(self, region: Region) -> np.ndarray:
        if self._sct is None:
            raise RuntimeError("mss is not available")
        shot = self._sct.grab(region.as_mss())
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        arr = np.array(img)
        self._apply_masks(arr, region)
        return arr

    def _apply_masks(self, arr: np.ndarray, region: Region) -> None:
        if self._mask_provider is None:
            return
        try:
            rects = self._mask_provider()
        except Exception:
            return
        for x, y, w, h in rects or []:
            # Convert from global screen coords to coords inside the
            # captured array, then clip to bounds.
            x0 = max(0, x - region.x)
            y0 = max(0, y - region.y)
            x1 = min(region.w, x - region.x + w)
            y1 = min(region.h, y - region.y + h)
            if x1 > x0 and y1 > y0:
                arr[y0:y1, x0:x1] = (12, 14, 22)

    def _ocr_items(self, img: np.ndarray) -> List[Tuple[float, float, float, str, float]]:
        """Returns list of (y_top, x_left, line_height, text, confidence)
        sorted by visual order (top-to-bottom, then left-to-right)."""
        engine = self._engine_lazy()
        try:
            results = engine.predict(input=img)
        except Exception as e:
            raise RuntimeError(f"OCR failed: {e}")

        items: List[Tuple[float, float, float, str, float]] = []
        for res in results or []:
            data = res if isinstance(res, dict) else None
            if data is None:
                try:
                    data = dict(res)
                except Exception:
                    continue
            texts = data.get("rec_texts") or []
            scores = data.get("rec_scores") or [1.0] * len(texts)
            boxes = data.get("rec_boxes")
            if boxes is None or (hasattr(boxes, "__len__") and len(boxes) == 0):
                # Fall back to polys.
                polys = data.get("rec_polys") or []
                for text, score, poly in zip(texts, scores, polys):
                    arr = np.asarray(poly).reshape(-1, 2)
                    y_top = float(arr[:, 1].min())
                    y_bot = float(arr[:, 1].max())
                    x_left = float(arr[:, 0].min())
                    items.append((y_top, x_left, y_bot - y_top, str(text), float(score)))
            else:
                arr = np.asarray(boxes)
                # rec_boxes is [N, 4] with [x1, y1, x2, y2]
                for i, (text, score) in enumerate(zip(texts, scores)):
                    if i >= len(arr):
                        break
                    x1, y1, x2, y2 = arr[i]
                    items.append(
                        (float(y1), float(x1), float(y2 - y1), str(text), float(score))
                    )
        items.sort(key=lambda t: (t[0], t[1]))
        return items

    @staticmethod
    def _group_messages(
        items: List[Tuple[float, float, float, str, float]],
    ) -> List[Tuple[str, float]]:
        """Combine wrapped chat messages.

        Strict rule: every detected line is its own message UNLESS the
        previous line ended with a hyphen — that's how Majestic's chat
        wraps long words mid-message ("При-чина", "прие-дете"). Any other
        line break is treated as a message boundary, so unrelated text
        (UI labels, system banners, our own translator window leaking
        into the capture) doesn't get glued onto chat lines."""
        messages: List[Tuple[str, float]] = []
        current_text: str | None = None
        current_score = 1.0

        for _y, _x, _h, text, score in items:
            text = _normalize(text)
            if not text:
                continue

            is_continuation = (
                current_text is not None
                and bool(_HYPHEN_AT_END.search(current_text))
                and not _TIMESTAMP_RE.match(text)
            )

            if is_continuation:
                # Drop the trailing hyphen of the previous fragment and join.
                stripped = _HYPHEN_AT_END.sub("", current_text or "")
                current_text = f"{stripped}{text}"
                current_score = min(current_score, score)
            else:
                if current_text is not None:
                    messages.append((current_text, current_score))
                current_text = text
                current_score = score

        if current_text is not None:
            messages.append((current_text, current_score))
        return messages

    @staticmethod
    def _is_chat_message(text: str) -> bool:
        if len(text) < 4:
            return False
        if not _HAS_CYRILLIC.search(text):
            return False
        if _TIMESTAMP_RE.match(text):
            return True
        if ":" in text and _HAS_CYRILLIC.search(text.split(":", 1)[1]):
            return True
        if re.match(r"^\s*/\w{1,6}\s+.+", text):
            return True
        return False

    def _filter(self, messages: List[Tuple[str, float]]) -> List[str]:
        out: List[str] = []
        for text, score in messages:
            if score < _MIN_CONFIDENCE:
                continue
            if not self._is_chat_message(text):
                continue
            out.append(text)
        return out

    def _is_dup(self, sig: str) -> bool:
        if not sig:
            return True
        return sig in self._seen_set

    def _remember(self, sig: str) -> None:
        if not sig:
            return
        # Incremental dedup-set update: when the deque is full, the next
        # append evicts its leftmost item, so drop that one from the set
        # before adding the new sig. Avoids rebuilding the set each call.
        if len(self._seen_sigs) >= (self._seen_sigs.maxlen or 0):
            evicted = self._seen_sigs[0]
            self._seen_set.discard(evicted)
        self._seen_sigs.append(sig)
        self._seen_set.add(sig)

    def _frame_unchanged(self, img: np.ndarray) -> bool:
        """Cheap per-cycle short-circuit: if the chat region looks
        essentially identical to the previous capture, don't bother
        running OCR. Compares 1/64-subsampled thumbnails for speed."""
        thumb = img[::8, ::8]
        prev = self._last_thumb
        self._last_thumb = thumb.copy()
        if prev is None or prev.shape != thumb.shape:
            return False
        diff = np.abs(thumb.astype(np.int16) - prev.astype(np.int16)).mean()
        return diff < _FRAME_DIFF_SKIP

    def poll_new_lines(self) -> List[str]:
        region = self.cfg.chat_region
        if region is None:
            return []
        img = self._grab(region)
        if self._frame_unchanged(img):
            return []

        items = self._ocr_items(img)
        messages = self._group_messages(items)
        candidates = self._filter(messages)

        fresh: List[str] = []
        for msg in candidates:
            sig = _signature(msg)
            if self._is_dup(sig):
                continue
            self._remember(sig)
            fresh.append(msg)
        return fresh

    def warmup(self) -> None:
        """Load PaddleOCR models and seed dedup with the current chat,
        so we don't translate the entire backlog on startup."""
        region = self.cfg.chat_region
        if region is None:
            self._engine_lazy()
            return
        try:
            img = self._grab(region)
            items = self._ocr_items(img)
            for msg in self._filter(self._group_messages(items)):
                self._remember(_signature(msg))
        except Exception:
            pass
