"""Frozen natural-text ladder analysis (stdlib only). Runs after Run B; never during it.

  python -I -B text_analysis.py <RUN_B_DIR> [<RUN_B2_DIR>] <NEW_OUT_DIR>      -> ANALYSIS.json, POINTS.csv, FITS.csv
  (one Run B directory, or the Run B1 and Run B2 directories of the pre-registered split)

Every rule is fixed before any outcome (PROTOCOL.md). Gains are signed per-sequence training-loss reductions from
E0, the uniform-weight pre-trained checkpoint (a sequence-weight-invariant baseline). p* is vendor/core.exponent
on [0, 8]; undefined fits stay undefined; the ten draws are the only inference unit (df 9).
Primary A (finding 2): per-draw OLS slope of the peak location on log2(epoch) over E4..E32.
Primary B (finding 1): INTERIOR_PEAK iff (i) the t interval of the mean epoch-averaged quadratic curvature lies below 0,
  (ii) the vertex of the mean quadratic lies in [log2 64, log2 384], and (iii) the two-lines test holds with a
  data-located break (owner decisions of 28 Oct 2026, revisions 03 and 04): per point, the break is the rung nearest the
  point's quadratic vertex, clamped to 96..256 so that each line has at least 2 widths, and it belongs to both lines;
  each draw averages its left and right OLS slopes over its points; across the ten draws the left interval lies above 0
  and the right interval below 0, and every draw must have a defined mean; and (iv) per point, min(left, -right) is the
  point's own rise and fall; each draw averages it over its points, and its df-9 interval lies above 0 (revision 04),
  else RISE_AND_FALL_NOT_WITHIN_POINTS. Both primaries use the follow-up's saturation rule. A result other than
  INTERIOR_PEAK is inconclusive for shallow peaks (PROTOCOL sections 8 and 10), not evidence that no peak exists.
Revision 05 (owner ruling of 28 Oct 2026): attempt 1, the revision 04 Run B that failed operationally, is never analysed;
load() refuses its folder and any run under the revision 04 subject before reading a draw.
"""
import csv, hashlib, json, math, statistics, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import text_plan as plan
from core import exponent

X = [math.log2(w) for w in plan.WIDTHS]
EPS = 1e-9
ATTEMPT_1_DIR = 'natural-text-ladder-b-20261028-01'
REVISION_04_SUBJECT = '90e3f3ef1c7dcad6e4be54e5bf5ac0eab2f7feb9de2121aa2ed7ce658c8beded'
NEVER_ANALYSED = 'Attempt 1 (the revision 04 Run B) is never analysed (owner ruling of 28 Oct 2026); analyse only the revision 05 run'
S32_UPPER = 32.0
SD_MIN_POINTS, SD_MIN_CORPORA = 3, 3
T95 = {2: 4.302652730, 3: 3.182446305, 4: 2.776445105, 5: 2.570581836, 6: 2.446911851, 7: 2.364624252,
       8: 2.306004135, 9: 2.262157163, 10: 2.228138852, 11: 2.200985160}
RULE = dict(epochs=plan.PRIMARY_EPOCHS, min_points=6, early=(4, 6), late=(24, 32))


# ------------------------------------------------------------------ estimator pieces (copies of the sealed functions)
def objective_at(weights, gains, p):
    """Exact copy of core.exponent's objective (ascending-weight cumulative discrepancy)."""
    order = sorted(range(len(weights)), key=weights.__getitem__); total = sum(gains)
    logw = [math.log(weights[i]) for i in order]; gn = [gains[i] / total for i in order]
    z = [p * x for x in logw]; m = max(z); z = [math.exp(x - m) for x in z]; s = sum(z); c = loss = 0.0
    for a, b in zip(gn, z): c += a - b / s; loss += c * c
    return loss / len(weights)


def exponent_upper(weights, gains, upper):
    """vendor/core.exponent with search bound `upper` (shift_analysis.exponent_upper); identical to it at 8."""
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


def peak_location(curve, xs=X):
    """ladder_analysis.peak_location on the given rungs: argmax (ties to the smaller width); interior -> vertex of the
    three-point parabola clamped to its bracket (middle rung if not concave); end rung -> boundary."""
    r = max(range(len(curve)), key=lambda i: (curve[i], -i))
    if r in (0, len(curve) - 1): return r, xs[r], 'boundary'
    x0, x1, x2 = xs[r - 1:r + 2]; y0, y1, y2 = curve[r - 1:r + 2]
    denom = (x0 - x1) * (x0 - x2) * (x1 - x2)
    a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / denom
    b = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / denom
    v = -b / (2 * a) if a < 0 else x1
    return r, min(max(v, x0), x2), 'interior'


