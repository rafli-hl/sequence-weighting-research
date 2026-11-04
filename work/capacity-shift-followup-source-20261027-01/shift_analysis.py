"""Frozen capacity-shift follow-up analysis (stdlib only). Runs after the owner run; never during it.

  python -I -B shift_analysis.py <RUN_DIR> <OUT_DIR>

Every rule here is fixed before any outcome exists (PROTOCOL.md). Loading, signed gains, the bounded estimator
core.exponent on [0, 8], the location rule and the secondaries tables are the sealed ladder functions
(ladder_analysis.py is a byte copy; it reads this source's ladder_plan). Undefined fits stay undefined; no
defined-only panel mean; boundary and saturated fits are retained and counted. Corpus draws are the only
inference unit; the twelve corpus slopes are the observations of every primary interval.
"""
import csv, json, math, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import ladder_plan as plan
import ladder_analysis as la

CONDITION = 'G16'
EPS = la.EPS                               # 1e-9 sign tolerance (round-off only), as in the ladder
S32_UPPER = 32.0                           # sensitivity search bound (same 0.05 grid step and refinement)
SD_MIN_POINTS = 3                          # drop-flagged sensitivity: points a corpus needs to keep a slope
SD_MIN_CORPORA = 3                         # ... and corpora the sensitivity needs (t interval df >= 2)
# Two-sided 95% Student t critical values (0.975 quantiles), df 2..11; verified by numeric integration in the fixtures.
T95 = {2: 4.302652730, 3: 3.182446305, 4: 2.776445105, 5: 2.570581836, 6: 2.446911851, 7: 2.364624252,
       8: 2.306004135, 9: 2.262157163, 10: 2.228138852, 11: 2.200985160}
PRIMARY = dict(epochs=plan.PRIMARY_EPOCHS, min_points=4, early=(15, 20), late=(30, 40))
WINDOW_E15_E30 = dict(epochs=(15, 20, 25, 30), min_points=3, early=(15, 20), late=(25, 30))


# ------------------------------------------------------------------ estimator with a different search bound
def exponent_upper(weights, gains, upper):
    """vendor/core.exponent with the upper search bound `upper` (a multiple of 0.05) instead of 8: the same 0.05
    grid from 0, the same 50-step ternary refinement in the best bracket, candidates {0, midpoint, upper}.
    At upper = 8 it returns exactly what core.exponent returns."""
    w = [float(x) for x in weights]
    g = [float(x) for x in gains]
    if max(w) - min(w) < 1e-12:
        return {"p": None, "reason": "constant_weights"}
    if sum(g) <= 1e-10:
        return {"p": None, "reason": "nonpositive_total_gain"}
    steps = int(round(upper * 20))
    if steps < 1 or abs(steps / 20 - upper) > 1e-12: raise ValueError('upper must be a positive multiple of 0.05')
    order = sorted(range(len(w)), key=w.__getitem__)
    logw = [math.log(w[i]) for i in order]
    total_gain = sum(g)
    gn = [g[i] / total_gain for i in order]

    def objective(p):
        z = [p * x for x in logw]
        m = max(z)
        z = [math.exp(x - m) for x in z]
        total = sum(z)
        c = 0.0
        loss = 0.0
        for a, b in zip(gn, z):
            c += a - b / total
            loss += c * c
        return loss / len(w)

    grid = [i / 20 for i in range(steps + 1)]
    j = min(range(len(grid)), key=lambda i: objective(grid[i]))
    lo, hi = grid[max(0, j - 1)], grid[min(len(grid) - 1, j + 1)]
    for _ in range(50):
        a, b = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if objective(a) < objective(b):
            hi = b
        else:
            lo = a
    candidates = [0.0, (lo + hi) / 2, float(upper)]
    p = min(candidates, key=objective)
    return {"p": p, "objective": objective(p), "at_upper_bound": p >= upper - 0.001,
            "mean_gain": sum(g) / len(g)}


# ------------------------------------------------------------------ intervals and slopes
def tint(values):
    """Two-sided 95% Student t interval over corpus values (df = n - 1, 2 <= df <= 11)."""
    n = len(values); m = math.fsum(values) / n; sd = statistics.stdev(values); half = T95[n - 1] * sd / math.sqrt(n)
    return dict(n=n, df=n - 1, t_critical=T95[n - 1], mean=m, sd=sd, se=sd / math.sqrt(n), interval=[m - half, m + half],
                negative=sum(v < 0 for v in values), positive=sum(v > 0 for v in values))


