"""导出服务：把确认的照片复制到目标目录；源照片保持不变；同名安全命名。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence


class ExportService:
    def export(self, source_paths: Sequence[str], destination: str | Path) -> list[Path]:
        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for raw in source_paths:
            src = Path(raw)
            if not src.exists():
                continue
            target = self._unique(dest / src.name)
            shutil.copyfile(src, target)
            written.append(target)
        return written

    def _unique(self, candidate: Path) -> Path:
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        parent = candidate.parent
        i = 2
        while True:
            alt = parent / f"{stem}_{i}{suffix}"
            if not alt.exists():
                return alt
            i += 1