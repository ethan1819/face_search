from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest
from PIL import Image


class FakeFace:
    def __init__(self, bbox, embedding, det_score=0.9):
        self.bbox = np.asarray(bbox, dtype=np.float32)
        self.normed_embedding = np.asarray(embedding, dtype=np.float32)
        self.embedding = np.asarray(embedding, dtype=np.float32)
        self.det_score = det_score
        self.detection_score = det_score


class ScriptedEngine:
    """测试用假引擎：按 path 决定返回的脸。"""

    def __init__(self, by_path: dict[str, list[FakeFace]] | None = None) -> None:
        self.by_path = by_path or {}
        self.calls: list[tuple[str, int]] = []

    def extract(self, image):
        if image is None:
            raise ValueError("图像为空")
        # 用 size 间接标识当前 path（test 中 image 来自 np.zeros）
        return []


def _save_rgb(path: Path, color=(255, 128, 64), size=(40, 30)) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG")


def _engine_with_one_face(emb_value: float = 1.0) -> ScriptedEngine:
    """返回固定一张脸；调用次数由调用方追踪。"""
    eng = ScriptedEngine()

    real_extract = eng.extract

    def extract(image):
        if image is None or image.size == 0:
            raise ValueError("图像为空")
        return [
            FakeFace(
                bbox=[0, 0, image.shape[1], image.shape[0]],
                embedding=[emb_value, 0.0, 0.0, 0.0],
                det_score=0.95,
            )
        ]

    eng.extract = extract  # type: ignore[assignment]
    return eng


def test_scanner_indexes_images_and_stores_faces(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.library_scanner import LibraryScanner

    db = Database(tmp_path / "scanner.db")
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    for i in range(3):
        _save_rgb(lib_dir / f"p{i}.jpg")

    engine = _engine_with_one_face()
    scanner = LibraryScanner(db, engine)
    report = scanner.scan(str(lib_dir))

    assert report.total_files == 3
    assert report.indexed == 3
    assert report.failed == 0
    assert db.count_faces() == 3
    # 二次扫描全部跳过（增量）
    report2 = scanner.scan(str(lib_dir))
    assert report2.indexed == 0
    assert report2.skipped == 3


def test_scanner_handles_missing_files(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.library_scanner import LibraryScanner

    db = Database(tmp_path / "scanner.db")
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    (lib_dir / "ghost.jpg").write_bytes(b"not a jpeg \x00\x01")
    _save_rgb(lib_dir / "ok.jpg")

    engine = _engine_with_one_face()

    scanner = LibraryScanner(db, engine)
    report = scanner.scan(str(lib_dir))
    assert report.failed == 1
    assert report.indexed == 1
    rows = db.list_unresolved_failures()
    assert len(rows) == 1


def test_scanner_reindexes_when_size_or_mtime_changes(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.library_scanner import LibraryScanner

    db = Database(tmp_path / "scanner.db")
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    p = lib_dir / "p.jpg"
    _save_rgb(p)
    engine = _engine_with_one_face()
    scanner = LibraryScanner(db, engine)
    scanner.scan(str(lib_dir))
    # 改变 mtime
    import os
    os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 5))
    report = scanner.scan(str(lib_dir))
    assert report.indexed == 1
    assert report.skipped == 0


def test_scanner_marks_missing_files(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.library_scanner import LibraryScanner

    db = Database(tmp_path / "scanner.db")
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    _save_rgb(lib_dir / "p.jpg")
    engine = _engine_with_one_face()
    scanner = LibraryScanner(db, engine)
    scanner.scan(str(lib_dir))
    # 删除一张
    (lib_dir / "p.jpg").unlink()
    report = scanner.scan(str(lib_dir))
    with db.connection() as conn:
        status = conn.execute(
            "SELECT scan_status FROM photos WHERE path=?", (str(lib_dir / "p.jpg"),)
        ).fetchone()["scan_status"]
    assert status == "missing"
    assert report.missing == 1


def test_cancelled_scan_does_not_mark_unvisited_photos_missing(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.library_scanner import LibraryScanner

    db = Database(tmp_path / "scanner.db")
    lib_dir = tmp_path / "photos"
    lib_dir.mkdir()
    for i in range(3):
        _save_rgb(lib_dir / f"p{i}.jpg")
    engine = _engine_with_one_face()
    scanner = LibraryScanner(db, engine)
    scanner.scan(str(lib_dir))

    # 强制 mtime 变化，确保第二轮不会被全部 skipped
    for p in lib_dir.iterdir():
        os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 5))

    scanner.reset_cancel()
    scanner.cancel()
    report = scanner.scan(str(lib_dir))

    with db.connection() as conn:
        statuses = [row["scan_status"] for row in conn.execute("SELECT scan_status FROM photos")]
    assert report.errors == ["已取消"]
    # 3 张照片 mtime 已变，扫描中途中断，0 张被访问，3 张应保留原状态
    assert statuses == ["ok", "ok", "ok"]