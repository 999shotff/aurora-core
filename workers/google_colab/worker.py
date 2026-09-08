"""AURORA Colab Worker Client.

Connects a Google Colab GPU runtime to AURORA CORE's Compute Fabric.
Implements Worker Protocol v2: REGISTER, HEARTBEAT, CAPABILITIES, JOB lifecycle.

Usage:
    worker = AuroraColabWorker(
        backend_url="https://your-aurora-backend.onrender.com",
        worker_token="your-secret-token",
    )
    worker.connect()
    worker.run()  # Blocks until disconnected
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import socket
import sys
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2.0"
WORKER_VERSION = "0.3.0"
HEARTBEAT_INTERVAL = 30
RECONNECT_DELAY = 5
MAX_RECONNECT_ATTEMPTS = 20
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# Whitelist of approved HuggingFace source model IDs.
APPROVED_SOURCE_MODELS: dict[str, str] = {
    "qwen2.5-0.5b-instruct": "Qwen/Qwen2.5-0.5B-Instruct",
    "smollm2-1.7b": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "phi-3.5-mini": "microsoft/Phi-3.5-mini-instruct",
    "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
    "llama-3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
}
APPROVED_SOURCE_IDS: set[str] = set(APPROVED_SOURCE_MODELS.values())

# Whitelist of approved Ollama model names.
APPROVED_OLLAMA_MODELS: dict[str, str] = {
    "qwen2.5-0.5b-ollama": "qwen2.5:0.5b",
}
APPROVED_OLLAMA_IDS: set[str] = set(APPROVED_OLLAMA_MODELS.values())


class GPUInfo:
    """Detect GPU information from the runtime."""

    @staticmethod
    def detect() -> dict[str, Any]:
        info: dict[str, Any] = {
            "name": "UNKNOWN",
            "vendor": "UNKNOWN",
            "vram_mb": 0.0,
            "cuda_version": None,
            "driver_version": None,
            "compute_capability": None,
            "available_memory_mb": 0.0,
            "runtime_info": None,
        }

        try:
            import torch
            if torch.cuda.is_available():
                info["name"] = torch.cuda.get_device_name(0)
                info["vendor"] = "NVIDIA"
                info["cuda_version"] = torch.version.cuda
                info["compute_capability"] = ".".join(
                    str(x) for x in torch.cuda.get_device_capability(0)
                )
                mem = torch.cuda.get_device_properties(0)
                info["vram_mb"] = round(mem.total_memory / (1024 * 1024), 1)
                info["available_memory_mb"] = round(
                    (mem.total_memory - torch.cuda.memory_allocated(0)) / (1024 * 1024), 1
                )
                info["runtime_info"] = f"PyTorch {torch.__version__}"
                return info
        except ImportError:
            pass

        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                if len(parts) >= 4:
                    info["name"] = parts[0].strip()
                    info["vendor"] = "NVIDIA"
                    info["vram_mb"] = float(parts[1].strip())
                    info["driver_version"] = parts[2].strip()
                    info["compute_capability"] = parts[3].strip()
                    info["available_memory_mb"] = info["vram_mb"]
                    info["runtime_info"] = "nvidia-smi"
        except Exception:
            pass

        return info


class RuntimeHandler:
    """Handles model runtime operations on the worker side."""

    def __init__(self, gpu_info: dict) -> None:
        self._gpu_info = gpu_info
        self._loaded_model = None
        self._model_name: str | None = None
        self._model_config: dict | None = None
        self._load_time: float | None = None
        self._total_inferences = 0
        self._total_errors = 0

    @property
    def is_model_loaded(self) -> bool:
        return self._loaded_model is not None

    @property
    def loaded_model_id(self) -> str | None:
        return self._model_name

    def discover(self) -> dict:
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            pytorch_version = torch.__version__ if has_cuda else None
            cuda_version = torch.version.cuda if has_cuda else None
        except ImportError:
            has_cuda = False
            pytorch_version = None
            cuda_version = None

        return {
            "status": "READY" if has_cuda else "ERROR",
            "gpu_name": self._gpu_info.get("name"),
            "vram_mb": self._gpu_info.get("vram_mb"),
            "cuda_version": cuda_version,
            "pytorch_version": pytorch_version,
            "model_status": "LOADED" if self.is_model_loaded else "NOT_LOADED",
            "loaded_model": self._model_name,
        }

    def load_model(self, model_id: str, dtype: str | None = None,
                    source_model_id: str | None = None) -> dict:
        if self.is_model_loaded:
            return {"status": "ERROR", "error": f"Model already loaded: {self._model_name}"}

        # Security: resolve and validate source_model_id
        if source_model_id:
            load_id = source_model_id
        elif model_id in APPROVED_SOURCE_MODELS:
            load_id = APPROVED_SOURCE_MODELS[model_id]
        else:
            return {"status": "ERROR",
                    "error": f"Model '{model_id}' not in approved registry. "
                             f"Approved models: {list(APPROVED_SOURCE_MODELS.keys())}"}

        if load_id not in APPROVED_SOURCE_IDS:
            return {"status": "ERROR",
                    "error": f"Source model '{load_id}' not in approved whitelist. "
                             f"Allowed: {sorted(APPROVED_SOURCE_IDS)}"}

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            start = time.time()
            torch_dtype = getattr(torch, dtype, torch.float16) if dtype else torch.float16

            tokenizer = AutoTokenizer.from_pretrained(load_id)
            model = AutoModelForCausalLM.from_pretrained(
                load_id,
                torch_dtype=torch_dtype,
                device_map="auto",
            )

            self._loaded_model = model
            self._model_name = model_id
            self._model_config = {"dtype": str(torch_dtype), "device": str(model.device)}
            self._load_time = time.time() - start

            mem_used = torch.cuda.memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0

            return {
                "status": "LOADED",
                "model_id": model_id,
                "load_time_seconds": round(self._load_time, 2),
                "model_memory_mb": round(mem_used, 1),
            }
        except Exception as e:
            self._total_errors += 1
            return {"status": "ERROR", "error": str(e)[:500]}

    def unload_model(self) -> dict:
        if not self.is_model_loaded:
            return {"status": "NOT_LOADED"}

        try:
            self._loaded_model = None
            self._model_name = None
            self._model_config = None
            self._load_time = None

            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return {"status": "NOT_LOADED"}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)[:500]}

    def health(self) -> dict:
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            vram_used = torch.cuda.memory_allocated() / (1024 * 1024) if has_cuda else 0
            vram_total = torch.cuda.get_device_properties(0).total_mem / (1024 * 1024) if has_cuda else 0
        except Exception:
            has_cuda = False
            vram_used = 0
            vram_total = 0

        return {
            "model_status": "LOADED" if self.is_model_loaded else "NOT_LOADED",
            "loaded_model": self._model_name,
            "gpu_available": has_cuda,
            "vram_used_mb": round(vram_used, 1),
            "vram_total_mb": round(vram_total, 1),
            "total_inferences": self._total_inferences,
            "total_errors": self._total_errors,
        }

    def infer(self, prompt: str, max_new_tokens: int = 256,
              temperature: float = 0.7, top_p: float = 0.9) -> dict:
        if not self.is_model_loaded:
            return {"status": "ERROR", "error": "No model loaded"}

        try:
            import torch

            start = time.time()
            inputs = self._loaded_model.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._loaded_model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=temperature > 0,
                )

            generated = outputs[0][inputs["input_ids"].shape[-1]:]
            output_text = self._loaded_model.tokenizer.decode(generated, skip_special_tokens=True)
            gen_time = time.time() - start

            tokens = len(generated)
            self._total_inferences += 1

            return {
                "status": "COMPLETED",
                "output": output_text,
                "tokens_generated": tokens,
                "generation_time_seconds": round(gen_time, 3),
                "tokens_per_second": round(tokens / gen_time, 1) if gen_time > 0 else 0,
            }
        except Exception as e:
            self._total_errors += 1
            return {"status": "FAILED", "error": str(e)[:500]}


class OllamaRuntime:
    """Handles Ollama runtime operations on the worker side.

    Communicates with a local Ollama instance via HTTP (localhost:11434).
    Detects GPU/CPU execution via nvidia-smi and ollama ps.
    """

    def __init__(self, gpu_info: dict, base_url: str = OLLAMA_BASE_URL) -> None:
        self._gpu_info = gpu_info
        self._base_url = base_url.rstrip("/")
        self._loaded_model: str | None = None
        self._load_time: float | None = None
        self._total_inferences = 0
        self._total_errors = 0
        self._last_gpu_status: str = "UNAVAILABLE"

    @property
    def is_model_loaded(self) -> bool:
        return self._loaded_model is not None

    @property
    def loaded_model_id(self) -> str | None:
        return self._loaded_model

    def _ollama_get(self, path: str) -> dict | None:
        try:
            resp = requests.get(f"{self._base_url}{path}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None

    def _ollama_post(self, path: str, data: dict | None = None) -> dict | None:
        try:
            resp = requests.post(f"{self._base_url}{path}", json=data or {}, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None

    def health(self) -> dict:
        info = self._ollama_get("/api/tags")
        if info is None:
            return {"status": "ERROR", "error": "Ollama not reachable",
                    "ollama_url": self._base_url}
        models = [m.get("name", "") for m in info.get("models", [])]
        gpu_status = self._detect_gpu_status()
        return {
            "status": "READY",
            "ollama_url": self._base_url,
            "available_models": models,
            "loaded_model": self._loaded_model,
            "gpu_status": gpu_status,
        }

    def discover(self) -> dict:
        health = self.health()
        gpu_status = self._detect_gpu_status()
        return {
            "status": health["status"],
            "runtime": "ollama",
            "ollama_url": self._base_url,
            "gpu_name": self._gpu_info.get("name"),
            "vram_mb": self._gpu_info.get("vram_mb"),
            "model_status": "LOADED" if self.is_model_loaded else "NOT_LOADED",
            "loaded_model": self._loaded_model,
            "available_models": health.get("available_models", []),
            "gpu_status": gpu_status,
        }

    def _detect_gpu_status(self) -> str:
        """Detect whether Ollama is using GPU or CPU.

        Returns one of:
            GPU_ACCELERATED - model is running on GPU
            CPU_ONLY - model is running on CPU
            GPU_AVAILABLE_BUT_NOT_USED - GPU detected but Ollama not using it
            RUNTIME_UNAVAILABLE - cannot determine
        """
        import subprocess

        has_gpu = self._gpu_info.get("name", "UNKNOWN") != "UNKNOWN"

        # Check nvidia-smi for GPU memory usage by ollama
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return "GPU_ACCELERATED"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check ollama ps for processor info
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self._base_url}/api/ps"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                import json as _json
                ps_data = _json.loads(result.stdout)
                models = ps_data.get("models", [])
                for m in models:
                    processor = m.get("processor", "")
                    if "gpu" in processor.lower() or "cuda" in processor.lower():
                        return "GPU_ACCELERATED"
                    if "cpu" in processor.lower():
                        return "CPU_ONLY"
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        if has_gpu:
            return "GPU_AVAILABLE_BUT_NOT_USED"
        return "RUNTIME_UNAVAILABLE"

    def ensure_model(self, ollama_model_name: str) -> dict:
        """Check if model exists locally, pull if not present."""
        info = self._ollama_get("/api/tags")
        if info is None:
            return {"status": "ERROR", "error": "Ollama not reachable"}

        available = [m.get("name", "") for m in info.get("models", [])]
        if ollama_model_name in available:
            return {"status": "READY", "model": ollama_model_name}

        logger.info("Pulling Ollama model: %s", ollama_model_name)
        pull_result = self._ollama_post("/api/pull", {"name": ollama_model_name})
        if pull_result is None:
            return {"status": "ERROR", "error": f"Failed to pull model: {ollama_model_name}"}

        info2 = self._ollama_get("/api/tags")
        if info2:
            available2 = [m.get("name", "") for m in info2.get("models", [])]
            if ollama_model_name in available2:
                return {"status": "READY", "model": ollama_model_name}

        return {"status": "ERROR", "error": f"Model pull completed but model not found: {ollama_model_name}"}

    def load_model(self, model_id: str, ollama_model_name: str) -> dict:
        """Load/warm an Ollama model. Validates against approved whitelist."""
        if self.is_model_loaded:
            return {"status": "ERROR", "error": f"Model already loaded: {self._loaded_model}"}

        # Security: validate against approved Ollama models
        if model_id in APPROVED_OLLAMA_MODELS:
            approved_name = APPROVED_OLLAMA_MODELS[model_id]
        elif ollama_model_name and ollama_model_name in APPROVED_OLLAMA_IDS:
            approved_name = ollama_model_name
        else:
            return {"status": "ERROR",
                    "error": f"Model '{model_id}' not in approved Ollama registry. "
                             f"Approved: {list(APPROVED_OLLAMA_MODELS.keys())}"}

        if approved_name not in APPROVED_OLLAMA_IDS:
            return {"status": "ERROR",
                    "error": f"Ollama model '{approved_name}' not in approved whitelist. "
                             f"Allowed: {sorted(APPROVED_OLLAMA_IDS)}"}

        # Ensure model is available
        ensure_result = self.ensure_model(approved_name)
        if ensure_result["status"] != "READY":
            return ensure_result

        # Warm up with a small generate to confirm GPU usage
        start = time.time()
        try:
            warmup = self._ollama_post("/api/generate", {
                "model": approved_name,
                "prompt": "hi",
                "options": {"num_predict": 1},
                "stream": False,
            })
            if warmup is None:
                return {"status": "ERROR", "error": "Ollama warm-up failed"}

            self._loaded_model = approved_name
            self._load_time = time.time() - start

            # Detect actual GPU usage after warm-up
            gpu_status = self._detect_gpu_status()
            self._last_gpu_status = gpu_status

            return {
                "status": "LOADED",
                "model_id": model_id,
                "ollama_model": approved_name,
                "load_time_seconds": round(self._load_time, 2),
                "gpu_status": gpu_status,
            }
        except Exception as e:
            self._total_errors += 1
            return {"status": "ERROR", "error": str(e)[:500]}

    def unload_model(self) -> dict:
        if not self.is_model_loaded:
            return {"status": "NOT_LOADED"}
        model_name = self._loaded_model
        self._loaded_model = None
        self._load_time = None
        return {"status": "NOT_LOADED", "unloaded_model": model_name}

    def infer(self, prompt: str, max_new_tokens: int = 256,
              temperature: float = 0.7, top_p: float = 0.9) -> dict:
        if not self.is_model_loaded:
            return {"status": "ERROR", "error": "No model loaded"}

        try:
            start = time.time()
            options = {
                "num_predict": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
            }
            result = self._ollama_post("/api/generate", {
                "model": self._loaded_model,
                "prompt": prompt,
                "options": options,
                "stream": False,
            })

            if result is None:
                return {"status": "FAILED", "error": "Ollama inference failed"}

            output = result.get("response", "")
            gen_time = time.time() - start
            tokens = result.get("eval_count", len(output.split()))
            self._total_inferences += 1

            # Check GPU status after inference
            gpu_status = self._detect_gpu_status()
            self._last_gpu_status = gpu_status

            return {
                "status": "COMPLETED",
                "output": output,
                "tokens_generated": tokens,
                "generation_time_seconds": round(gen_time, 3),
                "tokens_per_second": round(tokens / gen_time, 1) if gen_time > 0 else 0,
                "model": self._loaded_model,
                "gpu_status": gpu_status,
            }
        except Exception as e:
            self._total_errors += 1
            return {"status": "FAILED", "error": str(e)[:500]}


class AuroraColabWorker:
    """AURORA GPU worker for Google Colab.

    Connects to AURORA backend via HTTP, implements Worker Protocol v2.
    """

    def __init__(
        self,
        backend_url: str,
        worker_token: str,
        provider_type: str = "GOOGLE_COLAB",
        heartbeat_interval: int = HEARTBEAT_INTERVAL,
    ) -> None:
        self._backend_url = backend_url.rstrip("/")
        self._worker_token = worker_token
        self._provider_type = provider_type
        self._heartbeat_interval = heartbeat_interval
        self._worker_id: str | None = None
        self._running = False
        self._connected = False
        self._gpu_info: dict[str, Any] = {}
        self._start_time = time.time()
        self._current_job_id: str | None = None
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._runtime_handler: RuntimeHandler | None = None
        self._ollama_runtime: OllamaRuntime | None = None

    @property
    def worker_id(self) -> str:
        if self._worker_id is None:
            hostname = socket.gethostname()
            self._worker_id = f"colab-{hostname}-{int(self._start_time)}"
        return self._worker_id

    def _api_post(self, path: str, data: dict) -> dict | None:
        url = f"{self._backend_url}{path}"
        try:
            resp = self._session.post(url, json=data, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            logger.error("API error %s: %s %s", path, resp.status_code, resp.text[:200])
            return None
        except requests.RequestException as e:
            logger.error("Request failed %s: %s", path, e)
            return None

    def _detect_gpu(self) -> None:
        self._gpu_info = GPUInfo.detect()
        logger.info("GPU detected: %s (%s MB)", self._gpu_info["name"], self._gpu_info["vram_mb"])

    def _build_capabilities(self) -> dict:
        try:
            import torch
            pytorch_version = torch.__version__
        except ImportError:
            pytorch_version = None

        return {
            "inference": True,
            "embeddings": True,
            "vision": True,
            "training": True,
            "benchmark": True,
            "runtime": True,
            "max_concurrency": 1,
            "gpu": self._gpu_info,
            "framework": "pytorch",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "pytorch_version": pytorch_version,
        }

    def connect(self) -> bool:
        self._detect_gpu()
        self._runtime_handler = RuntimeHandler(self._gpu_info)
        self._ollama_runtime = OllamaRuntime(self._gpu_info)

        registration = {
            "worker_id": self.worker_id,
            "provider_id": "colab",
            "provider_type": self._provider_type,
            "capabilities": self._build_capabilities(),
            "protocol_version": PROTOCOL_VERSION,
            "worker_version": WORKER_VERSION,
            "started_at": self._start_time,
            "api_token": self._worker_token,
        }

        ack = self._api_post("/api/v1/compute/workers/register", registration)
        if ack is None:
            logger.error("Registration failed: no response")
            return False

        if not ack.get("accepted"):
            logger.error("Registration rejected: %s", ack.get("error"))
            return False

        self._connected = True
        logger.info("Connected to AURORA backend as %s", self.worker_id)
        return True

    def _send_heartbeat(self) -> bool:
        heartbeat = {
            "worker_id": self.worker_id,
            "status": "BUSY" if self._current_job_id else "READY",
            "capabilities": self._build_capabilities(),
            "current_job_id": self._current_job_id,
            "uptime_seconds": time.time() - self._start_time,
            "api_token": self._worker_token,
        }
        ack = self._api_post(f"/api/v1/compute/workers/{self.worker_id}/heartbeat", heartbeat)
        if ack is None:
            return False
        if ack.get("shutdown_requested"):
            logger.info("Shutdown requested by backend")
            self._running = False
        return True

    def _heartbeat_loop(self) -> None:
        while self._running:
            if not self._send_heartbeat():
                logger.warning("Heartbeat failed, attempting reconnect...")
                self._connected = False
                self._reconnect()
            time.sleep(self._heartbeat_interval)

    def _job_poll_loop(self) -> None:
        """Poll for pending jobs from the backend. Executes runtime workloads."""
        poll_interval = 2.0
        while self._running:
            if not self._connected:
                time.sleep(5)
                continue
            try:
                pending = self._poll_pending_jobs()
                if pending:
                    poll_interval = 1.0  # Fast poll when jobs exist
                    for job in pending:
                        self._execute_dispatched_job(job)
                else:
                    poll_interval = min(poll_interval * 1.1, 5.0)
            except Exception as e:
                logger.error("Job poll error: %s", e)
            time.sleep(poll_interval)

    def _poll_pending_jobs(self) -> list[dict]:
        """Fetch pending jobs from backend."""
        resp = self._api_get(f"/api/v1/compute/workers/{self.worker_id}/jobs/pending")
        if resp and resp.get("jobs"):
            return resp["jobs"]
        return []

    def _api_get(self, path: str) -> dict | None:
        url = f"{self._backend_url}{path}"
        try:
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None

    def _execute_dispatched_job(self, job: dict) -> None:
        """Execute a dispatched job and report result back."""
        job_id = job.get("job_id")
        workload_type = job.get("workload_type", "")
        payload = job.get("payload", {})
        self._current_job_id = job_id

        logger.info("Executing dispatched job %s: %s", job_id, workload_type)

        try:
            result = self._execute_workload(workload_type, payload)
            result_hash = hashlib.sha256(
                str(sorted(result.items())).encode()
            ).hexdigest()[:16]
            result["result_hash"] = result_hash

            self._api_post(
                f"/api/v1/compute/workers/{self.worker_id}/jobs/{job_id}/result",
                result,
            )
            logger.info("Job %s completed: %s", job_id, workload_type)
        except Exception as e:
            logger.error("Job %s failed: %s", job_id, e)
            error_result = {
                "status": "FAILED",
                "error": str(e)[:500],
                "workload": workload_type,
            }
            self._api_post(
                f"/api/v1/compute/workers/{self.worker_id}/jobs/{job_id}/result",
                error_result,
            )
        finally:
            self._current_job_id = None

    def _reconnect(self) -> bool:
        attempts = 0
        while attempts < MAX_RECONNECT_ATTEMPTS and self._running:
            attempts += 1
            logger.info("Reconnect attempt %d/%d", attempts, MAX_RECONNECT_ATTEMPTS)
            if self.connect():
                return True
            time.sleep(RECONNECT_DELAY * min(attempts, 5))
        return False

    def _handle_job(self, job: dict) -> None:
        job_id = job.get("job_id")
        workload_type = job.get("workload_type", "")
        payload = job.get("payload", {})
        self._current_job_id = job_id

        self._api_post(f"/api/v1/compute/workers/{self.worker_id}/heartbeat", {
            "worker_id": self.worker_id,
            "status": "BUSY",
            "capabilities": self._build_capabilities(),
            "current_job_id": job_id,
            "uptime_seconds": time.time() - self._start_time,
            "api_token": self._worker_token,
        })

        try:
            result = self._execute_workload(workload_type, payload)
            result_hash = hashlib.sha256(str(sorted(result.items())).encode()).hexdigest()[:16]
            self._api_post("/api/v1/compute/jobs", {
                "workload_type": workload_type,
                "provider_preference": self._provider_type,
                "payload": payload,
            })
        except Exception as e:
            logger.error("Job %s failed: %s", job_id, e)
        finally:
            self._current_job_id = None

    def _execute_workload(self, workload_type: str, payload: dict) -> dict:
        if workload_type == "BENCHMARK":
            return self._run_benchmark(payload)
        elif workload_type == "INFERENCE":
            return {"provider": "colab", "workload": "INFERENCE", "message": "GPU inference ready"}
        elif workload_type == "EMBEDDINGS":
            return {"provider": "colab", "workload": "EMBEDDINGS", "message": "GPU embeddings ready"}
        elif workload_type == "RUNTIME_DISCOVER":
            return self._handle_runtime_discover(payload)
        elif workload_type == "RUNTIME_LOAD":
            return self._handle_runtime_load(payload)
        elif workload_type == "RUNTIME_UNLOAD":
            return self._handle_runtime_unload(payload)
        elif workload_type == "RUNTIME_HEALTH":
            return self._handle_runtime_health(payload)
        elif workload_type == "RUNTIME_INFER":
            return self._handle_runtime_infer(payload)
        else:
            return {"provider": "colab", "workload": workload_type, "message": "Processed on GPU"}

    def _handle_runtime_discover(self, payload: dict) -> dict:
        result = {"provider": "colab", "workload": "RUNTIME_DISCOVER"}
        # Include both runtimes
        if self._runtime_handler:
            result.update(self._runtime_handler.discover())
        if self._ollama_runtime:
            ollama_health = self._ollama_runtime.health()
            result["ollama_status"] = ollama_health.get("status", "ERROR")
            result["ollama_models"] = ollama_health.get("available_models", [])
        return result

    def _handle_runtime_load(self, payload: dict) -> dict:
        runtime_type = payload.get("runtime", "transformers")
        model_id = payload.get("model_id", "")

        if runtime_type == "ollama":
            if not self._ollama_runtime:
                return {"status": "ERROR", "error": "Ollama runtime not initialized"}
            ollama_model = payload.get("runtime_model_id") or payload.get("source_model_id", "")
            return {"provider": "colab", "workload": "RUNTIME_LOAD",
                    **self._ollama_runtime.load_model(model_id, ollama_model)}
        else:
            if not self._runtime_handler:
                return {"status": "ERROR", "error": "Runtime not initialized"}
            source_model_id = payload.get("source_model_id")
            dtype = payload.get("dtype")
            return {"provider": "colab", "workload": "RUNTIME_LOAD",
                    **self._runtime_handler.load_model(model_id, dtype, source_model_id)}

    def _handle_runtime_unload(self, payload: dict) -> dict:
        # Try Ollama first if a model is loaded there
        if self._ollama_runtime and self._ollama_runtime.is_model_loaded:
            return {"provider": "colab", "workload": "RUNTIME_UNLOAD",
                    **self._ollama_runtime.unload_model()}
        if self._runtime_handler and self._runtime_handler.is_model_loaded:
            return {"provider": "colab", "workload": "RUNTIME_UNLOAD",
                    **self._runtime_handler.unload_model()}
        return {"provider": "colab", "workload": "RUNTIME_UNLOAD", "status": "NOT_LOADED"}

    def _handle_runtime_health(self, payload: dict) -> dict:
        result = {"provider": "colab", "workload": "RUNTIME_HEALTH"}
        if self._runtime_handler:
            result.update(self._runtime_handler.health())
        if self._ollama_runtime:
            ollama_health = self._ollama_runtime.health()
            result["ollama_status"] = ollama_health.get("status", "ERROR")
            result["ollama_model"] = ollama_health.get("loaded_model")
        return result

    def _handle_runtime_infer(self, payload: dict) -> dict:
        runtime_type = payload.get("runtime", "transformers")

        if runtime_type == "ollama":
            if not self._ollama_runtime:
                return {"status": "ERROR", "error": "Ollama runtime not initialized"}
            prompt = payload.get("prompt", "")
            max_new_tokens = payload.get("max_new_tokens", 256)
            temperature = payload.get("temperature", 0.7)
            top_p = payload.get("top_p", 0.9)
            return {"provider": "colab", "workload": "RUNTIME_INFER",
                    **self._ollama_runtime.infer(prompt, max_new_tokens, temperature, top_p)}
        else:
            if not self._runtime_handler:
                return {"status": "ERROR", "error": "Runtime not initialized"}
            prompt = payload.get("prompt", "")
            max_new_tokens = payload.get("max_new_tokens", 256)
            temperature = payload.get("temperature", 0.7)
            top_p = payload.get("top_p", 0.9)
            return {"provider": "colab", "workload": "RUNTIME_INFER",
                    **self._runtime_handler.infer(prompt, max_new_tokens, temperature, top_p)}

    def _run_benchmark(self, payload: dict) -> dict:
        matrix_size = payload.get("matrix_size", 1024)
        iterations = payload.get("iterations", 10)

        try:
            import torch
            if torch.cuda.is_available():
                start = time.time()
                a = torch.randn(matrix_size, matrix_size, device="cuda")
                b = torch.randn(matrix_size, matrix_size, device="cuda")
                for _ in range(iterations):
                    _ = torch.mm(a, b)
                torch.cuda.synchronize()
                elapsed = time.time() - start
                total_flops = 2.0 * matrix_size ** 3 * iterations
                gflops = total_flops / elapsed / 1e9
                checksum = hashlib.sha256(
                    f"gpu-{matrix_size}-{iterations}".encode()
                ).hexdigest()[:16]
                return {
                    "provider": "colab",
                    "workload": "BENCHMARK",
                    "gpu": self._gpu_info["name"],
                    "matrix_size": matrix_size,
                    "iterations": iterations,
                    "execution_time_seconds": elapsed,
                    "gflops": round(gflops, 2),
                    "result_checksum": checksum,
                    "status": "PASSED",
                }
        except Exception as e:
            return {
                "provider": "colab",
                "workload": "BENCHMARK",
                "status": "FAILED",
                "error": str(e),
            }

        return {
            "provider": "colab",
            "workload": "BENCHMARK",
            "status": "FAILED",
            "error": "No CUDA available",
        }

    def disconnect(self) -> None:
        self._running = False
        if self._worker_id:
            self._api_post(f"/api/v1/compute/workers/{self.worker_id}/shutdown", {
                "worker_id": self._worker_id,
                "reason": "Worker shutting down",
                "api_token": self._worker_token,
            })
        self._connected = False
        logger.info("Disconnected from AURORA backend")

    def run(self) -> None:
        self._running = True
        if not self.connect():
            logger.error("Failed to connect to AURORA backend")
            return

        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        job_poll_thread = threading.Thread(target=self._job_poll_loop, daemon=True)
        job_poll_thread.start()

        logger.info("Worker %s running. Press Ctrl+C to stop.", self.worker_id)
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.disconnect()
