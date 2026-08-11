"""照片库扫描器：枚举、增量判断、检测、入库；损坏隔离、可取消。"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Callable, Iterable

import numpy as np

from .database import Database
from .face_engine import FaceEngine
from .image_io import iter_image_files, load_image_bgr


log = logging.getLogger(__name__)


MODEL_NAME = "buffalo_l"
MODEL_VERSION = "v1"


@dataclass
class ScanReport:
    total_files: int = 0
    indexed: int = 0
    skipped: int = 0
    failed: int = 0
    missing: int = 0
    errors: list[str] = field(default_factory=list)


ProgressCallback = Callable[[int, int, str], None]  # done, total, message


class LibraryScanner:
    def __init__(
        self,
        db: Database,
        engine: FaceEngine,
        progress_cb: ProgressCallback | None = None,
    ) -> None:
        self._db = db
        self._engine = engine
        self._progress_cb = progress_cb
        self._cancel_event = Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def reset_cancel(self) -> None:
        self._cancel_event.clear()

    def scan(self, root: str | Path) -> ScanReport:
        root_path = Path(root)
        if not root_path.exists():
            raise FileNotFoundError(root_path)

        # 注意：不在此处清零 cancel 标志，否则同一 scanner 实例被复用时
        # 上一次 cancel 会被静默吞掉。worker 每次都新建 scanner，
        # 因此 Event 状态在 worker 层面天然是 "未取消"。

        report = ScanReport()
        paths = list(iter_image_files(root_path))
        report.total_files = len(paths)
        lib_id = self._db.upsert_library(str(root_path))

        seen: set[str] = set()

        for idx, p in enumerate(paths):
            if self._cancel_event.is_set():
                report.errors.append("已取消")
                break
            seen.add(str(p))
            try:
                self._scan_one(lib_id, p, report)
            except Exception as exc:  # noqa: BLE001 - 必须隔离
                log.exception("scan fatal: %s", p)
                report.failed += 1
                self._db.record_scan_failure(
                    photo_path=str(p),
                    stage="scan",
                    exception_type=type(exc).__name__,
                    message=str(exc),
                )
            if self._progress_cb is not None:
                self._progress_cb(idx + 1, report.total_files, str(p))

        # 标记 missing：仅当本轮扫描未取消时执行
        if not self._cancel_event.is_set():
            missing = self._db.list_missing_paths(lib_id, seen)
            if missing:
                self._db.mark_missing(missing)
                report.missing = len(missing)

        self._db.touch_library_scan(lib_id)
        return report

    # ---------------- internals ----------------

    def _scan_one(self, lib_id: int, path: Path, report: ScanReport) -> None:
        try:
            stat = path.stat()
        except OSError as exc:
            raise RuntimeError(f"stat 失败: {exc}") from exc

        sig = self._db.get_photo_signature(str(path))
        if sig is not None:
            photo_id, size, mtime_ns = sig
            if size == stat.st_size and mtime_ns == stat.st_mtime_ns:
                # 已经扫过且未变；恢复 scan_status 为 ok
                with self._db.connection() as conn:
                    conn.execute(
                        "UPDATE photos SET scan_status='ok', updated_at=datetime('now') "
                        "WHERE id=?",
                        (photo_id,),
                    )
                    conn.commit()
                report.skipped += 1
                return

        # 读图 + 检测
        img = load_image_bgr(path)
        if img is None:
            raise RuntimeError("图像读取失败/损坏")

        try:
            faces = self._engine.extract(img)
        except ValueError as exc:
            # 检测失败但图像可读：记为 ok 但 0 脸
            log.info("no faces in %s: %s", path, exc)
            photo_id = self._db.upsert_photo(
                library_id=lib_id,
                path=str(path),
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                width=int(img.shape[1]),
                height=int(img.shape[0]),
                face_count=0,
                scan_status="ok",
                error_message=str(exc)[:200],
            )
            report.indexed += 1
            return

        height, width = img.shape[:2]
        rows = []
        for i, face in enumerate(faces):
            vec = np.asarray(face.embedding, dtype=np.float32)
            bbox = (float(face.bbox[0]), float(face.bbox[1]),
                    float(face.bbox[2]), float(face.bbox[3]))
            rows.append(
                (
                    i,
                    bbox,
                    float(face.detection_score),
                    vec,
                    int(vec.shape[0]),
                    MODEL_NAME,
                    MODEL_VERSION,
                )
            )

        photo_id = self._db.upsert_photo(
            library_id=lib_id,
            path=str(path),
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            width=width,
            height=height,
            face_count=len(rows),
            scan_status="ok",
        )
        self._db.replace_faces(photo_id, rows)
        report.indexed += 1