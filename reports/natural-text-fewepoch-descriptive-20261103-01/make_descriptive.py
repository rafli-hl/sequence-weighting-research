"""The DESCRIPTIVE section of the few-epoch result (owner decision 20261103-02). Native Python 3.12 -I -B. Reads the sealed outputs and Run A's t00 records; writes DESCRIPTIVE.md and DESCRIPTIVE_CHECK.json next to this file. Each owner claim is tested against ANALYSIS.json, and against POINTS.csv where ANALYSIS.json keeps no per-draw value. RESULT.md is not touched: its layout is frozen and bound by hash."""
import csv, hashlib, json, math, sys
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = Path(r'D:\sequence-weighting-research'); AN = ROOT / 'reports/natural-text-fewepoch-analysis-20261103-01'; RES = ROOT / 'reports/natural-text-fewepoch-result-20261103-01'; RUN_A = ROOT / 'work/runs/natural-text-fewepoch-a-20261101-01'
load = lambda p: json.loads(Path(p).read_bytes()); sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
A = load(AN / 'ANALYSIS.json'); LR = load(RUN_A / 'LR_SELECTION.json'); points = {(r['draw'], float(r['epoch'])): r for r in csv.DictReader((AN / 'POINTS.csv').read_text(encoding='utf-8').splitlines())}
W, DRAWS = A['widths'], A['draws_available']; READ = ['E0.25', 'E0.5', 'E1', 'E2', 'E3']; ep = lambda k: float(k[1:]); BR = A['by_readout']; idx = {w: W.index(w) for w in W}
p = lambda d, w, k: float(points[(d, ep(k))][f'p_{w}'])
def num(x, n=4, plus=False):
    s = f'{abs(x):.{n}f}'; return ('−' if x < 0 else '+' if plus else '') + s
checks = []
def check(name, ok, detail=None):
    checks.append(dict(check=name, ok=bool(ok), detail=detail))
    if not ok: print('FAILED', name, detail)
# ---- recomputed from POINTS.csv against ANALYSIS.json
for k in READ:
    for w in W:
        panel = sum(p(d, w, k) for d in DRAWS) / len(DRAWS); check(f'panel {k} {w}: POINTS equals ANALYSIS', abs(panel - BR[k]['curve'][idx[w]]) < 1e-12)
    for d in DRAWS:
        check(f'argmax {k} {d}: POINTS equals ANALYSIS', max(W, key=lambda w: p(d, w, k)) == BR[k]['per_draw_argmax'][d])
x = [math.log2(w) for w in (384, 512, 768)]; xb = sum(x) / 3; sxx = sum((a - xb) ** 2 for a in x); wt = [(a - xb) / sxx for a in x]; identity = []
for k in READ:
    for d in DRAWS:
        a, b, c = p(d, 384, k), p(d, 512, k), p(d, 768, k); slope = wt[0] * a + wt[1] * b + wt[2] * c; two = wt[2] * (c - a) + wt[1] * (b - a); identity.append(max(abs(slope - float(points[(d, ep(k))]['fall'])), abs(slope - two)))
