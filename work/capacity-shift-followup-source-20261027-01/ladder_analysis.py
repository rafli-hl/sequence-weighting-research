"""Frozen capacity-ladder analysis (stdlib only). Runs after the owner run; never during it.

  python -I -B ladder_analysis.py <RUN_DIR> <OUT_DIR>

Every rule here is fixed before any outcome exists (PROTOCOL.md). Undefined fits stay undefined; no
defined-only panel mean; boundary fits are retained and counted. Corpus draws are the only resampling unit.
"""
import hashlib, itertools, json, math, statistics, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import ladder_plan as plan
from core import exponent

ROWS = dict(train=512, validation=256); PER_ROW = 7
LADDER_X = [math.log2(w) for (w, l) in plan.LADDER]
EXTRAP_FIT = (0, 1, 2, 3)          # 32, 48, 64, 96 at depth 4
EXTRAP_TARGET = 7                  # 384/4
EXTRAP_COPY = 3                    # persistence baseline: p*(96/4)
SHARE = 0.95


# ------------------------------------------------------------------ estimator helpers
def objective_at(weights, gains, p):
    """Exact copy of core.exponent's objective (ascending-weight cumulative discrepancy)."""
    order = sorted(range(len(weights)), key=weights.__getitem__); total = sum(gains)
    logw = [math.log(weights[i]) for i in order]; gn = [gains[i] / total for i in order]
    z = [p * x for x in logw]; m = max(z); z = [math.exp(x - m) for x in z]; s = sum(z); c = loss = 0.0
    for a, b in zip(gn, z): c += a - b / s; loss += c * c
    return loss / len(weights)


def fit(weights, gains):
    r = exponent(weights, gains); p = r.get('p')
    out = dict(p=p, reason=r.get('reason'))
    if p is not None:
        out.update(objective=r['objective'], J0=objective_at(weights, gains, 0.0), upper=p >= plan.P_UPPER, lower=p <= plan.P_LOWER)
    out.update(total_gain=sum(gains), negative_fraction=sum(g < 0 for g in gains) / len(gains))
    return out


def centered_profile(values, weights):
    order = sorted(range(len(weights)), key=weights.__getitem__); total = sum(values); n = len(values); s = 0.0; out = []
    for k, i in enumerate(order, 1): s += values[i]; out.append(s - k * total / n)
    return out


def area_rms(x):
    return dict(area=math.fsum(x) / len(x), rms=math.sqrt(math.fsum(v * v for v in x) / len(x)))


# ------------------------------------------------------------------ loading
def block(raw, index, rows):
    n = rows * PER_ROW; a = array('f'); a.frombytes(raw[4 * n * index:4 * n * (index + 1)])
    if len(a) != n: raise ValueError('Short array block')
    loss = list(a[:rows]); comp = [list(a[rows + 3 * i:rows + 3 * i + 3]) for i in range(rows)]
    acc = [list(a[4 * rows + 3 * i:4 * rows + 3 * i + 3]) for i in range(rows)]
    return dict(loss=loss, component=comp, accuracy=acc)


def load(run):
    run = Path(run); data = {}
    for corpus in plan.CORPORA:
        receipt = run / f'{corpus}-RECEIPT.json'
        if not receipt.exists() or json.loads(receipt.read_bytes()).get('status') != 'COMPLETE':
            data[corpus] = None; continue
        inputs = json.loads((run / corpus / 'INPUTS.json').read_bytes())
        pretrained = json.loads((run / corpus / 'PRETRAINED.json').read_bytes())
        trajectories = {}
        for (condition, arm, w, l) in plan.trajectories():
            base = run / corpus / f'{w}x{l}' / f'{condition}-{arm}'
            record = json.loads((base / 'record.json').read_bytes()); raw = (base / 'arrays.f32').read_bytes()
            e0raw = (run / corpus / f'{w}x{l}' / f'E0-{condition}.f32').read_bytes()
            for blob, bind in ((raw, record['arrays']), (e0raw, pretrained[f'{w}/{l}']['E0'][condition]['arrays'])):
                if len(blob) != bind['bytes'] or hashlib.sha256(blob).hexdigest() != bind['sha256']: raise ValueError('Array binding differs: ' + bind['path'])
            trajectories[(condition, arm, w, l)] = dict(record=record, raw=raw, e0=dict(train=block(e0raw, 0, 512), validation=block(e0raw[4 * 512 * PER_ROW:], 0, 256)))
        data[corpus] = dict(weights=inputs['weights'], trajectories=trajectories, pretrained=pretrained)
    return data


def checks_by_update(t):
    return {c['update']: (i, c) for i, c in enumerate(t['record']['checks'])}


