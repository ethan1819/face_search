# PyPI 发布清单

## 前置检查

### 1. pyproject.toml 里缺啥

当前 `pyproject.toml` 已经有：
- ✅ `[project]` 段（name, version, description, license, requires-python, dependencies）
- ✅ `[project.optional-dependencies]` 段（face / gpu / gui / dev）
- ✅ `[project.urls]` 段（Homepage, Repository, Issues, Changelog）

还需要 / 建议补的：
- ❌ `[project.scripts]` 段（让 `pip install` 后能跑 `face-search` 命令）
- ❌ `[build-system]` 段（声明用 hatchling / setuptools / poetry 打包）
- ⚠️ `name = "local-face-photo-search"` 里有连字符，可能跟 import path 不一致；建议改 `face-search` 或保持原样但加 `py_modules`
- ⚠️ `[tool.uv] package = false` 在发布时需要改为 `true`，或者保留 false + 单独用 `python -m build`

### 2. 包结构问题

当前 `app/__init__.py` + `app/main.py` 是「app layout」。如果想 import 成 `face_search`，需要：

```bash
# 选项 A: 加 src layout
mkdir src
git mv app src/face_search  # 重命名包
# 然后所有 import 改成 from face_search.xxx import ...

# 选项 B: 保持 app layout，加 py_modules
# pyproject.toml:
# [project]
# name = "face-search"  # PyPI 名
# packages = ["app"]     # 告诉构建工具要打包 app/
```

**建议**：选 A (`src/face_search/`)。更标准，避免与 `app` 这种通用名冲突。

### 3. LICENSE 兼容性

PyPI 要求 LICENSE 文件**在包根目录**。当前 `LICENSE` 在仓库根，包构建时会自动包含，✅。

### 4. README

PyPI 会自动从 `readme = "README.md"` 读取并渲染。✅ 已设置。

---

## 发布步骤

### 本地（一次性）

```bash
# 1. 装构建工具
.venv\Scripts\python.exe -m pip install --upgrade build twine

# 2. 清理旧的 build artifact
rm -rf dist/ build/ *.egg-info

# 3. 构建
.venv\Scripts\python.exe -m build
# 生成: dist/local_face_photo_search-0.1.0-py3-none-any.whl
#       dist/local-face-photo-search-0.1.0.tar.gz

# 4. 上传到 PyPI（需要 token，从 https://pypi.org/manage/account/token/ 生成）
#    先用 testpypi 试
.venv\Scripts\python.exe -m twine upload --repository testpypi dist/*
#    试装
pip install --index-url https://test.pypi.org/simple/ local-face-photo-search
#    确认没问题再上正式 PyPI
.venv\Scripts\python.exe -m twine upload dist/*
```

### 发布后 README 加一行

```markdown
[![PyPI](https://img.shields.io/pypi/v/local-face-photo-search.svg)](https://pypi.org/project/local-face-photo-search/)
[![Downloads](https://img.shields.io/pypi/dm/local-face-photo-search.svg)](https://pypi.org/project/local-face-photo-search/)
```

加在 README 顶部徽章区，跟 license / python 徽章一行。

---

## 我的建议（Codex 视角）

**先不要发 PyPI**。原因：

1. 项目是 v0.1.0 MVP，API 还在大改，发了之后 pin 0.1.x 的人升级会很痛
2. Windows 安装包（`face_search_cuda_win64.zip`）才是真正的「开箱即用」形态，PyPI 上装完还要 `start.bat` 启动
3. 现在 0 star，新包上传 PyPI 容易被 spam 标记

**更好的顺序**：
1. 先发 Show HN / V2EX 拿到 50-200 star
2. 跑 2-3 周看 issue / PR 反馈，把 API 收敛
3. 然后发 v0.2.0 + PyPI + GitHub Release 二进制
4. README 加 `pip install local-face-photo-search` 行

如果你坚持现在发，文件已经写好，按上面步骤执行即可。
