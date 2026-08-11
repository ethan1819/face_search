# 本地人脸照片检索 MVP

完全在本机运行的 PySide6 桌面程序。参考照片可包含多张脸；选择目标脸后，在已索引图库中按每张照片的最高人脸余弦相似度检索。源照片只读，程序不会上传、移动、删除或修改原图。

## 安装与启动

要求 Windows 10/11、Python 3.11 或 3.12。项目已带 `.venv` 时直接双击 **`start.bat`**。首次启动如果本地没有 `buffalo_l`，InsightFace 会尝试下载约 300MB 模型，请保持网络可用；下载或加载失败会显示明确错误，并写入 `data/logs/app.log`。

从零安装（在项目目录打开终端）：

```bat
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
start.bat
```

CPU 默认可用。程序检测到 `CUDAExecutionProvider` 时优先使用 CUDA；CUDA 初始化失败会自动回退 CPU。普通 `onnxruntime` 只提供 CPU，如需 GPU 应先按显卡/CUDA 版本安装匹配的 `onnxruntime-gpu`，不要同时保留两个 ORT 包。

## 使用

1. 双击 `start.bat`，默认图库为 `M:\1A 尹成毅\724大会资料`，也可点“选择图库”。
2. 点“选择参考照片”。检测到多张脸时，在人脸裁剪列表中点选目标人物。
3. 点“扫描/增量索引”。扫描在 QThread 后台执行，界面可继续操作；可安全停止。首次扫描较慢，之后只处理新增/修改照片。
4. 点“搜索”。结果分为默认 **高置信（≥0.55）** 和 **人工确认（0.35–0.55）**；阈值可调整，应使用实际照片校准。
5. 结果支持缩略图、打开原图、打开所在文件夹、确认、排除和复制所选。复制遇到重名会自动加后缀。
6. 工具栏可查看或导出失败记录；滚动日志在界面及 `data/logs/app.log` 中保留。

支持 JPG/JPEG/PNG。单张损坏照片不会终止扫描。

## 验证

```bat
set PYTHONPATH=
.venv\Scripts\python.exe -m pytest tests -q
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe -m pytest tests\test_gui_smoke.py -q
```

真实模型冒烟（会下载模型，若尚未缓存）：

```bat
set PYTHONPATH=
.venv\Scripts\python.exe -c "from app.core.model_factory import FaceAnalysisFactory; f=FaceAnalysisFactory(); f.create(); print(f.info)"
```

## 数据与授权

数据库为 `data/index.db`，缩略图为 `data/thumbnails/`，日志为 `data/logs/`。删除这些缓存不会影响原图，但会需要重新索引。

InsightFace 源代码为 MIT；其官方预训练模型（包括自动下载的 `buffalo_l`）并不因此自动获得商业使用许可。本 MVP 仅用于本地技术验证。商业使用前必须取得模型授权或替换为明确允许商业使用的模型，并重建索引。