def state_at(t, update):
    """Training arrays at an update (0 = E0) and the validation arrays if that check was validated."""
    if update == 0: return t['e0']['train'], t['e0']['validation']
    i, c = checks_by_update(t)[update]
    val = None
    if 'validation_block' in c:
        offset = len(t['record']['checks']) * 512 * PER_ROW * 4
        val = block(t['raw'][offset:], c['validation_block'], 256)
    return block(t['raw'], i, 512), val


def gains(t, update, channel):
    """Signed per-sequence training gains E0 -> update, in the confirmation's operation order.

    Total: float32 subtraction then float64 promotion. The float64 difference of two float32 values is exact,
    so rounding it back to float32 (array('f')) reproduces the correctly rounded float32 subtraction.
    Components: float64 promotion then subtraction; raw component gain (not divided by 3)."""
    e0 = t['e0']['train']; cur, _ = state_at(t, update)
    if channel == 'total': return array('f', (a - b for a, b in zip(e0['loss'], cur['loss']))).tolist()
    j = ('shared', 'group', 'instance').index(channel)
    return [float(a[j]) - float(b[j]) for a, b in zip(e0['component'], cur['component'])]


_FITS = {}
def cached_fit(corpus_data, t, update, channel='total'):
    key = (id(t), update, channel)
    if key not in _FITS: _FITS[key] = fit(corpus_data['weights'], gains(t, update, channel))
    return _FITS[key]


# ------------------------------------------------------------------ primary: peak location
T4 = 2.7764451                     # two-sided 95% Student t, 4 df (N = 5 corpora), as in the confirmation
MID = (3, 4, 5)                    # fixed central window 96/4, 128/4, 192/4 for the rise/fall contrasts
EPS = 1e-9                         # numerical tolerance for interval-sign rules (float round-off only; degenerate SD = 0 intervals)


def above(t): return t['interval'][0] > EPS
def below(t): return t['interval'][1] < -EPS


def t4(values):
    """Corpus-level mean with a two-sided 95% t4 interval (the exact percentile bootstrap under-covers at N = 5)."""
    n = len(values); m = math.fsum(values) / n; sd = statistics.stdev(values) if n > 1 else 0.0; half = T4 * sd / math.sqrt(n)
    return dict(mean=m, sd=sd, se=sd / math.sqrt(n), interval=[m - half, m + half], positive=sum(v > 0 for v in values),
                negative=sum(v < 0 for v in values), n=n)


def peak_location(curve):
    """Argmax rung (ties -> smaller width) and log2-width vertex of a 3-point parabola when interior."""
    r = max(range(len(curve)), key=lambda i: (curve[i], -i))
    if r in (0, len(curve) - 1): return r, LADDER_X[r], 'boundary'
    x0, x1, x2 = LADDER_X[r - 1:r + 2]; y0, y1, y2 = curve[r - 1:r + 2]
    denom = (x0 - x1) * (x0 - x2) * (x1 - x2)
    a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / denom
    b = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / denom
    v = -b / (2 * a) if a < 0 else x1
    return r, min(max(v, x0), x2), 'interior'


RESAMPLES = list(itertools.product(range(5), repeat=5))   # exact corpus bootstrap: 3,125 ordered resamples (descriptive)


