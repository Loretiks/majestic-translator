from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Tuple

from PySide6.QtCore import QObject, Signal

from .ocr import ChatOCR
from .translator import Translator


_TRANSLATE_WORKERS = 4


class OcrTranslateWorker(QObject):
    """Background OCR loop + parallel translation pool.

    The OCR thread only *schedules* translations onto a thread pool — it
    never waits on a future. That way slow Google calls never starve chat
    capture. Results land in a per-seq buffer and the worker drains
    consecutive ready items, emitting them in original chat order so the
    feed never shows messages out of sequence.
    """

    line_ready = Signal(str, str)  # original, translated
    error = Signal(str)
    status = Signal(str)

    def __init__(self, ocr: ChatOCR, translator: Translator, interval_ms: int) -> None:
        super().__init__()
        self.ocr = ocr
        self.translator = translator
        self.interval_ms = interval_ms

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pool: ThreadPoolExecutor | None = None

        self._buffer_lock = threading.Lock()
        self._next_seq = 0
        self._next_emit = 0
        self._buffer: Dict[int, Tuple[str, str]] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        with self._buffer_lock:
            self._next_seq = 0
            self._next_emit = 0
            self._buffer.clear()
        self._pool = ThreadPoolExecutor(
            max_workers=_TRANSLATE_WORKERS, thread_name_prefix="tr"
        )
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None

    def _loop(self) -> None:
        # Status payloads are i18n keys ("loading_models", "ocr_active");
        # the overlay maps them to translated strings via t().
        self.status.emit("loading_models")
        try:
            self.ocr.warmup()
        except Exception as e:
            self.error.emit(f"OCR warmup: {e}")
            return
        self.status.emit("ocr_active")

        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                lines = self.ocr.poll_new_lines()
                pool = self._pool
                if pool is None:
                    return
                for line in lines:
                    seq = self._next_seq
                    self._next_seq += 1
                    pool.submit(self._translate_publish, seq, line)
            except Exception as e:
                self.error.emit(str(e))
                time.sleep(2.0)
                continue

            # Adaptive pacing: if a cycle ran long (heavy OCR), reduce sleep.
            # Always leave a small floor so we don't pin a CPU core at 100%.
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            wait_ms = max(80.0, self.interval_ms - elapsed_ms)
            self._stop.wait(wait_ms / 1000.0)

    def _translate_publish(self, seq: int, line: str) -> None:
        if self._stop.is_set():
            return
        try:
            translated = self.translator.translate_line(line)
        except Exception as e:
            translated = f"[ошибка: {e}]"

        with self._buffer_lock:
            if self._stop.is_set():
                return
            self._buffer[seq] = (line, translated)
            # Drain consecutive ready items so the feed stays in chat order.
            # Qt queues cross-thread signal emissions, so emit() returns fast.
            while self._next_emit in self._buffer:
                orig, tr = self._buffer.pop(self._next_emit)
                self._next_emit += 1
                self.line_ready.emit(orig, tr)


class ManualTranslateWorker(QObject):
    """One-shot Polish→Russian translation for the input box."""

    done = Signal(str, str)
    error = Signal(str)

    def __init__(self, translator: Translator) -> None:
        super().__init__()
        self.translator = translator

    def submit(self, text: str) -> None:
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text: str) -> None:
        try:
            result = self.translator.translate_plain(text)
            self.done.emit(text, result)
        except Exception as e:
            self.error.emit(str(e))
