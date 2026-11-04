"""Independent check of the sealed one-rate analysis (revision 02 run, OWNER-20261030-ONERATE-02) and of every number
quoted in RESULT.md. Stdlib only; reads, never writes, the run, the activation and the analysis folder.

  python -I -B verify_result.py      -> RESULT_CHECK.json next to this script

- Binds the analysis outputs to the run (terminal, receipt and source hashes).
- Recomputes each point's three statistics from the p* and gap columns of POINTS.csv (OLS slope on log2 width;
  Spearman with average ranks) and compares them with POINTS.csv and ANALYSIS.json.
- Recomputes the three primaries and every by-epoch secondary (panel curve, gap, argmax with the sealed tie rule,
  df-9 intervals with a t quantile computed here) and compares them with ANALYSIS.json.
- Adds descriptive figures quoted in RESULT.md: the epoch decomposition of the turn-down primary, per-draw argmax
  widths, the validation-NLL minimum epoch per width, fit quality from FITS.csv, and the run's operations and power log.
Attempt 1 (work/runs/natural-text-onerate-20261030-01) is never read."""
import csv, hashlib, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A = ROOT / 'reports/natural-text-onerate-analysis-20261030-02'
RUN = ROOT / 'work/runs/natural-text-onerate-20261030-02'
ACT = ROOT / 'work/natural-text-onerate-activation-20261030-02'
SRC = ROOT / 'work/natural-text-onerate-source-20261030-02'
LADDER = [64, 96, 128, 192, 256, 384, 512, 768]
READOUTS = [1, 2, 4, 6, 8, 12, 16, 24, 32]
PRIMARY = [4, 6, 8, 12, 16, 24, 32]
DRAWS = [f'd{i:02d}' for i in range(1, 11)]
USED = dict(turn=[384, 512, 768], dip=[64, 96, 128], memo=LADDER)
TOL = 1e-9
problems = []


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_bytes().decode('utf-8'))
def mean(xs): return math.fsum(xs) / len(xs)


def check(name, got, want, tol=TOL):
    ok = (got == want) if not isinstance(want, float) else (got is not None and abs(got - want) <= tol)
    if not ok: problems.append(dict(check=name, recomputed=got, sealed=want))
    return ok


# ------------------------------------------------------------------ statistics (written here, not imported)
def t_pdf(x, df): return math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi) * (1 + x * x / df) ** (-(df + 1) / 2)


def t_cdf(x, df, steps=20000):
    """P(T <= x) for x >= 0 by Simpson's rule on [0, x]."""
    h = x / steps; s = t_pdf(0, df) + t_pdf(x, df)
    s += math.fsum((4 if k % 2 else 2) * t_pdf(k * h, df) for k in range(1, steps))
    return 0.5 + s * h / 3


def t_quantile(q, df):
    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_cdf(mid, df) < q else (lo, mid)
    return (lo + hi) / 2


T9 = t_quantile(0.975, 9)


def tint(xs):
    n = len(xs); m = mean(xs); sd = statistics_sd(xs); se = sd / math.sqrt(n)
    return dict(n=n, mean=m, sd=sd, se=se, interval=[m - T9 * se, m + T9 * se], negative=sum(x < 0 for x in xs), positive=sum(x > 0 for x in xs))


def statistics_sd(xs):
    m = mean(xs); return math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ols_slope(xs, ys):
    mx, my = mean(xs), mean(ys)
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.fsum((x - mx) ** 2 for x in xs)


def avg_ranks(xs):
    order = sorted(range(len(xs)), key=xs.__getitem__); r = [0.0] * len(xs); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(xs, ys):
    rx, ry = avg_ranks(xs), avg_ranks(ys); mx, my = mean(rx), mean(ry)
    return math.fsum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(math.fsum((a - mx) ** 2 for a in rx) * math.fsum((b - my) ** 2 for b in ry))


def stat(kind, p, g):
    ws = USED[kind]
    if kind == 'memo': return spearman([p[w] for w in ws], [g[w] for w in ws])
    return ols_slope([math.log2(w) for w in ws], [p[w] for w in ws])


