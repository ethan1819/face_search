from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


@pytest.fixture()
def db_with_faces(tmp_path: Path):
    from app.core.database import Database

    db = Database(tmp_path / "search.db")
    lib_id = db.upsert_library("M:/photos")
    photo_paths = ["p1", "p2", "p3", "p4"]
    photo_ids = []
    faces_per_photo = [
        # 每个 photo 一张脸，embedding 各异
        [np.array([1.0, 0.0, 0.0], dtype=np.float32)],
        [np.array([0.6, 0.8, 0.0], dtype=np.float32)],  # cosine ≈ 0.6
        [np.array([-1.0, 0.0, 0.0], dtype=np.float32)],
        [np.array([0.0, 1.0, 0.0], dtype=np.float32)],
    ]
    for i, path in enumerate(photo_paths):
        pid = db.upsert_photo(
            library_id=lib_id,
            path=path,
            size=1,
            mtime_ns=i,
            width=10,
            height=10,
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
                    faces_per_photo[i][0],
                    3,
                    "buffalo_l",
                    "v1",
                )
            ],
        )
    return db, photo_ids


def test_search_returns_photos_sorted_by_max_cosine(db_with_faces) -> None:
    from app.core.search_service import SearchService

    db, photo_ids = db_with_faces
    svc = SearchService(db)
    target = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = svc.search(target, threshold=0.5)
    # p1 完全匹配 -> p2 cosine=0.6 -> p4 正交 -> p3 反向
    assert [r.photo_id for r in results] == [photo_ids[0], photo_ids[1]]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(0.6)


def test_search_filters_below_threshold(db_with_faces) -> None:
    from app.core.search_service import SearchService

    db, photo_ids = db_with_faces
    svc = SearchService(db)
    target = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = svc.search(target, threshold=0.99)
    assert [r.photo_id for r in results] == [photo_ids[0]]


def test_search_handles_multi_face_photo(db_with_faces) -> None:
    from app.core.database import Database
    from app.core.search_service import SearchService

    db: Database
    db, photo_ids = db_with_faces
    lib_id = db.upsert_library("M:/photos")
    pid = db.upsert_photo(
        library_id=lib_id,
        path="multi",
        size=1,
        mtime_ns=99,
        width=10,
        height=10,
        face_count=2,
        scan_status="ok",
    )
    db.replace_faces(
        pid,
        [
            (
                0,
                (0.0, 0.0, 1.0, 1.0),
                0.9,
                np.array([-1.0, 0.0, 0.0], dtype=np.float32),
                3,
                "buffalo_l",
                "v1",
            ),
            (
                1,
                (2.0, 2.0, 3.0, 3.0),
                0.9,
                np.array([0.6, 0.8, 0.0], dtype=np.float32),
                3,
                "buffalo_l",
                "v1",
            ),
        ],
    )
    target = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    svc = SearchService(db)
    results = svc.search(target, threshold=0.5)
    # multi: max(face0=-1, face1=0.6) = 0.6 -> 应该返回
    found = next(r for r in results if r.photo_id == pid)
    assert found.score == pytest.approx(0.6)


def test_search_excludes_user_marked_photos(db_with_faces) -> None:
    from app.core.search_service import SearchService

    db, photo_ids = db_with_faces
    db.record_feedback("q", photo_ids[0], "excluded", 1.0)
    svc = SearchService(db)
    target = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = svc.search(target, threshold=0.5, query_id="q")
    assert all(r.photo_id != photo_ids[0] for r in results)


def test_search_empty_target_returns_empty(db_with_faces) -> None:
    from app.core.search_service import SearchService

    db, _ = db_with_faces
    svc = SearchService(db)
    target = np.zeros(3, dtype=np.float32)
    results = svc.search(target, threshold=0.0)
    # 零向量 -> cosine 未定义，按规约返回空
    assert results == []


def test_search_dim_mismatch_returns_empty(db_with_faces) -> None:
    from app.core.search_service import SearchService

    db, _ = db_with_faces
    svc = SearchService(db)
    target = np.array([1.0, 0.0], dtype=np.float32)  # 维度=2
    results = svc.search(target, threshold=0.0)
    assert results == []