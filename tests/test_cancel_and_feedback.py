"""Cancel/state tests covering both ScanWorker and Thumbnail thread."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEventLoop, QThread, QTimer
from PySide6.QtWidgets import QApplication


def _save_rgb(path: Path, size=(40, 30)) -> None:
    from PIL import Image
    Image.new("RGB", size, (255, 128, 64)).save(path, format="JPEG")


def _engine_with_one_face():
    from tests.test_library_scanner import _engine_with_one_face as _real
    return _real()


def test_repeated_scan_after_cancel_re_indexes(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.library_scanner import LibraryScanner

    db = Database(tmp_path / "scanner.db")
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    for i in range(2):
        _save_rgb(lib_dir / f"p{i}.jpg")

    engine = _engine_with_one_face()
    scanner = LibraryScanner(db, engine)
    first = scanner.scan(str(lib_dir))
    assert first.indexed == 2

    # 复用同一 scanner 实例：cancel() 对后续 scan 持续有效，
    # 这是"取消一个正在跑的长任务"的语义。
    scanner.cancel()
    import os as _os
    for p in lib_dir.iterdir():
        _os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 5))
    cancelled = scanner.scan(str(lib_dir))
    assert "已取消" in cancelled.errors

    # 复用同一 scanner 实例：调用方负责 reset_cancel()，再 scan 才正常
    scanner.reset_cancel()
    next_report = scanner.scan(str(lib_dir))
    assert next_report.errors == []
    assert next_report.indexed + next_report.skipped == 2


def test_scan_worker_resets_cancel_each_run(tmp_path: Path) -> None:
    """GUI 入口走 ScanWorker：每次新 worker 跑都应当清零 cancel 状态。"""
    from PySide6.QtCore import QEventLoop, QThread, QTimer
    from PySide6.QtWidgets import QApplication
    from app.core.database import Database
    from app.workers import ScanWorker

    app = QApplication.instance() or QApplication([])
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    for i in range(2):
        _save_rgb(lib_dir / f"p{i}.jpg")

    class _NoopEngine:
        def extract(self, image):
            return []

    db_path = tmp_path / "w.db"
    Database(db_path).close()
    worker = ScanWorker(str(db_path), _NoopEngine(), str(lib_dir))
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    worker.failed.connect(loop.quit)
    thread.start()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    thread.quit()
    thread.wait(2000)

    # 第二次再起 worker：先 cancel 一次，验证 worker 不会因此把第二次的 scan 标记取消
    worker2 = ScanWorker(str(db_path), _NoopEngine(), str(lib_dir))
    worker2.cancel()  # 在 worker.run 之前 set，但 worker 内部 reset_cancel 会清零
    thread2 = QThread()
    worker2.moveToThread(thread2)
    thread2.started.connect(worker2.run)
    results = []
    worker2.finished.connect(lambda r: results.append(r))
    worker2.finished.connect(loop.quit)
    thread2.start()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    thread2.quit()
    thread2.wait(2000)
    assert results, "第二次 ScanWorker 应当完成"
    assert results[0].errors == []
    assert results[0].indexed + results[0].skipped == 2


def test_feedback_worker_writes_in_background(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.workers import FeedbackWorker

    app = QApplication.instance() or QApplication([])

    db_path = tmp_path / "feedback.db"
    db = Database(db_path)
    lib_id = db.upsert_library("M:/x")
    photo_id = db.upsert_photo(
        library_id=lib_id,
        path="M:/x/a.jpg",
        size=1,
        mtime_ns=2,
        width=10,
        height=10,
        face_count=0,
        scan_status="ok",
    )
    db.close()

    worker = FeedbackWorker(str(db_path), "q1", photo_id, "confirmed", 0.9)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    worker.failed.connect(loop.quit)
    thread.start()
    QTimer.singleShot(5000, loop.quit)  # safety timeout
    loop.exec()
    thread.quit()
    thread.wait(2000)

    db = Database(db_path)
    rows = db.get_feedback_decisions("q1")
    db.close()
    assert rows.get(photo_id) == "confirmed"
