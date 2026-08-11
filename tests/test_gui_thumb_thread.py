"""GUI safety: search_done must drain any in-flight thumbnail thread."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


class _FakeEngine:
    def extract(self, image):  # noqa: ARG002
        return []


def test_search_done_drains_old_thumbnail_thread(tmp_path: Path) -> None:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from app.core.database import Database
    from app.main import MainWindow
    from app.core.search_service import SearchHit

    app = QApplication.instance() or QApplication([])

    db_path = tmp_path / "gui.db"
    lib_id = Database(db_path).upsert_library(str(tmp_path))
    photo_id = Database(db_path).upsert_photo(
        library_id=lib_id, path=str(tmp_path / "p.jpg"), size=1, mtime_ns=1, width=10, height=10, face_count=0, scan_status="ok"
    )
    Database(db_path).close()

    window = MainWindow(_FakeEngine(), "")
    window.library.setText(str(tmp_path))
    hit = SearchHit(photo_id=photo_id, photo_path=str(tmp_path / "p.jpg"), score=0.9)
    window.search_done([hit])
    first_thread = window.thumb_thread
    assert first_thread is not None and first_thread.isRunning()

    # second search_done while first is still alive must NOT segfault
    window.search_done([hit])
    assert window.thumb_thread is not None
    assert window.thumb_thread is not first_thread

    loop = QEventLoop()
    QTimer.singleShot(1500, loop.quit)
    loop.exec()
    window.close()
