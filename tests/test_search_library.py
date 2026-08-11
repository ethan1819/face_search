"""Search service must respect library_id filter and surface excluded photos."""
from __future__ import annotations

from pathlib import Path

import numpy as np


def _face_vec(value: float) -> np.ndarray:
    return np.asarray([value, 0.0, 0.0, 0.0], dtype=np.float32)


def test_search_filters_by_library_id(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.search_service import SearchService

    db = Database(tmp_path / "lib.db")
    a = db.upsert_library("M:/a")
    b = db.upsert_library("M:/b")
    pa = db.upsert_photo(library_id=a, path="M:/a/p.jpg", size=1, mtime_ns=1, width=10, height=10, face_count=1, scan_status="ok")
    pb = db.upsert_photo(library_id=b, path="M:/b/p.jpg", size=1, mtime_ns=1, width=10, height=10, face_count=1, scan_status="ok")
    for pid in (pa, pb):
        db.replace_faces(pid, [(0, (0.0, 0.0, 10.0, 10.0), 0.9, _face_vec(1.0), 4, "buffalo_l", "v1")])
    db.close()

    db = Database(tmp_path / "lib.db")
    service_a = SearchService(db, library_id=a)
    hits_a = service_a.search(_face_vec(1.0), threshold=0.5)
    assert [h.photo_id for h in hits_a] == [pa]

    service_b = SearchService(db, library_id=b)
    hits_b = service_b.search(_face_vec(1.0), threshold=0.5)
    assert [h.photo_id for h in hits_b] == [pb]
    db.close()


def test_search_respects_excluded_feedback(tmp_path: Path) -> None:
    from app.core.database import Database
    from app.core.search_service import SearchService

    db = Database(tmp_path / "lib.db")
    a = db.upsert_library("M:/a")
    p = db.upsert_photo(library_id=a, path="M:/a/p.jpg", size=1, mtime_ns=1, width=10, height=10, face_count=1, scan_status="ok")
    db.replace_faces(p, [(0, (0.0, 0.0, 10.0, 10.0), 0.9, _face_vec(1.0), 4, "buffalo_l", "v1")])
    db.record_feedback("q1", p, "excluded", 0.9)
    db.close()

    db = Database(tmp_path / "lib.db")
    hits = SearchService(db, library_id=a).search(_face_vec(1.0), threshold=0.5, query_id="q1")
    db.close()
    assert hits == []