def percentile(values, q):
    s = sorted(values); k = (len(s) - 1) * q; f = math.floor(k); c = math.ceil(k)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def classify_cell(matrix, saturated, lower=None):
    """matrix[corpus][rung] of p*; saturated/lower[corpus][rung] boundary flags.

    Order of rules (fixed): SATURATED (>= 3 corpora at the upper bound at the peak rung), FLAT_OR_LOWER_BOUND (curve
    constant within EPS, or >= 3 corpora at the lower bound at the peak rung), INTERIOR_PEAK (interior argmax in >= 95%
    of the exact bootstrap, an additional conservative gate, AND t4 intervals above 0 for both the central-window rise
    over 32/4 and fall to 384/4), otherwise PLATEAU_OR_INCONCLUSIVE when the argmax is interior; RISING_TO_LARGEST /
    FALLING_FROM_SMALLEST (boundary share >= 95% AND t4 interval of p(384) - p(32) beyond 0 in that direction);
    INCONCLUSIVE.
    """
    lower = lower or [[p <= plan.P_LOWER for p in row] for row in matrix]
    curve = [math.fsum(matrix[j][r] for j in range(5)) / 5 for r in range(len(plan.LADDER))]
    r, loc, kind = peak_location(curve)
    boot_r, boot_loc = [], []
    for s in RESAMPLES:
        c = [math.fsum(matrix[j][rr] for j in s) / 5 for rr in range(len(plan.LADDER))]
        rb, lb, _ = peak_location(c); boot_r.append(rb); boot_loc.append(lb)
    n = len(RESAMPLES); last = len(plan.LADDER) - 1
    shares = dict(interior=sum(0 < x < last for x in boot_r) / n, largest=sum(x == last for x in boot_r) / n, smallest=sum(x == 0 for x in boot_r) / n)
    mid = [math.fsum(matrix[j][k] for k in MID) / len(MID) for j in range(5)]
    rise_c = t4([mid[j] - matrix[j][0] for j in range(5)]); fall_c = t4([mid[j] - matrix[j][last] for j in range(5)])
    end_c = t4([matrix[j][last] - matrix[j][0] for j in range(5)])
    sat_at_peak = sum(saturated[j][r] for j in range(5)); low_at_peak = sum(lower[j][r] for j in range(5))
    if sat_at_peak >= 3: label = 'SATURATED'
    elif max(curve) - min(curve) <= EPS or low_at_peak >= 3: label = 'FLAT_OR_LOWER_BOUND'
    elif shares['interior'] >= SHARE and above(rise_c) and above(fall_c): label = 'INTERIOR_PEAK'
    elif 0 < r < last: label = 'PLATEAU_OR_INCONCLUSIVE'
    elif shares['largest'] >= SHARE and above(end_c): label = 'RISING_TO_LARGEST'
    elif shares['smallest'] >= SHARE and below(end_c): label = 'FALLING_FROM_SMALLEST'
    else: label = 'INCONCLUSIVE'
    corpus_loc = [peak_location(matrix[j]) for j in range(5)]
    return dict(label=label, curve=curve, argmax_rung=r, argmax_width=plan.LADDER[r][0], location_log2=loc, kind=kind, shares=shares,
                location_interval_bootstrap=[percentile(boot_loc, .025), percentile(boot_loc, .975)], rise_contrast=rise_c, fall_contrast=fall_c,
                end_contrast=end_c, saturated_at_peak=sat_at_peak, lower_at_peak=low_at_peak, saturated_total=sum(map(sum, saturated)),
                corpus_locations=[c[1] for c in corpus_loc], corpus_boundary=[c[2] == 'boundary' for c in corpus_loc], _boot_loc=boot_loc,
                note='Bootstrap shares and percentile intervals are descriptive; at N = 5 they under-cover. Gating contrasts use t4.')


def ladder_matrix(data, condition, arm, point, value):
    """point(t) -> update; value(t, update) -> fit dict. Returns (matrix, saturated, missing)."""
    matrix, sat, missing = [], [], []
    for j, corpus in enumerate(plan.CORPORA):
        if data.get(corpus) is None: missing.append(dict(corpus=corpus, reason='STAGE_UNAVAILABLE')); continue
        row, srow = [], []
        for (w, l) in plan.LADDER:
            t = data[corpus]['trajectories'][(condition, arm, w, l)]; u = point(t)
            f = value(data[corpus], t, u) if u is not None else dict(p=None, reason='LANDMARK_MISSED')
            if f['p'] is None: missing.append(dict(corpus=corpus, width=w, reason=f['reason']))
            row.append(f['p']); srow.append(bool(f.get('upper')))
        matrix.append(row); sat.append(srow)
    return matrix, sat, missing


def total_fit(corpus_data, t, update):
    return cached_fit(corpus_data, t, update, 'total')


def primary(data, points):
    """points: dict name -> function(t) -> update (fixed epochs or landmarks)."""
    cells = {}
    for condition in plan.CONDITIONS:
        for arm in ('R', 'S_batch'):
            for name, point in points.items():
                m, s, missing = ladder_matrix(data, condition, arm, point, total_fit)
                key = f'{condition}|{arm}|{name}'
                cells[key] = dict(label='UNDEFINED', missing=missing) if missing else dict(classify_cell(m, s), matrix=m)
    return cells


def shift(cells, condition, arm, a='E10', b='E30'):
    """P2: t4 interval of the per-corpus location change; censored if any corpus curve peaks at a ladder end."""
    x, y = cells[f'{condition}|{arm}|{a}'], cells[f'{condition}|{arm}|{b}']
    if 'curve' not in x or 'curve' not in y: return dict(label='UNDEFINED')
    d = t4([q - p for p, q in zip(x['corpus_locations'], y['corpus_locations'])])
    censored = any(x['corpus_boundary']) or any(y['corpus_boundary'])
    label = 'MOVES_SMALLER' if below(d) else 'MOVES_LARGER' if above(d) else 'NO_DETECTED_SHIFT'
    boot = [q - p for p, q in zip(x['_boot_loc'], y['_boot_loc'])]
    return dict(label=label + ('_CENSORED' if censored else ''), censored=censored, per_corpus=d,
                panel_delta_log2=y['location_log2'] - x['location_log2'], panel_bootstrap_interval=[percentile(boot, .025), percentile(boot, .975)])


