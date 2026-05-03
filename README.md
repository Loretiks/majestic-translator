# Majestic Translator

> Real-time chat overlay translator for [Majestic RP](https://majestic-rp.ru/) and other GTA V multiplayer servers. Reads the in-game chat with on-screen OCR, translates Russian → Polish (or any pair you configure), and lets you reply in Polish — the Russian translation lands in your clipboard, ready to paste back.

[Русский](README.ru.md) · [Polski](README.pl.md) · **English**

![Majestic Translator preview](docs/screenshots/preview.png)

---

## Why

Russian-speaking RP servers, Polish-speaking player. Or vice versa. Or you're learning the language. The official client has no translation, third-party translators don't read the chat, and copy/pasting individual messages out of game breaks immersion.

Majestic Translator runs as a small always-on-top window next to the game. It quietly OCRs the chat region, sends each new line through Google Translate, and shows the translation in chat order. The reverse direction goes through a tiny input box and into your clipboard.

## Features

- 🎯 **Region-based OCR** — calibrate once, point at the chat panel; works at any resolution.
- ⚡ **Frame-diff skip** — when the chat is idle, the OCR engine is idle, so the app sits at ~0% CPU.
- 🧠 **Smart message grouping** — long wrapped messages get glued back into a single line; UI labels and our own window are masked out before recognition.
- 🚀 **Parallel non-blocking translation** — slow Google calls never starve chat capture; results emit in original chat order.
- 🌍 **3 UI languages** — Russian, Polish, English.
- 🎨 **3 themes** — Majestic (dark + gold), Dark (graphite), Light (white).
- 🪶 **Native frameless window** — proper OS-level drag, no janky manual move loop.
- 🔓 **No API keys** — uses Google's public translate endpoint (the one Chrome's "Translate this page" hits).

## Quick start

### Option A — installer (Windows)

1. Download `MajesticTranslator-Setup.exe` from [Releases](../../releases).
2. Run, accept defaults, finish.
3. Launch from Start menu.
4. On first run, drag-select the chat region in your game.

### Option B — from source

You'll need **Python 3.11+** and a working internet connection (the OCR models download once, ~150 MB).

```powershell
git clone https://github.com/<your-user>/majestic-translator.git
cd majestic-translator

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py
```

On first launch a translucent overlay appears over your screen — drag a rectangle around the chat panel in your game, release. The region is saved to `config.json` and reused next time.

## Usage

### Reading the game chat

Just play. Every ~1 second the window OCRs the chat region, picks out new Russian lines, translates them to Polish, and appends to the feed (newest at the bottom).

- **Original** is shown faded underneath each translation.
- The feed keeps the last 40 messages.
- The status row shows OCR/translation state.

### Sending Polish → Russian

1. Type your Polish message in the input box at the bottom.
2. Press **Ctrl+Enter** (or click **TRANSLATE & COPY**).
3. The Russian translation is copied to your clipboard.
4. In the game: press **T** to open chat, **Ctrl+V** to paste, **Enter** to send.

### Switching language and theme

Status bar at the bottom has two dropdowns:

- **Language**: UI language (Russian / Polski / English). The chat translation direction is independent — it's still RU ↔ PL.
- **Theme**: Majestic (current dark + gold), Dark (neutral graphite), Light (white).

Both choices persist to `config.json` instantly.

### Recalibrating the chat region

Click the **⌖** icon in the title bar. The fullscreen overlay returns; drag a new rectangle.

## Configuration

`config.json` is created next to the executable on first run:

| Key | Description | Default |
|---|---|---|
| `chat_region` | OCR region in screen pixels | (set on calibration) |
| `ocr_interval_ms` | Chat poll interval. Lower = more responsive, more CPU | `1000` |
| `overlay_pos` / `overlay_size` | Window geometry | restored across runs |
| `source_lang` / `target_lang` | Chat translation direction | `ru` → `pl` |
| `input_lang` / `input_target_lang` | Reply box translation direction | `pl` → `ru` |
| `language` | UI language: `ru` \| `pl` \| `en` | `ru` |
| `theme` | UI theme: `majestic` \| `dark` \| `light` | `majestic` |

## How it works

