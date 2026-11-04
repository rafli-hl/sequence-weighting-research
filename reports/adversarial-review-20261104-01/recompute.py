"""Recomputations for the adversarial review, from saved tables only: POINTS.csv, FITS.csv, ANALYSIS.json under reports/.
Reads nothing under work/ and no per-sequence array. Writes RECOMPUTE.json next to this script and prints the figures quoted in
REVIEW.md. Stdlib only.

  python -I -B recompute.py
"""
import csv, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent; R = HERE.parent
N6 = R / 'natural-text-peak-analysis-20261103-01'; N5 = R / 'natural-text-fewepoch-analysis-20261103-01'; N4 = R / 'natural-text-lateturn-analysis-20261031-01'
N3 = R / 'natural-text-onerate-analysis-20261030-02'; N1 = R / 'natural-text-ladder-analysis-20261029-01/sealed-analysis'; S = R / 'capacity-shift-followup-analysis-20261027-01'
T = {2: 4.302652730, 3: 3.182446305, 4: 2.776445105, 5: 2.570581836, 8: 2.306004135, 9: 2.262157163, 11: 2.200985160}
rows = lambda p: list(csv.DictReader(p.read_text(encoding='utf-8').splitlines()))
load = lambda p: json.loads(p.read_bytes().decode('utf-8'))
out = {}


def mean(v): return sum(v) / len(v)
def sd(v): m = mean(v); return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
def tint(v):
    n = len(v); m = mean(v); s = sd(v); h = T[n - 1] * s / math.sqrt(n)
    return dict(n=n, mean=m, sd=s, low=m - h, high=m + h, negative=sum(x < 0 for x in v), positive=sum(x > 0 for x in v))
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r
def spearman(a, b):
    ra, rb = rank(a), rank(b); ma, mb = mean(ra), mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float('nan')
def ols(X, y):
    """Least squares by normal equations with Gaussian elimination: beta, R^2 and residuals."""
    k = len(X[0]); A = [[sum(X[i][a] * X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]; B = [sum(X[i][a] * y[i] for i in range(len(X))) for a in range(k)]
    M = [row[:] + [B[a]] for a, row in enumerate(A)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c])); M[c], M[piv] = M[piv], M[c]
        for r in range(k):
            if r != c and M[c][c] != 0:
                f = M[r][c] / M[c][c]; M[r] = [x - f * z for x, z in zip(M[r], M[c])]
    beta = [M[c][k] / M[c][c] for c in range(k)]
    yhat = [sum(b * x for b, x in zip(beta, X[i])) for i in range(len(X))]; my = mean(y)
    r2 = 1 - sum((a - b) ** 2 for a, b in zip(y, yhat)) / sum((a - my) ** 2 for a in y)
    return beta, r2, [a - b for a, b in zip(y, yhat)]


# ---------------------------------------------------------------- N6: the peak confirmation
P = {}
for r in rows(N6 / 'POINTS.csv'): P[(r['draw'], float(r['epoch']), int(r['width']), r['tag'])] = dict(p=float(r['p']), gap=float(r['gap']), train=float(r['train']), validation=float(r['validation']))
DR = sorted({k[0] for k in P}); EP = [0.25, 0.5, 1.0, 2.0, 3.0]; HI, LO = 'lr3e-04', 'lr1e-04'
ARMS = [(384, HI), (512, HI), (512, LO), (768, HI), (768, LO)]
A6 = load(N6 / 'ANALYSIS.json')
con = {'D1': lambda d, e: P[(d, e, 512, HI)]['p'] - P[(d, e, 384, HI)]['p'], 'D2': lambda d, e: P[(d, e, 512, HI)]['p'] - P[(d, e, 768, HI)]['p'],
       'D4': lambda d, e: P[(d, e, 512, LO)]['p'] - P[(d, e, 768, LO)]['p'], 'D3': lambda d, e: P[(d, e, 512, HI)]['p'] - P[(d, e, 768, LO)]['p']}
