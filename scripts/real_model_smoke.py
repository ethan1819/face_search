from __future__ import annotations

from pathlib import Path

from app.core.face_engine import FaceEngine
from app.core.image_io import load_image_bgr
from app.core.model_factory import FaceAnalysisFactory

ROOT = Path(r"M:\1A 尹成毅\724大会资料")
extensions = {".jpg", ".jpeg", ".png"}
paths = [path for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in extensions][:3]

factory = FaceAnalysisFactory()
engine = FaceEngine(factory.create())
print("provider:", factory.info)
for path in paths:
    image = load_image_bgr(str(path))
    faces = engine.extract(image)
    dims = sorted({int(face.embedding.size) for face in faces})
    print(f"{path} | faces={len(faces)} | embedding_dims={dims}")