def direction(t):
    if t['interval'][1] < -EPS: return 'MOVES_SMALLER'
    if t['interval'][0] > EPS: return 'MOVES_LARGER'
    return 'NO_DETECTED_SHIFT'


def ols_slope(xs, ys):
    """Ordinary least-squares slope of ys on xs."""
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.fsum((x - mx) ** 2 for x in xs)


def eligible(epochs, rule):
    """A corpus slope needs min_points defined epochs, including one early and one late epoch."""
    return len(epochs) >= rule['min_points'] and any(e in rule['early'] for e in epochs) and any(e in rule['late'] for e in epochs)


# ------------------------------------------------------------------ corpus-epoch points
def trajectory(cd, arm, arch): return cd['trajectories'][(CONDITION, arm) + tuple(arch)]


def point(cd, arm, epoch):
    """The eight rung fits of one corpus-epoch, its frozen location and the saturation flag (S1)."""
    u = plan.UPDATES_PER_EPOCH * epoch
    fits = [la.cached_fit(cd, trajectory(cd, arm, a), u, 'total') for a in plan.LADDER]
    ps = [f['p'] for f in fits]
    out = dict(epoch=epoch, update=u, p=ps, reasons=[f['reason'] for f in fits], at_upper=[bool(f.get('upper')) for f in fits],
               at_lower=[bool(f.get('lower')) for f in fits])
    if any(p is None for p in ps): return dict(out, defined=False)
    r, loc, kind = la.peak_location(ps)
    bracket = range(max(0, r - 1), min(len(ps), r + 2))
    return dict(out, defined=True, argmax_rung=r, location=loc, kind=kind, boundary=kind == 'boundary',
                flagged=any(ps[k] >= plan.P_UPPER for k in bracket))


def refit_point(cd, arm, epoch, upper=S32_UPPER):
    """S32: the same saved gains refitted at every rung with search bound `upper`; frozen location rule. The refit
    is unresolved if any refit fit within its own argmax +/- 1 bracket is >= upper - 0.001 (the S1 rule at the new bound)."""
    u = plan.UPDATES_PER_EPOCH * epoch
    fits = [exponent_upper(cd['weights'], la.gains(trajectory(cd, arm, a), u, 'total'), upper) for a in plan.LADDER]
    ps = [f['p'] for f in fits]
    # Unreachable: a flagged point's fits are all defined on the same gains, and both estimators share the undefined rules.
    if any(p is None for p in ps): raise RuntimeError('Refit undefined on gains whose bounded fit is defined')
    r, loc, kind = la.peak_location(ps)
    bracket = range(max(0, r - 1), min(len(ps), r + 2))
    return dict(defined=True, p=ps, argmax_rung=r, location=loc, kind=kind, boundary=kind == 'boundary',
                at_new_upper=sum(bool(f['at_upper_bound']) for f in fits), unresolved=any(ps[k] >= upper - 0.001 for k in bracket))