def quadratic(ys, xs=X):
    """Least-squares p = a + b u + c u^2 with u = x - mean(x) (x = log2 width). Returns a, b, c and the centre."""
    n = len(xs); xbar = math.fsum(xs) / n; u = [x - xbar for x in xs]
    S = [math.fsum(v ** k for v in u) for k in range(5)]; T = [math.fsum((v ** k) * y for v, y in zip(u, ys)) for k in range(3)]
    A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]; bvec = T[:]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(A[r][c])); A[c], A[p] = A[p], A[c]; bvec[c], bvec[p] = bvec[p], bvec[c]
        for r in range(c + 1, 3):
            f = A[r][c] / A[c][c]; A[r] = [x - f * y for x, y in zip(A[r], A[c])]; bvec[r] -= f * bvec[c]
    coef = [0.0] * 3
    for r in (2, 1, 0): coef[r] = (bvec[r] - sum(A[r][k] * coef[k] for k in range(r + 1, 3))) / A[r][r]
    return dict(a=coef[0], b=coef[1], c=coef[2], centre=xbar)


def tint(values):
    n = len(values); m = math.fsum(values) / n; sd = statistics.stdev(values); half = T95[n - 1] * sd / math.sqrt(n)
    return dict(n=n, df=n - 1, t_critical=T95[n - 1], mean=m, sd=sd, se=sd / math.sqrt(n), interval=[m - half, m + half],
                negative=sum(v < 0 for v in values), positive=sum(v > 0 for v in values))


def direction(t):
    if t['interval'][1] < -EPS: return 'MOVES_SMALLER'
    if t['interval'][0] > EPS: return 'MOVES_LARGER'
    return 'NO_DETECTED_SHIFT'


def shape(t, vertex, left=None, right=None, rise_fall=None):
    """Primary B label from the curvature interval, the vertex of the mean quadratic, the two-lines intervals and the
    per-point rise-and-fall interval (revision 04)."""
    if t['interval'][1] < -EPS:
        if vertex is None or not X[0] <= vertex <= X[-1]: return 'CONCAVE_VERTEX_OUTSIDE_LADDER'
        if left is None or right is None or not (left['interval'][0] > EPS and right['interval'][1] < -EPS): return 'CONCAVE_WITHOUT_RISE_AND_FALL'
        if rise_fall is not None and rise_fall['interval'][0] > EPS: return 'INTERIOR_PEAK'
        return 'RISE_AND_FALL_NOT_WITHIN_POINTS'
    if t['interval'][0] > EPS: return 'CONVEX'
    return 'NO_DETECTED_CURVATURE'


def two_lines(ps, q=None):
    """Two lines with a data-located break (revisions 03 and 04). The break is the rung nearest the point's own quadratic
    vertex (ties to the smaller width), clamped in to the nearest rung that leaves at least TWO_LINES_MIN_WIDTHS widths
    on each line (revision 04: a point is never discarded because its vertex lies near or beyond a ladder end; that
    selection biased the slopes); it belongs to both lines. The slopes are the OLS slopes of p* on log2 width over the
    rungs up to the break and from it. Undefined only if the vertex is not finite (c = 0)."""
    q = q or quadratic(ps); v = vertex_log2(q['b'], q['c'], q['centre'])
    if v is None: return dict(defined=False, reason='NO_FINITE_VERTEX', vertex_log2=None, break_width=None, break_clamped=None, left=None, right=None, rise_fall=None)
    m = plan.TWO_LINES_MIN_WIDTHS; k0 = min(range(len(X)), key=lambda i: (abs(X[i] - v), i)); k = min(max(k0, m - 1), len(X) - m)
    left, right = ols_slope(X[:k + 1], ps[:k + 1]), ols_slope(X[k:], ps[k:])
    return dict(defined=True, reason=None, vertex_log2=v, break_width=plan.WIDTHS[k], break_clamped=k != k0, left=left, right=right, rise_fall=min(left, -right))


def vertex_width(v):
    lo, hi = plan.VERTEX_WIDTH_LOG2_RANGE
    return 2 ** v if v is not None and lo <= v <= hi else None


