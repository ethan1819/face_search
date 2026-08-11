"""SQLite 数据库封装：WAL、schema 迁移、CRUD 与按批读取人脸特征。"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np
from numpy.typing import NDArray


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_scan_at TEXT
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    path TEXT NOT NULL UNIQUE,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    width INTEGER NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 0,
    face_count INTEGER NOT NULL DEFAULT 0,
    scan_status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    indexed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_photos_library ON photos(library_id);
CREATE INDEX IF NOT EXISTS idx_photos_status ON photos(scan_status);

CREATE TABLE IF NOT EXISTS faces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    face_index INTEGER NOT NULL,
    bbox_x1 REAL NOT NULL,
    bbox_y1 REAL NOT NULL,
    bbox_x2 REAL NOT NULL,
    bbox_y2 REAL NOT NULL,
    det_score REAL NOT NULL,
    embedding BLOB NOT NULL,
    embedding_dim INTEGER NOT NULL,
    embedding_norm REAL NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_faces_photo ON faces(photo_id);

CREATE TABLE IF NOT EXISTS scan_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_path TEXT NOT NULL,
    stage TEXT NOT NULL,
    exception_type TEXT NOT NULL,
    message TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_failures_unresolved
    ON scan_failures(resolved_at) WHERE resolved_at IS NULL;

CREATE TABLE IF NOT EXISTS search_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('confirmed','excluded')),
    score REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (query_id, photo_id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_query ON search_feedback(query_id);
"""


