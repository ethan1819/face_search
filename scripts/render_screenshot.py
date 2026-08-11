"""Render the main window in offscreen Qt mode and save a PNG screenshot."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, QFontDatabase, QPixmap
from PySide6.QtWidgets import QApplication

from app.core.face_engine import FaceEngine
from app.main import MainWindow


# Headless / sandboxed Qt may not see any system fonts. Load Microsoft YaHei
# (always present on Windows; on Linux CI we fall back gracefully).
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _ensure_font(app: QApplication) -> str:
    db = QFontDatabase
    families = db.families()
    if families:
        # already have fonts (e.g. real desktop)
        return families[0]
    # try to load each candidate
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            fid = db.addApplicationFont(path)
            if fid >= 0:
                fams = db.applicationFontFamilies(fid)
                if fams:
                    app.setFont(QFont(fams[0], 10))
                    return fams[0]
    return ""


class _StubApp:
    def get(self, image):
        return []


def main() -> int:
    out = ROOT / "docs" / "screenshot.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    fam = _ensure_font(app)
    if not fam:
        sys.stderr.write("warning: no fonts available; screenshot will show tofu for CJK\n")

    window = MainWindow(FaceEngine(_StubApp()), "CPU smoke: rendered offscreen")
    window.resize(QSize(1180, 780))
    window.show()
    app.processEvents()
    window.repaint()
    app.processEvents()

    pixmap = window.grab()
    if not pixmap.save(str(out), "PNG"):
        sys.stderr.write("Failed to save " + str(out) + "\n")
        return 1
    print("Saved", out, "size:", pixmap.size().width(), "x", pixmap.size().height(), "font:", fam or "(none)")
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
