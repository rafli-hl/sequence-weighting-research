"""Check the local CUDA runtime with a real forward/backward calculation."""
import argparse
import json
import platform
from pathlib import Path

import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no CPU fallback.")
    torch.manual_seed(17)
    x = torch.randn(128, 128, device="cuda", requires_grad=True)
    loss = (x @ x.T).square().mean()
    loss.backward()
    torch.cuda.synchronize()
    assert torch.isfinite(loss) and torch.isfinite(x.grad).all()
    reference = x.detach().cpu().requires_grad_()
    reference_loss = (reference @ reference.T).square().mean()
    reference_loss.backward()
    torch.testing.assert_close(loss.detach().cpu(), reference_loss.detach(), rtol=1e-4, atol=1e-5)
    torch.testing.assert_close(x.grad.cpu(), reference.grad, rtol=1e-4, atol=1e-5)
    result = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_build": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "gpu_total_mib": torch.cuda.get_device_properties(0).total_memory / 2**20,
        "cuda_forward_backward": "PASS",
        "cpu_gpu_numerical_agreement": "PASS",
        "device": str(x.device),
        "training_result": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