def decide(cells, shifts, condition):
    """Pre-declared mapping for questions (a) and (b) under full weighting R; the trigger is ANY of E10/E20/E30."""
    late = [cells[f'{condition}|R|E{e}']['label'] for e in (10, 20, 30)]
    if any(x in ('UNDEFINED', 'SATURATED', 'FLAT_OR_LOWER_BOUND') for x in late): return 'INCONCLUSIVE_UNDEFINED_SATURATED_OR_FLAT'
    if 'INTERIOR_PEAK' in late:
        s = shifts[f'{condition}|R']
        if s['label'].startswith('MOVES_'):
            return 'MOVING_PEAK_' + s['label'].split('_')[1] + ('_CENSORED' if s.get('censored') else '')
        return 'INTERIOR_PEAK_NO_DETECTED_SHIFT'
    if all(x in ('RISING_TO_LARGEST', 'FALLING_FROM_SMALLEST') for x in late):
        return 'MONOTONIC_WITHIN_LADDER' if len(set(late)) == 1 else 'MONOTONIC_DIRECTION_CHANGES'   # a peak may sweep across the ladder
    return 'INCONCLUSIVE'


# ------------------------------------------------------------------ (c) late rise and instance dependence
def rise(data, condition, arm, epoch):
    vals = []
    for corpus in plan.CORPORA:
        if data.get(corpus) is None: return None
        ps = []
        for (w, l) in plan.LADDER:
            f = total_fit(data[corpus], data[corpus]['trajectories'][(condition, arm, w, l)], 16 * epoch)
            if f['p'] is None: return None
            ps.append(f['p'])
        vals.append(math.fsum(p - ps[0] for p in ps) / len(ps))
    return vals


def late_rise(data):
    """Rise = mean over ladder rungs of p* minus p*(32/4), per corpus; t4 intervals at E20 and E30 (both required)."""
    out = {}
    for condition in plan.CONDITIONS:
        rows = {}
        for e in (20, 30):
            rR, rS = rise(data, condition, 'R', e), rise(data, condition, 'S_batch', e)
            if rR is None or rS is None: rows[f'E{e}'] = dict(label='UNDEFINED'); continue
            rows[f'E{e}'] = dict(rise_R=t4(rR), rise_S=t4(rS), delta=t4([a - b for a, b in zip(rR, rS)]))
        if any('delta' not in v for v in rows.values()): label = 'UNDEFINED'
        elif not all(above(v['rise_R']) for v in rows.values()): label = 'NO_LATE_RISE_UNDER_R'   # lower bound not above 0 at E20 or E30
        elif all(above(v['delta']) for v in rows.values()): label = 'RISE_DEPENDS_ON_INSTANCE_HETEROGENEITY'
        elif all(below(v['delta']) for v in rows.values()): label = 'RISE_LARGER_WITHOUT_HETEROGENEITY'
        else: label = 'NOT_SUPPORTED_OR_INCONCLUSIVE'
        out[condition] = dict(label=label, epochs=rows)
    return out


# ------------------------------------------------------------------ finding (3): extrapolation
def lstsq_poly(xs, ys, degree):
    n = degree + 1
    A = [[sum(x ** (i + j) for x in xs) for j in range(n)] for i in range(n)]; b = [sum(y * x ** i for x, y in zip(xs, ys)) for i in range(n)]
    for c in range(n):                         # Gaussian elimination with partial pivoting
        p = max(range(c, n), key=lambda r: abs(A[r][c])); A[c], A[p] = A[p], A[c]; b[c], b[p] = b[p], b[c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]; A[r] = [a - f * q for a, q in zip(A[r], A[c])]; b[r] -= f * b[c]
    coef = [0.0] * n
    for r in reversed(range(n)): coef[r] = (b[r] - sum(A[r][k] * coef[k] for k in range(r + 1, n))) / A[r][r]
    return coef


def clamp(p): return min(8.0, max(0.0, p))