n6 = {}
for k, f in con.items():
    v = [f(d, 3.0) for d in DR]; full = tint(v)
    sealed = A6['contrasts'][k]['interval']; agree = abs(full['mean'] - sealed['mean']) < 1e-9 and abs(full['low'] - sealed['interval'][0]) < 1e-9
    loo = {d: tint([f(x, 3.0) for x in DR if x != d]) for d in DR}
    n6[k] = dict(values=dict(zip(DR, v)), full=full, equals_sealed=agree,
                 leave_one_out={d: dict(mean=i['mean'], low=i['low'], high=i['high'], excludes_zero=(i['high'] < 0 or i['low'] > 0)) for d, i in loo.items()},
                 sign_test_two_sided_p=2 ** (1 - len(v)) if full['negative'] in (0, len(v)) else None)
out['N6_contrasts_at_E3'] = n6


# Matched progress: p*(512 at 3e-4) read along its own readout path at the training NLL (or the gap, or the validation NLL) that 512 at 1e-4 reaches at E3.
def interp_on_path(d, w, tag, key, target):
    path = [(P[(d, e, w, tag)][key], P[(d, e, w, tag)]['p'], e) for e in EP]
    for (x0, p0, e0), (x1, p1, e1) in zip(path, path[1:]):
        lo, hi = min(x0, x1), max(x0, x1)
        if lo <= target <= hi:
            t = 0 if x1 == x0 else (target - x0) / (x1 - x0); return p0 + t * (p1 - p0), f'E{e0:g}-E{e1:g}'
    return None, 'outside the path'


mp = {}
for key in ('train', 'gap', 'validation'):
    per = {}
    for d in DR:
        tgt = P[(d, 3.0, 512, LO)][key]; pi, seg = interp_on_path(d, 512, HI, key, tgt)
        per[d] = dict(target=tgt, p_512_3e4_at_matched=pi, segment=seg, p_512_1e4_E3=P[(d, 3.0, 512, LO)]['p'], p_768_1e4_E3=P[(d, 3.0, 768, LO)]['p'],
                      D4_matched=(None if pi is None else pi - P[(d, 3.0, 768, LO)]['p']), rate_effect_512_at_matched=(None if pi is None else P[(d, 3.0, 512, LO)]['p'] - pi))
    vals = [x['D4_matched'] for x in per.values() if x['D4_matched'] is not None]; re = [x['rate_effect_512_at_matched'] for x in per.values() if x['rate_effect_512_at_matched'] is not None]
    mp[key] = dict(per_draw=per, D4_matched_interval=(tint(vals) if len(vals) == 6 else dict(n=len(vals))), rate_effect_512_at_matched_interval=(tint(re) if len(re) == 6 else dict(n=len(re))))
per = {}
for d in DR:
    tgt = P[(d, 3.0, 768, LO)]['train']; pi, seg = interp_on_path(d, 768, HI, 'train', tgt)
    per[d] = dict(target=tgt, p_768_3e4_at_matched=pi, segment=seg, p_768_1e4_E3=P[(d, 3.0, 768, LO)]['p'], rate_effect_768_at_matched=(None if pi is None else P[(d, 3.0, 768, LO)]['p'] - pi))
vals = [x['rate_effect_768_at_matched'] for x in per.values() if x['rate_effect_768_at_matched'] is not None]
mp['train_768'] = dict(per_draw=per, interval=(tint(vals) if len(vals) == 6 else dict(n=len(vals))))
out['N6_matched_progress'] = mp

