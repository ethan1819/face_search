"""人脸搜索服务：按 photo_id 聚合最大余弦相似度，按阈值过滤，可应用用户反馈。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .database import Database


@dataclass(frozen=True, slots=True)
class SearchHit:
    photo_id: int
    photo_path: str
    score: float


class SearchService:
    """线性扫描 SQLite 中的人脸特征，按 photo 取最大 cosine 排序。"""

    def __init__(self, db: Database, batch_size: int = 20000, library_id: int | None = None) -> None:
        self._db = db
        self._batch_size = batch_size
        self._library_id = library_id

    def search(
        self,
        target: NDArray[np.float32],
        *,
        threshold: float,
        limit: int = 200,
        query_id: str | None = None,
    ) -> list[SearchHit]:
        if target.size == 0:
            return []
        target = np.asarray(target, dtype=np.float32)
        norm = float(np.linalg.norm(target))
        if norm <= 1e-12:
            return []
        target = target / norm
        target_dim = int(target.shape[0])

        best_by_photo: dict[int, float] = {}
        excluded: set[int] = set()
        if query_id is not None:
            decisions = self._db.get_feedback_decisions(query_id)
            excluded = {pid for pid, d in decisions.items() if d == "excluded"}

        photo_paths = self._load_photo_paths(library_id=self._library_id)
        for batch in self._db.iter_face_embeddings(
            batch_size=self._batch_size, library_id=self._library_id
        ):
            for face_id, photo_id, vec in batch:
                if int(vec.shape[0]) != target_dim:
                    continue
                # 索引端已 L2 归一化；保险起见重新归一化
                norm = float(np.linalg.norm(vec))
                if norm <= 1e-12:
                    continue
                normed = vec / norm
                score = float(np.dot(target, normed))
                if score < threshold:
                    continue
                prev = best_by_photo.get(photo_id)
                if prev is None or score > prev:
                    best_by_photo[photo_id] = score

        hits: list[SearchHit] = []
        for photo_id, score in best_by_photo.items():
            if photo_id in excluded:
                continue
            path = photo_paths.get(photo_id)
            if path is None:
                continue
            hits.append(SearchHit(photo_id=photo_id, photo_path=path, score=score))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    def _load_photo_paths(self, library_id: int | None = None) -> dict[int, str]:
        with self._db.connection() as conn:
            if library_id is None:
                rows = conn.execute("SELECT id, path FROM photos").fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, path FROM photos WHERE library_id=?", (library_id,)
                ).fetchall()
        return {int(r["id"]): str(r["path"]) for r in rows}