"""Real-model smoke test for the face engine.

Run after the dev environment is installed:

    # PowerShell
    $env:LOCAL_FACE_PHOTO_LIBRARY = "D:\\photos\\family"
    .venv\\Scripts\\python.exe scripts\\real_model_smoke.py

    # bash
    LOCAL_FACE_PHOTO_LIBRARY=/data/photos python scripts/real_model_smoke.py

No default library path is provided on purpose so this script never picks up
a personal folder by accident.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from app.core.face_engine import FaceEngine
from app.core.image_io import load_image_bgr
from app.core.model_factory import FaceAnalysisFactory

ROOT = Path(os.environ.get("LOCAL_FACE_PHOTO_LIBRARY", "") or ".")
if not str(ROOT) or not ROOT.exists():
    sys.stderr.write(
        "Set LOCAL_FACE_PHOTO_LIBRARY to a folder that contains .jpg/.jpeg/.png photos.\n"
    )
    raise SystemExit(2)

extensions = {".jpg", ".jpeg", ".png"}
paths = [path for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in extensions][:3]
if not paths:
    sys.stderr.write(f"No .jpg/.jpeg/.png images found under {ROOT}\n")
    raise SystemExit(3)

factory = FaceAnalysisFactory()
engine = FaceEngine(factory.create())
print("provider:", factory.info)
for path in paths:
    image = load_image_bgr(str(path))
    faces = engine.extract(image)
    dims = sorted({int(face.embedding.size) for face in faces})
    print(f"{path} | faces={len(faces)} | embedding_dims={dims}")
