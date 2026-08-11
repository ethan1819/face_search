# 本地人脸照片检索系统：技术架构

## 1. MVP 边界

第一阶段只验证一条端到端链路：一张参考照片 → 检测全部人脸 → 选定目标脸 → 扫描一个照片文件夹 → 每张照片检测全部人脸 → 以该照片最高余弦相似度排序并返回整张照片。

MVP 不提前实现：HEIC、ANN 向量索引、安装包、多库管理、复杂权限。SQLite 索引和 PySide6 UI 在核心链路验证后逐步加入。

## 2. 技术选型

- Python 3.11：兼容 PySide6、ONNX Runtime、OpenCV，当前 Windows 主机已安装。
- PySide6：Windows 原生桌面 GUI；`QThreadPool + QRunnable` 或专用 `QThread` 执行扫描，主线程只更新 UI。
- InsightFace `FaceAnalysis`：统一做人脸检测、关键点、对齐和 512 维特征提取。
- ONNX Runtime：默认 `CPUExecutionProvider`；检测到可用 CUDA 时优先 `CUDAExecutionProvider`，失败自动降级 CPU。
- OpenCV + Pillow：图像处理；Windows 中文路径优先 Pillow/`np.fromfile + cv2.imdecode`，避免 `cv2.imread` 中文路径问题。
- SQLite：WAL 模式；照片、脸、扫描失败、用户确认记录分表保存。
- NumPy：特征向量 L2 归一化和余弦相似度批量计算。
- pytest：单元、数据库、增量扫描与集成测试。
- structlog/标准 logging：滚动日志和失败文件记录。
- PyInstaller：Windows 第一版打包；模型作为外部目录，不塞进单文件 exe。

## 3. 分层架构

```text
PySide6 UI
  ├─ 参考图与人脸选择
  ├─ 照片库/扫描进度
  └─ 搜索结果、确认、排除、复制
          ↓ signals/slots
后台 Workers
  ├─ ScanWorker（枚举、增量判断、检测、入库）
  ├─ SearchWorker（目标特征与索引批量比对）
  └─ ThumbnailWorker（异步缩略图）
          ↓
核心服务
  ├─ FaceEngine（InsightFace/ORT provider 封装）
  ├─ LibraryScanner（损坏隔离、断点续扫）
  ├─ SearchService（每张照片 max(face scores)）
  └─ ExportService（只复制，不修改源照片）
          ↓
SQLite Repository + 本地文件系统（源照片只读）
```

FaceEngine 必须作为接口注入，业务测试使用假引擎，模型集成测试才加载真实 InsightFace，避免每个测试下载/加载大模型。

## 4. 数据库设计

### `libraries`
- `id`, `root_path`（唯一）, `created_at`, `last_scan_at`

### `photos`
- `id`, `library_id`, `path`（唯一）, `size`, `mtime_ns`, `content_hash`（可选延迟计算）
- `width`, `height`, `face_count`, `scan_status`, `error_message`
- `indexed_at`, `updated_at`

增量键第一版使用 `(path, size, mtime_ns)`；相同则跳过，变化则事务内删除旧 faces 后重建。扫描结束后，可将本次未见到的记录标为 `missing`，不触碰原文件。

### `faces`
- `id`, `photo_id`, `face_index`
- `bbox_x1/y1/x2/y2`, `det_score`
- `embedding BLOB`（float32、512 维、L2 归一化）
- `embedding_dim`, `model_name`, `model_version`

索引：`photo_id`；每张照片允许 0..N 张脸。

### `scan_failures`
- `id`, `photo_path`, `stage`, `exception_type`, `message`, `occurred_at`, `resolved_at`

### `search_feedback`
- `id`, `query_id`, `photo_id`, `decision`（confirmed/excluded）, `score`, `created_at`

## 5. 搜索与阈值

1. 参考图检测所有脸；0 张则提示换图，1 张自动选，多张显示人脸裁剪供用户选择。
2. 目标 embedding 归一化。
3. 从 SQLite 分批加载 embeddings（例如每批 20,000 张脸），矩阵点积计算余弦相似度。
4. 按 `photo_id` 聚合最大分数；只要一张脸匹配就返回整张照片。
5. 初始区间仅作为可调默认值，必须用用户实际照片校准：
   - 高置信度：`score >= 0.55`
   - 人工确认：`0.35 <= score < 0.55`
   - 不返回：`score < 0.35`
6. UI 允许调整阈值；确认/排除记录不修改源图。

## 6. 性能设计

- 一万到数万照片：SQLite 全量 embedding 分批向量化足够作为第一版，不急用 FAISS。
- 每脸 512×4 = 2048 字节；10 万张脸约 195 MiB 原始向量，SQLite 可承受。
- 扫描使用单个模型会话 + 后台 worker；GPU 模式可批量推理，CPU 模式先保证稳定。
- 数据库写入按照片事务提交；进程崩溃最多损失当前照片。
- WAL、`busy_timeout`、批量 insert；UI 线程不持有扫描连接。
- 缩略图进入独立缓存目录，按路径/mtime 生成 key；不修改原图。
- 数十万脸后再引入 FAISS/HNSW，并以 SQLite 为真源、向量索引为可重建缓存。

## 7. 稳定性与隐私

- 全离线推理，默认禁止任何照片上传；首次模型下载可通过安装阶段完成，运行阶段离线。
- 每张照片独立 try/except，损坏文件记入 `scan_failures` 后继续。
- 源照片只读打开；复制结果只写目标目录，发生同名时生成安全后缀。
- 支持取消扫描；每张照片完成后检查取消标记。
- 日志滚动保存到 `data/logs/app.log`，失败清单可导出 CSV。
- SQLite 定期备份；schema 使用迁移版本。

## 8. 模型授权风险

InsightFace 源代码为 MIT，但其官方自动下载的预训练模型包通常限定非商业研究用途。MVP 可用于本地技术验证；商业交付前必须：

1. 取得模型商业授权；或
2. 替换为明确允许商业使用的检测/识别 ONNX 模型；或
3. 使用具备合法来源的数据自行训练并保留授权证据。

因此模型层不得与业务层耦合，数据库中必须记录 `model_name/model_version`，换模型后应重建特征索引。

## 9. 八阶段交付顺序

1. 架构、依赖、授权边界（本文件）。
2. 最小检测/特征提取 CLI 和真实模型冒烟测试。
3. 文件夹扫描、SQLite schema、全脸入库、损坏隔离。
4. 参考脸选择模型与按照片最大值搜索。
5. PySide6 主界面、后台 worker、进度与取消。
6. 缩略图、打开原图/文件夹、确认/排除、复制结果。
7. 增量扫描、断点恢复、批量计算、日志、阈值校准。
8. 单元/集成/UI 测试、中文 README、CPU/CUDA 安装脚本、PyInstaller 打包。
