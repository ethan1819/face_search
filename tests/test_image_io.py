from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image


def _save_rgb(path: Path, color=(255, 128, 64), size=(40, 30)) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG")


def test_load_image_supports_unicode_path(tmp_path: Path) -> None:
    from app.core.image_io import load_image_bgr

    p = tmp_path / "中文 测试 1.jpg"
    _save_rgb(p)
    img = load_image_bgr(p)
    assert isinstance(img, np.ndarray)
    assert img.shape == (30, 40, 3)
    assert img.dtype == np.uint8


def test_load_image_returns_none_for_corrupt_file(tmp_path: Path) -> None:
    from app.core.image_io import load_image_bgr

    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"not a real jpeg \x00\x01\x02")
    assert load_image_bgr(bad) is None


def test_load_image_returns_none_for_missing_file(tmp_path: Path) -> None:
    from app.core.image_io import load_image_bgr

    assert load_image_bgr(tmp_path / "missing.jpg") is None


def test_load_image_supports_png(tmp_path: Path) -> None:
    from app.core.image_io import load_image_bgr

    p = tmp_path / "图.png"
    Image.new("RGB", (16, 12), (10, 20, 30)).save(p, format="PNG")
    img = load_image_bgr(p)
    assert img is not None
    assert img.shape == (12, 16, 3)


def test_is_supported_extension() -> None:
    from app.core.image_io import is_supported_extension

    assert is_supported_extension("a.JPG")
    assert is_supported_extension("a.jpeg")
    assert is_supported_extension("a.png")
    assert is_supported_extension("中文.JPG")
    assert not is_supported_extension("a.heic")
    assert not is_supported_extension("a.txt")


def test_iter_image_files_yields_paths(tmp_path: Path) -> None:
    from app.core.image_io import iter_image_files

    (tmp_path / "sub").mkdir()
    _save_rgb(tmp_path / "a.jpg")
    _save_rgb(tmp_path / "b.jpeg")
    _save_rgb(tmp_path / "sub" / "c.png")
    (tmp_path / "ignore.txt").write_text("no")
    paths = list(iter_image_files(tmp_path))
    names = sorted(p.name for p in paths)
    assert names == ["a.jpg", "b.jpeg", "c.png"]