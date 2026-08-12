# dev.to / Hashnode — English long-form article

**Title**: Building a 100% Local Face Photo Search with InsightFace + PySide6
**Tags**: python, pyside6, insightface, privacy, open-source, face-recognition
**Estimated length**: ~1800 words / 10 min read

---

After Apple''s CSAM-scanning controversy in 2021, I wanted to organise my own
family photos by face without uploading them anywhere. None of the cloud
options felt right, and the existing on-device tools had rough edges — Chinese
path bugs, no incremental scan, no GUI. So I built
[Local Face Photo Search](https://github.com/ethan1819/face_search).

This is what I learned along the way.

## What it does

Pick a reference photo, select the target face, and the app scans your local
library. Photos are ranked by the maximum face cosine similarity against your
target embedding. Source photos are read-only — nothing is uploaded, modified,
or deleted.

## Stack

| Component | Choice | Why |
|---|---|---|
| Face detection + embedding | InsightFace `FaceAnalysis` (buffalo_l) | Detection + recognition in one model; 512-dim embeddings |
| GUI | PySide6 | Native desktop; `QThread` for background work that doesn''t block UI |
| Inference | ONNX Runtime | `CUDAExecutionProvider` if available, silent fallback to CPU |
| Storage | SQLite (WAL) | Single file; 100k faces still OK; FAISS later if needed |
| Packaging | uv | Fast, deterministic lock file |

## Key design decisions

### 1. Per-photo max score, not top-K faces

The question is "does this photo contain this person", not "which face in
this photo is the closest match". So I aggregate by `photo_id` and keep the
maximum similarity score:

```python
sims = query_emb @ all_face_embs.T          # (1, N)
max_per_photo = scatter_max(sims, photo_ids)
return list(zip(photo_ids, max_per_photo))
```

This directly matches user intent and avoids needing to explain why the
result table shows a photo where the top face is someone else.

### 2. Incremental key = (path, size, mtime_ns)

```sql
SELECT id FROM photos WHERE path = ? AND size = ? AND mtime_ns = ?
```

Much faster than a content hash (no file read), and good enough for normal
photo-library use. A `content_hash` column is reserved for when you need
stronger guarantees.

### 3. Chinese paths need a `cv2.imdecode` workaround

`cv2.imread(''C:\Users\张三\照片.jpg'')` silently fails on Windows — cv2 uses
narrow-char APIs internally. The fix is to read the bytes yourself:

```python
img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
```

Or use Pillow. The project uses the cv2 path because the rest of the
pipeline already depends on OpenCV.

### 4. Thresholds aren''t one-size-fits-all

The README defaults (0.55 / 0.35) are calibrated against my own photos. Your
library will differ. The UI exposes the sliders and saves feedback to a
`search_feedback` table so you can later run KMeans to auto-calibrate.

## The InsightFace commercial-license gotcha

This is the one thing I want every reader to walk away with:

> **InsightFace''s source is MIT, but the auto-downloaded pre-trained weights
> (including `buffalo_l`) are restricted to non-commercial research.**

The code is free, but the model isn''t. For commercial deployment you must:

1. Obtain a commercial InsightFace / buffalo_l license, **or**
2. Swap in a commercially-licensed ONNX detector / recogniser, **or**
3. Train your own with documented authorisation.

Every `faces` row records `model_name` and `model_version`, so you can
rebuild the index after a model swap. **Do not** ship this app commercially
without completing one of those three steps.

## Performance

Tested on a Windows machine with i7-12700 + RTX 3060:

| Workload | CPU | GPU |
|---|---|---|
| Scan 2,890 photos (initial index) | 12 min | 35 s |
| One search across 89 faces | 80 ms | 5 ms |
| Incremental scan (50 new photos) | 30 s | 2 s |

GPU mode is enabled automatically when `CUDAExecutionProvider` is
available; CUDA init failure silently falls back to CPU.

## CI and engineering hygiene

- 43 pytest tests covering database, scanner, search, export, GUI smoke,
  thumbnail thread
- GitHub Actions on Ubuntu + Windows × Python 3.11 + 3.12 (4 jobs)
- Dependabot weekly updates grouped by python-core / inference / gui
- No personal data committed (the default library is `Path.home() / "Pictures"`)

## Install

```bash
git clone https://github.com/ethan1819/face_search.git
cd face_search
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
start.bat
```

MIT-licensed code; remember the InsightFace caveat above.

If you found this useful, a star on GitHub helps:
https://github.com/ethan1819/face_search