def vertex_log2(b, c, centre):
    """Vertex centre - b / (2c) of p = a + b u + c u^2; None when |c| <= CURVATURE_ZERO_TOL or the vertex is not finite."""
    if abs(c) <= plan.CURVATURE_ZERO_TOL: return None
    v = centre - b / (2 * c)
    return v if math.isfinite(v) else None


def ols_slope(xs, ys):
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.fsum((x - mx) ** 2 for x in xs)


def eligible(epochs, rule=RULE):
    return len(epochs) >= rule['min_points'] and any(e in rule['early'] for e in epochs) and any(e in rule['late'] for e in epochs)


# ------------------------------------------------------------------ loading
def sha(b): return hashlib.sha256(b).hexdigest()


def load(runs):
    """Draws from one Run B directory or from the B1 and B2 directories. Each draw must have a COMPLETE receipt in at
    most one run whose mode covers it; the runs must share one source subject; records must match the frozen layout."""
    runs = [Path(r) for r in (runs if isinstance(runs, (list, tuple)) else [runs])]; data = {}; subjects = set(); modes = {}; terms = {}
    for r in runs:
        if r.resolve().name == ATTEMPT_1_DIR: raise ValueError(NEVER_ANALYSED)
        raw = (r / 'TERMINAL.json').read_bytes() if (r / 'TERMINAL.json').exists() else b'{}'; term = json.loads(raw)
        if term.get('subject') == REVISION_04_SUBJECT: raise ValueError(NEVER_ANALYSED)
        if term.get('mode') not in ('B', 'B1', 'B2'): raise ValueError('Not a Run B directory: ' + str(r))
        if term.get('status') not in ('COMPLETE', 'FAILED'):
            raise ValueError(f"Run {term['mode']} ended {term.get('status')}; only a COMPLETE or FAILED run is analysed (after a start-up fallback, analyse Runs B1 and B2)")
        subjects.add(term.get('subject')); modes[r] = term['mode']; terms[term['mode']] = (term, raw)
    if len(subjects) != 1 or sorted(modes.values()) not in (['B'], ['B1', 'B2']): raise ValueError('Run B directories must be one Run B, or Run B1 and Run B2, under one subject')
    if 'B2' in terms:
        b1, b2 = terms['B1'][0].get('bindings', {}), terms['B2'][0].get('bindings', {})
        if b2.get('run_b1_terminal_sha256') != sha(terms['B1'][1]): raise ValueError('Run B2 was not admitted on this Run B1')
        if any(b1.get(k) != b2.get(k) for k in ('registry_sha256', 'corpus_manifest_sha256', 'partition_sha256', 'lr_selection_sha256', 'run_a_terminal_sha256', 'run_b_fallback_terminal_sha256')):
            raise ValueError('Runs B1 and B2 differ in their bindings')
    for d in plan.DRAWS:
        found = [r for r in runs if d in plan.RUN_STAGES[modes[r]] and (r / f'{d}-RECEIPT.json').exists() and json.loads((r / f'{d}-RECEIPT.json').read_bytes()).get('status') == 'COMPLETE']
        if len(found) > 1: raise ValueError('Draw completed in more than one run: ' + d)
        if not found: data[d] = None; continue
        run = found[0]
        inputs = json.loads((run / d / 'INPUTS.json').read_bytes()); pre = json.loads((run / d / 'PRETRAINED.json').read_bytes())
        n = inputs['n_train']; widths = {}
        for w in plan.WIDTHS:
            e0raw = (run / d / f'w{w}' / 'E0.f32').read_bytes(); b = pre[str(w)]['E0_arrays']
            if len(e0raw) != b['bytes'] or sha(e0raw) != b['sha256']: raise ValueError('E0 binding differs: ' + b['path'])
            base = run / d / f'w{w}' / 'selected'; rec = json.loads((base / 'record.json').read_bytes()); raw = (base / 'arrays.f32').read_bytes()
            if len(raw) != rec['arrays']['bytes'] or sha(raw) != rec['arrays']['sha256']: raise ValueError('Array binding differs: ' + rec['arrays']['path'])
            if (rec['layout']['block_epochs'] != list(plan.READOUTS) or rec['layout']['train_rows'] != n or rec['layout']['validation_rows'] != plan.N_VALIDATION
                    or [rec['lr']] != inputs['learning_rates'][str(w)] or rec['width'] != w or len(e0raw) != 4 * (n + plan.N_VALIDATION)): raise ValueError('Record layout differs: ' + rec['arrays']['path'])
            e0 = array('f'); e0.frombytes(e0raw)
            widths[w] = dict(e0=e0, raw=raw, record=rec, pretrained=pre[str(w)])
        data[d] = dict(weights=inputs['weights'], n=n, widths=widths, inputs=inputs)
    if len({json.dumps(v['inputs']['learning_rates'], sort_keys=True) for v in data.values() if v is not None}) > 1: raise ValueError('Draws differ in learning rates')
    return data


