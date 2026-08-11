from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray


class InsightFaceApp(Protocol):
    def get(self, image: NDArray[np.uint8]) -> list[Any]: ...


@dataclass(frozen=True, slots=True)
class DetectedFace:
    bbox: tuple[float, float, float, float]
    embedding: NDArray[np.float32]
    detection_score: float


class FaceEngine:
    """InsightFace 的轻量封装，业务层不直接依赖第三方对象。"""

    def __init__(self, app: InsightFaceApp):
        self._app = app

    def extract(self, image: NDArray[np.uint8] | None) -> list[DetectedFace]:
        if image is None or image.size == 0:
            raise ValueError("图像为空")

        result: list[DetectedFace] = []
        for face in self._app.get(image):
            vector = np.asarray(face.normed_embedding, dtype=np.float32)
            norm = float(np.linalg.norm(vector))
            if norm <= 1e-12:
                raise ValueError("人脸特征是零向量")
            normalized = vector / norm
            bbox = tuple(float(value) for value in face.bbox)
            result.append(
                DetectedFace(
                    bbox=bbox,
                    embedding=normalized,
                    detection_score=float(face.det_score),
                )
            )
        return result
