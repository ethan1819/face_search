# awesome-* PR 提交文本（4 个目标）

## 1. awesome-face-recognition
- 目标仓库：https://github.com/aneeshneduvana/awesome-face-recognition
- 提 PR 到 `main` 分支
- 提议加的章节：**Open-source Face Recognition Apps** 或 **Desktop Apps**
- 建议位置：在 README.md 里加一行，按字母序排列

### PR title

```
Add local-face-photo-search to Open-source Face Recognition Apps
```

### PR body

```markdown
Adding [local-face-photo-search](https://github.com/ethan1819/face_search)
to the **Open-source Face Recognition Apps** section.

- 100% local — no photo data ever leaves the user''s machine
- PySide6 GUI with reference photo picker + multi-face selector
- InsightFace + ONNX Runtime (auto CUDA / CPU)
- SQLite index with incremental `(path, size, mtime_ns)` keying
- 43 pytest tests, CI on Windows + Linux × Python 3.11 + 3.12
- MIT-licensed code (note: InsightFace `buffalo_l` model is non-commercial research only)

Placed in the **Desktop Apps** subsection in alphabetical order.
```

### 复制的链接行（参考格式）

```markdown
- [local-face-photo-search](https://github.com/ethan1819/face_search) — 100% local desktop face photo search (PySide6 + InsightFace).
```

---

## 2. awesome-pyside6 (或类似 Qt for Python 列表)
- 候选仓库：
  - https://github.com/sergeevpasha/awesome-pyside6
  - https://github.com/search?q=awesome-pyside6&type=repositories
- 如果没有现成 awesome list，**跳过**这个 channel
- 提议加的章节：**Applications** / **Desktop Apps**

### PR title

```
Add local-face-photo-search
```

### PR body

```markdown
Adding [local-face-photo-search](https://github.com/ethan1819/face_search)
to the Applications section. A practical PySide6 desktop app for
face-photo search — useful as a real-world example beyond demos.
```

---

## 3. awesome-privacy (or privacytools)
- 候选仓库：https://github.com/KevinColemanInc/awesome-privacy
- 提议加的章节：**Photo & Video** 或 **Local-first Software**

### PR title

```
Add local-face-photo-search to Local-first Software
```

### PR body

```markdown
Adding [local-face-photo-search](https://github.com/ethan1819/face_search)
— a 100% on-device face photo search tool. No photos, embeddings, or
query results ever leave the user''s machine. Useful for anyone who
wants face-photo organisation without trusting cloud providers.
```

---

## 4. awesome-self-hosted (或类似自托管列表)
- 候选仓库：https://github.com/awesome-selfhosted/awesome-selfhosted
- 注：这是 desktop app，可能不太契合。**可选**

---

## 提交步骤

```bash
# 1. fork 目标 repo
# 2. 在 fork 里编辑 README.md（找对应章节，按字母序加一行）
# 3. commit + push
git checkout -b add-local-face-photo-search
# 编辑 README.md 加一行
git add README.md
git commit -m "Add local-face-photo-search"
git push origin add-local-face-photo-search
# 4. 在 GitHub 网页点 "Compare & pull request"
```

**预计收益**：每个 PR 进来 5-30 star。4 个全提大概 2 周内能增 30-100 star。

---

## PR 提交模板（GitHub 网页界面粘贴）

**Title**: 上面每个 PR 都有

**Body**:

```
<!-- Please make sure you''ve read the contributing guidelines before opening a PR. -->

## What''s being added
- Repo: https://github.com/ethan1819/face_search
- Section: Open-source Face Recognition Apps / Desktop Apps

## Why it fits
- 100% on-device face photo search
- PySide6 GUI + InsightFace + ONNX Runtime
- MIT-licensed code, 43 passing pytest, CI on 4 OS/Python combos
- No upload, source photos are read-only

## Checklist
- [x] Repo is open-source
- [x] Repo has a license
- [x] Repo has a README
- [x] Project is actively maintained (latest commit < 30 days)
- [x] Entry is in alphabetical order
```