def block(t, epoch, split):
    n, nv = t['record']['layout']['train_rows'], t['record']['layout']['validation_rows']; k = t['record']['layout']['block_epochs'].index(epoch)
    a = array('f'); start = k * (n + nv) + (0 if split == 'train' else n); a.frombytes(t['raw'][4 * start:4 * (start + (n if split == 'train' else nv))])
    return a


def gains(dd, w, epoch):
    """Signed per-sequence training gains E0 -> epoch: float32 subtraction (as the ladder analysis), then float64."""
    t = dd['widths'][w]; n = dd['n']; cur = block(t, epoch, 'train')
    return array('f', (a - b for a, b in zip(t['e0'][:n], cur))).tolist()


_FITS = {}
def fit(dd, w, epoch):
    key = (id(dd), w, epoch)
    if key not in _FITS:
        g = gains(dd, w, epoch); r = exponent(dd['weights'], g); p = r.get('p')
        out = dict(p=p, reason=r.get('reason'), total_gain=math.fsum(g), negative_fraction=sum(x < 0 for x in g) / len(g))
        if p is not None: out.update(objective=r['objective'], J0=objective_at(dd['weights'], g, 0.0), upper=p >= plan.P_UPPER, lower=p <= plan.P_LOWER)
        _FITS[key] = out
    return _FITS[key]


def point(dd, epoch):
    fits = [fit(dd, w, epoch) for w in plan.WIDTHS]; ps = [f['p'] for f in fits]
    out = dict(epoch=epoch, p=ps, reasons=[f['reason'] for f in fits], at_upper=[bool(f.get('upper')) for f in fits], at_lower=[bool(f.get('lower')) for f in fits])
    if any(p is None for p in ps): return dict(out, defined=False)
    r, loc, kind = peak_location(ps); bracket = range(max(0, r - 1), min(len(ps), r + 2))
    q = quadratic(ps)
    return dict(out, defined=True, argmax_rung=r, location=loc, kind=kind, boundary=kind == 'boundary',
                flagged=any(ps[k] >= plan.P_UPPER for k in bracket), quad=q, lines=two_lines(ps, q))


def refit_point(dd, epoch, upper=S32_UPPER):
    fits = [exponent_upper(dd['weights'], gains(dd, w, epoch), upper) for w in plan.WIDTHS]; ps = [f['p'] for f in fits]
    if any(p is None for p in ps): raise RuntimeError('Refit undefined on gains whose bounded fit is defined')
    r, loc, kind = peak_location(ps); bracket = range(max(0, r - 1), min(len(ps), r + 2)); q = quadratic(ps)
    return dict(p=ps, argmax_rung=r, location=loc, kind=kind, boundary=kind == 'boundary', quad=q, lines=two_lines(ps, q),
                at_new_upper=sum(bool(f['at_upper_bound']) for f in fits), unresolved=any(ps[k] >= upper - 0.001 for k in bracket))


# ------------------------------------------------------------------ the two primaries with the saturation rule
def _shift_value(pts, xmap, use):       # per-draw slope from a list of points and a location accessor
    return ols_slope([xmap[p['epoch']] for p in pts], [use(p) for p in pts])


def _curv(pts, use):
    """Per-draw (b, c, left, right, n_lines, rise_fall) from points and an accessor: b and c averaged over the draw's
    points; the two slopes and the per-point rise and fall averaged over the points whose two lines are defined (None if
    there is none)."""
    qs = [use(p) for p in pts]; n = len(qs); ln = [q for q in qs if q['left'] is not None]
    mean = lambda k: math.fsum(q[k] for q in ln) / len(ln) if ln else None
    return (math.fsum(q['b'] for q in qs) / n, math.fsum(q['c'] for q in qs) / n, mean('left'), mean('right'), len(ln), mean('rise_fall'))


