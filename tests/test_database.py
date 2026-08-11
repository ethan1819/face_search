from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "faces.db"


def test_opens_db_and_creates_schema(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)

    assert db_path.exists()
    with db.connection() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"libraries", "photos", "faces", "scan_failures", "search_feedback"} <= tables
    with db.connection() as conn:
        info = conn.execute("PRAGMA table_info(faces)").fetchall()
    names = {row[1] for row in info}
    assert {
        "photo_id",
        "face_index",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
        "det_score",
        "embedding",
        "embedding_dim",
        "model_name",
        "model_version",
    } <= names
    assert "embedding_norm" in names


def test_wal_mode_enabled(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    with db.connection() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_upsert_library_returns_id(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    lib_id_1 = db.upsert_library("M:/photos")
    lib_id_2 = db.upsert_library("M:/photos")
    assert lib_id_1 == lib_id_2
    with db.connection() as conn:
        rows = conn.execute("SELECT id, root_path FROM libraries").fetchall()
    assert [(r["id"], r["root_path"]) for r in rows] == [(lib_id_1, "M:/photos")]


def test_upsert_photo_inserts_and_updates(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    lib_id = db.upsert_library("M:/photos")
    photo_id = db.upsert_photo(
        library_id=lib_id,
        path="M:/photos/a.jpg",
        size=123,
        mtime_ns=456,
        width=800,
        height=600,
        face_count=0,
        scan_status="ok",
        error_message=None,
    )
    assert photo_id > 0
    same = db.upsert_photo(
        library_id=lib_id,
        path="M:/photos/a.jpg",
        size=123,
        mtime_ns=456,
        width=800,
        height=600,
        face_count=2,
        scan_status="ok",
        error_message=None,
    )
    assert same == photo_id
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT face_count FROM photos WHERE id=?", (photo_id,)
        ).fetchall()
    assert [r["face_count"] for r in rows] == [2]


def test_replace_faces_clears_old_and_inserts_new(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    lib_id = db.upsert_library("M:/photos")
    photo_id = db.upsert_photo(
        library_id=lib_id,
        path="M:/photos/a.jpg",
        size=1,
        mtime_ns=1,
        width=10,
        height=10,
        face_count=1,
        scan_status="ok",
    )
    import numpy as np

    db.replace_faces(
        photo_id,
        [
            (
                0,
                (0.0, 0.0, 1.0, 1.0),
                0.9,
                np.ones(4, dtype=np.float32),
                4,
                "buffalo_l",
                "v1",
            )
        ],
    )
    db.replace_faces(
        photo_id,
        [
            (
                0,
                (1.0, 1.0, 2.0, 2.0),
                0.8,
                np.zeros(4, dtype=np.float32),
                4,
                "buffalo_l",
                "v1",
            ),
            (
                1,
                (3.0, 3.0, 4.0, 4.0),
                0.7,
                np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
                4,
                "buffalo_l",
                "v1",
            ),
        ],
    )
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT face_index, det_score FROM faces WHERE photo_id=? ORDER BY face_index",
            (photo_id,),
        ).fetchall()
    assert [(r["face_index"], r["det_score"]) for r in rows] == [(0, 0.8), (1, 0.7)]


def test_record_scan_failure_and_resolve(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    fid = db.record_scan_failure(
        photo_path="M:/photos/bad.jpg",
        stage="decode",
        exception_type="OSError",
        message="无法识别图像格式",
    )
    assert fid > 0
    db.resolve_scan_failure(fid)
    with db.connection() as conn:
        resolved = conn.execute(
            "SELECT resolved_at FROM scan_failures WHERE id=?", (fid,)
        ).fetchone()[0]
    assert resolved is not None


def test_record_feedback_is_unique_per_photo(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    lib_id = db.upsert_library("M:/photos")
    photo_id = db.upsert_photo(
        library_id=lib_id,
        path="M:/photos/x.jpg",
        size=1,
        mtime_ns=1,
        width=1,
        height=1,
        face_count=1,
        scan_status="ok",
    )
    db.record_feedback("q1", photo_id, "confirmed", 0.7)
    db.record_feedback("q1", photo_id, "excluded", 0.7)  # upsert
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT decision FROM search_feedback WHERE query_id=? AND photo_id=?",
            ("q1", photo_id),
        ).fetchall()
    assert [r["decision"] for r in rows] == ["excluded"]


def test_iter_face_embeddings_returns_batches(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    lib_id = db.upsert_library("M:/photos")
    import numpy as np

    photo_ids = []
    for i in range(3):
        pid = db.upsert_photo(
            library_id=lib_id,
            path=f"M:/photos/{i}.jpg",
            size=1,
            mtime_ns=1,
            width=1,
            height=1,
            face_count=1,
            scan_status="ok",
        )
        photo_ids.append(pid)
        db.replace_faces(
            pid,
            [
                (
                    0,
                    (0.0, 0.0, 1.0, 1.0),
                    0.9,
                    np.full(4, float(i + 1), dtype=np.float32),
                    4,
                    "buffalo_l",
                    "v1",
                )
            ],
        )
    batches = list(db.iter_face_embeddings(batch_size=2))
    # 三张脸，每批 2 -> 共 2 批
    assert len(batches) == 2
    total = sum(len(b) for b in batches)
    assert total == 3
    # 确认维度
    face_id, photo_id, vec = batches[0][0]
    assert vec.shape == (4,)
    assert vec.dtype == np.float32


def test_close_is_idempotent(db_path: Path) -> None:
    from app.core.database import Database

    db = Database(db_path)
    db.close()
    db.close()  # 不报错