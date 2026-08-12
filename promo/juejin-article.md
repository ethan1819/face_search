# 掘金 / 少数派 深度文大纲

**建议标题**：我用 Python 写了一个完全本地的人脸照片检索（InsightFace + PySide6）
**副标题**：源码、踩坑、与商业部署前必须知道的事

**目标字数**：2500–3500 字（中文）
**预计阅读时间**：12 分钟

---

## 一、为什么做这个（动机）

- 2021 年 Apple CSAM 扫描事件之后，对「云端人脸识别」不信任
- 我家有 1 万多张照片需要按人脸整理，商业工具都要传云
- 开源方案要么是 CLI 没有 GUI，要么踩中文路径坑，要么没增量扫描

→ 「我需要的是一个 100% 本地、源照片只读、能用鼠标点点选目标脸然后帮我找」的工具

## 二、技术选型（为什么是这套）

| 组件 | 候选 | 我选它的原因 |
|---|---|---|
| 人脸检测 + 特征 | face_recognition / InsightFace / CompreFace | InsightFace 检测 + 识别一体；512 维 embedding 在 90 张人脸的库上召回率明显更高 |
| GUI | PySide6 / Tkinter / Web (Flask + 浏览器) | PySide6 原生桌面、Qt 的 QThread 处理后台不会阻塞 UI |
| 推理 | onnxruntime / onnxruntime-gpu / TensorRT | ORT 自动选 provider，CUDA 初始化失败静默回退 CPU |
| 存储 | SQLite / PostgreSQL / DuckDB | 本地单文件，10 万张脸还撑得住，再大再考虑 FAISS |
| 包管理 | pip / poetry / uv | uv 速度快、锁文件可靠 |

## 三、关键设计决策（以及踩过的坑）

### 1. 每张照片取最大相似度，不是 top-K 脸

```python
# app/core/search_service.py 简化版
def score_per_photo(query_emb, all_face_embs, photo_ids):
    sims = query_emb @ all_face_embs.T          # (1, N)
    max_per_photo = scatter_max(sims, photo_ids)  # 按 photo_id 取 max
    return list(zip(photo_ids, max_per_photo))
```

**为什么**：用户的问题是「这张照片里有没有这个人」，不是「这张照片里最像这个人的是哪张脸」。取 max 是直接对应业务语义的。

### 2. 增量键 = (path, size, mtime_ns)

```sql
SELECT id FROM photos WHERE path = ? AND size = ? AND mtime_ns = ?
```

比 content_hash 快得多（不用读文件），且对绝大多数场景足够准确。改算法时可以加 `content_hash` 列做兜底。

### 3. 中文路径必须绕过 cv2.imread

`cv2.imread(''C:\Users\张三\照片.jpg'')` 在 Windows 下会读失败——cv2 内部用窄字符 API。

正确做法：

```python
img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
```

### 4. 阈值不能拍脑袋

README 默认 0.55 / 0.35 是我的家用照片校准的，但**这跟你家不一样**。UI 暴露滑块让你自己调；保存到 `search_feedback` 表里方便后续用 KMeans 自动校准。

## 四、InsightFace 模型商用限制（重要！）

很多人忽略这一段。InsightFace 源代码 MIT，但**自动下载的 buffalo_l 模型权重是非商用研究许可**。代码随便用，模型不行。

商业上线前必须：

1. 拿 InsightFace / buffalo_l 商业授权
2. 或者换成明确允许商用的 ONNX 检测 / 识别模型
3. 或者自训并保留训练数据授权证据

我们用 `model_name` + `model_version` 两列在 `faces` 表里记账，换模型后能干净重建索引。

## 五、性能：我的家用机数据

| 数据量 | CPU (i7-12700) | GPU (RTX 3060) |
|---|---|---|
| 扫 2,890 张照片（建索引） | 12 分钟 | 35 秒 |
| 单次检索（89 张脸） | 80 ms | 5 ms |
| 增量扫描（50 张新照片） | 30 秒 | 2 秒 |

## 六、CI / 工程化那些事

- 43 个 pytest，覆盖数据库 / 扫描 / 检索 / 导出 / GUI 烟雾 / 缩略图线程
- GitHub Actions 跑 Ubuntu + Windows × Python 3.11 + 3.12 共 4 个 job
- Dependabot 周更依赖（按 python-core / inference / gui 分组）
- 隐私：默认图库路径是 `Path.home() / "Pictures"`，**没有任何个人信息**

## 七、开源协议

代码 MIT，模型注意 InsightFace 的限制。Issue 模板 / SECURITY.md / Contributor Covenant 都齐了，欢迎 PR。

## 八、源码

https://github.com/ethan1819/face_search

```bash
git clone https://github.com/ethan1819/face_search.git
cd face_search
uv venv --python 3.12
uv pip install -p .venv\Scripts\python.exe -r requirements.txt
start.bat
```

---

**觉得有帮助的话点 ⭐**：https://github.com/ethan1819/face_search
