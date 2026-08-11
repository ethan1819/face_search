# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | ✅ Active          |

Older versions are not maintained. Please upgrade before reporting issues.

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security problems.**

This project deals with **biometric data (face embeddings)**. Even though
the app is local-only, security issues can still affect users — e.g. if a
maliciously crafted photo causes the face engine to crash, read arbitrary
files, or execute code.

Report privately via one of:

- **Email**: open a GitHub issue titled `[security contact]` and we will
  reply with a secure channel.
- **GitHub Security Advisories**: https://github.com/ethan1819/face_search/security/advisories/new

Please include:

1. A clear description of the vulnerability and its impact.
2. Steps to reproduce (or a minimal proof-of-concept).
3. The commit / version affected.
4. Whether you intend to disclose publicly and on what timeline.

You can expect:

- An acknowledgement within **7 days**.
- A status update at least every **14 days** until resolution.
- Credit in the fix commit (unless you prefer to remain anonymous).

## Scope

This policy covers:

- `app/` and `scripts/` Python source code shipped in this repo.
- The bundled `face_search` PyInstaller binaries (if released).

It does **not** cover:

- Third-party libraries (`insightface`, `onnxruntime`, `PySide6`, …) — please
  report upstream.
- The pre-trained `buffalo_l` model itself — that is an InsightFace /
  DeepInsight distribution concern.
- User-installed InsightFace models other than the bundled ones.

## Privacy Reminder

This project intentionally runs **entirely on-device**. No photo data,
embedding data, or query logs are ever transmitted off the user's machine.
If you find a code path that violates that promise, that's a security bug
and falls under this policy.
