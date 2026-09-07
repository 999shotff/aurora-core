"""Compute Runtime LLM Provider — bridges compute fabric with LLM interface.

Uses runtime manager to run inference on remote GPU workers.
"""

from __future__ import annotations

import logging
import time

from aurora.ai.errors import LLMTimeout, LLMUnavailable
from aurora.ai.providers import LLMProvider, ProviderCapabilities
from aurora.runtime.manager import RuntimeManager
from aurora.runtime.schemas import InferenceRequest, InferenceStatus

logger = logging.getLogger(__name__)


class ComputeRuntimeProvider(LLMProvider):
    """LLM provider backed by compute fabric runtime."""

    def __init__(self, runtime_manager: RuntimeManager) -> None:
        self._runtime = runtime_manager
        self._available = False
        self._model_id: str | None = None
        self._worker_id: str | None = None
        self._name = "compute-runtime"

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        if not self._available:
            return False
        runtimes = self._runtime.list_runtimes()
        return any(
            r.status.value == "READY" and r.model_load_status.value == "LOADED"
            for r in runtimes
        )

    def configure(self, model_id: str, worker_id: str | None = None) -> None:
        self._model_id = model_id
        self._worker_id = worker_id
        self._available = True

    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> str:
        if not self._model_id:
            raise LLMUnavailable("No model configured")

        prompt = self._messages_to_prompt(messages)

        request = InferenceRequest(
            model_id=self._model_id,
            worker_id=self._worker_id,
            prompt=prompt,
            max_new_tokens=min(max_tokens, 4096),
            temperature=temperature,
            timeout_seconds=int(timeout),
        )

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run, self._runtime.run_inference(request)
                    )
                    result = future.result(timeout=timeout + 5)
            else:
                result = loop.run_until_complete(
                    self._runtime.run_inference(request)
                )
        except TimeoutError:
            raise LLMTimeout(f"Inference timed out after {timeout}s")
        except Exception as exc:
            raise LLMUnavailable(f"Inference failed: {exc}")

        if result.status == InferenceStatus.TIMEOUT:
            raise LLMTimeout("Inference timed out")
        if result.status != InferenceStatus.COMPLETED:
            raise LLMUnavailable(
                f"Inference failed: {result.error or result.status.value}"
            )

        return result.output or ""

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self._name,
            models=[self._model_id] if self._model_id else [],
            max_context_tokens=8192,
            max_output_tokens=4096,
            supports_structured_output=False,
            requires_api_key=False,
            is_demo=True,
        )

    def health_check(self) -> dict:
        runtime = None
        for r in self._runtime.list_runtimes():
            if self._worker_id and r.worker_id == self._worker_id:
                runtime = r
                break
        if not runtime:
            runtimes = self._runtime.list_runtimes()
            runtime = runtimes[0] if runtimes else None

        return {
            "provider": self._name,
            "available": self.is_available,
            "model_id": self._model_id,
            "worker_id": self._worker_id or "auto",
            "runtime_status": runtime.status.value if runtime else "NO_RUNTIME",
            "model_status": (
                runtime.model_load_status.value if runtime else "NOT_LOADED"
            ),
            "gpu": runtime.gpu_name if runtime else None,
        }

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"[{role}]: {content}")
        return "\n".join(parts)