check('the OLS weights reproduce every FALL value in POINTS, and the two-term form equals them', max(identity) < 1e-12, max(identity))
check('E3 FALL values in ANALYSIS equal POINTS', all(abs(A['primaries']['FALL']['values'][d] - float(points[(d, 3.0)]['fall'])) < 1e-12 for d in DRAWS))
# ---- the owner's claims
argmax_all = all(BR[k]['per_draw_argmax'][d] == 512 for k in READ for d in DRAWS); panel_argmax = all(BR[k]['argmax_width'] == 512 for k in READ)
below_panel = all(BR[k]['curve'][idx[768]] < BR[k]['curve'][idx[512]] for k in READ); below_draw = all(p(d, 768, k) < p(d, 512, k) for k in READ for d in DRAWS)
e3 = [BR['E3']['curve'][idx[w]] for w in (384, 512, 768)]; e3_round = [round(v, 3) for v in e3]
fall_mean = {k: BR[k]['fall']['mean'] for k in READ}; fall_iv = {k: BR[k]['fall']['interval'] for k in READ}; fall_pos = {k: BR[k]['fall']['positive'] for k in READ}
sign_panel = {k: (BR[k]['curve'][idx[768]] > BR[k]['curve'][idx[384]]) == (fall_mean[k] > 0) for k in READ}
mismatch = [(k, d) for k in READ for d in DRAWS if (p(d, 768, k) > p(d, 384, k)) != (float(points[(d, ep(k))]['fall']) > 0)]
above_e3 = sum(p(d, 768, 'E3') > p(d, 384, 'E3') for d in DRAWS)
pw = LR['per_rate']; v_1e4, v_3e4 = pw['lr1e-04']['per_width']['768']['E3'], pw['lr3e-04']['per_width']['768']['E3']
t00 = {w: {t: load(RUN_A / f't00/w{w}/{t}/record.json') for t in ('lr1e-04', 'lr3e-04')} for w in (384, 512, 768)}
last = lambda w, t: t00[w][t]['readouts'][-1]; val = lambda w, t: last(w, t)['validation_loss']; trn = lambda w, t: last(w, t)['train_loss']; gap = lambda w, t: val(w, t) - trn(w, t)
check('LR_SELECTION equals the t00 records at 768', abs(v_1e4 - val(768, 'lr1e-04')) < 1e-12 and abs(v_3e4 - val(768, 'lr3e-04')) < 1e-12)
lower_all = all(a['validation_loss'] < b['validation_loss'] for a, b in zip(t00[768]['lr1e-04']['readouts'], t00[768]['lr3e-04']['readouts']))
claims = [
 dict(claim='At every readout E0.25-E3, the per-draw argmax width is 512 in 10/10 draws', verdict='HOLDS', holds=argmax_all and panel_argmax, source='ANALYSIS.json by_readout.*.per_draw_argmax; recomputed from POINTS.csv'),
 dict(claim='p* at 768 is below p* at 512', verdict='HOLDS', holds=below_panel and below_draw, source='ANALYSIS.json by_readout.*.curve for the panel; POINTS.csv for each of the 50 draw-readout points'),
 dict(claim='E3 panel 0.098, 0.118, 0.104 at 384, 512, 768', verdict='HOLDS', holds=e3_round == [0.098, 0.118, 0.104], source='ANALYSIS.json by_readout.E3.curve'),
 dict(claim='The FALL slope over 384-768 stays positive', verdict='DOES NOT HOLD AS WORDED', holds=not all(v > 0 for v in fall_mean.values()), source='ANALYSIS.json by_readout.*.fall'),
 dict(claim='It is positive because 768 sits above 384', verdict='HOLDS AS ARITHMETIC ON THE PANEL', holds=all(sign_panel.values()), source='ANALYSIS.json curves and fall means; the OLS weights, checked against every FALL value in POINTS.csv'),
 dict(claim='On t00, 768 had lower validation NLL at 1e-4 than at 3e-4', verdict='HOLDS', holds=v_1e4 < v_3e4 and lower_all, source='LR_SELECTION.json and t00/w768/*/record.json. ANALYSIS.json holds no t00 value, so this one could not be verified from it'),
]
for c in claims: check('claim: ' + c['claim'], c['holds'], c['verdict'])
if not all(c['ok'] for c in checks): raise SystemExit('A check failed; nothing written')
# ---- the tables
def contrast(k, a, b):
    v = [p(d, a, k) - p(d, b, k) for d in DRAWS]; return sum(v) / len(v), min(v), max(v)