def _shape_summary(bc):
    """Primary B summary over draws: curvature interval, vertex of the mean quadratic, two-lines intervals (evaluable
    only if every draw has a defined mean slope pair), label."""
    vals = list(bc.values()); t = tint([v[1] for v in vals]); mb = math.fsum(v[0] for v in vals) / len(vals); mc = t['mean']
    vertex = vertex_log2(mb, mc, math.fsum(X) / len(X))
    evaluable = all(v[2] is not None for v in vals)
    left, right, rf = (tint([v[2] for v in vals]), tint([v[3] for v in vals]), tint([v[5] for v in vals])) if evaluable else (None, None, None)
    return dict(curvature=t, vertex_log2=vertex, vertex_width=vertex_width(vertex), left_slope=left, right_slope=right, rise_fall=rf,
                two_lines=dict(evaluable=evaluable, draws_with_defined_lines=sum(v[2] is not None for v in vals), points_with_defined_lines=sum(v[4] for v in vals)),
                label=shape(t, vertex, left, right, rf))


def _qa(p, key='quad', lines='lines'):  # the quadratic, two-lines and rise-and-fall values of a point (or its refit); None if undefined
    return dict(b=p[key]['b'], c=p[key]['c'], left=p[lines]['left'], right=p[lines]['right'], rise_fall=p[lines]['rise_fall'])


