"""Lazy framework setup for the ladder worker. Linux owner only; never imported by native fixtures."""
import json, os, platform, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def setup(cache_dir):
    if not sys.platform.startswith('linux'): raise RuntimeError('Existing Linux owner only')
    expected = json.loads((HERE / 'ORIGINAL_ENVIRONMENT.json').read_bytes())
    if platform.python_version() != expected['python']: raise RuntimeError('Original Python version mismatch')
    cache_dir = Path(cache_dir); cache_dir.mkdir(exist_ok=False)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', CUDA_CACHE_DISABLE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
    for k in ('TMPDIR', 'TMP', 'TEMP'): os.environ[k] = str(cache_dir)
    for k in ('XDG_CACHE_HOME', 'TORCH_HOME', 'TRITON_CACHE_DIR', 'TORCHINDUCTOR_CACHE_DIR'): os.environ[k] = str(cache_dir / k.lower())
    import torch
    if str(torch.__version__) != expected['torch'] or torch.version.cuda != expected['cuda']: raise RuntimeError('Original Torch/CUDA version mismatch')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required; no fallback')
    torch.cuda.set_device(0)
    if torch.cuda.get_device_name(0) != expected['gpu'] or torch.backends.cudnn.version() != expected['cudnn']: raise RuntimeError('Original device/cuDNN mismatch')
    if torch.cuda.mem_get_info()[0] < 2 * 2 ** 30: raise RuntimeError('Less than 2 GiB available device memory')
    sys.path.insert(0, str(HERE / 'vendor'))
    import engine
    from model import Model
    return torch, engine, Model