# p* against the loss state: Spearman of p* with the gap over the 5 arms, per draw and readout; tallies; a pooled OLS of p* on the loss state.
sp = {f'E{e:g}': {d: spearman([P[(d, e, w, t)]['p'] for w, t in ARMS], [P[(d, e, w, t)]['gap'] for w, t in ARMS]) for d in DR} for e in EP}
out['N6_spearman_p_vs_gap_over_5_arms'] = {e: dict(per_draw=v, mean=mean(list(v.values()))) for e, v in sp.items()}
above = lambda e, tag, key: sum(P[(d, e, 512, tag)][key] > P[(d, e, 768, tag)][key] for d in DR)
out['N6_tally_512_above_768'] = {f'E{e:g}': dict(p_3e4=above(e, HI, 'p'), gap_3e4=above(e, HI, 'gap'), p_1e4=above(e, LO, 'p'), gap_1e4=above(e, LO, 'gap')) for e in EP}
keys = sorted(P); y = [P[k]['p'] for k in keys]
X_gap = [[1, P[k]['gap']] for k in keys]; X_tv = [[1, P[k]['train'], P[k]['validation']] for k in keys]; X_tve = [[1, P[k]['train'], P[k]['validation'], math.log2(k[1])] for k in keys]
regs = {}
for name, X in (('gap', X_gap), ('train+validation', X_tv), ('train+validation+log2readout', X_tve)):
    beta, r2, res = ols(X, y); res = dict(zip(keys, res)); adj = {}
    for c, (a, b) in {'D1': ((512, HI), (384, HI)), 'D2': ((512, HI), (768, HI)), 'D4': ((512, LO), (768, LO))}.items():
        adj[c] = tint([res[(d, 3.0) + a] - res[(d, 3.0) + b] for d in DR])
    regs[name] = dict(beta=beta, r2=r2, residual_contrasts_at_E3=adj, residual_mean_by_arm_E3={f'{w}|{t}': mean([res[(d, 3.0, w, t)] for d in DR]) for w, t in ARMS})
out['N6_pooled_ols_of_p_on_loss_state'] = regs
out['N6_E0'] = {k: A6['losses'][k] for k in A6['losses'] if k.endswith('|E0')}
out['N6_panel_E3'] = {f'{w}|{t}': {q: mean([P[(d, 3.0, w, t)][q] for d in DR]) for q in ('p', 'gap', 'train', 'validation')} for w, t in ARMS}
F6 = rows(N6 / 'FITS.csv')
out['N6_fit_quality'] = dict(fits=len(F6), objective_over_J0_min=min(float(r['objective']) / float(r['J0']) for r in F6), objective_over_J0_max=max(float(r['objective']) / float(r['J0']) for r in F6),
                             largest_negative_fraction=max(float(r['negative_fraction']) for r in F6), p_min=min(float(r['p']) for r in F6), p_max=max(float(r['p']) for r in F6))

# ---------------------------------------------------------------- N5: the few-epoch ladder
W5 = [64, 96, 128, 192, 256, 384, 512, 768]; Q = {}
for r in rows(N5 / 'POINTS.csv'):
    Q[(r['draw'], float(r['epoch']))] = dict(p=[float(r[f'p_{w}']) for w in W5], gap=[float(r[f'gap_{w}']) for w in W5], fall=float(r['fall']), rise=float(r['rise']))
D5 = sorted({k[0] for k in Q}); n5 = {}
for e in EP:
    rho = {d: spearman(Q[(d, e)]['p'], Q[(d, e)]['gap']) for d in D5}
    pan_p = [mean([Q[(d, e)]['p'][i] for d in D5]) for i in range(8)]; pan_g = [mean([Q[(d, e)]['gap'][i] for d in D5]) for i in range(8)]
    n5[f'E{e:g}'] = dict(spearman_per_draw=rho, spearman_mean=mean(list(rho.values())), spearman_panel=spearman(pan_p, pan_g), panel_argmax_p=W5[pan_p.index(max(pan_p))], panel_argmax_gap=W5[pan_g.index(max(pan_g))],
                        draws_with_gap_argmax_512=sum(W5[Q[(d, e)]['gap'].index(max(Q[(d, e)]['gap']))] == 512 for d in D5), draws_with_p_argmax_512=sum(W5[Q[(d, e)]['p'].index(max(Q[(d, e)]['p']))] == 512 for d in D5),
                        draws_gap_768_below_512=sum(Q[(d, e)]['gap'][7] < Q[(d, e)]['gap'][6] for d in D5), panel_p=pan_p, panel_gap=pan_g)
