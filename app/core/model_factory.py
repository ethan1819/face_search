"""InsightFace FaceAnalysis factory with CPU default and CUDA fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelInfo:
    name: str
    providers: tuple[str, ...]
    device: str
    warning: str | None = None


class FaceAnalysisFactory:
    """Create the real InsightFace app lazily, without importing it in unit tests."""

    def __init__(self, model_name: str = "buffalo_l", root: str | None = None) -> None:
        self.model_name = model_name
        self.root = root
        self.info: ModelInfo | None = None

    def create(self, prefer_cuda: bool = True) -> Any:
        try:
            import onnxruntime as ort
            from insightface.app import FaceAnalysis
        except Exception as exc:
            raise RuntimeError(
                "无法加载 InsightFace/ONNX Runtime。请在 .venv 中安装 face 依赖。"
            ) from exc
        available = tuple(ort.get_available_providers())
        use_cuda = prefer_cuda and "CUDAExecutionProvider" in available
        providers = ("CUDAExecutionProvider", "CPUExecutionProvider") if use_cuda else ("CPUExecutionProvider",)
        warning = None if use_cuda else "CUDA 不可用，已使用 CPU；首次运行可能下载 buffalo_l 模型。"
        kwargs: dict[str, Any] = {"name": self.model_name, "providers": list(providers)}
        if self.root:
            kwargs["root"] = self.root
        try:
            app = FaceAnalysis(**kwargs)
            app.prepare(ctx_id=0 if use_cuda else -1, det_size=(640, 640))
        except Exception as exc:
            if use_cuda:
                log.warning("CUDA model initialization failed; retrying CPU: %s", exc)
                providers = ("CPUExecutionProvider",)
                app = FaceAnalysis(name=self.model_name, providers=list(providers), **({"root": self.root} if self.root else {}))
                app.prepare(ctx_id=-1, det_size=(640, 640))
                warning = f"CUDA 初始化失败，已降级 CPU：{exc}"
            else:
                raise RuntimeError(
                    f"模型 {self.model_name} 加载失败。请检查网络/模型目录后重试：{exc}"
                ) from exc
        self.info = ModelInfo(self.model_name, providers, "CUDA" if "CUDAExecutionProvider" in providers else "CPU", warning)
        if warning:
            log.warning(warning)
        log.info("FaceAnalysis ready: model=%s providers=%s", self.model_name, providers)
        return app
