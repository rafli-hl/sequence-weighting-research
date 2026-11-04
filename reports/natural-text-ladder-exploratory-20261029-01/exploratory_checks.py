"""EXPLORATORY (written after the analysis result was seen; not pre-registered). Recomputes, from the sealed analysis
outputs of Run B (revision 05), the descriptive statements in EXPLORATORY_NOTE.md. Panel means only; no inference.

  python.exe -I -B exploratory_checks.py      -> EXPLORATORY_CHECKS.json next to this file
"""
import hashlib, json, sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent / 'natural-text-ladder-analysis-20261029-01' / 'sealed-analysis' / 'ANALYSIS.json'
LR = HERE.parent / 'natural-text-ladder-lr-selection-20261028-01' / 'LR_SELECTION.json'
raw = A.read_bytes(); assert hashlib.sha256(raw).hexdigest() == '4414abfdfb163b393d1c09a4051505985475c63478829267e35c1014533c62a8'
lraw = LR.read_bytes(); assert hashlib.sha256(lraw).hexdigest() == 'cb059387dc26f6743199f446940487d55d868700130faa68b9256eb333b2c217'
a = json.loads(raw); lr = json.loads(lraw)['learning_rates']
W = (64, 96, 128, 192, 256, 384); E = (1, 2, 4, 6, 8, 12, 16, 24, 32)


def ranks(xs):
    order = sorted(range(len(xs)), key=xs.__getitem__); r = [0.0] * len(xs); i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(x, y):
    n = len(x); mx, my = sum(x) / n, sum(y) / n
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y)); sxx = sum((u - mx) ** 2 for u in x); syy = sum((v - my) ** 2 for v in y)
    return sxy / (sxx * syy) ** 0.5


spearman = lambda x, y: pearson(ranks(x), ranks(y))
p = {e: a['by_epoch'][f'E{e}']['curve'] for e in E}                                  # ten-draw panel mean p* per width
gap = {e: [a['losses'][f'{w}|E{e}']['gap'] for w in W] for e in E}                    # mean validation minus train NLL
argmin = lambda ys: W[min(range(6), key=ys.__getitem__)]
out = dict(
    note='EXPLORATORY: written after the result was seen; not pre-registered; descriptive panel means; no interval or test.',
    analysis_sha256=hashlib.sha256(raw).hexdigest(), lr_selection_sha256=hashlib.sha256(lraw).hexdigest(),
    learning_rates={str(w): lr[str(w)] for w in W},
    by_epoch_labels={f'E{e}': a['by_epoch'][f'E{e}']['shape_label'] for e in E},
    p_argmin_width={f'E{e}': argmin(p[e]) for e in E},
    gap_argmin_width={f'E{e}': argmin(gap[e]) for e in E},
    p_rises_128_to_384={f'E{e}': all(p[e][k] < p[e][k + 1] for k in range(2, 5)) for e in E},
    gap_rises_128_to_384={f'E{e}': all(gap[e][k] < gap[e][k + 1] for k in range(2, 5)) for e in E},
    spearman_pooled_54=spearman([v for e in E for v in p[e]], [v for e in E for v in gap[e]]),
    pearson_pooled_54=pearson([v for e in E for v in p[e]], [v for e in E for v in gap[e]]),
    spearman_within_epoch={f'E{e}': spearman(p[e], gap[e]) for e in E},
    spearman_within_width_across_epochs={str(w): spearman([p[e][k] for e in E], [gap[e][k] for e in E]) for k, w in enumerate(W)},
    panel_p={f'E{e}': p[e] for e in E}, panel_gap={f'E{e}': gap[e] for e in E},
    draws_with_positive_curvature=sum(v['c'] > 0 for v in a['primaries']['B']['draw_coefficients'].values()))
(HERE / 'EXPLORATORY_CHECKS.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k not in ('panel_p', 'panel_gap')}, indent=1))
