"""Environment audit for Phase 5.1 — local model runtime validation.

Detects hardware, software, and resource availability.
Produces machine-readable environment report.
"""
from __future__ import annotations

import importlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field


@dataclass
class EnvironmentReport:
    python_version: str = ""
    platform: str = ""
    machine: str = ""
    os_name: str = ""
    cpu_count: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    disk_free_gb: float = 0.0
    gpu_available: bool = False
    gpu_name: str = ""
    cuda_available: bool = False
    cuda_version: str = ""
    torch_available: bool = False
    torch_version: str = ""
    torch_device: str = ""
    transformers_available: bool = False
    transformers_version: str = ""
    accelerate_available: bool = False
    sentencepiece_available: bool = False
    protobuf_available: bool = False
    bitsandbytes_available: bool = False
    llama_cpp_available: bool = False
    errors: list[str] = field(default_factory=list)


def _get_ram_info() -> tuple[int, int]:
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        total = 0
        available = 0
        for line in lines:
            if line.startswith("MemTotal:"):
                total = int(line.split()[1]) // 1024
            elif line.startswith("MemAvailable:"):
                available = int(line.split()[1]) // 1024
        return total, available
    except Exception:
        return 0, 0


def _get_disk_free() -> float:
    try:
        st = os.statvfs("/")
        return (st.f_bavail * st.f_frsize) / (1024**3)
    except Exception:
        return 0.0


def _check_gpu() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return False, ""


def _check_cuda() -> tuple[bool, str]:
    try:
        import torch
        return torch.cuda.is_available(), torch.version.cuda or ""
    except Exception:
        return False, ""


def _check_module(name: str) -> tuple[bool, str]:
    try:
        m = importlib.import_module(name)
        return True, getattr(m, "__version__", "installed")
    except ImportError:
        return False, ""


def audit_environment() -> EnvironmentReport:
    report = EnvironmentReport()
    report.python_version = sys.version
    report.platform = platform.platform()
    report.machine = platform.machine()
    report.os_name = os.name

    try:
        report.cpu_count = os.cpu_count() or 0
    except Exception:
        report.cpu_count = 0

    report.ram_total_mb, report.ram_available_mb = _get_ram_info()
    report.disk_free_gb = round(_get_disk_free(), 1)

    report.gpu_available, report.gpu_name = _check_gpu()
    report.cuda_available, report.cuda_version = _check_cuda()

    for mod in ["torch", "transformers", "accelerate", "sentencepiece",
                "protobuf", "bitsandbytes", "llama_cpp"]:
        available, version = _check_module(mod)
        setattr(report, f"{mod}_available", available)
        setattr(report, f"{mod}_version", version)

    if report.torch_available:
        try:
            import torch
            report.torch_device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            report.torch_device = "unknown"

    return report


def run_audit() -> dict:
    report = audit_environment()
    return asdict(report)


def main() -> None:
    report = audit_environment()
    print("=" * 60)
    print("PHASE 5.1 — ENVIRONMENT AUDIT")
    print("=" * 60)
    d = asdict(report)
    for k, v in d.items():
        print(f"  {k}: {v}")
    print()
    print("JSON:")
    print(json.dumps(d, indent=2))


if __name__ == "__main__":
    main()
