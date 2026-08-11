# 在其他电脑上传本项目到 GitHub

本项目当前在 `E:\AI\workspace\local-face-photo-search`，已完成首次 git commit（hash `9803826`，尚未 push 到任何远程）。本说明文档给"在另一台电脑上用 Hermes（或任何 AI agent）帮你把仓库上传到 GitHub"使用。

---

## 0. 这台机器的现状（关键事实）

- **没有 GitHub 远程**：当前仅本地仓库，`git remote -v` 为空。
- **没有 `gh` CLI**：用 `git` 直接推即可。
- **没有配 GitHub 账号 SSH / HTTPS token**：你需要先在 GitHub 网站上 `Sign in` 才能 push。
- **`.gitignore` 已生效**：`.venv/`、`data/`、`.pytest_cache/`、`__pycache__/`、`*.pyc`、模型、build/dist 都不会被 push。
- **首次 commit 已存在**（`9803826`），但如果你 clone 的是本指南的 zip，commit hash 会不同。

---

## 1. 在 GitHub 网站上建仓库（任何电脑必做）

1. 浏览器打开 https://github.com/new
2. **Repository name**：`local-face-photo-search`（随便叫，但下面命令里要写对）
3. **Description**（可选）：完全本地运行的人脸照片检索程序
4. 选 **Public**（公开）或 **Private**（私有）
5. **⚠️ 不要勾** 任何 "Add a README" / "Add .gitignore" / "Choose a license"（本地已有）
6. 点 **Create repository**

建完后 GitHub 会跳到 `https://github.com/<你的用户名>/local-face-photo-search`，**把 URL 复制下来**。下面命令里用 `<USER>` `<REPO>` 替代。

---

## 2. 在另一台电脑上让 Hermes 上传（最小流程）

### 2.1 准备文件

**方式 A**：把项目目录打包成 zip 拷贝（推荐）

在原电脑（这台电脑）执行：

```bash
cd /e/AI/workspace
"C:\Program Files\7-Zip\7z.exe" a -t7z -mx=5 -mmt=on -m0=LZMA2 local-face-photo-search.7z local-face-photo-search \
  -xr!".venv" -xr!"data" -xr!".pytest_cache" -xr!__pycache__ -xr!*.pyc
```

> 不打 `.venv`（装了也无意义，对方重装）和 `data/`（对方不需要你的图库索引）。
>
> `-mx=5` 是快档；约 1-2 MB（项目源码 + 模型脚本 + 8.3KB uv.lock + 几个文档）。
>
> ⚠️ **不要用 Compress-Archive**（Windows PowerShell 自带），对大目录会 OOM 静默卡死。
>
> ⚠️ **不要用普通 cmd `echo` 写 PowerShell 脚本**（参考 skill `windows-batch-pitfalls` 坑 1 / 11）；用本目录的 `Hermes` 写文件工具直接写 `.bat` 和 `.ps1` 也可以。

**方式 B**：直接拷目录（如果是 U 盘 / 局域网）

跳过 zip，但**务必确认**没把 `.venv` 一起拷——那里面有上 GB 的 Python 库。

### 2.2 在目标电脑上

落到任意路径，推荐**无中文 + 无空格 + 无括号**：

```text
D:\face-search\
```

（如果有用户提示说"路径必须 ASCII"——这是为了兼容 OpenCV / 部分安装脚本，不是 GitHub 强制。）

### 2.3 打开 Hermes，写下面这段 prompt（最快 30 秒）

> **Hermes prompt 模板（直接复制粘贴）**：
>
> 请帮我把 `D:\face-search\local-face-photo-search` 上传到 GitHub。
>
> 1. 在该目录执行 `git status` 确认是 git 仓库；
> 2. 如未 `git init` 请先 `git init -b main` 并 `git add -A && git commit -m "init: local face photo search"`；
> 3. 添加远程：`git remote add origin https://github.com/USER/REPO.git`（用我提供的 URL）；
> 4. `git push -u origin main`；
> 5. 如果推送失败说"could not read Username"或"terminal prompts disabled"，停下来告诉我**完整报错**（必须包含最后 10 行原文），不要瞎填账号密码；
> 6. 如果 push 成功，把 GitHub 页面 URL 告诉我。
>
> 注意：不要因为 push 失败而加 `--force`；不要清空 `.git`；不要修改 `.gitignore`。
>
> 失败时按 3 件事反馈给我：完整输出 / 跑了什么命令 / git remote -v 输出。