LABELS = dict(turn=('TURNS_DOWN', 'CONTINUES_RISING', 'INCONCLUSIVE'), dip=('DIP_PERSISTS', 'NO_DIP_AT_ONE_RATE', 'INCONCLUSIVE'),
              memo=('OPPOSES_MEMORIZATION', 'TRACKS_MEMORIZATION', 'NO_DETECTED_TRACKING'))


def label(kind, t):
    below, above, other = LABELS[kind]
    return below if t['interval'][1] < -TOL else above if t['interval'][0] > TOL else other


# ------------------------------------------------------------------ bindings
an = load(A / 'ANALYSIS.json'); term = load(RUN / 'TERMINAL.json'); rec = load(ACT / 'OWNER_EXIT_RECEIPT.json'); appr = load(ACT / 'APPROVAL_RECORD.json')
bind = dict(analysis_sha256=sha(A / 'ANALYSIS.json'), points_sha256=sha(A / 'POINTS.csv'), fits_sha256=sha(A / 'FITS.csv'),
            terminal_sha256=sha(RUN / 'TERMINAL.json'), receipt_sha256=sha(ACT / 'OWNER_EXIT_RECEIPT.json'), approval_record_sha256=sha(ACT / 'APPROVAL_RECORD.json'),
            power_log_sha256=sha(ACT / 'POWER_LOG.jsonl'), source_subject_sha256=sha(ACT / 'SOURCE_SUBJECT.json'),
            analysis_source_sha256=sha(ACT / 'onerate_analysis.py'))
check('analysis binds the run terminal', an['run_terminal_sha256'], bind['terminal_sha256'])
check('receipt binds the run terminal', rec['terminal_sha256'], bind['terminal_sha256'])
check('receipt binds the power log', rec['power_log_sha256'], bind['power_log_sha256'])
check('activation subject is the approved one', bind['source_subject_sha256'], appr['source_subject_sha256'])
check('approval record bound in the terminal', term['bindings']['approval_record_sha256'], bind['approval_record_sha256'])
check('analysis source equals the sealed source copy', bind['analysis_source_sha256'], sha(SRC / 'onerate_analysis.py'))
check('terminal subject', term['subject'], appr['source_subject_sha256'])
check('approval id', appr['approval_id'], 'OWNER-20261030-ONERATE-02')
check('statuses', [term['status'], rec['status'], an['status'], an['run_status']], ['COMPLETE'] * 4)

# ------------------------------------------------------------------ points
rows = list(csv.DictReader((A / 'POINTS.csv').open(encoding='utf-8', newline='')))
pts = {}
for r in rows:
    p = {w: float(r[f'p_{w}']) for w in LADDER}; g = {w: float(r[f'gap_{w}']) for w in LADDER}
    pts[(r['draw'], int(r['epoch']))] = dict(p=p, gap=g, sealed={k: float(r[k]) for k in ('turn', 'dip', 'memo')})
check('points present', sorted(pts), sorted((d, e) for d in DRAWS for e in READOUTS))
vals = {}; worst = 0.0
for key, pt in pts.items():
    for k in ('turn', 'dip', 'memo'):
        v = stat(k, pt['p'], pt['gap']); vals[(key, k)] = v; worst = max(worst, abs(v - pt['sealed'][k]))
check('point statistics equal POINTS.csv (max abs diff <= 1e-12)', worst <= 1e-12, True)
for k in ('turn', 'dip', 'memo'):
    for d in DRAWS:
        for e in PRIMARY: check(f'{k} {d} E{e} point value', vals[((d, e), k)], an['primaries'][k]['point_values'][d][f'E{e}'])

# ------------------------------------------------------------------ primaries
prim = {}
for k in ('turn', 'dip', 'memo'):
    dm = {d: mean([vals[((d, e), k)] for e in PRIMARY]) for d in DRAWS}; t = tint([dm[d] for d in DRAWS])
    for d in DRAWS: check(f'{k} {d} draw mean', dm[d], an['primaries'][k]['draw_means'][d])
    for f in ('mean', 'sd', 'se'): check(f'{k} {f}', t[f], an['primaries'][k]['interval'][f])
    for i in (0, 1): check(f'{k} interval {i}', t['interval'][i], an['primaries'][k]['interval']['interval'][i])
    check(f'{k} label', label(k, t), an['primaries'][k]['label'])
    prim[k] = dict(label=label(k, t), **t)