```
                ┌─────────────────────────┐
                │  Majestic RP / GTA V    │
                │  ┌───────────────────┐  │
   chat region  │  │   in-game chat    │  │
   ═════════════╪══╪═══════════════════╪══╪═══
                │  │  [HH:MM] reply…   │  │
                │  └───────────────────┘  │
                └─────────────┬───────────┘
                              │ mss.grab()
                              ▼
                    ┌─────────────────┐
                    │ frame-diff skip │── unchanged ──▶ done
                    └────────┬────────┘
                             │ changed
                             ▼
                    ┌─────────────────┐
                    │ PaddleOCR (ru)  │── lines + boxes
                    │ mobile det+rec  │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ group by hyphen │── chat lines
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ dedup by [HH:MM]│── new lines
                    └────────┬────────┘
                             │ seq number
                             ▼
                    ┌─────────────────┐
                    │ translate pool  │── parallel × 4
                    │ (Google /gtx)   │   ordered emit
                    └────────┬────────┘
                             ▼
                       overlay feed
```

Key bits:
- **Detection model**: `PP-OCRv5_mobile_det` (~10 MB, ~150 ms/cycle on CPU).
- **Recognition model**: `eslav_PP-OCRv5_mobile_rec` (East-Slavic — Russian / Ukrainian / Belarusian).
- **Translation**: direct call to `translate.googleapis.com/translate_a/single?client=gtx`. Same endpoint Chrome uses to translate web pages. No API key.
- **Threading**: OCR loop never blocks on translation — slow Google calls don't pause chat capture. A `ThreadPoolExecutor` runs translations in parallel; a seq-numbered buffer reorders results so the feed stays in chat order.

## Building from source

You need:
- Python 3.11 or 3.12
- ~5 GB free disk for build artifacts
- (Optional) [Inno Setup 6](https://jrsoftware.org/isdl.php) to produce an installer

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt pyinstaller

# 1. Build the dist folder
pyinstaller build/MajesticTranslator.spec --noconfirm

# 2. (Optional) Wrap into a Windows installer
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\installer.iss
```

Outputs:
- `dist/MajesticTranslator/` — runnable folder, ~700 MB unpacked
- `installer/output/MajesticTranslator-Setup.exe` — single installer, ~250 MB

## Privacy / what hits the network

- **OCR models** download once on first launch from PaddleOCR's official mirror (~150 MB, cached in `%USERPROFILE%\.paddlex\`).
- **Translations** go to Google's public translate endpoint over HTTPS. Each chat line you OCR is sent as a query string. No telemetry, no analytics. Source is in `app/translator.py:23` if you want to verify.
- **Nothing is sent anywhere else.**

## Limitations

- **Anti-cheat warning**: Majestic RP runs RAGE Multiplayer with a custom anti-cheat. This app only **reads** the screen and emulates the clipboard — it does not inject into or modify the game. Other RP servers may have different policies; check before using.
- **OCR accuracy** isn't perfect on stylized chat fonts. Player nicks and faction tags occasionally come out garbled (`Фракция` → `Фрakция` etc.). The chat content itself is usually fine.
- **Google rate limits**: at very high chat volume (~> 30 lines/min sustained) the public Google endpoint may throttle. Slow it down or use a paid translator backend.
- **Single monitor first**: works on multi-monitor, but the calibration overlay shows on the primary monitor only.

## Contributing

Issues and PRs welcome. The codebase is small (~1000 lines) and laid out conventionally:

```
app/
├── config.py        # JSON config persistence
├── i18n.py          # UI translations (RU/PL/EN)
├── themes.py        # Three Qt stylesheet palettes
├── ocr.py           # mss capture → PaddleOCR → grouping → dedup
├── translator.py    # Direct Google /gtx client + nick/RP-command preserver
├── workers.py       # Non-blocking parallel pipeline (Qt signals)
├── region_picker.py # Fullscreen drag-to-select calibrator
└── overlay.py       # Frameless PySide6 main window
main.py              # Entry point: load config, pick region if needed, show
```

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) for the East-Slavic recognition model.
- [PySide6](https://wiki.qt.io/Qt_for_Python) for the frameless window plumbing.
- [mss](https://github.com/BoboTiG/python-mss) for fast screen capture.
- [Inno Setup](https://jrsoftware.org/isinfo.php) for installer packaging.

Not affiliated with Majestic RP, Rockstar Games, or Take-Two Interactive. GTA V is a trademark of Rockstar Games.