### 2.4 上传时 Hermes 容易踩的 3 个坑

| 坑 | 症状 | 修法 |
|---|---|---|
| HTTPS push 需要认证 | `fatal: could not read Username for 'https://github.com'` | 在 GitHub 网站 → Settings → Developer settings → Personal access tokens → 生成一个 `repo` 权限的 token，然后用 `https://<TOKEN>@github.com/USER/REPO.git` 作为 remote URL |
| `gh` 误用 | `gh auth login` 走完没生效 | 不要用 `gh`，直接 `git push`；`gh` 在这台机器可能没装 |
| 子目录里 `git init` | 误以为根目录已有 repo | 先 `cd` 到项目根，再 `git status` 看有没有 `.git` |

---

## 3. 同事 / 另一台电脑：在收到 GitHub 链接后怎么跑

```bat
:: 1. 装 Python 3.12（如还没装）
winget install --id Python.Python.3.12 -e

:: 2. 装 uv
pip install uv

:: 3. 把仓库 download 下来
git clone https://github.com/<USER>/local-face-photo-search.git
cd local-face-photo-search

:: 4. 建虚拟环境 + 装依赖
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

:: 5. 启动
start.bat
```

首次启动 InsightFace 会自动下载 `buffalo_l` 模型约 300MB 到 `C:\Users\<user>\.insightface\models\`（已下过的电脑秒开）。下载好之后离线可用。

---

## 4. 已知的坑（用 Hermes 或者自己跑都预留好）

1. **依赖装错路径**：`onnxruntime` 不能同时装 CPU + GPU 两个版本，参考 `README.md` 第 5 段。
2. **Chinese path 可能 OpenCV 读不下**：本项目用 `np.fromfile + cv2.imdecode` 兜底，不影响。
3. **模型首次启动慢**：CPU 模式 1-2 秒/张，GPU 模式 0.1-0.3 秒/张。库大时耐心等。
4. **商业授权**：InsightFace 开源协议是 MIT，但官方预训练模型仅限非商业研究使用。商业上线前必须替换或取得授权。已在 `README.md` 第 6 段强调。
5. **图片读不到**：默认图库为空，对方必须在程序里点「选择图库」指定图库目录。
6. **HEIC 暂不支持**：iPhone 新格式；未来加 pillow-heif 即可。
7. **磁盘空间**：.venv 装好约 1.5GB（cp312 + onnxruntime + insightface + pyside6 + 模型额外 300MB）。如果是小硬盘机器，预先计划好。

---

## 5. 验证清单（上传后必须过一遍）

- [ ] `git remote -v` → 显示 origin URL
- [ ] `git log --oneline` → 至少有 init commit
- [ ] GitHub 网页上能看到 24 个文件（不含 .venv / data / __pycache__）
- [ ] 另一台电脑 `git clone` 能成功
- [ ] `python -m pytest` 全部 43 项通过
- [ ] `start.bat` 双击能看到 PySide6 窗口
- [ ] 默认空图库（点击「选择图库」指定目录后能正常扫描）

---

## 6. 需要我立刻帮你做的话

- 想要 **另一台电脑的 putscreen 上传视频**：录 Hermes TUI 给我
- 想要 **desktop shortcut 直接打开 GitHub 桌面**：装 GitHub Desktop 后 `File → Add local repository`
- 想要 **不通过 GitHub 直接给同事**：见上面 §2.1 方式 A，打 zip 即可

---

版权：纯简科技
项目维护：aze
commit hash：9803826
