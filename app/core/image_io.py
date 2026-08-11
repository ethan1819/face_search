"""Windows 安全图像加载与扫描辅助。中文路径一律走 np.fromfile + cv2.imdecode 或 Pillow 兜底。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, UnidentifiedImageError


_SUPPORTED = {".jpg", ".jpeg", ".png"}


def is_supported_extension(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _SUPPORTED


def load_image_bgr(path: str | Path) -> NDArray[np.uint8] | None:
    """以 BGR uint8 加载图像。失败/缺失返回 None。优先 cv2（性能），失败回退 Pillow。"""
    p = Path(path)
    try:
        if not p.exists():
            return None
    except OSError:
        return None

    try:
        data = np.fromfile(str(p), dtype=np.uint8)
        if data.size == 0:
            return None
        buf = np.asarray(data)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is not None:
            return img
    except (OSError, ValueError):
        pass

    # Pillow 兜底（覆盖某些 cv2 不认的 JPEG 子集）
    try:
        with Image.open(p) as pil_img:
            pil_img = pil_img.convert("RGB")
            arr = np.asarray(pil_img, dtype=np.uint8)
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def iter_image_files(root: str | Path) -> Iterator[Path]:
    """递归遍历 root 下所有支持的图像文件，顺序按 path 排序。"""
    base = Path(root)
    if not base.exists():
        return
    for p in sorted(base.rglob("*")):
        if p.is_file() and is_supported_extension(p):
            yield p