def extrapolation(data):
    """Primary: a straight line in log2 width fitted to 32/48/64/96 predicts p*(384/4) (clamped to [0, 8]); baseline
    persistence p*(96/4). Per corpus, d = |persistence error| - |line error|; t4 interval of the mean d. The quadratic
    is secondary (it amplifies rung noise about 13-fold at 384/4)."""
    out = {}
    xs = [LADDER_X[i] for i in EXTRAP_FIT]; xt = LADDER_X[EXTRAP_TARGET]
    for condition in plan.CONDITIONS:
        epochs = {}
        for e in plan.FIXED_EPOCHS:
            m, s, missing = ladder_matrix(data, condition, 'R', lambda t, e=e: 16 * e, total_fit)
            if missing: epochs[f'E{e}'] = dict(label='UNAVAILABLE', missing=len(missing)); continue
            err = dict(linear=[], quadratic=[], copy=[]); d = []; line_err = []; dens = []; sign = 0
            for j in range(5):
                ys = [m[j][i] for i in EXTRAP_FIT]; target = m[j][EXTRAP_TARGET]; base = m[j][EXTRAP_COPY]
                lin = lstsq_poly(xs, ys, 1); quad = lstsq_poly(xs, ys, 2)
                pl = clamp(lin[0] + lin[1] * xt); pq = clamp(quad[0] + quad[1] * xt + quad[2] * xt * xt)
                err['linear'].append(abs(pl - target)); err['quadratic'].append(abs(pq - target)); err['copy'].append(abs(base - target))
                d.append(abs(base - target) - abs(pl - target)); line_err.append(abs(pl - target)); dens.append(abs(target - base))
                sign += (pl - base > 0) == (target - base > 0)
            dd = t4(d); change = t4([m[j][EXTRAP_TARGET] - m[j][EXTRAP_COPY] for j in range(5)])
            label = 'BEATS_PERSISTENCE' if above(dd) else 'WORSE_THAN_PERSISTENCE' if below(dd) else 'NO_DETECTED_DIFFERENCE'
            # Relative error only when every corpus has a real 96 -> 384 change (no defined-only median).
            median_rel = statistics.median(a / b for a, b in zip(line_err, dens)) if all(b > EPS for b in dens) else None
            large_change = above(change) or below(change)
            # PREDICTED needs the line to beat persistence AND to capture most of the change (median relative error < 0.5);
            # a line that beats persistence but misses most of the change is NEITHER (review of revision 03, F1).
            reading = ('PREDICTED' if label == 'BEATS_PERSISTENCE' and median_rel is not None and median_rel < 0.5 else
                       'UNPREDICTED_CHANGE' if label != 'BEATS_PERSISTENCE' and large_change and median_rel is not None and median_rel >= 0.5 else 'NEITHER')
            epochs[f'E{e}'] = dict(label=label, finding3_epoch=reading, MAE={k: math.fsum(v) / 5 for k, v in err.items()}, error_difference=dd,
                                   change_96_to_384=change, median_relative_error=median_rel, sign_agreement=sign / 5,
                                   target_saturated=sum(s[j][EXTRAP_TARGET] for j in range(5)))
        good = [v for v in epochs.values() if v['label'] != 'UNAVAILABLE']
        beats = sum(v['label'] == 'BEATS_PERSISTENCE' for v in good); worse = sum(v['label'] == 'WORSE_THAN_PERSISTENCE' for v in good)
        unpredicted = sum(v['finding3_epoch'] == 'UNPREDICTED_CHANGE' for v in good); predicted = sum(v['finding3_epoch'] == 'PREDICTED' for v in good)
        if len(good) < 4: label, finding3 = 'UNAVAILABLE', 'UNDETERMINED'
        else:
            label = 'EXTRAPOLATION_BEATS_PERSISTENCE' if beats >= 4 else 'EXTRAPOLATION_WORSE_THAN_PERSISTENCE' if worse >= 4 else 'NO_CONSISTENT_DIFFERENCE'
            finding3 = 'CONSISTENT_WITH_FINDING_3' if unpredicted >= 4 else 'NOT_CONSISTENT_WITH_FINDING_3' if predicted >= 4 else 'UNDETERMINED'
        out[condition] = dict(label=label, finding3=finding3, epochs=epochs,
                              rule='line in log2 width on 32..96 -> 384, clamped; t4 on per-corpus |persistence error| - |line error|; '
                                   'condition label needs >= 4 of 6 epochs. Finding (3): an epoch is UNPREDICTED_CHANGE if the line does not beat '
                                   'persistence, the t4 interval of p(384) - p(96) excludes 0, and the median over all 5 corpora of '
                                   '|line error| / |p(384) - p(96)| is >= 0.5 (undefined if any change <= EPS); PREDICTED if the line beats '
                                   'persistence and that median is defined and < 0.5; NEITHER otherwise. CONSISTENT if >= 4 epochs '
                                   'UNPREDICTED_CHANGE, NOT_CONSISTENT if >= 4 PREDICTED, else UNDETERMINED.')
    return out


# ------------------------------------------------------------------ secondaries and matched progress
def landmark_update(q):
    def point(t):
        s = t['record']['landmarks'][str(q)]
        return s['update'] if s['status'] == 'CROSSED' else None
    return point


def lm_name(q): return 'P' + ('%g' % (100 * q))


def interaction_shared(data, update_of, pair):
    """RHG shared R-H architecture interaction in the RHG sign convention (METHOD.md of the RHG source):
    I = (d_R,big - d_H,big) - (d_R,small - d_H,small), with d = mean shared training NLL at the point minus own E0
    (an NLL change, i.e. minus the gain). Positive means a larger relative R penalty at the bigger architecture."""
    vals = []
    for corpus in plan.CORPORA:
        if data.get(corpus) is None: return None
        d = {}
        for arm in ('R', 'H'):
            for (w, l) in pair:
                t = data[corpus]['trajectories'][('G1', arm, w, l)]; u = update_of(t)
                if u is None: return None
                g = gains(t, u, 'shared'); d[(arm, (w, l))] = -math.fsum(g) / len(g)
        small, big = pair
        vals.append((d[('R', big)] - d[('H', big)]) - (d[('R', small)] - d[('H', small)]))
    return vals


