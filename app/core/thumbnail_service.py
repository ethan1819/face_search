"""缩略图服务：缓存到本地目录，按 (path, mtime, size) 作 key；不修改原图。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


class ThumbnailService:
    def __init__(self, cache_dir: str | Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def render(self, source_path: str, size: tuple[int, int] = (200, 200)) -> str | None:
        src = Path(source_path)
        try:
            stat = src.stat()
        except OSError:
            return None
        key = f"{src.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{size[0]}x{size[1]}"
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        out = self._cache_dir / f"{digest}.jpg"
        if out.exists():
            return str(out)
        try:
            with Image.open(src) as img:
                img = img.convert("RGB")
                img.thumbnail(size)
                img.save(out, format="JPEG", quality=80)
        except Exception:
            return None
        return str(out)