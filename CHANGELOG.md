# Changelog

All notable changes to **local-face-photo-search** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-11

### Added
- First public release of the **Local Face Photo Search** MVP.
- PySide6 desktop GUI: reference photo picker, multi-face selector, library scanner,
  search results with high-confidence / manual-review thresholds, confirm / exclude / copy.
- InsightFace `FaceAnalysis` (buffalo_l) integration with auto GPU/CPU provider selection
  and silent fallback from CUDA to CPU on initialization failure.
- SQLite (`data/index.db`) with `libraries`, `photos`, `faces`, `scan_failures`,
  `search_feedback` tables and WAL mode for concurrent access.
- QThread-based background workers for scanning, searching, and thumbnail generation.
- Native Chinese path support via `Pillow` + `np.fromfile + cv2.imdecode` (avoids
  `cv2.imread` Unicode bugs on Windows).
- Incremental scanning keyed by `(path, size, mtime_ns)` with safe cancellation
  between photos.
- 43 pytest tests covering database, image IO, library scanner, face engine
  (mocked), search service, export service, GUI smoke, and thumbnail threading.

### Known Limitations
- **InsightFace pre-trained models are non-commercial research only.** See
  `README.md` §"License & Model Restrictions" before any production use.
- HEIC (iPhone) is not yet supported.
- Default library path 空字符串（用户必须点「选择图库」指定） is a personal default;
  click "选择图库" to point at your own photos.

[0.1.0]: https://github.com/ethan1819/face_search/releases/tag/v0.1.0
