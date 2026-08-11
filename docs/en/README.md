# Local Face Photo Search

> 100% local face photo search. Your photos never leave your machine.
> PySide6 desktop GUI + InsightFace embeddings.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](../pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](#)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blueviolet.svg)](../.github/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-43%20passed-success.svg)](#verification)

**Other languages**: [中文](../README.md) · [Architecture (中文)](../ARCHITECTURE.md) · [Architecture (English)](ARCHITECTURE.md)

## What is this

Pick a **reference photo** (with one or more faces), select the target face, and the
app scans your local photo library. Photos are ranked by the **maximum face cosine
similarity** against your target embedding. **Source photos are read-only — nothing
is uploaded, modified, or deleted.**

![screenshot of the local face photo search app — main window with reference photo picker on the left, threshold sliders, scan / search controls, and empty results table on the right; the app is fully local and never uploads photos](../screenshot.png)

## Features

- 🖥️ **PySide6 GUI**: reference picker, multi-face crop selector, background scan with cancel, results split into high-confidence / manual-review
- ⚡ **GPU acceleration**: auto-detects `CUDAExecutionProvider`; CUDA init failure **silently falls back** to CPU
- 📂 **Incremental indexing**: skip unchanged photos via `(path, size, mtime_ns)`; crash-resumable
- 🛡️ **Bad-file isolation**: a single corrupt photo does not stop a scan; it is logged to `scan_failures`
- 🈶 **Chinese-path-safe**: `Pillow` + `np.fromfile + cv2.imdecode` works around `cv2.imread`'s Unicode bug
- 💾 **SQLite WAL**: UI and background readers/writers don't block each other; 100k-face scale does not yet need FAISS
- 🧪 **43 pytest tests**: database, scanning, search, export, GUI smoke, thumbnail thread — full coverage

## Install

> Requires Python **3.11 or 3.12**. Works on Windows and Linux.

```bat
git clone https://github.com/ethan1819/face_search.git
cd face_search

uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

start.bat          :: Windows: launches the GUI
```

On first launch, if `buffalo_l` is not cached, InsightFace will auto-download
about **300 MB** of model weights into `~/.insightface/models/`. A failed
download shows an explicit error and writes to `data/logs/app.log`.

### Optional GPU

```bat
uv pip uninstall onnxruntime
uv pip install --python .venv\Scripts\python.exe "onnxruntime-gpu>=1.18,<2"
```

⚠️ **Don't keep both** `onnxruntime` and `onnxruntime-gpu` installed at the
same time — they share the same import name and will conflict. The
verification snippet below tells you which provider is active.

## Usage

1. Double-click `start.bat`. The default library is `Path.home() / "Pictures"`
   (click **"选择图库"** in the UI to point at your real library).
2. Click **"选择参考照片"** — when multiple faces are detected, click the target person.
3. Click **"扫描/增量索引"** — runs in a background QThread; cancel anytime.
4. Click **"搜索"** — results are split into **high confidence (≥ 0.55)** and
   **manual review (0.35 – 0.55)**.
5. Thumbnail, open original, open containing folder, confirm / exclude / copy.

The thresholds are starting points; calibrate with your **own** photos.

## Verification

```bat
set PYTHONPATH=
.venv\Scripts\python.exe -m pytest -q
```

43 tests, GUI smoke included (offscreen Qt). The face engine is mocked, so you
don't need to download `buffalo_l` just to run the suite.

Real-model smoke (downloads ~300 MB on first run):

```bat
.venv\Scripts\python.exe scripts\real_model_smoke.py
```

You must set `LOCAL_FACE_PHOTO_LIBRARY` first:

```bat
set LOCAL_FACE_PHOTO_LIBRARY=D:\photos\family
```

## Data layout

| Path | Purpose | Delete impact |
|---|---|---|
| `data/index.db` | SQLite index (photos / faces / failures / feedback) | needs a re-scan |
| `data/thumbnails/` | Thumbnail cache | regenerated |
| `data/logs/app.log` | Rotating logs | none |
| `~/.insightface/models/` | InsightFace models | re-downloaded on first launch |
| Original photo folder | **Read-only** | — |

## ⚠️ License & Model Restrictions

**The code in this repository is MIT licensed** (see [LICENSE](../LICENSE)) —
free to use, modify, and commercially distribute.

**However, the pre-trained InsightFace models (including the auto-downloaded
`buffalo_l`) are NOT automatically licensed for commercial use.** InsightFace
restricts them to **non-commercial research**.

This project is **for local technical validation only**. Before any commercial
deployment you **must**: obtain a commercial InsightFace / buffalo_l license,
swap in a commercially-licensed ONNX model, or train your own with proper
authorization. After a model swap, rebuild the index using `model_name` keys.

## Roadmap

- [ ] HEIC (iPhone) support
- [ ] FAISS / HNSW vector index (hundreds of thousands of faces)
- [ ] Multi-library switching
- [ ] Command-line mode (batch search without GUI)
- [ ] Automatic threshold calibration tool
- [ ] Model migration script (buffalo_l → commercial model)
- [ ] Linux packaging (PyInstaller / AppImage)

## Community

- 🤝 [Code of Conduct](../CODE_OF_CONDUCT.md) — Contributor Covenant v2.1
- 🔒 [Security Policy](../SECURITY.md) — how to report vulnerabilities privately
- 🐛 [Issue templates](../.github/ISSUE_TEMPLATE/) — bug report + feature request
- 📥 [CONTRIBUTING.md](../CONTRIBUTING.md) — dev setup, running tests, PR checklist

## Acknowledgments

- [InsightFace](https://github.com/deepinsight/insightface) — face detection &
  recognition (MIT)
- [ONNX Runtime](https://onnxruntime.ai/) — inference backend
- [PySide6](https://doc.qt.io/qtforpython-6/) — desktop GUI framework
- [OpenCV](https://opencv.org/) / [Pillow](https://pillow.readthedocs.io/) — image IO

## Maintainer

纯简科技 · `aze`