# ------------------------------------------------------------------ slope test with the saturation rule
def slope_test(data, arm, rule=PRIMARY):
    """Per-corpus OLS slope of the location on log2(epoch); t interval over corpora; pre-registered saturation rule.

    S0  The estimator stays bounded at [0, 8]; every defined point enters at its fitted value.
    S1  A corpus-epoch is flagged if any fit within argmax +/- 1 rung is >= 7.999 (equivalently, any fit there).
    S32 Required if any point is flagged: each flagged point is refitted on the same gains with bound 32; slopes
        over the same points; same interval rule. A refit is unresolved if a fit within its own argmax +/- 1 bracket
        is >= 31.999 (counted, never removed).
    SD  Flagged points dropped; a corpus keeps a slope with >= 3 points; computable with >= 3 corpora
        (df = corpora - 1). Required if more than 25% of the nominal points are flagged (primary: more than 15 of
        60) OR any S32 refit is unresolved (owner decision, 27 Oct 2026). Computed descriptively whenever any point
        is flagged.
    Decision: UNDEFINED if any corpus is unavailable or lacks an eligible slope; else SATURATED if any required
    sensitivity cannot be computed (owner decision, 27 Oct 2026); else SATURATION_SENSITIVE if any required
    sensitivity has a different label from the primary; else the primary label. _CENSORED if any primary point is
    a ladder end (not appended to UNDEFINED or SATURATED)."""
    nominal = len(plan.CORPORA) * len(rule['epochs'])
    x = {e: math.log2(e) for e in rule['epochs']}
    per_corpus, slopes, missing = [], {}, []
    for corpus in plan.CORPORA:
        cd = data.get(corpus)
        if cd is None:
            per_corpus.append(dict(corpus=corpus, status='STAGE_UNAVAILABLE')); missing.append(dict(corpus=corpus, reason='STAGE_UNAVAILABLE')); continue
        pts = [point(cd, arm, e) for e in rule['epochs']]
        good = [p for p in pts if p['defined']]
        row = dict(corpus=corpus, points=pts, defined_epochs=[p['epoch'] for p in good])
        if eligible(row['defined_epochs'], rule):
            row['slope'] = slopes[corpus] = ols_slope([x[p['epoch']] for p in good], [p['location'] for p in good])
        else:
            missing.append(dict(corpus=corpus, reason='SLOPE_INELIGIBLE', defined_epochs=row['defined_epochs']))
        per_corpus.append(row)
    defined_points = [(r['corpus'], p) for r in per_corpus for p in r.get('points', []) if p['defined']]
    flagged = [(c, p) for c, p in defined_points if p['flagged']]
    counts = dict(nominal_points=nominal, defined_points=len(defined_points), undefined_points=nominal - len(defined_points),
                  flagged_points=len(flagged), flagged_fraction_of_nominal=len(flagged) / nominal,
                  flagged_by_epoch={f'E{e}': sum(p['epoch'] == e for _, p in flagged) for e in rule['epochs']},
                  fits_at_upper_by_epoch={f'E{e}': sum(sum(p['at_upper']) for _, p in defined_points if p['epoch'] == e) for e in rule['epochs']},
                  boundary_points=sum(p['boundary'] for _, p in defined_points),
                  boundary_points_by_epoch={f'E{e}': dict(smallest=sum(p['boundary'] and p['argmax_rung'] == 0 for _, p in defined_points if p['epoch'] == e),
                                                          largest=sum(p['boundary'] and p['argmax_rung'] > 0 for _, p in defined_points if p['epoch'] == e))
                                            for e in rule['epochs']})
    out = dict(arm=arm, epochs=list(rule['epochs']), rule=dict(rule, epochs=list(rule['epochs'])), counts=counts, per_corpus=per_corpus, missing=missing)
    if missing:
        return dict(out, label='UNDEFINED', primary=None, sensitivities={})
    primary = tint([slopes[c] for c in plan.CORPORA]); base = direction(primary)
    censored = counts['boundary_points'] > 0
    sens = {}; refits = []
    if flagged:
        s32_slopes = {}
        for row in per_corpus:
            cd = data[row['corpus']]; xs, ys = [], []
            for p in row['points']:
                if not p['defined']: continue
                loc = p['location']
                if p['flagged']:
                    rf = refit_point(cd, arm, p['epoch']); p['s32'] = rf; refits.append(rf)
                    loc = rf['location']
                xs.append(x[p['epoch']]); ys.append(loc)
            s32_slopes[row['corpus']] = ols_slope(xs, ys)
        t32 = tint([s32_slopes[c] for c in plan.CORPORA])
        sens['S32'] = dict(required=True, computable=True, label=direction(t32), interval=t32, slopes=s32_slopes,
                           refitted_points=len(refits), refitted_fits_at_32=sum(r['at_new_upper'] for r in refits),
                           refitted_points_with_a_fit_at_32=sum(r['at_new_upper'] > 0 for r in refits),
                           unresolved_points=sum(r['unresolved'] for r in refits),
                           boundary_points_after_refit=sum(r['boundary'] for r in refits))
    else:
        sens['S32'] = dict(required=False, reason='NO_FLAGGED_POINTS')
    unresolved = sum(r['unresolved'] for r in refits)
    sd_required = 4 * len(flagged) > nominal or unresolved > 0
    sd_why = [w for w, c in (('MORE_THAN_25_PERCENT_FLAGGED', 4 * len(flagged) > nominal), ('UNRESOLVED_S32_REFIT', unresolved > 0)) if c]
    if flagged:
        sd_slopes, dropped = {}, []
        for row in per_corpus:
            keep = [p for p in row['points'] if p['defined'] and not p['flagged']]
            if len(keep) >= SD_MIN_POINTS: sd_slopes[row['corpus']] = ols_slope([x[p['epoch']] for p in keep], [p['location'] for p in keep])
            else: dropped.append(row['corpus'])
        if len(sd_slopes) >= SD_MIN_CORPORA:
            tsd = tint(list(sd_slopes.values()))
            sens['SD'] = dict(required=sd_required, required_because=sd_why, computable=True, label=direction(tsd), interval=tsd, slopes=sd_slopes, corpora_dropped=dropped)
        else:
            sens['SD'] = dict(required=sd_required, required_because=sd_why, computable=False, corpora_kept=len(sd_slopes), corpora_dropped=dropped)
    else:
        sens['SD'] = dict(required=False, reason='NO_FLAGGED_POINTS')
    required = [s for s in sens.values() if s['required']]
    if any(not s['computable'] for s in required): label = 'SATURATED'
    elif any(s['label'] != base for s in required): label = 'SATURATION_SENSITIVE'
    else: label = base
    if censored and label != 'SATURATED': label += '_CENSORED'
    return dict(out, label=label, primary_label=base, censored=censored, primary=primary, slopes=slopes, sensitivities=sens,
                saturation_rate=dict(flagged=len(flagged), of_nominal=nominal, of_defined=len(defined_points)))


