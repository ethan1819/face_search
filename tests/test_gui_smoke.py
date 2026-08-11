from __future__ import annotations

import os
from pathlib import Path

import numpy as np


def test_main_window_constructs_offscreen(tmp_path: Path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from app.core.face_engine import FaceEngine
    from app.main import MainWindow

    class FakeApp:
        def get(self, image):
            return []

    app = QApplication.instance() or QApplication([])
    window = MainWindow(FaceEngine(FakeApp()), "CPU smoke")
    assert window.windowTitle() == "本地人脸照片检索"
    assert window.library.text()
    assert "CPU smoke" in window.log.toPlainText()
    window.close()


def test_failure_csv_export(tmp_path: Path):
    from app.core.database import Database
    from app.workers import export_failures

    db_path = tmp_path / "x.db"
    db = Database(db_path)
    db.record_scan_failure(photo_path="broken.jpg", stage="scan", exception_type="ValueError", message="bad")
    db.close()
    out = tmp_path / "failures.csv"
    assert export_failures(str(db_path), str(out)) == 1
    assert "broken.jpg" in out.read_text(encoding="utf-8-sig")
