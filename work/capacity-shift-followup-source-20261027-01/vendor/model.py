"""Small, reproducible mechanism pilot inspired by Jane Street (2026).

Conditional next-token learning on synthetic sequences; not a replication of
the private benchmark. See README.md for scope and interpretation.
"""
import argparse
import hashlib
import json
import math
import platform
import random
import time
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

TYPES = ("shared", "group", "instance")
VOCAB = 84


from core import exponent, make_data_lists


def make_data(seed, regime, ntrain, nval, ntest):
    raw, metadata = make_data_lists(seed, regime, ntrain, nval, ntest)
    return {name: tuple(torch.tensor(x, dtype=torch.long) for x in data)
            for name, data in raw.items()}, metadata


class Block(nn.Module):
    def __init__(self, width, heads):
        super().__init__()
        self.heads = heads
        self.ln1, self.ln2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.qkv = nn.Linear(width, 3 * width)
        self.proj = nn.Linear(width, width)
        self.ff = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(), nn.Linear(4 * width, width))

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.qkv(self.ln1(x)).reshape(b, t, 3, self.heads, c // self.heads).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(b, t, c))
        return x + self.ff(self.ln2(x))


class Model(nn.Module):
    def __init__(self, width, layers, length):
        super().__init__()
        self.token = nn.Embedding(VOCAB, width)
        self.position = nn.Embedding(length, width)
        self.blocks = nn.Sequential(*[Block(width, 4) for _ in range(layers)])
        self.norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, VOCAB, bias=False)
        self.apply(self.initialize)

    @staticmethod
    def initialize(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, x):
        h = self.token(x) + self.position(torch.arange(x.shape[1], device=x.device))[None]
        return self.head(self.norm(self.blocks(h)))


def losses(model, tokens, kinds):
    logits = model(tokens[:, :-1])
    loss = F.cross_entropy(logits.transpose(1, 2), tokens[:, 1:], reduction="none")
    valid = kinds >= 0
    seq_loss = (loss * valid).sum(1) / valid.sum(1)
    return seq_loss, loss, logits.argmax(-1).eq(tokens[:, 1:])


@torch.no_grad()
def evaluate(model, data, device, batch):
    model.eval()
    seq, component, correct = [], {t: [] for t in TYPES}, {t: [] for t in TYPES}
    for start in range(0, len(data[0]), batch):
        tokens, kinds = (x[start:start+batch].to(device) for x in data)
        sl, loss, acc = losses(model, tokens, kinds)
        seq.append(sl.cpu())
        for j, typ in enumerate(TYPES):
            mask = kinds == j
            if mask.any():
                component[typ].append(loss[mask].cpu())
                correct[typ].append(acc[mask].float().cpu())
    out = {"loss": float(torch.cat(seq).mean())}
    for typ in TYPES:
        if component[typ]:
            out[typ] = {"loss": float(torch.cat(component[typ]).mean()),
                        "accuracy": float(torch.cat(correct[typ]).mean())}
    return out, torch.cat(seq)