T1 = ['| Readout | Panel p\\* at 384 | at 512 | at 768 | Per-draw argmax | 512 − 384, mean (lowest, highest draw) | 512 − 768, mean (lowest, highest draw) |', '|---|---|---|---|---|---|---|']
for k in READ:
    c = BR[k]['curve']; a1, a2, a3 = contrast(k, 512, 384); b1, b2, b3 = contrast(k, 512, 768); T1.append(f"| {k} | {num(c[idx[384]])} | {num(c[idx[512]])} | {num(c[idx[768]])} | 512 ×{sum(BR[k]['per_draw_argmax'][d] == 512 for d in DRAWS)} | {num(a1, 4, True)} ({num(a2, 4, True)}, {num(a3, 4, True)}) | {num(b1, 4, True)} ({num(b2, 4, True)}, {num(b3, 4, True)}) |")
T2 = ['| Readout | FALL statistic, unadjusted 95% interval (df 9) | Draws above 0 | Panel p\\* at 768 − at 384 | Draws with 768 above 384 |', '|---|---|---|---|---|']
for k in READ:
    c = BR[k]['curve']; T2.append(f"| {k} | {num(fall_mean[k], 4, True)} [{num(fall_iv[k][0], 4, True)}, {num(fall_iv[k][1], 4, True)}] | {fall_pos[k]} | {num(c[idx[768]] - c[idx[384]], 4, True)} | {sum(p(d, 768, k) > p(d, 384, k) for d in DRAWS)} |")
T3 = ['| Width | Validation NLL at E3: 1e-4 | 3e-4 | Training NLL at E3: 1e-4 | 3e-4 | Change in training NLL, 1e-4 to 3e-4 | Gap at E3: 1e-4 | 3e-4 |', '|---|---|---|---|---|---|---|---|']
for w in (384, 512, 768):
    best = 'lr1e-04' if val(w, 'lr1e-04') < val(w, 'lr3e-04') else 'lr3e-04'; b = lambda t, s: f'**{s}**' if t == best else s
    T3.append(f"| {w} | {b('lr1e-04', num(val(w, 'lr1e-04')))} | {b('lr3e-04', num(val(w, 'lr3e-04')))} | {num(trn(w, 'lr1e-04'))} | {num(trn(w, 'lr3e-04'))} | {num(trn(w, 'lr3e-04') - trn(w, 'lr1e-04'), 4, True)} | {num(gap(w, 'lr1e-04'))} | {num(gap(w, 'lr3e-04'))} |")