def primaries(data):
    """Primary A and B on the same corpus-epoch points; shared saturation flags and requirements."""
    nominal = len(plan.DRAWS) * len(RULE['epochs']); xmap = {e: math.log2(e) for e in RULE['epochs']}
    per, missing = {}, []
    for d in plan.DRAWS:
        dd = data.get(d)
        if dd is None: missing.append(dict(draw=d, reason='STAGE_UNAVAILABLE')); continue
        pts = [point(dd, e) for e in RULE['epochs']]; good = [p for p in pts if p['defined']]
        per[d] = dict(points=pts, defined_epochs=[p['epoch'] for p in good])
        if not eligible(per[d]['defined_epochs']): missing.append(dict(draw=d, reason='INELIGIBLE', defined_epochs=per[d]['defined_epochs']))
    unavailable = any(m['reason'] == 'STAGE_UNAVAILABLE' for m in missing)
    defined = [(d, p) for d, v in per.items() for p in v['points'] if p['defined']]; flagged = [(d, p) for d, p in defined if p['flagged']]
    counts = dict(nominal_points=nominal, defined_points=len(defined), undefined_points=nominal - len(defined), flagged_points=len(flagged),
                  flagged_by_epoch={f'E{e}': sum(p['epoch'] == e for _, p in flagged) for e in RULE['epochs']},
                  fits_at_upper_by_epoch={f'E{e}': sum(sum(p['at_upper']) for _, p in defined if p['epoch'] == e) for e in RULE['epochs']},
                  fits_at_lower_by_epoch={f'E{e}': sum(sum(p['at_lower']) for _, p in defined if p['epoch'] == e) for e in RULE['epochs']},
                  boundary_points=sum(p['boundary'] for _, p in defined),
                  boundary_points_by_epoch={f'E{e}': dict(smallest=sum(p['boundary'] and p['argmax_rung'] == 0 for _, p in defined if p['epoch'] == e),
                                                          largest=sum(p['boundary'] and p['argmax_rung'] > 0 for _, p in defined if p['epoch'] == e)) for e in RULE['epochs']},
                  two_lines_by_epoch={f'E{e}': dict(defined=sum(p['lines']['defined'] for _, p in defined if p['epoch'] == e),
                                                    break_clamped=sum(p['lines']['break_clamped'] is True for _, p in defined if p['epoch'] == e),
                                                    no_finite_vertex=sum(p['lines']['reason'] == 'NO_FINITE_VERTEX' for _, p in defined if p['epoch'] == e),
                                                    break_widths={str(w): sum(p['lines']['break_width'] == w and p['lines']['defined'] for _, p in defined if p['epoch'] == e) for w in plan.WIDTHS[1:-1]})
                                      for e in RULE['epochs']})
    out = dict(counts=counts, per_draw=per, missing=missing)
    if missing:
        label = 'UNAVAILABLE' if unavailable else 'UNDEFINED'      # missing draws (failed or infeasible runs) vs undefined fits
        return dict(out, A=dict(label=label), B=dict(label=label))
    refits = []
    if flagged:
        for d, p in flagged: p['s32'] = refit_point(data[d], p['epoch']); refits.append(p['s32'])
    unresolved = sum(r['unresolved'] for r in refits)
    sd_required = 4 * len(flagged) > nominal or unresolved > 0
    sd_why = [w for w, c in (('MORE_THAN_25_PERCENT_FLAGGED', 4 * len(flagged) > nominal), ('UNRESOLVED_S32_REFIT', unresolved > 0)) if c]
    goods = {d: [p for p in v['points'] if p['defined']] for d, v in per.items()}
    keeps = {d: [p for p in g if not p['flagged']] for d, g in goods.items()}
    sd_draws = [d for d in plan.DRAWS if len(keeps[d]) >= SD_MIN_POINTS]
    refit_info = dict(refitted_points=len(refits), refitted_fits_at_32=sum(r['at_new_upper'] for r in refits),
                      unresolved_points=unresolved, boundary_points_after_refit=sum(r['boundary'] for r in refits))

    def decide(primary_label, sens):
        required = [s for s in sens.values() if s['required']]
        if any(not s['computable'] for s in required): return 'SATURATED'
        if any(s['label'] != primary_label for s in required): return 'SATURATION_SENSITIVE'
        return primary_label

    # Primary A: peak shift
    slopes = {d: _shift_value(goods[d], xmap, lambda p: p['location']) for d in plan.DRAWS}
    tA = tint([slopes[d] for d in plan.DRAWS]); baseA = direction(tA); censored = counts['boundary_points'] > 0
    sensA = {}
    if flagged:
        s32 = {d: _shift_value(goods[d], xmap, lambda p: p['s32']['location'] if p['flagged'] else p['location']) for d in plan.DRAWS}
        t32 = tint([s32[d] for d in plan.DRAWS]); sensA['S32'] = dict(required=True, computable=True, label=direction(t32), interval=t32, slopes=s32, **refit_info)
        if len(sd_draws) >= SD_MIN_CORPORA:
            sd = {d: _shift_value(keeps[d], xmap, lambda p: p['location']) for d in sd_draws}; tsd = tint(list(sd.values()))
            sensA['SD'] = dict(required=sd_required, required_because=sd_why, computable=True, label=direction(tsd), interval=tsd, slopes=sd, draws_dropped=[d for d in plan.DRAWS if d not in sd_draws])
        else:
            sensA['SD'] = dict(required=sd_required, required_because=sd_why, computable=False, draws_kept=len(sd_draws))
    else:
        sensA = dict(S32=dict(required=False, reason='NO_FLAGGED_POINTS'), SD=dict(required=False, reason='NO_FLAGGED_POINTS'))
    labelA = decide(baseA, sensA)
    if censored and labelA != 'SATURATED': labelA += '_CENSORED'
    A = dict(label=labelA, primary_label=baseA, censored=censored, interval=tA, slopes=slopes, sensitivities=sensA)

    # Primary B: quadratic curvature and vertex, the two-lines test with data-located breaks, and the per-point rise and fall
    bc = {d: _curv(goods[d], _qa) for d in plan.DRAWS}
    sB = _shape_summary(bc); baseB = sB['label']
    sensB = {}
    if flagged:
        sb32 = _shape_summary({d: _curv(goods[d], lambda p: _qa(p['s32']) if p['flagged'] else _qa(p)) for d in plan.DRAWS})
        sensB['S32'] = dict(required=True, computable=True, **sb32, **refit_info)
        if len(sd_draws) >= SD_MIN_CORPORA:
            sbsd = _shape_summary({d: _curv(keeps[d], _qa) for d in sd_draws})
            sensB['SD'] = dict(required=sd_required, required_because=sd_why, computable=True, **sbsd, draws_dropped=[d for d in plan.DRAWS if d not in sd_draws])
        else:
            sensB['SD'] = dict(required=sd_required, required_because=sd_why, computable=False, draws_kept=len(sd_draws))
    else:
        sensB = dict(S32=dict(required=False, reason='NO_FLAGGED_POINTS'), SD=dict(required=False, reason='NO_FLAGGED_POINTS'))
    B = dict(sB, label=decide(baseB, sensB), primary_label=baseB, sensitivities=sensB,
             draw_coefficients={d: dict(b=v[0], c=v[1], left_slope=v[2], right_slope=v[3], points_with_defined_lines=v[4], rise_fall=v[5]) for d, v in bc.items()},
             draw_vertices_log2={d: vertex_log2(v[0], v[1], math.fsum(X) / len(X)) for d, v in bc.items()})
    return dict(out, A=A, B=B)


