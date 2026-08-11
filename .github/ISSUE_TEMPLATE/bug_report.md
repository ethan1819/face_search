---
name: Bug report
about: Something broke or gave a wrong result.
title: "[bug] "
labels: ["bug"]
---

## Environment
- OS: (e.g. Windows 11 23H2)
- Python version: (`python --version`)
- `pip freeze` of the venv: (`pip freeze`)
- Install: CPU / CUDA (`pip show onnxruntime | grep Version`)
- Commit / branch: (`git rev-parse HEAD`)

## What I did
Steps to reproduce.

## What I expected

## What actually happened
Include the **full traceback** if there was an exception.
If this is a wrong-result issue (face match), attach:
- A description of the reference photo (pose, lighting, age).
- The wrongly returned library photo + the score shown in the UI.