T4 = ['| Readout | E0.25 | E0.5 | E1 | E2 | E3 |', '|---|---|---|---|---|---|'] + [f"| 768 at {r} | " + ' | '.join(num(x['validation_loss']) for x in t00[768][t]['readouts']) + ' |' for r, t in (('1e-4', 'lr1e-04'), ('3e-4', 'lr3e-04'))]
L = A['losses']; cl = lambda w: L[f'{w}|clipping']; g = lambda w, k: BR[k]['gap'][idx[w]]; ec = lambda w: L[f'{w}|E0']['validation']
T5 = ['| Claim as you worded it | Verdict | Source |', '|---|---|---|'] + [f"| {c['claim']} | **{c['verdict']}** | {c['source']} |" for c in claims]
fd08 = float(points[('d08', 3.0)]['fall']); gd08 = p('d08', 768, 'E3') - p('d08', 384, 'E3')
md = f"""# Few-epoch study: DESCRIPTIVE section

**DESCRIPTIVE ONLY: sealed secondaries, not a primary.** You asked for these comparisons after the outcomes had been seen. None is pre-registered and none is a test. They change no label. The labels stay those of `reports/natural-text-fewepoch-result-20261103-01/RESULT.md`: **M CAPACITY_BEYOND_MEMORIZATION, FALL CONTINUES_RISING, RISE RISES,** with NOT_OVERFIT at every width.

**Where this sits.** `RESULT.md` stays exactly as `make_results_report.py` wrote it, because its layout was frozen and bound by hash before any outcome was opened. This file sits beside it.

**Read sections 1 and 2 together.** Section 1 is what was measured. Section 2 is a reason it may not be about width alone. The reason in section 2 is a hypothesis: nothing in this study measures p\\* at another rate.

## 1. At every readout, the largest p\\* is at 512

All at 3e-4, the one rate of Runs B1 and B2.

{chr(10).join(T1)}

- **The argmax is 512 in all 50 draw-readout points,** and on the panel at all five readouts.
- **p\\* at 768 is below p\\* at 512 in all 50 points.** The smallest difference is {num(min(contrast(k, 512, 768)[1] for k in READ), 4, True)}.
- **The gap does not fall with it.** At E0.25–E2 the panel gap at 768 is above that at 512 ({num(g(768, 'E0.25'))} against {num(g(512, 'E0.25'))} at E0.25, {num(g(768, 'E2'))} against {num(g(512, 'E2'))} at E2). At E3 it is just below ({num(g(768, 'E3'))} against {num(g(512, 'E3'))}).
- **What 10/10 means.** All ten draws share the pre-training pool, the tokenizer, the recipe and the rate, so 10/10 shows consistency across corpus draws, not across those.

### The FALL slope, which does not always stay positive

{chr(10).join(T2)}

- **"Stays positive" does not hold as worded.** The statistic is positive at E3, the primary, in 9 of 10 draws (d08: {num(fd08, 4, True)}). At E2 its interval spans 0. At E0.25, E0.5 and E1 it is negative, with intervals below 0.
- **"Because 768 sits above 384" holds as arithmetic on the panel.** The OLS weights give FALL = {wt[2]:.4f} × (p\\*768 − p\\*384) − {abs(wt[1]):.4f} × (p\\*512 − p\\*384), checked against every FALL value in `POINTS.csv`. So the sign of the panel slope follows 768 against 384 at all five readouts: 768 is above 384 at E2 and E3, and below it at E0.25–E1. It is an identity about the statistic, not a cause.
- **It can differ in a single draw.** The signs differ in {len(mismatch)} of 50 points. At E3 that is d08, where 768 is above 384 by {num(gd08, 4, True)} and the slope is still negative, because of the second term.
- **So FALL mostly compares 768 with 384.** The weight on 512 is about a ninth of that on 768, so FALL says little about the shape in the table above.

**How this stands against the sealed text.** Sealed reading 4 says "no turn-down within this ladder". That sentence reads the slope. In the curve itself, p\\* falls from 512 to 768 in every draw at every readout. The frozen words "an interior p\\* peak" require FALL TURNS_DOWN with RISE RISES, and FALL is CONTINUES_RISING, so **this study does not report an interior peak as a result.** Neither can this section; that is what a fresh confirmation would be for.

## 2. The learning-rate caveat: 768 may be running at a rate too high for it

**The caveat.** On t00, 768 had lower validation NLL at 1e-4 than at 3e-4, so the drop at 768 may reflect a rate that is too high for 768. The common rate of 3e-4 was selected on the mean over eight widths, by validation NLL only. It is the lowest at 192–512 and not at 768.

**Measured on t00: one draw, one fit per width and rate, no interval.** In bold, the lower validation NLL of the two rates.

{chr(10).join(T3)}

Validation NLL at 768 on t00, lower at 1e-4 at all five readouts:

{chr(10).join(T4)}

**What fits the caveat:**
- **Validation.** At 768 the lower rate is better at every readout, by {num(val(768, 'lr3e-04') - val(768, 'lr1e-04'))} at E3.
- **Training.** Tripling the rate lowered training NLL at E3 by {num(trn(384, 'lr1e-04') - trn(384, 'lr3e-04'))} at 384 and {num(trn(512, 'lr1e-04') - trn(512, 'lr3e-04'))} at 512, and by only {num(trn(768, 'lr1e-04') - trn(768, 'lr3e-04'))} at 768.
- **Clipping and gradient norm, at 3e-4 over the ten draws.** Both rise with width through 512 (clip fraction {cl(64)['clip_fraction_mean']:.3f} at 64 to {cl(512)['clip_fraction_mean']:.3f} at 512; mean norm {cl(64)['gradient_norm_mean']:.3f} to {cl(512)['gradient_norm_mean']:.3f}), then drop at 768 ({cl(768)['clip_fraction_mean']:.3f}; {cl(768)['gradient_norm_mean']:.3f}). On t00 in the third epoch, the step from 512 to 768 takes the mean norm from {t00[512]['lr3e-04']['epochs'][2]['gradient_norm_mean']:.3f} to {t00[768]['lr3e-04']['epochs'][2]['gradient_norm_mean']:.3f} at 3e-4, and only from {t00[512]['lr1e-04']['epochs'][2]['gradient_norm_mean']:.3f} to {t00[768]['lr1e-04']['epochs'][2]['gradient_norm_mean']:.3f} at 1e-4; the clip fraction goes from {t00[512]['lr3e-04']['epochs'][2]['clip_fraction']:.3f} to {t00[768]['lr3e-04']['epochs'][2]['clip_fraction']:.3f}, and from {t00[512]['lr1e-04']['epochs'][2]['clip_fraction']:.3f} to {t00[768]['lr1e-04']['epochs'][2]['clip_fraction']:.3f}.

**What limits it:**
- **p\\* at 1e-4 was never recorded.** Run A wrote no per-sequence adaptation arrays, so nothing measures what the lower rate does to p\\*, in either direction.
- **The gap points the other way.** On t00 the gap at 768 is smaller at 1e-4 ({num(gap(768, 'lr1e-04'))} against {num(gap(768, 'lr3e-04'))}). If p\\* tracked the gap, it would fall at the lower rate, not rise.
- **3e-4 is not failing at 768.** Over the ten draws, 768 has the lowest validation NLL of all widths ({num(L['768|E3']['validation'])}, against {num(L['512|E3']['validation'])} at 512) and passes NOT_OVERFIT.
- **Another width difference is present.** After the same pre-training, 768 starts from a higher E0 validation NLL than 384 and 512 ({num(ec(768))}, against {num(ec(384))} and {num(ec(512))}). A change of adaptation rate does not touch that.
- **The grid is coarse.** The rates tested are 3e-5, 1e-4, 3e-4, 1e-3 and 3e-3, so the best rate for 768 is not located.

**No mechanism is claimed in either direction.**

## 3. How your claims were checked

{chr(10).join(T5)}

{len(checks):,} checks pass (`DESCRIPTIVE_CHECK.json`). The per-draw differences and the sign counts come from `POINTS.csv`, because `ANALYSIS.json` keeps panel curves and argmaxes, not p\\* per draw and width. `POINTS.csv` is itself recomputed from the run files in `RESULT_CHECK.json` (PASS, 0 mismatches), and here its panel means and argmaxes are compared with `ANALYSIS.json` again.
"""
(HERE / 'DESCRIPTIVE.md').write_bytes(md.encode('utf-8'))
rec = dict(schema=1, purpose='The check of the DESCRIPTIVE section; owner decision 20261103-02', inputs={k: sha(v) for k, v in {'ANALYSIS.json': AN / 'ANALYSIS.json', 'POINTS.csv': AN / 'POINTS.csv', 'RESULT.md': RES / 'RESULT.md', 'RESULT_CHECK.json': RES / 'RESULT_CHECK.json', 'LR_SELECTION.json': RUN_A / 'LR_SELECTION.json'}.items()}, passed=sum(c['ok'] for c in checks), total=len(checks), claims=[{k: v for k, v in c.items()} for c in claims], ols_weights=dict(zip(('384', '512', '768'), wt)), sign_mismatches=[dict(readout=k, draw=d) for k, d in mismatch], largest_identity_difference=max(identity), e3_panel=dict(zip(('384', '512', '768'), e3)), draws_with_768_above_384_at_e3=above_e3, checks=[c for c in checks if c['check'].startswith(('claim', 'the OLS', 'E3 FALL', 'LR_SELECTION'))])
(HERE / 'DESCRIPTIVE_CHECK.json').write_bytes((json.dumps(rec, indent=1) + '\n').encode('utf-8'))
print(json.dumps(dict(passed=rec['passed'], total=rec['total'], verdicts=[(c['claim'], c['verdict'], c['holds']) for c in claims], mismatches=len(mismatch), weights=wt), indent=0))
