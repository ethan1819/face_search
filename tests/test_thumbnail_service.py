from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


def _save_rgb(path: Path, color=(255, 0, 0), size=(800, 600)) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG")


def test_thumbnail_caches_by_path_and_size(tmp_path: Path) -> None:
    from app.core.thumbnail_service import ThumbnailService

    src = tmp_path / "src.jpg"
    _save_rgb(src)
    cache = tmp_path / "cache"
    svc = ThumbnailService(cache)
    out1 = svc.render(str(src), size=(120, 90))
    out2 = svc.render(str(src), size=(120, 90))
    assert out1 == out2
    assert Path(out1).exists()
    img = Image.open(out1)
    assert img.size == (120, 90)


def test_thumbnail_different_size_creates_new_cache(tmp_path: Path) -> None:
    from app.core.thumbnail_service import ThumbnailService

    src = tmp_path / "src.jpg"
    _save_rgb(src)
    cache = tmp_path / "cache"
    svc = ThumbnailService(cache)
    out1 = svc.render(str(src), size=(120, 90))
    out2 = svc.render(str(src), size=(240, 180))
    assert out1 != out2
    assert Path(out2).exists()


def test_thumbnail_returns_none_for_missing(tmp_path: Path) -> None:
    from app.core.thumbnail_service import ThumbnailService

    svc = ThumbnailService(tmp_path / "cache")
    assert svc.render(str(tmp_path / "missing.jpg")) is None