def slope_difference(a, b):
    """Paired R - S_batch slope difference (descriptive); defined only if both slope tests are defined."""
    if a.get('primary') is None or b.get('primary') is None: return dict(label='UNDEFINED')
    t = tint([a['slopes'][c] - b['slopes'][c] for c in plan.CORPORA])
    label = 'R_MINUS_S_BELOW_ZERO' if t['interval'][1] < -EPS else 'R_MINUS_S_ABOVE_ZERO' if t['interval'][0] > EPS else 'NO_DETECTED_DIFFERENCE'
    return dict(label=label, interval=t)


def two_point(data, arm, a=20, b=30):
    """Revision-1 readout: per-corpus location change E20 -> E30 (both points defined in every corpus)."""
    deltas, flagged, boundary = [], 0, False
    for corpus in plan.CORPORA:
        cd = data.get(corpus)
        if cd is None: return dict(label='UNDEFINED', reason='STAGE_UNAVAILABLE', corpus=corpus)
        p, q = point(cd, arm, a), point(cd, arm, b)
        if not (p['defined'] and q['defined']): return dict(label='UNDEFINED', reason='POINT_UNDEFINED', corpus=corpus)
        deltas.append(q['location'] - p['location']); flagged += p['flagged'] + q['flagged']; boundary |= p['boundary'] or q['boundary']
    t = tint(deltas)
    return dict(label=direction(t) + ('_CENSORED' if boundary else ''), interval=t, deltas=deltas, flagged_points=flagged)


