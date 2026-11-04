"""Second set of recomputations for the adversarial review: contrasts at matched training progress (N6), the epoch at which each width's
p* peaks (N4, N3), and what the pooled gap model predicts for each contrast (N6). Saved tables only; writes RECOMPUTE_MATCHED.json.

  python -I -B recompute_matched.py
"""
import csv, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent; R = HERE.parent
N6 = R / 'natural-text-peak-analysis-20261103-01'; N4 = R / 'natural-text-lateturn-analysis-20261031-01'; N3 = R / 'natural-text-onerate-analysis-20261030-02'
T = {3: 3.182446305, 5: 2.570581836, 9: 2.262157163}
rows = lambda p: list(csv.DictReader(p.read_text(encoding='utf-8').splitlines()))
def mean(v): return sum(v) / len(v)
def tint(v):
    n = len(v); m = mean(v); s = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)); h = T[n - 1] * s / math.sqrt(n)
    return dict(n=n, mean=m, low=m - h, high=m + h, negative=sum(x < 0 for x in v), positive=sum(x > 0 for x in v))
out = {}

# ---------------------------------------------------------------- N6: each contrast at matched progress
P = {}
for r in rows(N6 / 'POINTS.csv'): P[(r['draw'], float(r['epoch']), int(r['width']), r['tag'])] = dict(p=float(r['p']), gap=float(r['gap']), train=float(r['train']), validation=float(r['validation']))
DR = sorted({k[0] for k in P}); EP = [0.25, 0.5, 1.0, 2.0, 3.0]; HI, LO = 'lr3e-04', 'lr1e-04'


def read_at(d, arm, key, target):
    """p* of an arm read along its own readout path, by linear interpolation, at the readout where `key` equals `target`."""
    path = [(P[(d, e) + arm][key], P[(d, e) + arm]['p'], e) for e in EP]
    for (x0, p0, e0), (x1, p1, e1) in zip(path, path[1:]):
        if min(x0, x1) <= target <= max(x0, x1):
            t = 0 if x1 == x0 else (target - x0) / (x1 - x0); return p0 + t * (p1 - p0), e0 + t * (e1 - e0)
    return None, None


def matched(a, b, key):
    """a's p* minus b's p* at E3 after matching on `key`: the arm whose E3 value lies inside the other's path is kept at E3, and the other is read at that value."""
    per = {}
    for d in DR:
        ta, tb = P[(d, 3.0) + a][key], P[(d, 3.0) + b][key]
        pb, eb = read_at(d, b, key, ta)
        if pb is not None: per[d] = dict(contrast=P[(d, 3.0) + a]['p'] - pb, read_arm='b', read_at_readout=eb); continue
        pa, ea = read_at(d, a, key, tb)
        if pa is not None: per[d] = dict(contrast=pa - P[(d, 3.0) + b]['p'], read_arm='a', read_at_readout=ea); continue
        per[d] = dict(contrast=None, read_arm=None, read_at_readout=None)
    vals = [x['contrast'] for x in per.values() if x['contrast'] is not None]
    return dict(per_draw=per, interval=(tint(vals) if len(vals) >= 3 else dict(n=len(vals))), draws_used=len(vals))


pairs = {'D1 (512 vs 384, 3e-4)': ((512, HI), (384, HI)), 'D2 (512 vs 768, 3e-4)': ((512, HI), (768, HI)), 'D4 (512 vs 768, 1e-4)': ((512, LO), (768, LO)), 'D3 (512 at 3e-4 vs 768 at 1e-4)': ((512, HI), (768, LO))}
out['N6_contrasts_at_matched_progress'] = {name: {key: matched(a, b, key) for key in ('train', 'gap', 'validation')} for name, (a, b) in pairs.items()}
out['N6_contrasts_at_fixed_updates_E3'] = {name: tint([P[(d, 3.0) + a]['p'] - P[(d, 3.0) + b]['p'] for d in DR]) for name, (a, b) in pairs.items()}
# the progress each arm has reached at E3, as the panel's training NLL, and where on the other arm's path that lies
out['N6_panel_train_E3'] = {f'{w}|{t}': mean([P[(d, 3.0, w, t)]['train'] for d in DR]) for w, t in ((384, HI), (512, HI), (512, LO), (768, HI), (768, LO))}

