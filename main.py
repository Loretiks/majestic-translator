from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import Config
from app.overlay import Overlay
from app.region_picker import RegionPicker


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    cfg = Config.load()

    if cfg.chat_region is None:
        picker = RegionPicker()

        def on_region(region):
            cfg.chat_region = region
            cfg.save()
            window = Overlay(cfg)
            window.show()
            app.setProperty("_main", window)

        def on_cancel():
            QMessageBox.warning(
                None,
                "Калибровка отменена",
                "Без области чата OCR работать не будет. "
                "Запусти приложение снова и выдели область.",
            )
            app.quit()

        picker.region_selected.connect(on_region)
        picker.cancelled.connect(on_cancel)
        picker.show()
    else:
        window = Overlay(cfg)
        window.show()
        app.setProperty("_main", window)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