# ------------------------------------------------------------------ per-epoch descriptive curves
def epoch_curves(data, arm):
    """Descriptive, non-gating: per fixed epoch, panel curve over all twelve corpora (UNDEFINED if any fit is),
    Rise/Fall/End contrasts on the ladder's fixed window with t intervals (df 11), boundary counts per rung, and a
    descriptive shape label (no bootstrap gate): SATURATED / FLAT_OR_LOWER_BOUND if more than half the corpora are at
    the upper / lower bound at the panel argmax rung (or the curve is constant), INTERIOR_PEAK if the argmax is
    interior and Rise and Fall lie above 0, PLATEAU_OR_INCONCLUSIVE if interior otherwise, RISING_TO_LARGEST /
    FALLING_FROM_SMALLEST if the argmax is at that end and End lies above / below 0, else INCONCLUSIVE."""
    out = {}; last = len(plan.LADDER) - 1; n = len(plan.CORPORA)
    for e in plan.FIXED_EPOCHS:
        rows, undefined = [], []
        for corpus in plan.CORPORA:
            cd = data.get(corpus)
            if cd is None: undefined.append(dict(corpus=corpus, reason='STAGE_UNAVAILABLE')); continue
            p = point(cd, arm, e); rows.append(p)
            undefined += [dict(corpus=corpus, width=w, reason=p['reasons'][k]) for k, (w, l) in enumerate(plan.LADDER) if p['p'][k] is None]
        counts = dict(undefined_fits=len(undefined),
                      at_upper_by_rung=[sum(p['at_upper'][k] for p in rows if p['p'][k] is not None) for k in range(len(plan.LADDER))],
                      at_lower_by_rung=[sum(p['at_lower'][k] for p in rows if p['p'][k] is not None) for k in range(len(plan.LADDER))],
                      flagged_points=sum(p.get('flagged', False) for p in rows))
        if undefined: out[f'E{e}'] = dict(label='UNDEFINED', missing=undefined[:200], counts=counts); continue
        m = [p['p'] for p in rows]
        curve = [math.fsum(m[j][r] for j in range(n)) / n for r in range(len(plan.LADDER))]
        r, loc, kind = la.peak_location(curve)
        mid = [math.fsum(m[j][k] for k in la.MID) / len(la.MID) for j in range(n)]
        rise, fall = tint([mid[j] - m[j][0] for j in range(n)]), tint([mid[j] - m[j][last] for j in range(n)])
        end = tint([m[j][last] - m[j][0] for j in range(n)])
        up = sum(m[j][r] >= plan.P_UPPER for j in range(n)); low = sum(m[j][r] <= plan.P_LOWER for j in range(n))
        if 2 * up > n: label = 'SATURATED'
        elif max(curve) - min(curve) <= EPS or 2 * low > n: label = 'FLAT_OR_LOWER_BOUND'
        elif 0 < r < last: label = 'INTERIOR_PEAK' if rise['interval'][0] > EPS and fall['interval'][0] > EPS else 'PLATEAU_OR_INCONCLUSIVE'
        elif r == last and end['interval'][0] > EPS: label = 'RISING_TO_LARGEST'
        elif r == 0 and end['interval'][1] < -EPS: label = 'FALLING_FROM_SMALLEST'
        else: label = 'INCONCLUSIVE'
        out[f'E{e}'] = dict(label=label, curve=curve, argmax_rung=r, argmax_width=plan.LADDER[r][0], location_log2=loc, kind=kind,
                            rise=rise, fall=fall, end=end, upper_at_argmax=up, lower_at_argmax=low, counts=counts,
                            corpus_locations=[p['location'] for p in rows], corpus_boundary=[p['boundary'] for p in rows])
    return out


# ------------------------------------------------------------------ validation, memorization, crossings
def loss_table(data):
    """Per arm, rung and fixed epoch: train and validation NLL (total and instance), the generalization gaps, and the
    R - S_batch validation difference (t interval when all twelve corpora are available). Descriptive."""
    out = {}
    for (w, l) in plan.LADDER:
        for e in plan.FIXED_EPOCHS:
            vals = {}
            for arm in plan.ARMS:
                rows = []
                for corpus in plan.CORPORA:
                    cd = data.get(corpus)
                    if cd is None: continue
                    tr, va = la.state_at(trajectory(cd, arm, (w, l)), 16 * e)
                    rows.append(dict(train=math.fsum(tr['loss']) / 512, validation=math.fsum(va['loss']) / 256,
                                     train_instance=math.fsum(x[2] for x in tr['component']) / 512,
                                     validation_instance=math.fsum(x[2] for x in va['component']) / 256))
                vals[arm] = rows
                summary = {k: math.fsum(r[k] for r in rows) / len(rows) for k in ('train', 'validation', 'train_instance', 'validation_instance')} if rows else {}
                if rows: summary.update(gap=summary['validation'] - summary['train'], instance_gap=summary['validation_instance'] - summary['train_instance'])
                out[f'{arm}|{w}/{l}|E{e}'] = dict(n=len(rows), **summary)
            if len(vals['R']) == len(plan.CORPORA) == len(vals['S_batch']):
                out[f'R-S_batch|{w}/{l}|E{e}|validation'] = tint([a['validation'] - b['validation'] for a, b in zip(vals['R'], vals['S_batch'])])
    return out


def crossings(data):
    out = {}
    for arm in plan.ARMS:
        for (w, l) in plan.LADDER:
            for q in plan.ALL_LANDMARKS:
                ups, missed, undefined = [], 0, 0
                for corpus in plan.CORPORA:
                    cd = data.get(corpus)
                    if cd is None: continue
                    s = trajectory(cd, arm, (w, l))['record']['landmarks'][str(q)]
                    if s['status'] == 'CROSSED': ups.append(s['update'])
                    elif s['status'] == 'UNDEFINED_E0': undefined += 1
                    else: missed += 1
                out[f'{arm}|{w}/{l}|{la.lm_name(q)}'] = dict(crossed=len(ups), missed=missed, undefined_E0=undefined, median_update=statistics.median(ups) if ups else None)
    return out


