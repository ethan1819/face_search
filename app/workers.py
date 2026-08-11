from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from app.core.database import Database
from app.core.face_engine import FaceEngine
from app.core.image_io import load_image_bgr
from app.core.library_scanner import LibraryScanner
from app.core.search_service import SearchService
from app.core.thumbnail_service import ThumbnailService


def _resolve_library_id(db: Database, library_root: str | None) -> int | None:
    if not library_root:
        return None
    try:
        resolved = str(Path(library_root).resolve())
    except OSError:
        resolved = library_root
    with db.connection() as conn:
        row = conn.execute(
            "SELECT id FROM libraries WHERE root_path=?", (resolved,)
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT id FROM libraries WHERE root_path=?", (library_root,)
            ).fetchone()
    return int(row["id"]) if row else None


class ScanWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, db_path: str, engine: FaceEngine, root: str) -> None:
        super().__init__()
        self.db_path = db_path
        self.engine = engine
        self.root = root
        self.scanner: LibraryScanner | None = None

    @Slot()
    def run(self) -> None:
        db = Database(self.db_path)
        try:
            self.scanner = LibraryScanner(
                db, self.engine, lambda a, b, c: self.progress.emit(a, b, c)
            )
            # 每次新建 scanner 实例后清零 cancel 状态：扫描任务天然
            # 是 "上一次没完成就开启新的" 的语义，不应该被前一次
            # 的 cancel 标志污染。
            self.scanner.reset_cancel()
            self.finished.emit(self.scanner.scan(self.root))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            db.close()
            self.scanner = None

    @Slot()
    def cancel(self) -> None:
        if self.scanner is not None:
            self.scanner.cancel()


class SearchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        db_path: str,
        target: np.ndarray,
        threshold: float,
        query_id: str,
        library_root: str | None = None,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.target = target
        self.threshold = threshold
        self.query_id = query_id
        self.library_root = library_root

    @Slot()
    def run(self) -> None:
        db = Database(self.db_path)
        try:
            library_id = _resolve_library_id(db, self.library_root)
            self.finished.emit(
                SearchService(db, library_id=library_id).search(
                    self.target,
                    threshold=self.threshold,
                    limit=1000,
                    query_id=self.query_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            db.close()


class ThumbnailWorker(QObject):
    ready = Signal(int, str)
    finished = Signal()

    def __init__(self, cache_dir: str, items: list[tuple[int, str]]) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.items = items

    @Slot()
    def run(self) -> None:
        service = ThumbnailService(self.cache_dir)
        for row, path in self.items:
            out = service.render(path, (180, 135))
            if out:
                self.ready.emit(row, out)
        self.finished.emit()


class FeedbackWorker(QObject):
    finished = Signal(int, str)  # photo_id, decision
    failed = Signal(str)

    def __init__(
        self,
        db_path: str,
        query_id: str,
        photo_id: int,
        decision: str,
        score: float,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.query_id = query_id
        self.photo_id = photo_id
        self.decision = decision
        self.score = float(score)

    @Slot()
    def run(self) -> None:
        db = Database(self.db_path)
        try:
            db.record_feedback(self.query_id, self.photo_id, self.decision, self.score)
            self.finished.emit(self.photo_id, self.decision)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            db.close()


def export_failures(db_path: str, destination: str) -> int:
    db = Database(db_path)
    try:
        rows = db.list_unresolved_failures()
        with Path(destination).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["时间", "文件", "阶段", "异常", "详情"])
            for row in rows:
                writer.writerow(
                    [
                        row["occurred_at"],
                        row["photo_path"],
                        row["stage"],
                        row["exception_type"],
                        row["message"],
                    ]
                )
        return len(rows)
    finally:
        db.close()