def secondaries(data):
    rows, clipping = [], []
    for corpus in plan.CORPORA:
        if data.get(corpus) is None: continue
        wts = data[corpus]['weights']
        for key, t in data[corpus]['trajectories'].items():
            condition, arm, w, l = key
            for ep in t['record']['epochs']:
                clipping.append(dict(corpus=corpus, condition=condition, arm=arm, arch=f'{w}/{l}', **ep))
            points = {f'E{e}': 16 * e for e in plan.FIXED_EPOCHS}
            points.update({lm_name(q): landmark_update(q)(t) for q in plan.ALL_LANDMARKS})
            for name, u in points.items():
                row = dict(corpus=corpus, condition=condition, arm=arm, arch=f'{w}/{l}', point=name, update=u)
                if u is not None:
                    tr, va = state_at(t, u)
                    row['train_loss'] = math.fsum(tr['loss']) / 512
                    row['progress'] = checks_by_update(t)[u][1]['progress']
                    for j, c in enumerate(('shared', 'group', 'instance')):
                        g = gains(t, u, c); row[f'gain_{c}'] = math.fsum(g) / 512
                        prof = area_rms(centered_profile([x / 3 for x in g], wts)); row[f'profile_{c}_area'] = prof['area']; row[f'profile_{c}_rms'] = prof['rms']
                        if arm != 'U':
                            f = cached_fit(data[corpus], t, u, c); row.update({f'p_{c}': f['p'], f'reason_{c}': f['reason'], f'J_{c}': f.get('objective'), f'J0_{c}': f.get('J0')})
                    if arm != 'U':
                        f = cached_fit(data[corpus], t, u, 'total'); row.update(p_total=f['p'], reason_total=f['reason'], J_fit=f.get('objective'), J0=f.get('J0'), upper=f.get('upper'), lower=f.get('lower'))
                    if va is not None:
                        row['validation_loss'] = math.fsum(va['loss']) / 256
                        for j, c in enumerate(('shared', 'group', 'instance')): row[f'validation_{c}'] = math.fsum(r[j] for r in va['component']) / 256
                rows.append(row)
    return rows, clipping


def u_comparisons(data):
    """Validation NLL (total and per component) of each weighted arm minus the paired U arm, fixed epochs; t4 over corpora."""
    out = {}
    for condition in plan.CONDITIONS:
        for (w, l) in plan.ARCHS:
            for arm in ('R', 'S_batch', 'H'):
                if (condition, arm, w, l) not in plan.trajectories(): continue
                for e in plan.FIXED_EPOCHS:
                    vals = {k: [] for k in ('total', 'shared', 'group', 'instance')}
                    for corpus in plan.CORPORA:
                        if data.get(corpus) is None: vals = None; break
                        tr = data[corpus]['trajectories']
                        _, a = state_at(tr[(condition, arm, w, l)], 16 * e); _, u = state_at(tr[(condition, 'U', w, l)], 16 * e)
                        vals['total'].append((math.fsum(a['loss']) - math.fsum(u['loss'])) / 256)
                        for j, c in enumerate(('shared', 'group', 'instance')):
                            vals[c].append((math.fsum(r[j] for r in a['component']) - math.fsum(r[j] for r in u['component'])) / 256)
                    out[f'{condition}|{w}/{l}|{arm}-U|E{e}'] = {k: t4(v) for k, v in vals.items()} if vals is not None else dict(label='UNDEFINED')
    return out


def instance_profile_contrast(data, condition, point, archs=((64, 4), (256, 4))):
    """R - S_batch signed instance capacity-profile area between two rungs, each trajectory at its own point."""
    vals = []
    for corpus in plan.CORPORA:
        if data.get(corpus) is None: return None
        tr = data[corpus]['trajectories']; w = data[corpus]['weights']; areas = {}
        for arm in ('R', 'S_batch'):
            prof = {}
            for arch in archs:
                t = tr[(condition, arm) + arch]; u = point(t)
                if u is None: return None
                g_total = sum(gains(t, u, 'total'))
                if g_total <= 1e-10 or sum(gains(t, u, 'group')) <= 1e-10: return None   # the confirmation's normalization guard
                prof[arch] = ([x / 3 for x in gains(t, u, 'instance')], g_total)
            lo, hi = centered_profile(prof[archs[0]][0], w), centered_profile(prof[archs[1]][0], w)
            scale = 0.5 * (1 / prof[archs[1]][1] + 1 / prof[archs[0]][1])
            areas[arm] = math.fsum(scale * (h - l) for l, h in zip(lo, hi)) / len(lo)
        vals.append(areas['R'] - areas['S_batch'])
    return vals


