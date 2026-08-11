# Contributing

Thanks for considering a contribution. The project keeps the bar low on purpose
so it stays approachable for individual developers who want a private face-photo
search tool.

## Development setup

```bat
git clone https://github.com/ethan1819/face_search.git
cd face_search
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe pytest pytest-cov
```

## Running the tests

```bat
set PYTHONPATH=
.venv\Scripts\python.exe -m pytest -q
```

GUI tests use Qt offscreen mode (`QT_QPA_PLATFORM=offscreen`) — no display required.

The face engine is mocked in tests so contributors don't need to download the
~300 MB `buffalo_l` model just to run the suite. To run the real-model smoke:

```bat
.venv\Scripts\python.exe scripts\real_model_smoke.py
```

## Style

- Python 3.11+, `from __future__ import annotations`.
- Type hints on all public APIs.
- Keep `FaceEngine` swappable: business tests must not require a real InsightFace
  session.

## Pull Requests

- One feature or fix per PR.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` under an `Unreleased` section.
- Make sure `pytest` passes locally before opening the PR.

## Reporting bugs

Open an issue with: OS / Python version / `pip freeze` of the venv / exact
command + full traceback. If the bug is "wrong face match", attach a description
of the reference photo (pose, lighting) and which library photo was wrongly
returned with the score shown in the UI.