# ------------------------------------------------------------------ secondaries (non-gating)
def by_epoch(data):
    """Per readout epoch: panel p* curve and location, the vertex of the mean quadratic with the df-9 interval of the
    mean curvature, per-draw vertices, and fit counts. UNAVAILABLE if a draw is missing; UNDEFINED if any of the 60 fits
    is undefined (no defined-only panel)."""
    out = {}
    for e in plan.READOUTS:
        pts = {d: point(data[d], e) for d in plan.DRAWS if data.get(d) is not None}
        und = [dict(draw=d, width=w, reason=p['reasons'][k]) for d, p in pts.items() for k, w in enumerate(plan.WIDTHS) if p['p'][k] is None]
        counts = dict(undefined_fits=len(und), at_upper=sum(sum(p['at_upper']) for p in pts.values()), at_lower=sum(sum(p['at_lower']) for p in pts.values()),
                      flagged_points=sum(p.get('flagged', False) for p in pts.values()))
        if len(pts) < len(plan.DRAWS): out[f'E{e}'] = dict(label='UNAVAILABLE', counts=counts); continue
        if und: out[f'E{e}'] = dict(label='UNDEFINED', missing=und[:100], counts=counts); continue
        curve = [math.fsum(pts[d]['p'][k] for d in plan.DRAWS) / len(plan.DRAWS) for k in range(len(plan.WIDTHS))]
        r, loc, kind = peak_location(curve)
        sh = _shape_summary({d: _curv([pts[d]], _qa) for d in plan.DRAWS})
        out[f'E{e}'] = dict(curve=curve, argmax_width=plan.WIDTHS[r], location_log2=loc, location_width=2 ** loc, kind=kind, curvature=sh['curvature'], vertex_log2=sh['vertex_log2'],
                            vertex_width=sh['vertex_width'], left_slope=sh['left_slope'], right_slope=sh['right_slope'], rise_fall=sh['rise_fall'], two_lines=sh['two_lines'],
                            shape_label=sh['label'], counts=counts,
                            draw_breaks={d: pts[d]['lines']['break_width'] if pts[d]['lines']['defined'] else None for d in plan.DRAWS},
                            draw_locations={d: pts[d]['location'] for d in plan.DRAWS},
                            draw_vertices_log2={d: vertex_log2(pts[d]['quad']['b'], pts[d]['quad']['c'], pts[d]['quad']['centre']) for d in plan.DRAWS})
    return out


def two_point(data, a=8, b=32):
    deltas, boundary = [], False
    for d in plan.DRAWS:
        if data.get(d) is None: return dict(label='UNAVAILABLE', reason='STAGE_UNAVAILABLE')
        p, q = point(data[d], a), point(data[d], b)
        if not (p['defined'] and q['defined']): return dict(label='UNDEFINED', reason='POINT_UNDEFINED', draw=d)
        deltas.append(q['location'] - p['location']); boundary |= p['boundary'] or q['boundary']
    t = tint(deltas); return dict(label=direction(t) + ('_CENSORED' if boundary else ''), interval=t, deltas=deltas)


def losses(data):
    out = {}
    for w in plan.WIDTHS:
        avail = [data[d] for d in plan.DRAWS if data.get(d) is not None]
        if not avail: continue
        e0 = [dd['widths'][w]['pretrained'] for dd in avail]
        out[f'{w}|E0'] = dict(train=math.fsum(x['E0_train_loss'] for x in e0) / len(e0), validation=math.fsum(x['E0_validation_loss'] for x in e0) / len(e0), n=len(e0),
                              pretraining_clip_fraction=math.fsum(x['pretraining_clip_fraction'] for x in e0) / len(e0))
        for e in plan.READOUTS:
            rows = [next(r for r in dd['widths'][w]['record']['readouts'] if r['epoch'] == e) for dd in avail]
            tr = math.fsum(r['train_loss'] for r in rows) / len(rows); va = math.fsum(r['validation_loss'] for r in rows) / len(rows)
            out[f'{w}|E{e}'] = dict(train=tr, validation=va, gap=va - tr, n=len(rows))
        ep = [x for dd in avail for x in dd['widths'][w]['record']['epochs']]
        out[f'{w}|clipping'] = dict(clip_fraction_mean=math.fsum(x['clip_fraction'] for x in ep) / len(ep), gradient_norm_mean=math.fsum(x['gradient_norm_mean'] for x in ep) / len(ep),
                                    gradient_norm_max=max(x['gradient_norm_max'] for x in ep), learning_rate=avail[0]['widths'][w]['record']['lr'])
    return out