check('t quantile df 9', T9, an['primaries']['turn']['interval']['t_critical'], 1e-8)
check('decision', [prim['turn']['label'], prim['dip']['label'], prim['memo']['label']],
      [an['decision']['turn_down'], an['decision']['dip_at_one_rate'], an['decision']['memorization']])
check('no flagged points', [an['primaries'][k]['counts']['flagged_points'] for k in ('turn', 'dip', 'memo')], [0, 0, 0])
check('fit bounds', an['fit_bounds'], dict(upper=0, lower=0, undefined=0))

# ------------------------------------------------------------------ by-epoch secondaries
by = {}
for e in READOUTS:
    curve = [mean([pts[(d, e)]['p'][w] for d in DRAWS]) for w in LADDER]
    gap = [mean([pts[(d, e)]['gap'][w] for d in DRAWS]) for w in LADDER]
    arg = LADDER[max(range(len(LADDER)), key=lambda i: (curve[i], -i))]
    s = an['by_epoch'][f'E{e}']
    for i, w in enumerate(LADDER):
        check(f'E{e} curve {w}', curve[i], s['curve'][i]); check(f'E{e} gap {w}', gap[i], s['gap'][i])
    check(f'E{e} argmax', arg, s['argmax_width'])
    row = dict(curve=dict(zip(LADDER, curve)), gap=dict(zip(LADDER, gap)), argmax_width=arg)
    for k in ('turn', 'dip', 'memo'):
        t = tint([vals[((d, e), k)] for d in DRAWS])
        for f in ('mean', 'sd'): check(f'E{e} {k} {f}', t[f], s[k]['interval'][f])
        for i in (0, 1): check(f'E{e} {k} interval {i}', t['interval'][i], s[k]['interval']['interval'][i])
        check(f'E{e} {k} signs', [t['negative'], t['positive']], [s[k]['interval']['negative'], s[k]['interval']['positive']])
        check(f'E{e} {k} label', label(k, t), s[k]['label'])
        row[k] = dict(label=label(k, t), **t)
    # per-draw argmax with the same tie rule (largest p*, then the smaller width)
    row['per_draw_argmax'] = {d: LADDER[max(range(len(LADDER)), key=lambda i: (pts[(d, e)]['p'][LADDER[i]], -i))] for d in DRAWS}
    row['gap_rises_with_every_width_step'] = all(gap[i + 1] > gap[i] for i in range(len(LADDER) - 1))
    row['p_curve_steps'] = {f'{LADDER[i]}->{LADDER[i + 1]}': curve[i + 1] - curve[i] for i in range(len(LADDER) - 1)}
    by[f'E{e}'] = row

# epoch decomposition of the turn-down primary: its mean is the mean of the seven by-epoch means
contrib = {f'E{e}': by[f'E{e}']['turn']['mean'] / len(PRIMARY) for e in PRIMARY}
decomp = dict(contributions=contrib, E4_E16=math.fsum(contrib[f'E{e}'] for e in (4, 6, 8, 12, 16)), E24_E32=math.fsum(contrib[f'E{e}'] for e in (24, 32)),
              total=math.fsum(contrib.values()), primary_mean=prim['turn']['mean'])
check('turn primary mean equals the mean of the by-epoch means', decomp['total'], prim['turn']['mean'], 1e-12)

