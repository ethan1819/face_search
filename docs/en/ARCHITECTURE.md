# Local Face Photo Search — Architecture

> English edition. For the bilingual Chinese/English version see [../ARCHITECTURE.md](../ARCHITECTURE.md).
> For the project overview see [README.md](README.md).

## 1. MVP scope

Phase 1 validates exactly one end-to-end chain:

```
reference photo → detect all faces → pick the target face
              → scan one photo folder → detect all faces per photo
              → rank photos by max cosine similarity to target
              → return the whole photo
```

Explicitly **out of scope** for MVP: HEIC, ANN vector index, installers,
multi-library management, complex permissions. SQLite indexing and the
PySide6 UI are layered on after the core chain works.

## 2. Tech choices

| Component | Choice | Why |
|---|---|---|
| Python | 3.11 | Compatible with PySide6, ONNX Runtime, OpenCV. |
| GUI | PySide6 | Native Windows desktop; `QThread` for background work. |
| Face engine | InsightFace `FaceAnalysis` | Unified detection, landmarks, alignment, 512-dim embeddings. |
| Inference | ONNX Runtime | `CPUExecutionProvider` by default; `CUDAExecutionProvider` if available, falls back to CPU on failure. |
| Image IO | OpenCV + Pillow | Chinese-path safe via `Pillow` and `np.fromfile + cv2.imdecode` to avoid `cv2.imread` Unicode bugs. |
| Storage | SQLite WAL | Photos / faces / scan failures / feedback in separate tables. |
| Math | NumPy | L2 normalisation + batched cosine similarity. |
| Tests | pytest | Unit, database, incremental scan, integration. |
| Logging | structlog / stdlib logging | Rotating logs + failure file list. |
| Packaging | PyInstaller (Windows) | Model stays as an external dir, not stuffed into a single-file exe. |

## 3. Layered architecture

```
PySide6 UI
  ├─ Reference photo + face picker
  ├─ Library + scan progress
  └─ Results, confirm, exclude, copy
          ↓ signals/slots
Background workers
  ├─ ScanWorker      enumerate, incrementality, detect, store
  ├─ SearchWorker    batch compare target vs index
  └─ ThumbnailWorker async thumbnails
          ↓
Core services
  ├─ FaceEngine      InsightFace / ORT provider wrapper (injectable interface)
  ├─ LibraryScanner  bad-file isolation, resumable
  ├─ SearchService   max(face scores) per photo
  └─ ExportService   copy-only, never modifies sources
          ↓
SQLite repo + local FS (source photos read-only)
```

`FaceEngine` is injected via an interface, so business tests use a fake engine;
only the model-integration tests load the real InsightFace (avoiding model
downloads on every test run).

## 4. Database design

### `libraries`
- `id`, `root_path` (unique), `created_at`, `last_scan_at`

### `photos`
- `id`, `library_id`, `path` (unique), `size`, `mtime_ns`, `content_hash` (optional, lazily computed)
- `width`, `height`, `face_count`, `scan_status`, `error_message`
- `indexed_at`, `updated_at`

Incremental key: `(path, size, mtime_ns)`. Skip when unchanged; on change,
delete old `faces` rows and re-extract within one transaction. After a scan,
records not seen this round are marked `missing` without touching the source files.

### `faces`
- `id`, `photo_id`, `face_index`
- `bbox_x1/y1/x2/y2`, `det_score`
- `embedding BLOB` (float32, 512-dim, L2-normalised)
- `embedding_dim`, `model_name`, `model_version`

Index: `photo_id`; each photo allows 0..N faces.

### `scan_failures`
- `id`, `photo_path`, `stage`, `exception_type`, `message`, `occurred_at`, `resolved_at`

### `search_feedback`
- `id`, `query_id`, `photo_id`, `decision` (confirmed/excluded), `score`, `created_at`

## 5. Search & thresholds

1. Detect all faces in the reference image. 0 → prompt to change; 1 → auto-pick; N → show face crops.
2. Normalise the target embedding.
3. Load embeddings in batches (e.g. 20k faces per batch), compute dot products.
4. Aggregate by `photo_id`, keep the maximum score; any match on a photo returns the whole photo.
5. Initial intervals are **defaults only** — calibrate with your own photos:
   - **High confidence**: `score >= 0.55`
   - **Manual review**: `0.35 <= score < 0.55`
   - **Hidden**: `score < 0.35`
6. The UI lets the user move the thresholds; confirm / exclude decisions never modify source photos.

## 6. Performance

- 10k–100k photos: SQLite-only is fine for v1; FAISS not urgent.
- Per-face storage is 2 KB (512 × 4); 100k faces ≈ 195 MiB raw vectors — SQLite handles that comfortably.
- Single model session + background worker; GPU can batch-infer; CPU prioritises stability.
- Per-photo transaction commits; a process crash loses at most the in-flight photo.
- WAL, `busy_timeout`, batched inserts; the UI thread does not hold the scan connection.
- Thumbnails live in a separate cache keyed by path + mtime; originals are never modified.
- Introduce FAISS / HNSW only past hundreds of thousands of faces; SQLite remains the source of truth, the vector index is a rebuildable cache.

## 7. Stability & privacy

- 100% offline inference. No photo upload. First-time model download can be done at install time so runtime is offline.
- Per-photo try/except; bad files go to `scan_failures` and scanning continues.
- Source photos are opened read-only. Copying writes only to the destination, with safe-name suffixes on collisions.
- Cancellation checked between photos.
- Rotating logs in `data/logs/app.log`; failure list CSV-exportable.
- SQLite backups + versioned schema migrations.

## 8. Model licensing

InsightFace **source code** is MIT, but the auto-downloaded pre-trained weights
(including `buffalo_l`) are restricted to **non-commercial research**.

For commercial deployment you must:

1. Obtain a commercial model license, **or**
2. Swap in a detector / recogniser ONNX model that is explicitly commercially licensed, **or**
3. Train your own with documented authorisation.

The model layer is decoupled from the business layer; every face row records
`model_name` and `model_version` so you can rebuild the index after a model swap.
**Do not** ship this app commercially without completing one of those three steps.

## 9. Eight-phase delivery

1. Architecture, deps, licensing boundaries (this document).
2. Minimal detection / embedding CLI + real-model smoke.
3. Folder scan, SQLite schema, all-faces ingest, bad-file isolation.
4. Reference face picker + per-photo max search.
5. PySide6 main window, background workers, progress & cancel.
6. Thumbnails, open-original / open-folder, confirm / exclude / copy.
7. Incremental scan, resume, batched compute, logs, threshold calibration.
8. Unit / integration / UI tests, README, CPU/CUDA install scripts, PyInstaller packaging.