out['N5_p_vs_gap_over_8_widths'] = n5
fall = [Q[(d, 3.0)]['fall'] for d in D5]
out['N5_FALL_E3'] = dict(full=tint(fall), leave_one_out={d: (lambda i: dict(low=i['low'], high=i['high'], excludes_zero=i['low'] > 0))(tint([Q[(x, 3.0)]['fall'] for x in D5 if x != d])) for d in D5})
F5 = rows(N5 / 'FITS.csv'); out['N5_fit_quality'] = dict(fits=len(F5), p_min=min(float(r['p']) for r in F5), p_max=max(float(r['p']) for r in F5), objective_over_J0_max=max(float(r['objective']) / float(r['J0']) for r in F5))


# ---------------------------------------------------------------- N4 and N3: the late turn-down, with the losses behind it
def late(points_path, analysis_path, widths, epochs):
    pts = rows(points_path); A = load(analysis_path); L = A['losses']; byep = {}
    for e in epochs:
        sub = [r for r in pts if int(float(r['epoch'])) == e]
        pan = {w: mean([float(r[f'p_{w}']) for r in sub]) for w in widths}
        byep[f'E{e}'] = dict(panel_p=pan, train={w: L[f'{w}|E{e}']['train'] for w in widths}, validation={w: L[f'{w}|E{e}']['validation'] for w in widths}, gap={w: L[f'{w}|E{e}']['gap'] for w in widths},
                            per_draw_argmax={r['draw']: widths[max(range(len(widths)), key=lambda i: float(r[f'p_{widths[i]}']))] for r in sub})
    return byep


out['N4_by_epoch'] = late(N4 / 'POINTS.csv', N4 / 'ANALYSIS.json', [256, 384, 512, 768], [1, 2, 4, 6, 8, 12, 16, 24, 32])
out['N3_by_epoch'] = late(N3 / 'POINTS.csv', N3 / 'ANALYSIS.json', [64, 96, 128, 192, 256, 384, 512, 768], [1, 2, 4, 6, 8, 12, 16, 24, 32])
p4 = {}
for r in rows(N4 / 'POINTS.csv'):
    if int(r['epoch']) in (8, 32): p4.setdefault(r['draw'], {})[int(r['epoch'])] = dict(location_log2=float(r['location_log2']), turn=float(r['turn']), p=[float(r[f'p_{w}']) for w in (256, 384, 512, 768)])
out['N4_P1_P3_per_draw'] = {d: dict(L_E8=v[8]['location_log2'], L_E32=v[32]['location_log2'], S=v[8]['location_log2'] - v[32]['location_log2'], P1_turn_E32=v[32]['turn'], E32_curve=v[32]['p'], E8_curve=v[8]['p']) for d, v in p4.items()}
F4 = rows(N4 / 'FITS.csv'); out['N4_negative_gain_fraction_E32_by_width'] = {w: max(float(r['negative_fraction']) for r in F4 if int(r['width']) == w and int(float(r['epoch'])) == 32) for w in (256, 384, 512, 768)}
F3 = rows(N3 / 'FITS.csv'); out['N3_negative_gain_fraction_E32_by_width'] = {w: max(float(r['negative_fraction']) for r in F3 if int(r['width']) == w and int(float(r['epoch'])) == 32) for w in (64, 96, 128, 192, 256, 384, 512, 768)}

# ---------------------------------------------------------------- N1: the ladder, rank agreement of the panel p* with the panel gap by epoch
A1 = load(N1 / 'ANALYSIS.json'); pts1 = rows(N1 / 'POINTS.csv'); W1 = [64, 96, 128, 192, 256, 384]; n1 = {}
for e in (4, 6, 8, 12, 16, 24, 32):
    sub = [r for r in pts1 if int(r['epoch']) == e]; pan = [mean([float(r[f'p_{w}']) for r in sub]) for w in W1]
    gap = [A1['losses'][f'{w}|E{e}']['gap'] if f'{w}|E{e}' in A1['losses'] else None for w in W1]
    n1[f'E{e}'] = dict(panel_p=pan, panel_gap=gap, spearman=(spearman(pan, gap) if None not in gap else None))