def companions(data):
    """Section 5 companions: K per arm on the ladder (256/4 - 64/4) and bridge (256/4 - 64/2), Delta_K (t4), and the
    instance capacity-profile area R - S_batch (64/4 -> 256/4) at E20 and at each landmark."""
    out = {}
    for condition in plan.CONDITIONS:
        for e in (10, 20, 30):
            for name, (lo, hi) in dict(ladder=((64, 4), (256, 4)), bridge=((64, 2), (256, 4))).items():
                ks = {}
                for arm in ('R', 'S_batch'):
                    vals = []
                    for corpus in plan.CORPORA:
                        if data.get(corpus) is None: vals = None; break
                        tr = data[corpus]['trajectories']
                        a = total_fit(data[corpus], tr[(condition, arm) + lo], 16 * e); b = total_fit(data[corpus], tr[(condition, arm) + hi], 16 * e)
                        if a['p'] is None or b['p'] is None: vals = None; break
                        vals.append(b['p'] - a['p'])
                    ks[arm] = vals
                key = f'{condition}|E{e}|{name}'
                if ks['R'] is None or ks['S_batch'] is None: out[key] = dict(label='UNDEFINED'); continue
                out[key] = dict(K_R=t4(ks['R']), K_S_batch=t4(ks['S_batch']), Delta_K=t4([a - b for a, b in zip(ks['R'], ks['S_batch'])]))
        for name, point in [('E20', lambda t: 320)] + [(lm_name(q), landmark_update(q)) for q in plan.ALL_LANDMARKS]:
            v = instance_profile_contrast(data, condition, point)
            out[f'{condition}|{name}|instance_profile_R_minus_S'] = t4(v) if v is not None else dict(label='UNDEFINED')
    return out


def interpolated_landmark_fit(corpus_data, t, q):
    """Sensitivity: p* from per-sequence losses interpolated between the bracketing checks at the crossing."""
    s = t['record']['landmarks'][str(q)]
    if s['status'] != 'CROSSED': return dict(p=None, reason='LANDMARK_MISSED')
    if s['P'] == s['previous_P']: return total_fit(corpus_data, t, s['update'])
    alpha = (q - s['previous_P']) / (s['P'] - s['previous_P'])
    prev, _ = state_at(t, s['previous_update']); cur, _ = state_at(t, s['update']); e0 = t['e0']['train']['loss']
    interp = [(1 - alpha) * a + alpha * b for a, b in zip(prev['loss'], cur['loss'])]
    return fit(corpus_data['weights'], array('f', (x - y for x, y in zip(e0, interp))).tolist())


SUBSTANTIVE = ('INTERIOR_PEAK', 'RISING_TO_LARGEST', 'FALLING_FROM_SMALLEST')


def persistence_reading(data, cells, matched):
    """Pre-declared fixed-epoch <-> landmark mapping: the reference epoch is the fixed epoch whose update count is
    nearest to the median crossing update of the 40 ladder trajectories in that cell (ties -> earlier epoch).
    UNDEFINED if any of the 40 trajectories missed the landmark or either cell is UNDEFINED; NOT_INFORMATIVE unless both
    labels are substantive (INTERIOR_PEAK, RISING_TO_LARGEST, FALLING_FROM_SMALLEST); otherwise PERSISTS if they are
    equal and NOT_SEPARABLE_FROM_PROGRESS if they differ."""
    out = {}
    for condition in plan.CONDITIONS:
        for arm in ('R', 'S_batch'):
            for q in plan.ALL_LANDMARKS:
                key = f'{condition}|{arm}|{lm_name(q)}'; lm = matched.get(key, {})
                ups = []
                for corpus in plan.CORPORA:
                    if data.get(corpus) is None: break
                    for (w, l) in plan.LADDER:
                        u = landmark_update(q)(data[corpus]['trajectories'][(condition, arm, w, l)])
                        if u is not None: ups.append(u)
                if len(ups) < 40 or 'curve' not in lm: out[key] = dict(reading='UNDEFINED', crossed=len(ups)); continue
                med = statistics.median(ups); ref = min(plan.FIXED_EPOCHS, key=lambda e: (abs(16 * e - med), e))
                fixed_cell = cells[f'{condition}|{arm}|E{ref}']; fixed = fixed_cell['label']
                if 'curve' not in fixed_cell: reading = 'UNDEFINED'
                elif fixed not in SUBSTANTIVE or lm['label'] not in SUBSTANTIVE: reading = 'NOT_INFORMATIVE'
                else: reading = 'PERSISTS' if fixed == lm['label'] else 'NOT_SEPARABLE_FROM_PROGRESS'
                out[key] = dict(reading=reading, reference_epoch=ref, median_crossing_update=med, fixed_label=fixed, landmark_label=lm['label'])
    return out


