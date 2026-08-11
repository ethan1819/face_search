# Changelog / 更新日志

> 中英双语 · Bilingual edition
>
> Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
> the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-11

### 中文版
#### 新增
- **Local Face Photo Search** MVP 首次公开发布。
- PySide6 桌面 GUI：参考图选择、多脸裁剪挑选、图库扫描、搜索结果按高置信/人工确认分档、确认/排除/复制操作。
- 集成 InsightFace `FaceAnalysis` (buffalo_l)，自动 GPU/CPU provider 切换；CUDA 初始化失败**静默回退** CPU。
- SQLite（WAL 模式）存储：`libraries` / `photos` / `faces` / `scan_failures` / `search_feedback` 五张表，支持并发读写。
- QThread 后台 worker：扫描、检索、缩略图三个独立线程。
- 中文路径安全 IO：通过 Pillow 与 `np.fromfile + cv2.imdecode` 绕过 `cv2.imread` 的 Unicode bug。
- 增量扫描以 `(path, size, mtime_ns)` 为键，支持安全的逐张照片取消。
- **43 项 pytest 测试**覆盖数据库、图像 IO、图库扫描、人脸引擎（mock）、搜索服务、导出服务、GUI 烟雾和缩略图线程。

#### 已知限制
- **InsightFace 预训练模型仅限非商业研究用途**。商业上线前必须取得授权或替换模型，详见 README。
- 暂不支持 HEIC（iPhone 新格式）；后续可加 `pillow-heif`。
- 旧版本 `app/main.py` 里的默认图库曾是 `M:\1A 尹成毅\724大会资料`（个人路径），已通过 git-filter-repo 重写历史彻底抹除；现默认 `Path.home() / "Pictures"`，首次启动后点「选择图库」指定你自己的目录即可。

### English
#### Added
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

#### Known Limitations
- **InsightFace pre-trained models are non-commercial research only.** See
  `README.md` §"License & Model Restrictions" before any production use.
- HEIC (iPhone) is not yet supported.
- An earlier version of `app/main.py` defaulted the library path to a personal
  folder (`M:\1A 尹成毅\724大会资料`). That string has been scrubbed from every
  commit via `git-filter-repo`; the current default is `Path.home() / "Pictures"`
  and the UI lets you point at your own folder via "选择图库" on first run.

[0.1.0]: https://github.com/ethan1819/face_search/releases/tag/v0.1.0