out['N1_panel_p_vs_gap'] = n1

# ---------------------------------------------------------------- S: the synthetic follow-up, saturation and the scale of p*
ptsS = [r for r in rows(S / 'POINTS.csv') if r['readout'] == 'primary|R']; WS = [32, 48, 64, 96, 128, 192, 256, 384]
defined = [r for r in ptsS if r['defined'] == 'True']; allp = [float(r[f'p_{w}']) for r in defined for w in WS]; flagged = [r for r in defined if r['flagged'] == 'True']
out['S_saturation'] = dict(defined_points=len(defined), flagged_points=len(flagged), points_whose_argmax_fit_is_at_8=sum(max(float(r[f'p_{w}']) for w in WS) >= 7.999 for r in defined),
                           points_with_two_or_more_fits_at_8=sum(sum(float(r[f'p_{w}']) >= 7.999 for w in WS) >= 2 for r in defined), p_min=min(allp), p_max=max(allp), p_median=sorted(allp)[len(allp) // 2],
                           by_epoch={e: dict(points=sum(int(r['epoch']) == e for r in defined), flagged=sum(int(r['epoch']) == e for r in flagged), fits_at_upper=sum(int(r['fits_at_upper']) for r in defined if int(r['epoch']) == e)) for e in (15, 20, 25, 30, 40)},
                           location_change_S32={f"{r['corpus']}|E{r['epoch']}": float(r['s32_location']) - float(r['location']) for r in flagged if r['s32_location']})

# ---------------------------------------------------------------- arithmetic: the estimator's scale, and tokens per parameter
out['implied_gain_ratio_1000_to_the_p'] = {str(p): 1000 ** p for p in (0.02, 0.05, 0.1, 0.117, 0.2, 0.5, 1.0, 8.0)}
PARAMS = {384: 10293504, 512: 16870400, 768: 34742784}
out['tokens'] = dict(pretraining_token_passes=2048 * 128 * 4, adaptation_token_passes=16384 * 128 * 3, unique_adaptation_tokens=16384 * 128, parameters=PARAMS,
                     adaptation_token_passes_per_parameter={w: 16384 * 128 * 3 / n for w, n in PARAMS.items()}, overfit_recipe_unique_tokens=1536 * 128, overfit_recipe_token_passes=1536 * 128 * 32)

(HERE / 'RECOMPUTE.json').write_bytes((json.dumps(out, indent=1, default=float) + '\n').encode('utf-8'))

# ---------------------------------------------------------------- print the figures quoted in the review
f4 = lambda x: f'{x:+.4f}'
print('== N6 contrasts at E3 (recomputed from POINTS.csv; equals the sealed interval?)')
for k, v in n6.items():
    print(k, 'equals sealed:', v['equals_sealed'], 'mean', f4(v['full']['mean']), 'interval', f4(v['full']['low']), f4(v['full']['high']), 'sign test p', v['sign_test_two_sided_p'])
    print('   leave-one-out intervals:', {d: (f4(i['low']), f4(i['high']), 'excl0' if i['excludes_zero'] else 'SPANS 0') for d, i in v['leave_one_out'].items()})
print('== N6 matched progress (512 at 3e-4 read at the loss state 512 at 1e-4 reaches at E3)')
for key in ('train', 'gap', 'validation'):
    m = mp[key]; iv = m['D4_matched_interval']; rv = m['rate_effect_512_at_matched_interval']
    print(key, 'D4 at matched', {d: (None if x['D4_matched'] is None else f4(x['D4_matched'])) for d, x in m['per_draw'].items()}, 'interval', (f4(iv['low']), f4(iv['high'])) if 'low' in iv else iv)
    print('   rate effect at 512 at matched', (f4(rv['mean']), f4(rv['low']), f4(rv['high'])) if 'low' in rv else rv, 'segments', {d: x['segment'] for d, x in m['per_draw'].items()})
m = mp['train_768']; iv = m['interval']; print('768: rate effect at matched training NLL', (f4(iv['mean']), f4(iv['low']), f4(iv['high'])) if 'low' in iv else iv, {d: x['segment'] for d, x in m['per_draw'].items()})
print('== N6 Spearman of p* with the gap over the 5 arms, mean over draws:', {e: round(v['mean'], 3) for e, v in out['N6_spearman_p_vs_gap_over_5_arms'].items()})
print('== N6 tally 512 above 768 (of 6):', out['N6_tally_512_above_768'])
print('== N6 pooled OLS of p* on the loss state')
for name, g in regs.items():
    print(name, 'R2', round(g['r2'], 3), 'beta', [round(b, 4) for b in g['beta']]); print('   residual contrasts at E3:', {c: (f4(i['mean']), f4(i['low']), f4(i['high'])) for c, i in g['residual_contrasts_at_E3'].items()})
print('== N6 E0', out['N6_E0']); print('== N6 panel E3', {k: {q: round(x, 4) for q, x in v.items()} for k, v in out['N6_panel_E3'].items()}); print('== N6 fit quality', out['N6_fit_quality'])
print('== N5 p* against the gap over 8 widths')
for e, v in n5.items(): print(e, 'spearman mean', round(v['spearman_mean'], 3), 'panel', round(v['spearman_panel'], 3), 'argmax p', v['panel_argmax_p'], 'argmax gap', v['panel_argmax_gap'], 'draws gap-argmax 512', v['draws_with_gap_argmax_512'], 'draws p-argmax 512', v['draws_with_p_argmax_512'], 'draws gap768<gap512', v['draws_gap_768_below_512'])
print('== N5 FALL at E3 leave-one-out', {d: ('excl0' if i['excludes_zero'] else 'SPANS 0', f4(i['low'])) for d, i in out['N5_FALL_E3']['leave_one_out'].items()}); print('== N5 fit quality', out['N5_fit_quality'])
print('== N4 by epoch: panel p* and training NLL at 384/512/768')
for e, v in out['N4_by_epoch'].items(): print(e, 'p*', {w: round(v['panel_p'][w], 4) for w in (384, 512, 768)}, 'train', {w: round(v['train'][w], 3) for w in (384, 512, 768)}, 'gap', {w: round(v['gap'][w], 3) for w in (384, 512, 768)})
print('== N4 P1/P3 per draw', {d: (round(v['L_E8'], 3), round(v['L_E32'], 3), round(v['S'], 3), round(v['P1_turn_E32'], 4)) for d, v in out['N4_P1_P3_per_draw'].items()})
print('== N4 largest negative-gain fraction at E32 by width', out['N4_negative_gain_fraction_E32_by_width']); print('== N3 largest negative-gain fraction at E32 by width', out['N3_negative_gain_fraction_E32_by_width'])
print('== N3 by epoch: panel p* and training NLL at 384/512/768')
for e, v in out['N3_by_epoch'].items(): print(e, 'p*', {w: round(v['panel_p'][w], 4) for w in (384, 512, 768)}, 'train', {w: round(v['train'][w], 3) for w in (384, 512, 768)}, 'gap', {w: round(v['gap'][w], 3) for w in (384, 512, 768)})
print('== N1 panel Spearman p* vs gap by epoch', {e: (round(v['spearman'], 3) if v['spearman'] is not None else None) for e, v in n1.items()})
print('== S saturation', {k: v for k, v in out['S_saturation'].items() if k != 'location_change_S32'})
print('== implied gain ratios', {k: round(v, 3) for k, v in out['implied_gain_ratio_1000_to_the_p'].items()}); print('== tokens', out['tokens'])