def selected_view(data):
    """Descriptive validation-selected epoch per trajectory (lowest total validation NLL over E0 and fixed epochs)."""
    rows = []
    for corpus in plan.CORPORA:
        if data.get(corpus) is None: continue
        for key, t in data[corpus]['trajectories'].items():
            candidates = [(0, math.fsum(t['e0']['validation']['loss']) / 256)]
            for e in plan.FIXED_EPOCHS:
                _, va = state_at(t, 16 * e); candidates.append((e, math.fsum(va['loss']) / 256))
            e, v = min(candidates, key=lambda x: (x[1], x[0]))
            f = total_fit(data[corpus], t, 16 * e) if e > 0 and key[1] != 'U' else dict(p=None, reason='E0_SELECTED' if e == 0 else 'constant_weights')
            rows.append(dict(corpus=corpus, condition=key[0], arm=key[1], arch=f'{key[2]}/{key[3]}', selected_epoch=e, validation_nll=v, p_total=f['p'], reason=f['reason']))
    return rows


def strip(cells): return {k: {x: y for x, y in v.items() if not x.startswith('_')} for k, v in cells.items()}


def analyse(run):
    data = load(run)
    fixed = {f'E{e}': (lambda t, e=e: 16 * e) for e in plan.FIXED_EPOCHS}
    cells = primary(data, fixed)
    shifts = {f'{c}|{a}': shift(cells, c, a) for c in plan.CONDITIONS for a in ('R', 'S_batch')}
    matched = primary(data, {lm_name(q): landmark_update(q) for q in plan.ALL_LANDMARKS})
    sensitivity = {}
    for q in plan.ALL_LANDMARKS:
        for condition in plan.CONDITIONS:
            for arm in ('R', 'S_batch'):
                m, s, missing = ladder_matrix(data, condition, arm, landmark_update(q), lambda cd, t, u, q=q: interpolated_landmark_fit(cd, t, q))
                sensitivity[f'{condition}|{arm}|{lm_name(q)}_interpolated'] = dict(label='UNDEFINED', missing=missing) if missing else {x: y for x, y in classify_cell(m, s).items() if not x.startswith('_')}
    bridge_order = {}
    for name, point in [(f'E{e}', (lambda t, e=e: 16 * e)) for e in (10, 20, 30)] + [(lm_name(q), landmark_update(q)) for q in plan.ALL_LANDMARKS]:
        for condition in plan.CONDITIONS:
            means = {}
            for arch in ((64, 2), (128, 3), (256, 4)):
                vals = []
                for corpus in plan.CORPORA:
                    if data.get(corpus) is None: vals = None; break
                    t = data[corpus]['trajectories'][(condition, 'R') + arch]; u = point(t)
                    f = total_fit(data[corpus], t, u) if u is not None else dict(p=None)
                    if f['p'] is None: vals = None; break
                    vals.append(f['p'])
                means[f'{arch[0]}/{arch[1]}'] = math.fsum(vals) / 5 if vals is not None else None
            bridge_order[f'{condition}|R|{name}'] = means
    rhg = {}
    for name, pair in (('bridge_64x2_256x4', ((64, 2), (256, 4))), ('fixed_depth_64x4_256x4', ((64, 4), (256, 4)))):
        rhg[name] = {}
        for label, fn in [('update80', lambda t: 80)] + [(lm_name(q), landmark_update(q)) for q in plan.ALL_LANDMARKS]:
            v = interaction_shared(data, fn, pair); rhg[name][label] = t4(v) if v is not None else dict(label='UNDEFINED')
    rows, clipping = secondaries(data)
    result = dict(
        status='COMPLETE' if all(data[c] is not None for c in plan.CORPORA) else 'PARTIAL_UNAVAILABLE_CORPORA',
        corpora_available=[c for c in plan.CORPORA if data[c] is not None],
        primary_fixed_epoch=strip(cells), peak_shift_E10_E30=shifts, decisions={c: decide(cells, shifts, c) for c in plan.CONDITIONS},
        instance_late_rise=late_rise(data), late_rise_companions=companions(data), extrapolation=extrapolation(data),
        matched_progress=dict(primary=strip(matched), persistence_reading=persistence_reading(data, cells, matched),
                              interpolated_sensitivity=sensitivity, bridge_p_order=bridge_order, shared_R_minus_H_RHG_sign=rhg),
        u_comparisons=u_comparisons(data), validation_selected_view=selected_view(data),
        note='Fixed-epoch and matched-progress results are reported side by side; neither is chosen after outcomes.')
    return result, rows, clipping


if __name__ == '__main__':
    run, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=False, exist_ok=False)
    result, rows, clipping = analyse(run)
    (out / 'ANALYSIS.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    import csv
    for name, table in (('SECONDARIES.csv', rows), ('CLIPPING.csv', clipping)):
        fields = sorted({k for r in table for k in r})
        with (out / name).open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)
    print(json.dumps(dict(status=result['status'], decisions=result['decisions']), indent=1))
