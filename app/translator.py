from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Tuple

import requests

# Match a leading nickname like "Ivan_Ivanov:" or "[OOC] Ivan_Ivanov:".
_NICK_PREFIX = re.compile(r"^([\[\]\w\d_\-\| ]{1,40}?:\s*)(.+)$")
# Roleplay commands at the start of a message: /me, /do, /try, /b, /s, etc.
_RP_COMMAND = re.compile(r"^(/[a-zA-Zа-яА-Я]{1,6}\s+)(.+)$")


def _split_protected(line: str) -> Tuple[str, str]:
    prefix = ""
    body = line

    m = _NICK_PREFIX.match(body)
    if m:
        prefix += m.group(1)
        body = m.group(2)

    m = _RP_COMMAND.match(body)
    if m:
        prefix += m.group(1)
        body = m.group(2)

    return prefix, body


class _GoogleClient:
    """Thin direct client for the public Google Translate endpoint that
    Chrome's "Translate this page" feature uses. No API key. Session-pooled
    HTTPS so calls after the first warm-up are ~200–400ms instead of ~1.5s."""

    URL = "https://translate.googleapis.com/translate_a/single"

    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def translate(self, text: str) -> str:
        if not text.strip():
            return text
        params = {
            "client": "gtx",
            "sl": self.source,
            "tl": self.target,
            "dt": "t",
            "q": text,
        }
        for attempt in range(3):
            try:
                r = self._session.get(self.URL, params=params, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    out = ""
                    for seg in data[0] or []:
                        if seg and seg[0]:
                            out += seg[0]
                    return out or text
                if r.status_code in (429, 503) and attempt < 2:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                raise RuntimeError(f"http {r.status_code}")
            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(0.3)
                    continue
                raise RuntimeError(str(e))
        return text


class Translator:
    """Google-backed translator. Free, no key, fast (session-pooled)."""

    def __init__(self, source: str, target: str, email: str | None = None) -> None:
        # email kept for forward compat with config.json, ignored for Google.
        self.source = source
        self.target = target
        self._client = _GoogleClient(source, target)

    @lru_cache(maxsize=4096)
    def _translate_raw(self, text: str) -> str:
        if not text.strip():
            return text
        try:
            return self._client.translate(text)
        except Exception as e:
            return f"[ошибка перевода: {e}]"

    def translate_line(self, line: str) -> str:
        prefix, body = _split_protected(line)
        if not body.strip():
            return line
        return f"{prefix}{self._translate_raw(body)}"

    def translate_plain(self, text: str) -> str:
        return self._translate_raw(text.strip())
