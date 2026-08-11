from __future__ import annotations

import numpy as np
import pytest


class FakeFace:
    def __init__(self, bbox, embedding, det_score=0.99):
        self.bbox = np.asarray(bbox, dtype=np.float32)
        self.normed_embedding = np.asarray(embedding, dtype=np.float32)
        self.det_score = det_score


class FakeInsightApp:
    def __init__(self, faces):
        self.faces = faces

    def get(self, image):
        assert image.shape == (8, 12, 3)
        return self.faces


def test_extracts_all_faces_and_normalizes_embeddings():
    from app.core.face_engine import FaceEngine

    app = FakeInsightApp([
        FakeFace([1, 2, 5, 7], [3.0, 4.0]),
        FakeFace([6, 1, 10, 6], [0.0, 2.0]),
    ])
    engine = FaceEngine(app)

    faces = engine.extract(np.zeros((8, 12, 3), dtype=np.uint8))

    assert len(faces) == 2
    assert faces[0].bbox == (1.0, 2.0, 5.0, 7.0)
    np.testing.assert_allclose(faces[0].embedding, [0.6, 0.8])
    np.testing.assert_allclose(faces[1].embedding, [0.0, 1.0])


def test_rejects_empty_image():
    from app.core.face_engine import FaceEngine

    with pytest.raises(ValueError, match="图像为空"):
        FaceEngine(FakeInsightApp([])).extract(None)


def test_rejects_zero_length_embedding():
    from app.core.face_engine import FaceEngine

    app = FakeInsightApp([FakeFace([1, 2, 5, 7], [0.0, 0.0])])
    with pytest.raises(ValueError, match="零向量"):
        FaceEngine(app).extract(np.zeros((8, 12, 3), dtype=np.uint8))
