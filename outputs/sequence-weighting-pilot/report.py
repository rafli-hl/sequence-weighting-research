"""Build figures and a factual pilot report from completed run JSON files."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = [json.loads((path / "result.json").read_text()) for path in args.runs]
    max_epoch = max(r["config"]["epochs"] for r in results)
    seeds = sorted({r["config"]["seed"] for r in results})
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), layout="constrained")
    colors = ["#156f9b", "#a85c19", "#3f7455", "#8555a4", "#333333"]
    for i, result in enumerate(results):
        cfg, history = result["config"], result["history"]
        label = f'{cfg["regime"]}, {cfg["weighting"]}, {cfg["parameters"]/1e6:.2f}M'
        available = [h for h in history if h.get("p_star", {}).get("p") is not None]
        if available:
            axes[0].plot([h["epoch"] for h in available],
                         [h["p_star"]["p"] for h in available], marker="o",
                         label=label, color=colors[i % len(colors)])
        axes[1].plot([h["epoch"] for h in history], [h["validation"]["loss"] for h in history],
                     marker="o", label=label, color=colors[i % len(colors)])
    axes[0].set(title="Effective sequence-weight exponent", xlabel="Training epoch", ylabel="p* (dimensionless)")
    axes[0].set_ylim(bottom=0)
    axes[1].set(title="Validation answer loss", xlabel="Training epoch", ylabel="NLL (nats / answer token)")
    for ax in axes:
        ax.grid(axis="y", alpha=.2)
        ax.legend(fontsize=8)
        ax.set_xticks(range(max_epoch + 1))
    fig.suptitle(f"Synthetic sequence-weighting pilot — exploratory, {len(seeds)} seed(s)", fontsize=13)
    fig.savefig(args.output / "pilot-curves.png", dpi=180)
    fig.savefig(args.output / "pilot-curves.svg")
    plt.close(fig)

    mixed = next((r for r in results if r["config"]["regime"] == "mixed" and r["config"]["weighting"] == "random"), None)
    if mixed:
        fig, ax = plt.subplots(figsize=(7.6, 4.4), layout="constrained")
        for typ, color in zip(("shared", "group", "instance"), colors):
            ax.plot([h["epoch"] for h in mixed["history"]],
                    [h["validation"][typ]["accuracy"] * 100 for h in mixed["history"]],
                    marker="o", color=color, label=typ)
        ax.axhline(6.25, color="#666666", linestyle="--", label="16-answer chance: 6.25%")
        ax.set(title="Mixed data, random weights: validation accuracy", xlabel="Training epoch", ylabel="Answer accuracy (%)", xticks=range(max_epoch + 1), ylim=(0, 105))
        ax.legend()
        ax.grid(axis="y", alpha=.2)
        fig.savefig(args.output / "pattern-learning.png", dpi=180)
        fig.savefig(args.output / "pattern-learning.svg")
        plt.close(fig)

    rows = []
    for result in results:
        cfg, final = result["config"], result["history"][-1]
        rows.append({"regime": cfg["regime"], "weighting": cfg["weighting"], "parameters": cfg["parameters"],
                     "seed": cfg["seed"], "final_p_star": final["p_star"]["p"],
                     "p_star_details": final["p_star"], "epochs": cfg["epochs"], "train_size": cfg["train_size"],
                     "initial_train_loss": result["history"][0]["train"]["loss"],
                     "final_train_loss": final["train"]["loss"], "final_test": result["final_test"],
                     "elapsed_seconds": result["elapsed_seconds"],
                     "peak_allocated_mib": result["peak_allocated_mib"],
                     "peak_reserved_mib": result["peak_reserved_mib"],
                     "clipping_fractions": [h["gradient_clip_fraction"] for h in result["history"][1:]]})
    (args.output / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = ["# GPU pilot results", "", "These are measured exploratory results, not a scaling-law claim.", "",
             "- Data: training count per run below; 256 validation, 512 test sequences; 12 answer tokens per sequence.",
             "- Random initialization, float32, fixed final-epoch evaluation.",
             f"- Seeds: {seeds}. This report does not compute between-seed confidence intervals.",
             "- Memory figures describe the PyTorch allocator, excluding desktop/driver allocations.", ""]
    lines += ["- Timings cover the instrumented training/evaluation section; interpreter imports, model/optimizer setup, package installation, and final checkpoint serialization are excluded.", ""]
    for row in rows:
        ptext = f'undefined ({row["p_star_details"].get("reason")})' if row["final_p_star"] is None else f'{row["final_p_star"]:.5f}'
        lines += [f'## {row["regime"]} / {row["weighting"]}', "",
                  f'- Model parameters: {row["parameters"]:,}.',
                  f'- Training sequences / epochs / seed: {row["train_size"]:,} / {row["epochs"]} / {row["seed"]}.',
                  f'- Final p*: {ptext}.',
                  f'- Training answer NLL: {row["initial_train_loss"]:.4f} -> {row["final_train_loss"]:.4f} nats/token.',
                  f'- Final test answer NLL: {row["final_test"]["loss"]:.4f} nats/token.',
                  f'- Elapsed training + evaluation: {row["elapsed_seconds"]:.1f} seconds.',
                  f'- Peak allocated / reserved VRAM: {row["peak_allocated_mib"]:.1f} / {row["peak_reserved_mib"]:.1f} MiB.',
                  f'- Clipped-step fractions by epoch: {row["clipping_fractions"]}.']
        for typ in ("shared", "group", "instance"):
            if typ in row["final_test"]:
                lines.append(f'- {typ} test accuracy: {row["final_test"][typ]["accuracy"]*100:.2f}%.')
        lines.append("")
    lines += ["## Interpretation limits", "",
              "The original Jane Street study uses pretrained model families and an internal text benchmark. This pilot starts from random weights and applies sequence weights to conditional answer losses. The initial gain also includes learning that answer tokens occupy a restricted vocabulary. That shared gain can dilute p*. A low exponent alone therefore does not identify a capacity regime.", "",
              "Uniform weights have no identifiable exponent. Rule accuracy on held-out examples is a diagnostic, not a replacement for the original training-set metric. One seed cannot establish a non-monotonic capacity curve or its epoch shift.", "",
              "The next decision should depend on pattern learnability, gradient clipping, and fit quality. Freeze a validation-selected setup before running a multi-seed capacity ladder.", "",
              "Source: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/", ""]
    (args.output / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
