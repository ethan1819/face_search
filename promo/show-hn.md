# Hacker News — Show HN post

**Title**: Show HN: Local Face Photo Search – 100% on-device, no upload, MIT

**URL field**: https://github.com/ethan1819/face_search

**Text**:

After Apple''s CSAM-scanning controversy in 2021, I wanted to organise my own
family photos by face without uploading them anywhere. None of the cloud
options felt right, and the existing on-device tools had rough edges
(Chinese-path bugs, no incremental scan, no GUI). So I built this.

What it does:

- Pick a reference photo, select the target face, the app scans your
  local library and ranks photos by max face cosine similarity
- Source photos are read-only — nothing is uploaded, modified, or deleted
- Background scan with cancel; incremental indexing via (path, size, mtime_ns)
- 43 pytest tests, CI on Windows + Linux × Python 3.11 + 3.12, MIT

Stack: Python 3.11+, PySide6, InsightFace (buffalo_l), ONNX Runtime, SQLite.

One caveat I want to be upfront about: InsightFace''s auto-downloaded
pre-trained weights are non-commercial-research only. The code is MIT but
you''ll need to swap the model for commercial use. README has the full
caveat.

Happy to discuss any of the design choices (the per-photo-max scoring,
threshold defaults, Chinese-path workaround, etc.).
