# V2EX 帖正文（直接复制到「创意创造」节点）

**标题**：写了个完全本地的人脸照片检索，不上传任何照片

**正文**：

本来想给家里上万张照片按人脸整理一下，结果发现要么得传上 iCloud / Google Photos（你懂的），要么就得自己折腾 InsightFace。

于是写了一个开源的 PySide6 桌面程序：

- **100% 本地运行**：照片、特征向量、查询结果全在你电脑上，不会出网
- **源照片只读**：不会移动、修改、删除原图
- **支持中文路径**（踩过 cv2.imread 的坑）
- **后台增量索引**：扫过一次的图库之后只处理新增/修改
- **MIT 协议 + 43 个 pytest**

技术栈：Python 3.11/3.12 · PySide6 · InsightFace（buffalo_l） · ONNX Runtime · SQLite

截图：https://github.com/ethan1819/face_search/blob/main/docs/screenshot.png

仓库：https://github.com/ethan1819/face_search

提醒一下：InsightFace 默认的 buffalo_l 模型是非商用研究的，商业上线前需要换模型或拿授权。代码本身是 MIT。

写得比较仓促，欢迎吐槽和 PR。
