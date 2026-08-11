from __future__ import annotations

from pathlib import Path

import pytest


def test_export_copies_files_with_unique_names(tmp_path: Path) -> None:
    from app.core.export_service import ExportService

    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    (src_dir / "a.jpg").write_bytes(b"a")
    (src_dir / "b.jpg").write_bytes(b"b")

    svc = ExportService()
    written = svc.export(
        [str(src_dir / "a.jpg"), str(src_dir / "b.jpg"), str(src_dir / "a.jpg")],
        dst_dir,
    )
    assert (dst_dir / "a.jpg").read_bytes() == b"a"
    assert (dst_dir / "b.jpg").read_bytes() == b"b"
    # 重复出现 a.jpg，自动追加 _2
    assert (dst_dir / "a_2.jpg").read_bytes() == b"a"
    assert len(written) == 3


def test_export_creates_missing_destination(tmp_path: Path) -> None:
    from app.core.export_service import ExportService

    src = tmp_path / "x.jpg"
    src.write_bytes(b"x")
    dst = tmp_path / "new" / "sub"
    svc = ExportService()
    svc.export([str(src)], dst)
    assert (dst / "x.jpg").exists()


def test_export_keeps_source_read_only(tmp_path: Path) -> None:
    from app.core.export_service import ExportService

    src = tmp_path / "x.jpg"
    src.write_bytes(b"orig")
    original = src.read_bytes()
    svc = ExportService()
    svc.export([str(src)], tmp_path / "dst")
    assert src.read_bytes() == original