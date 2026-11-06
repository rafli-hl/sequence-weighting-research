"""Post-hoc, assistant-run recomputation of N7's confirmed statistics from the sealed analysis output only.
Reads reports/natural-text-matched-analysis-20261105-01/POINTS.csv (sha256 234434a3...); opens nothing under work/runs/.
(1) Recomputes P1, S1, S2, S3, S4, S5 independently of matched_analysis.py: linear interpolation of 768's p* along its own
    E2.0-E3.5 readouts at the value 512 reaches at E3, 95% t interval with df = 5.
(2) Bounds the epoch-boundary concern: replaces each interpolated 768 value in P1 with the higher p* of its two bracketing
    readouts, the reading least favourable to a reversal.
It cannot check p* itself, the per-draw losses, E0 or clipping: those need the run files.
Usage: python -I -B recompute.py <path to POINTS.csv>
"""
import csv, json, math, statistics as st, sys
P = {}
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    P[(r['draw'], float(r['epoch']), int(r['width']), r['tag'])] = {k: float(r[k]) for k in ('gap', 'p', 'train', 'validation')}
D = sorted({k[0] for k in P}); EP = [2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]; LO, HI = 'lr1e-04', 'lr3e-04'; T5 = 2.570581836
def ci(v):
    m = st.mean(v); s = st.stdev(v); h = T5 * s / math.sqrt(len(v))
    return dict(n=len(v), mean=m, low=m - h, high=m + h, positive=sum(x > 0 for x in v), negative=sum(x < 0 for x in v))
def bracket(d, rate, key, tgt):
    path = [(P[(d, e, 768, rate)][key], P[(d, e, 768, rate)]['p'], e) for e in EP]
    for (x0, p0, e0), (x1, p1, e1) in zip(path, path[1:]):
        if min(x0, x1) <= tgt <= max(x0, x1):
            t = 0.0 if x1 == x0 else (tgt - x0) / (x1 - x0)
            return dict(linear=p0 + t * (p1 - p0), higher_end=max(p0, p1), between=[e0, e1], t=t)
    return None
out = {}
for name, rate, key in (('P1', LO, 'train'), ('S1', LO, 'gap'), ('S2', LO, 'validation'), ('S4', HI, 'train')):
    per = {}
    for d in D:
        b = bracket(d, rate, key, P[(d, 3.0, 512, rate)][key])
        per[d] = None if b is None else dict(contrast=P[(d, 3.0, 512, rate)]['p'] - b['linear'], **b)
    vals = [x['contrast'] for x in per.values() if x]
    out[name] = dict(per_draw=per, interval=ci(vals) if len(vals) >= 5 else dict(n=len(vals), note='fewer than 5 draws: not read'))
for name, rate in (('S3', LO), ('S5', HI)):
    out[name] = dict(interval=ci([P[(d, 3.0, 512, rate)]['p'] - P[(d, 3.0, 768, rate)]['p'] for d in D]))
worst = [P[(d, 3.0, 512, LO)]['p'] - out['P1']['per_draw'][d]['higher_end'] for d in D]
out['P1_epoch_boundary_worst_case'] = dict(interval=ci(worst), note='768 read at the higher p* of its bracket in every draw')
json.dump(out, sys.stdout, indent=1); print()