class Database:
    """线程本地连接的 SQLite 封装。同一 Database 实例可在多线程复用。"""

    def __init__(self, path: Path | str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._closed = False
        # 先用 root connection 完成迁移（WAL 不能跨连接保持，但模式被持久化）
        with sqlite3.connect(self._path) as conn:
            conn.executescript("PRAGMA journal_mode=WAL;")
            conn.executescript(SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO schema_version(version) VALUES (1)"
            )
            conn.commit()

    # ---------------- connection ----------------

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._closed:
            raise RuntimeError("Database 已关闭")
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self._path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        self._closed = True
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ---------------- libraries ----------------

    def upsert_library(self, root_path: str) -> int:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM libraries WHERE root_path=?", (root_path,)
            ).fetchone()
            if row is not None:
                return int(row["id"])
            cur = conn.execute(
                "INSERT INTO libraries(root_path) VALUES (?)", (root_path,)
            )
            conn.commit()
            return int(cur.lastrowid)

    def touch_library_scan(self, library_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE libraries SET last_scan_at=datetime('now') WHERE id=?",
                (library_id,),
            )
            conn.commit()

    # ---------------- photos ----------------

    def upsert_photo(
        self,
        *,
        library_id: int,
        path: str,
        size: int,
        mtime_ns: int,
        width: int,
        height: int,
        face_count: int,
        scan_status: str,
        error_message: str | None = None,
    ) -> int:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM photos WHERE path=?", (path,)
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    UPDATE photos
                    SET library_id=?, size=?, mtime_ns=?, width=?, height=?,
                        face_count=?, scan_status=?, error_message=?,
                        indexed_at=datetime('now'), updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (
                        library_id,
                        size,
                        mtime_ns,
                        width,
                        height,
                        face_count,
                        scan_status,
                        error_message,
                        row["id"],
                    ),
                )
                conn.commit()
                return int(row["id"])
            cur = conn.execute(
                """
                INSERT INTO photos(library_id, path, size, mtime_ns,
                                   width, height, face_count, scan_status,
                                   error_message, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    library_id,
                    path,
                    size,
                    mtime_ns,
                    width,
                    height,
                    face_count,
                    scan_status,
                    error_message,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_photo_signature(self, path: str) -> tuple[int, int, int] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id, size, mtime_ns FROM photos WHERE path=?", (path,)
            ).fetchone()
        if row is None:
            return None
        return int(row["id"]), int(row["size"]), int(row["mtime_ns"])

    def list_missing_paths(self, library_id: int, current_paths: set[str]) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT path FROM photos WHERE library_id=?", (library_id,)
            ).fetchall()
        known = {row["path"] for row in rows}
        return sorted(known - current_paths)

    def mark_missing(self, paths: Sequence[str]) -> None:
        if not paths:
            return
        with self.connection() as conn:
            conn.executemany(
                "UPDATE photos SET scan_status='missing', updated_at=datetime('now') "
                "WHERE path=?",
                [(p,) for p in paths],
            )
            conn.commit()

    # ---------------- faces ----------------

    def replace_faces(
        self,
        photo_id: int,
        faces: Sequence[
            tuple[
                int,
                tuple[float, float, float, float],
                float,
                NDArray[np.float32],
                int,
                str,
                str,
            ]
        ],
    ) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM faces WHERE photo_id=?", (photo_id,))
            for face_index, (x1, y1, x2, y2), score, vec, dim, model_name, model_version in faces:
                norm = float(np.linalg.norm(vec))
                conn.execute(
                    """
                    INSERT INTO faces(photo_id, face_index, bbox_x1, bbox_y1,
                                      bbox_x2, bbox_y2, det_score, embedding,
                                      embedding_dim, embedding_norm,
                                      model_name, model_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        photo_id,
                        face_index,
                        float(x1),
                        float(y1),
                        float(x2),
                        float(y2),
                        float(score),
                        np.asarray(vec, dtype=np.float32).tobytes(),
                        int(dim),
                        norm,
                        model_name,
                        model_version,
                    ),
                )
            conn.commit()

    def iter_face_embeddings(
        self,
        batch_size: int = 20000,
        model_name: str | None = None,
        library_id: int | None = None,
    ) -> Iterator[list[tuple[int, int, NDArray[np.float32]]]]:
        offset = 0
        where_parts: list[str] = []
        params: list[object] = []
        if model_name is not None:
            where_parts.append("f.model_name = ?")
            params.append(model_name)
        if library_id is not None:
            where_parts.append("p.library_id = ?")
            params.append(library_id)
        where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        while True:
            with self.connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT f.id, f.photo_id, f.embedding, f.embedding_dim
                    FROM faces f
                    JOIN photos p ON p.id = f.photo_id{where_sql}
                    ORDER BY f.photo_id, f.face_index
                    LIMIT ? OFFSET ?
                    """,
                    (*params, batch_size, offset),
                ).fetchall()
            if not rows:
                return
            batch: list[tuple[int, int, NDArray[np.float32]]] = []
            for row in rows:
                vec = np.frombuffer(row["embedding"], dtype=np.float32)
                batch.append((int(row["id"]), int(row["photo_id"]), vec))
            yield batch
            offset += len(rows)

    def count_faces(self, model_name: str | None = None) -> int:
        with self.connection() as conn:
            if model_name is None:
                row = conn.execute("SELECT COUNT(*) AS c FROM faces").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM faces WHERE model_name=?",
                    (model_name,),
                ).fetchone()
        return int(row["c"])

    # ---------------- failures ----------------

    def record_scan_failure(
        self, *, photo_path: str, stage: str, exception_type: str, message: str
    ) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO scan_failures(photo_path, stage, exception_type, message)
                VALUES (?, ?, ?, ?)
                """,
                (photo_path, stage, exception_type, message[:2000]),
            )
            conn.commit()
            return int(cur.lastrowid)

    def resolve_scan_failure(self, failure_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE scan_failures SET resolved_at=datetime('now') WHERE id=?",
                (failure_id,),
            )
            conn.commit()

    def list_unresolved_failures(self) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(
                """
                SELECT id, photo_path, stage, exception_type, message, occurred_at
                FROM scan_failures WHERE resolved_at IS NULL
                ORDER BY occurred_at DESC
                """
            ).fetchall()

    # ---------------- feedback ----------------

    def record_feedback(
        self, query_id: str, photo_id: int, decision: str, score: float
    ) -> None:
        assert decision in ("confirmed", "excluded")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO search_feedback(query_id, photo_id, decision, score)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(query_id, photo_id) DO UPDATE SET
                    decision=excluded.decision,
                    score=excluded.score,
                    created_at=datetime('now')
                """,
                (query_id, photo_id, decision, float(score)),
            )
            conn.commit()

    def get_feedback_decisions(self, query_id: str) -> dict[int, str]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT photo_id, decision FROM search_feedback WHERE query_id=?",
                (query_id,),
            ).fetchall()
        return {int(row["photo_id"]): str(row["decision"]) for row in rows}