# what the pooled gap-only model (fitted in recompute.py) predicts for each contrast at E3: slope times the gap difference
beta_gap = json.loads((HERE / 'RECOMPUTE.json').read_bytes())['N6_pooled_ols_of_p_on_loss_state']['gap']['beta'][1]
out['N6_gap_model_prediction_at_E3'] = {name: dict(gap_difference=mean([P[(d, 3.0) + a]['gap'] - P[(d, 3.0) + b]['gap'] for d in DR]), predicted=beta_gap * mean([P[(d, 3.0) + a]['gap'] - P[(d, 3.0) + b]['gap'] for d in DR]), observed=mean([P[(d, 3.0) + a]['p'] - P[(d, 3.0) + b]['p'] for d in DR])) for name, (a, b) in pairs.items()}


# ---------------------------------------------------------------- N4 and N3: the readout at which each width's p* is largest
def peak_epochs(path, widths):
    pts = rows(path); draws = sorted({r['draw'] for r in pts}); epochs = sorted({int(float(r['epoch'])) for r in pts})
    per = {w: {d: max(epochs, key=lambda e: float(next(r for r in pts if r['draw'] == d and int(float(r['epoch'])) == e)[f'p_{w}'])) for d in draws} for w in widths}
    panel = {w: max(epochs, key=lambda e: mean([float(r[f'p_{w}']) for r in pts if int(float(r['epoch'])) == e])) for w in widths}
    return dict(per_draw=per, panel=panel, epochs=epochs)


out['N4_epoch_of_peak_p_by_width'] = peak_epochs(N4 / 'POINTS.csv', [256, 384, 512, 768])
out['N3_epoch_of_peak_p_by_width'] = peak_epochs(N3 / 'POINTS.csv', [64, 96, 128, 192, 256, 384, 512, 768])

(HERE / 'RECOMPUTE_MATCHED.json').write_bytes((json.dumps(out, indent=1, default=float) + '\n').encode('utf-8'))
f4 = lambda x: f'{x:+.4f}'
print('== N6 contrasts at E3, fixed updates:', {k: (f4(v['mean']), f4(v['low']), f4(v['high'])) for k, v in out['N6_contrasts_at_fixed_updates_E3'].items()})
print('== N6 panel training NLL at E3:', {k: round(v, 4) for k, v in out['N6_panel_train_E3'].items()})
for name, m in out['N6_contrasts_at_matched_progress'].items():
    for key, v in m.items():
        iv = v['interval']; arm = {x['read_arm'] for x in v['per_draw'].values()}; rd = [round(x['read_at_readout'], 2) for x in v['per_draw'].values() if x['read_at_readout'] is not None]
        print(name, 'matched on', key, ':', (f4(iv['mean']), f4(iv['low']), f4(iv['high']), f"{iv['positive']}/{iv['n']} positive") if 'low' in iv else iv, '| arm read along its path:', arm, 'at readouts', rd)
print('== gap-model prediction at E3:', {k: {q: round(x, 4) for q, x in v.items()} for k, v in out['N6_gap_model_prediction_at_E3'].items()})
print('== N4 epoch of peak p* by width: panel', out['N4_epoch_of_peak_p_by_width']['panel'], 'per draw', out['N4_epoch_of_peak_p_by_width']['per_draw'])
print('== N3 epoch of peak p* by width: panel', out['N3_epoch_of_peak_p_by_width']['panel'], 'per draw', {w: sorted(v.values()) for w, v in out['N3_epoch_of_peak_p_by_width']['per_draw'].items()})