def clipping_summary(clipping):
    out = {}
    for arm in plan.ARMS:
        for (w, l) in plan.LADDER:
            rows = [r for r in clipping if r['arm'] == arm and r['arch'] == f'{w}/{l}']
            for name, lo, hi in (('E1-E30', 1, 30), ('E31-E40', 31, 40)):
                sel = [r for r in rows if lo <= r['epoch'] <= hi]
                out[f'{arm}|{w}/{l}|{name}'] = dict(rows=len(sel), clip_fraction_mean=math.fsum(r['clip_fraction'] for r in sel) / len(sel) if sel else None,
                                                    gradient_norm_mean=math.fsum(r['gradient_norm_mean'] for r in sel) / len(sel) if sel else None,
                                                    gradient_norm_max=max(r['gradient_norm_max'] for r in sel) if sel else None)
    return out


def point_rows(tests):
    rows = []
    for key, t in tests.items():
        for c in t['per_corpus']:
            for p in c.get('points', []):
                row = dict(readout=key, arm=t['arm'], corpus=c['corpus'], epoch=p['epoch'], defined=p['defined'], location=p.get('location'),
                           kind=p.get('kind'), argmax_rung=p.get('argmax_rung'), flagged=p.get('flagged'), fits_at_upper=sum(p['at_upper']),
                           undefined_reasons=';'.join(sorted({r for r in p['reasons'] if r})))
                row.update({f'p_{w}': v for (w, l), v in zip(plan.LADDER, p['p'])})
                if 's32' in p:
                    row.update(s32_location=p['s32']['location'], s32_kind=p['s32']['kind'], s32_fits_at_32=p['s32']['at_new_upper'], s32_unresolved=p['s32']['unresolved'])
                    row.update({f's32_p_{w}': v for (w, l), v in zip(plan.LADDER, p['s32']['p'])})
                rows.append(row)
    return rows


def analyse(run):
    data = la.load(run)
    tests = {'primary|R': slope_test(data, 'R'), 'primary|S_batch': slope_test(data, 'S_batch'),
             'E15-E30|R': slope_test(data, 'R', WINDOW_E15_E30), 'E15-E30|S_batch': slope_test(data, 'S_batch', WINDOW_E15_E30)}
    rows, clipping = la.secondaries(data)
    available = [c for c in plan.CORPORA if data[c] is not None]
    result = dict(
        status='COMPLETE' if len(available) == len(plan.CORPORA) else 'PARTIAL_UNAVAILABLE_CORPORA', corpora_available=available,
        decision=dict(label=tests['primary|R']['label'], arm='R', condition=CONDITION,
                      rule='Primary: per-corpus OLS slope of the frozen location on log2(epoch) over E15/E20/E25/E30/E40; '
                           't interval df 11 over 12 corpora; saturation rule S0/S1/S32/SD (slope_test).'),
        slope_tests=tests,
        slope_difference_R_minus_S_batch=dict(primary=slope_difference(tests['primary|R'], tests['primary|S_batch']),
                                              E15_E30=slope_difference(tests['E15-E30|R'], tests['E15-E30|S_batch'])),
        two_point_E20_E30={arm: two_point(data, arm) for arm in plan.ARMS},
        epoch_curves={arm: epoch_curves(data, arm) for arm in plan.ARMS},
        losses=loss_table(data), landmark_crossings=crossings(data), clipping_summary=clipping_summary(clipping),
        validation_selected_view=la.selected_view(data),
        note='Only decision.label is the pre-registered primary; every other section is secondary or descriptive.')
    return result, point_rows(tests), rows, clipping


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    run, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=False, exist_ok=False)
    result, points, rows, clipping = analyse(run)
    (out / 'ANALYSIS.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for name, table in (('POINTS.csv', points), ('SECONDARIES.csv', rows), ('CLIPPING.csv', clipping)): write_csv(out / name, table)
    print(json.dumps(dict(status=result['status'], decision=result['decision']['label'],
                          labels={k: v['label'] for k, v in result['slope_tests'].items()}), indent=1))