def validate():
    weights = [math.exp(-3 + 6 * i / 99) for i in range(100)]
    for expected in (0, .5, 1, 2):
        fit = exponent(weights, [2 * w ** expected for w in weights])
        assert abs(fit["p"] - expected) < 1e-5, (expected, fit)
    # Independent direct quadratic-form check of the optimized estimator.
    gains = [1 + .3 * math.sin(i) for i in range(100)]
    fit = exponent(weights, gains)
    p = fit["p"]
    total = sum(w ** p for w in weights)
    d = [g / sum(gains) - w ** p / total for g, w in zip(gains, weights)]
    direct = sum(d[i] * min((i+1)/100, (j+1)/100) * d[j] for i in range(100) for j in range(100))
    assert abs(direct - fit["objective"]) < 1e-12
    assert exponent([1, 1], [1, 2])["p"] is None
    assert exponent([1, 2], [-1, 0])["p"] is None
    splits, meta = make_data(7, "mixed", 32, 16, 16)
    control, _ = make_data(7, "shared", 32, 16, 16)
    for name in splits:
        assert torch.equal(splits[name][0][:, :5], control[name][0][:, :5])
        assert torch.equal(splits[name][0][:, 6::3], control[name][0][:, 6::3])
    assert meta["unique_keys"] == 64
    for data in splits.values():
        assert data[0].shape[1] == 41
        assert ((data[1] >= 0).sum(1) == 12).all()
        for row, mask in zip(*data):
            for j in (mask == 0).nonzero().flatten().tolist():
                assert int(row[j+1]) - 68 == (int(row[j]) - 52 + 1) % 16
            for j in (mask == 1).nonzero().flatten().tolist():
                assert int(row[j+1]) - 68 == meta["group_permutations"][int(row[1])-1][int(row[j])-52]
    torch.manual_seed(9)
    model = Model(32, 1, 40).eval()
    x = splits["train"][0][:2, :-1].clone()
    before = model(x).detach()
    x[:, 20:] = (x[:, 20:] + 1) % VOCAB
    assert torch.allclose(before[:, :20], model(x)[:, :20], atol=1e-6)
    print("PASS: estimator recovery, quadratic equivalence, data alignment, disjoint keys, causal mask", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("work/runs/pilot"))
    parser.add_argument("--regime", choices=("mixed", "structured", "shared"), default="mixed")
    parser.add_argument("--weighting", choices=("random", "uniform"), default="random")
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--train-size", type=int, default=2048)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lr", type=float, default=0.0003)
    args = parser.parse_args()
    torch.set_num_threads(4)
    if args.validate_only:
        validate()
        return
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this GPU benchmark; no silent CPU fallback.")
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    args.output.mkdir(parents=True, exist_ok=False)
    splits, metadata = make_data(1729, args.regime, args.train_size, 256, 512)
    wrng = random.Random(1000 + args.seed)
    raw = [math.exp(wrng.uniform(math.log(.01), math.log(10))) for _ in range(args.train_size)]
    weights = torch.tensor(raw if args.weighting == "random" else [1.] * len(raw))
    weights /= weights.mean()  # One corpus-level normalization, never batch normalization.
    device = torch.device("cuda")
    model = Model(args.width, args.layers, metadata["length"] - 1).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=.1)
    config = {**vars(args), "output": str(args.output), "parameters": sum(p.numel() for p in model.parameters()),
              "torch": torch.__version__, "python": platform.python_version(),
              "gpu": torch.cuda.get_device_name(0), "precision": "float32", "weight_decay": .1,
              "objective": "mean next-token NLL at 12 answer positions per sequence",
              "pretrained": False, "loss_units": "nats/answer token",
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "core_sha256": hashlib.sha256(Path(__file__).with_name("core.py").read_bytes()).hexdigest(),
              "weight_min": float(weights.min()), "weight_max": float(weights.max()),
              "weight_mean": float(weights.mean()),
              "weight_effective_sample_size": float(weights.sum()**2 / weights.square().sum())}
    (args.output / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (args.output / "data.json").write_text(json.dumps(metadata), encoding="utf-8")
    torch.save(splits, args.output / "dataset.pt")
    print(json.dumps(config), flush=True)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    start_time = time.perf_counter()
    train_initial, initial_losses = evaluate(model, splits["train"], device, args.batch)
    val_initial, _ = evaluate(model, splits["validation"], device, args.batch)
    history = [{"epoch": 0, "train": train_initial, "validation": val_initial}]
    sequence_losses = [initial_losses]
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = torch.randperm(args.train_size, generator=torch.Generator().manual_seed(999 + args.seed + epoch))
        ep_start = time.perf_counter()
        norms = []
        for step, ids in enumerate(order.split(args.batch)):
            tokens, kinds = (x[ids].to(device) for x in splits["train"])
            sl, _, _ = losses(model, tokens, kinds)
            loss = (sl * weights[ids].to(device)).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if not torch.isfinite(loss) or not torch.isfinite(norm):
                raise RuntimeError("Non-finite loss or gradient; refusing to continue.")
            norms.append(float(norm))
            optimizer.step()
            if (step + 1) % 32 == 0:
                print(f"epoch={epoch} step={step+1} weighted_loss={float(loss):.4f}", flush=True)
        torch.cuda.synchronize()
        train_seconds = time.perf_counter() - ep_start
        train_metrics, current = evaluate(model, splits["train"], device, args.batch)
        val_metrics, _ = evaluate(model, splits["validation"], device, args.batch)
        fitted = exponent(weights.tolist(), (initial_losses - current).tolist())
        item = {"epoch": epoch, "train": train_metrics, "validation": val_metrics,
                "p_star": fitted, "train_seconds": train_seconds,
                "gradient_norm_mean": sum(norms) / len(norms),
                "gradient_clip_fraction": sum(x > 1 for x in norms) / len(norms)}
        history.append(item)
        sequence_losses.append(current)
        (args.output / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
        print(json.dumps(item), flush=True)
    test, _ = evaluate(model, splits["test"], device, args.batch)
    torch.cuda.synchronize()
    result = {"config": config, "history": history, "final_test": test,
              "elapsed_seconds": time.perf_counter() - start_time,
              "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
              "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20,
              "warning": "Single-seed feasibility pilot; no scaling-law or statistical-significance claim."}
    (args.output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    torch.save({"weights": weights, "losses": torch.stack(sequence_losses)}, args.output / "sequence_losses.pt")
    torch.save(model.state_dict(), args.output / "model.pt")
    print(json.dumps({k: result[k] for k in ("elapsed_seconds", "peak_allocated_mib", "peak_reserved_mib", "final_test")}), flush=True)


if __name__ == "__main__":
    main()