def point_rows(prim):
    rows = []
    for d, v in prim['per_draw'].items():
        for p in v['points']:
            row = dict(draw=d, epoch=p['epoch'], defined=p['defined'], location=p.get('location'), kind=p.get('kind'), flagged=p.get('flagged'),
                       quad_c=p['quad']['c'] if p['defined'] else None, quad_b=p['quad']['b'] if p['defined'] else None,
                       left_slope=p['lines']['left'] if p['defined'] else None, right_slope=p['lines']['right'] if p['defined'] else None,
                       break_width=p['lines']['break_width'] if p['defined'] else None, break_clamped=p['lines']['break_clamped'] if p['defined'] else None,
                       rise_fall=p['lines']['rise_fall'] if p['defined'] else None,
                       lines_undefined_reason=p['lines']['reason'] if p['defined'] else None,
                       undefined_reasons=';'.join(sorted({r for r in p['reasons'] if r})))
            row.update({f'p_{w}': x for w, x in zip(plan.WIDTHS, p['p'])})
            if 's32' in p:
                row.update(s32_location=p['s32']['location'], s32_quad_c=p['s32']['quad']['c'], s32_unresolved=p['s32']['unresolved'],
                           s32_left_slope=p['s32']['lines']['left'], s32_right_slope=p['s32']['lines']['right'], s32_break_width=p['s32']['lines']['break_width'],
                           s32_break_clamped=p['s32']['lines']['break_clamped'], s32_rise_fall=p['s32']['lines']['rise_fall'])
                row.update({f's32_p_{w}': x for w, x in zip(plan.WIDTHS, p['s32']['p'])})
            rows.append(row)
    return rows


def strip(prim):
    return {k: v for k, v in prim.items() if k != 'per_draw'} | dict(per_draw={d: dict(defined_epochs=v['defined_epochs']) for d, v in prim['per_draw'].items()})


def analyse(runs):
    _FITS.clear(); data = load(runs); prim = primaries(data)
    avail = [d for d in plan.DRAWS if data[d] is not None]
    fits = [dict(draw=d, width=w, epoch=e, **{k: v for k, v in fit(data[d], w, e).items()}) for d in avail for w in plan.WIDTHS for e in plan.READOUTS]
    result = dict(status='COMPLETE' if len(avail) == len(plan.DRAWS) else 'PARTIAL_UNAVAILABLE_DRAWS', draws_available=avail,
                  decision=dict(finding_2_peak_shift=prim['A']['label'], finding_1_interior_peak=prim['B']['label'],
                                rule='A: per-draw OLS slope of the peak location on log2 epoch over E4..E32, df-9 t interval. B: INTERIOR_PEAK iff the df-9 interval '
                                     'of the mean epoch-averaged quadratic curvature lies below 0, the vertex of the mean quadratic lies in [log2 64, log2 384], and '
                                     'with a data-located break (per point, the rung nearest its quadratic vertex clamped to 96..256, in both lines) every draw has '
                                     'mean two-lines slopes and their df-9 intervals lie above 0 (left) and below 0 (right), and the df-9 interval of the per-point rise '
                                     'and fall min(left, -right), averaged per draw, lies above 0 (else RISE_AND_FALL_NOT_WITHIN_POINTS). Saturation rule S1/S32/SD for '
                                     'both. A result other than INTERIOR_PEAK is inconclusive for shallow peaks, not evidence that no peak exists.'),
                  primaries=strip(prim), by_epoch=by_epoch(data), two_point_E8_E32=two_point(data), losses=losses(data),
                  note='Only the two decision labels are pre-registered primaries; every other section is secondary or descriptive.')
    return result, point_rows(prim), fits


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4): raise SystemExit('usage: text_analysis.py <RUN_B_DIR> [<RUN_B2_DIR>] <NEW_OUT_DIR>')
    runs, out = [Path(x) for x in sys.argv[1:-1]], Path(sys.argv[-1]); out.mkdir(parents=False, exist_ok=False)
    result, points, fits = analyse(runs)
    (out / 'ANALYSIS.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_csv(out / 'POINTS.csv', points); write_csv(out / 'FITS.csv', fits)
    print(json.dumps(dict(status=result['status'], decision=result['decision']), indent=1))