# ------------------------------------------------------------------ losses: validation-NLL minimum epoch per width
loss = an['losses']; vmin = {}
for w in LADDER:
    series = [(0, loss[f'{w}|E0']['validation'])] + [(e, loss[f'{w}|E{e}']['validation']) for e in READOUTS]
    for e in READOUTS: check(f'gap {w} E{e} = validation - train', loss[f'{w}|E{e}']['gap'], loss[f'{w}|E{e}']['validation'] - loss[f'{w}|E{e}']['train'], 1e-12)
    e_best, v_best = min(series, key=lambda x: (x[1], x[0]))
    vmin[str(w)] = dict(epoch=e_best, validation=v_best, E32_validation=loss[f'{w}|E32']['validation'], E32_train=loss[f'{w}|E32']['train'],
                        E32_gap=loss[f'{w}|E32']['gap'], clip_fraction_mean=loss[f'{w}|clipping']['clip_fraction_mean'], clipping_source=loss[f'{w}|clipping']['source'])

# ------------------------------------------------------------------ fit quality (FITS.csv, the 3e-5 fits)
fits = [r for r in csv.DictReader((A / 'FITS.csv').open(encoding='utf-8', newline=''))]
f3 = [r for r in fits if float(r['lr']) == 3e-5]
fitq = dict(n_fits_3e5=len(f3), n_fits_run_b_rates=len(fits) - len(f3), p_min=min(float(r['p']) for r in f3), p_max=max(float(r['p']) for r in f3),
            upper_flags=sum(r['upper'] == 'True' for r in f3), lower_flags=sum(r['lower'] == 'True' for r in f3), undefined=sum(r['p'] in ('', 'None') for r in f3),
            min_total_gain=min(float(r['total_gain']) for r in f3), max_negative_fraction=max(float(r['negative_fraction']) for r in f3),
            fits_with_negative_gains=sum(float(r['negative_fraction']) > 0 for r in f3))
check('3e-5 fits: 8 widths x 9 readouts x 10 draws', fitq['n_fits_3e5'], 720)

# ------------------------------------------------------------------ operations and the power log
plog = [json.loads(x) for x in (ACT / 'POWER_LOG.jsonl').read_bytes().decode('utf-8').splitlines() if x.strip()]
ops = dict(stage_seconds={s['stage']: s['seconds'] for s in term['stages']}, worker_elapsed_seconds=term['elapsed_seconds'], owner_elapsed_seconds=rec['elapsed_seconds'],
           ladder=term['ladder'], peaks=term['peaks'], counts=term['counts'], states_deleted=sum(s['states_deleted'] for s in term['stages']),
           state_deletion_errors=sum(s['state_deletion_errors'] for s in term['stages']), inventory=term['inventory'], draw_folders=term['draw_folders'],
           counted_as_final_attempt=term['counted_as_final_attempt'], gpu_gates=[g['verdict'] for g in rec['gpu_gates']], power_prestart=rec['power_prestart'],
           power_during_run=rec['power_during_run'],
           power_log=dict(lines=len(plog), not_ac=sum(x['power'] != 'AC' for x in plog), schemes=sorted({x['scheme_name'] for x in plog}),
                          errors=sum(x['error'] is not None for x in plog), battery_min=min(x['battery_percent'] for x in plog), first_utc=plog[0]['utc'], last_utc=plog[-1]['utc']))
check('power log line count equals the receipt', ops['power_log']['lines'], rec['power_during_run']['samples'])
check('power log off-AC count equals the receipt', ops['power_log']['not_ac'], rec['power_during_run']['off_ac_samples'])
st = list(ops['stage_seconds'].values()); ops['stage_seconds_summary'] = dict(min=min(st), max=max(st), mean=mean(st))

out = dict(schema=1, purpose='Independent check of the sealed one-rate analysis and of the numbers quoted in RESULT.md',
           bindings=bind, t_quantile_df9=T9, problems=problems, verdict='PASS' if not problems else 'MISMATCH',
           primaries=prim, reading=an['reading'], by_epoch=by, turn_epoch_decomposition=decomp, validation_minimum=vmin,
           rate_pairs_64_96=an['rate_pairs_64_96'], fit_quality=fitq, operations=ops)
(HERE / 'RESULT_CHECK.json').write_bytes((json.dumps(out, indent=1, allow_nan=False) + '\n').encode('utf-8'))
print(out['verdict'], len(problems), 'problems'); [print(p) for p in problems[:20]]
