"""D0 CUDA smoke test: versions, device, fp16/bf16 matmul, SDPA backends, large allocation.

Writes runs/<run_id>/smoke_cuda.json and exits non-zero on failure.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pinstyle.runs import new_run_dir  # noqa: E402


def main() -> int:
    report: dict = {"ok": False, "checks": {}}
    c = report["checks"]
    c["torch"] = torch.__version__
    c["cuda_available"] = torch.cuda.is_available()
    if not c["cuda_available"]:
        print(json.dumps(report, indent=2))
        return 1
    c["cuda"] = torch.version.cuda
    c["cudnn"] = torch.backends.cudnn.version()
    c["device"] = torch.cuda.get_device_name(0)
    c["capability"] = list(torch.cuda.get_device_capability(0))
    c["total_vram_gib"] = round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2)

    for dtype in (torch.float16, torch.bfloat16):
        a = torch.randn(8192, 8192, device="cuda", dtype=dtype)
        b = torch.randn(8192, 8192, device="cuda", dtype=dtype)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(10):
            a @ b
        torch.cuda.synchronize()
        dt = (time.perf_counter() - t0) / 10
        c[f"matmul_{str(dtype).split('.')[-1]}_tflops"] = round(2 * 8192**3 / dt / 1e12, 1)
        del a, b

    q = torch.randn(1, 10, 4096, 64, device="cuda", dtype=torch.float16)
    out = torch.nn.functional.scaled_dot_product_attention(q, q, q)
    c["sdpa_ok"] = bool(torch.isfinite(out).all().item())
    c["sdpa_flash_enabled"] = torch.backends.cuda.flash_sdp_enabled()
    c["sdpa_mem_efficient_enabled"] = torch.backends.cuda.mem_efficient_sdp_enabled()

    big = torch.empty(int(20 * 2**30), dtype=torch.uint8, device="cuda")
    big.fill_(1)
    c["alloc_20gib_ok"] = True
    del big
    torch.cuda.empty_cache()

    report["ok"] = c["capability"] == [8, 9] and c["sdpa_ok"]
    run_dir = new_run_dir("smoke_cuda")
    (run_dir / "smoke_cuda.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"run dir: {run_dir}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
