"""Independent check of the sealed late-turn analysis (OWNER-20261031-LATETURN-01) and of every number quoted in RESULT.md.
Stdlib only; reads, never writes, the run, the activation and the analysis folder.

  python -I -B verify_result.py      -> RESULT_CHECK.json next to this script

- Binds the analysis outputs to the run (terminal, receipt, approval, builder, source and power-log hashes) and records
  whether TERMINAL.json carries the terminal_outside_ledger flag (the limitation the owner accepted).
- Recomputes each point's turn statistic (OLS slope of p* on log2 width over 384, 512, 768) and peak location (argmax with
  ties to the smaller width; interior argmax refined by the vertex of the three-point parabola in log2 width, clamped to
  its bracket, the middle rung if not concave; an end rung recorded at that rung) from the p* columns of POINTS.csv, with
  formulas written here, and compares them with POINTS.csv and ANALYSIS.json.
- Recomputes P1, P3 and P2 (df-3 intervals with a t quantile computed here), their labels, the fixed sequence, the P3
  censoring counts, and every by-epoch secondary, and compares them with ANALYSIS.json.
- Adds the descriptive figures quoted in RESULT.md: the seen values on d01-d10 for comparison (from the planning record and
  the one-rate POINTS.csv restricted to 256-768), validation-NLL minima, fit quality, and the run's operations."""
import csv, hashlib, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A = ROOT / 'reports/natural-text-lateturn-analysis-20261031-01'
RUN = ROOT / 'work/runs/natural-text-lateturn-20261031-01'
ACT = ROOT / 'work/natural-text-lateturn-activation-20261031-01'
SRC = ROOT / 'work/natural-text-lateturn-source-20261031-01'
BUILDER = ROOT / 'reports/natural-text-lateturn-preparation-20261031-01/build_lateturn_activation.py'
SEEN_A = ROOT / 'reports/natural-text-onerate-analysis-20261030-02'
PLANNING = ROOT / 'reports/natural-text-onerate-confirmation-draft-20261031-01/CONFIRMATION_PLANNING.json'
WIDTHS = [256, 384, 512, 768]
TURN = [384, 512, 768]
READOUTS = [1, 2, 4, 6, 8, 12, 16, 24, 32]
AVERAGED = [4, 6, 8, 12, 16, 24, 32]
DRAWS = ['f01', 'f02', 'f03', 'f04']
SEEN = [f'd{i:02d}' for i in range(1, 11)]
PRED = dict(P1='TURNS_DOWN', P3='SHIFTS_TO_SMALLER_WIDTH', P2='TURNS_DOWN')
LABELS = dict(turn=('TURNS_DOWN', 'CONTINUES_RISING', 'INCONCLUSIVE'), shift=('SHIFTS_TO_LARGER_WIDTH', 'SHIFTS_TO_SMALLER_WIDTH', 'NO_DETECTED_SHIFT'))
TOL = 1e-9
GIB = 1024 ** 3
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
    h = x / steps; s = t_pdf(0, df) + t_pdf(x, df)
    s += math.fsum((4 if k % 2 else 2) * t_pdf(k * h, df) for k in range(1, steps))
    return 0.5 + s * h / 3


def t_quantile(q, df):
    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_cdf(mid, df) < q else (lo, mid)
    return (lo + hi) / 2


T3 = t_quantile(0.975, 3)
T9 = t_quantile(0.975, 9)


def sd(xs):
    m = mean(xs); return math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def tint(xs, t=T3):
    n = len(xs); m = mean(xs); s = sd(xs); se = s / math.sqrt(n)
    return dict(n=n, mean=m, sd=s, se=se, interval=[m - t * se, m + t * se], negative=sum(x < 0 for x in xs), positive=sum(x > 0 for x in xs))


def label(kind, t):
    below, above, other = LABELS[kind]
    return below if t['interval'][1] < -TOL else above if t['interval'][0] > TOL else other


def ols_slope(xs, ys):
    mx, my = mean(xs), mean(ys)
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.fsum((x - mx) ** 2 for x in xs)


def turn(p): return ols_slope([math.log2(w) for w in TURN], [p[w] for w in TURN])


def argmax(p, widths=WIDTHS):
    best = widths[0]
    for w in widths[1:]:
        if p[w] > p[best]: best = w           # strict: ties stay with the smaller width
    return best


def location(p):
    """(rung width, L in log2 width, kind)."""
    w = argmax(p); i = WIDTHS.index(w)
    if i in (0, len(WIDTHS) - 1): return w, math.log2(w), 'boundary'
    (x0, x1, x2), (y0, y1, y2) = [math.log2(v) for v in WIDTHS[i - 1:i + 2]], [p[v] for v in WIDTHS[i - 1:i + 2]]
    curvature = ((y2 - y1) / (x2 - x1) - (y1 - y0) / (x1 - x0)) / (x2 - x0)
    if not curvature < 0: return w, x1, 'interior'
    num = (x1 - x0) ** 2 * (y1 - y2) - (x1 - x2) ** 2 * (y1 - y0)
    den = (x1 - x0) * (y1 - y2) - (x1 - x2) * (y1 - y0)
    return w, min(max(x1 - 0.5 * num / den, x0), x2), 'interior'


# ------------------------------------------------------------------ bindings and the terminal flag
an = load(A / 'ANALYSIS.json'); term = load(RUN / 'TERMINAL.json'); rec = load(ACT / 'OWNER_EXIT_RECEIPT.json'); appr = load(ACT / 'APPROVAL_RECORD.json')
auth = load(ACT / 'AUTHORIZATION.json'); fresh = load(ACT / 'FRESH_CHECK.json'); bench = load(RUN / 'BENCHMARK.json')
bind = dict(analysis_sha256=sha(A / 'ANALYSIS.json'), points_sha256=sha(A / 'POINTS.csv'), fits_sha256=sha(A / 'FITS.csv'),
            terminal_sha256=sha(RUN / 'TERMINAL.json'), benchmark_sha256=sha(RUN / 'BENCHMARK.json'), receipt_sha256=sha(ACT / 'OWNER_EXIT_RECEIPT.json'),
            approval_record_sha256=sha(ACT / 'APPROVAL_RECORD.json'), authorization_sha256=sha(ACT / 'AUTHORIZATION.json'), power_log_sha256=sha(ACT / 'POWER_LOG.jsonl'),
            source_subject_sha256=sha(ACT / 'SOURCE_SUBJECT.json'), sealed_source_subject_sha256=sha(SRC / 'SOURCE_SUBJECT.json'),
            analysis_source_sha256=sha(ACT / 'lateturn_analysis.py'), builder_sha256=sha(BUILDER), fresh_check_sha256=sha(ACT / 'FRESH_CHECK.json'))
check('analysis binds the run terminal', an['run_terminal_sha256'], bind['terminal_sha256'])
check('analysis binds the run benchmark', an['run_benchmark_sha256'], bind['benchmark_sha256'])
check('terminal binds the benchmark', term['benchmark']['sha256'], bind['benchmark_sha256'])
check('receipt binds the run terminal', rec['terminal_sha256'], bind['terminal_sha256'])
check('receipt binds the power log', rec['power_log_sha256'], bind['power_log_sha256'])
check('activation subject equals the sealed source subject', bind['source_subject_sha256'], bind['sealed_source_subject_sha256'])
check('activation subject is the approved one', bind['source_subject_sha256'], '9286f324f9dfb49bdf2b6956c7ea76112c2a24214bdec12e931ea646f543f5ba')
check('approval record subject', appr['source_subject_sha256'], bind['source_subject_sha256'])
check('terminal subject', term['subject'], bind['source_subject_sha256'])
check('receipt subject', rec['subject'], bind['source_subject_sha256'])
check('builder is the pinned one', bind['builder_sha256'], '3d2efd0e4a305eff5d587367c3b26b986bec1000708e08c73544f33f00025714')
check('approval record names the pinned builder', appr['builder_sha256'], bind['builder_sha256'])
check('approval record bound in the terminal', term['bindings']['approval_record_sha256'], bind['approval_record_sha256'])
check('approval record bound in the authorization', auth['approval_record_sha256'], bind['approval_record_sha256'])
check('fresh check bound in the terminal', term['bindings']['fresh_check_sha256'], bind['fresh_check_sha256'])
check('registry bound in the terminal', term['bindings']['registry_sha256'], 'b9b6a8821613a1f2de610404145aaff56279a7967c130d0c215cdcf5beb0b9ff')
check('analysis source equals the sealed source copy', bind['analysis_source_sha256'], sha(SRC / 'lateturn_analysis.py'))
check('approval id', [appr['approval_id'], auth['approval_id'], term['bindings']['approval_id']], ['OWNER-20261031-LATETURN-01'] * 3)
check('approval is real', [appr['fixture'], auth['fixture'], appr['approval_id'].upper().startswith('FIXTURE')], [False, False, False])
for phrase in ('I choose option a', 'I accept the documented limitation that the terminal_outside_ledger flag is recorded in TERMINAL.json only', 'No retries'):
    check(f'approval text contains: {phrase}', phrase in appr['user_text'], True)
check('approval text has no quotes or apostrophes', any(c in appr['user_text'] for c in '"\'‘’“”'), False)
check('statuses', [term['status'], rec['status'], rec['terminal_status'], an['status'], an['run_status']], ['COMPLETE'] * 5)
check('startup', [term['startup'], an['startup']], [dict(decision='GO', reason='ALL_WIDTHS_WITHIN_LIMIT')] * 2)
check('draw folders', [term['draw_folders'], rec['draw_folders'], an['draws_available']], [DRAWS] * 3)
check('counted as the final attempt', [term['counted_as_final_attempt'], rec['counted_as_final_attempt'], rec['retry']], [True, True, False])
terminal_flag = dict(terminal_outside_ledger_present='terminal_outside_ledger' in term, draw_folders_error_present='draw_folders_error' in term,
                     inventory_present='inventory' in term, worker_stderr_bytes=(ACT / 'WORKER_STDERR.log').stat().st_size)
check('TERMINAL.json has no terminal_outside_ledger flag', terminal_flag['terminal_outside_ledger_present'], False)
check('TERMINAL.json has its ledger inventory', terminal_flag['inventory_present'], True)
check('worker stderr is empty (no terminal-publication message)', terminal_flag['worker_stderr_bytes'], 0)

# ------------------------------------------------------------------ points
rows = list(csv.DictReader((A / 'POINTS.csv').open(encoding='utf-8', newline='')))
pts = {}
for r in rows:
    pts[(r['draw'], int(r['epoch']))] = dict(p={w: float(r[f'p_{w}']) for w in WIDTHS}, gap={w: float(r[f'gap_{w}']) for w in WIDTHS},
                                             turn=float(r['turn']), loc=float(r['location_log2']))
check('points present', sorted(pts), sorted((d, e) for d in DRAWS for e in READOUTS))
worst_turn = worst_loc = 0.0; loc = {}
for key, pt in pts.items():
    worst_turn = max(worst_turn, abs(turn(pt['p']) - pt['turn']))
    loc[key] = location(pt['p']); worst_loc = max(worst_loc, abs(loc[key][1] - pt['loc']))
    check(f'{key} location equals ANALYSIS by_epoch', loc[key][1], an['by_epoch'][f'E{key[1]}']['location_log2'][key[0]])
check('turn statistics equal POINTS.csv (max abs diff <= 1e-12)', worst_turn <= 1e-12, True)
check('locations equal POINTS.csv (max abs diff <= 1e-12)', worst_loc <= 1e-12, True)

# ------------------------------------------------------------------ fits
fits = list(csv.DictReader((A / 'FITS.csv').open(encoding='utf-8', newline='')))
check('fits: 4 draws x 4 widths x 9 readouts', len(fits), 144)
for f in fits: check(f"fit p equals POINTS {f['draw']} {f['width']} E{f['epoch']}", float(f['p']), pts[(f['draw'], int(f['epoch']))]['p'][int(f['width'])], 0.0)
negfr = [float(f['negative_fraction']) for f in fits]
fitq = dict(n=len(fits), p_min=min(float(f['p']) for f in fits), p_max=max(float(f['p']) for f in fits), upper_flags=sum(f['upper'] == 'True' for f in fits),
            lower_flags=sum(f['lower'] == 'True' for f in fits), undefined=sum(f['p'] in ('', 'None') for f in fits), min_total_gain=min(float(f['total_gain']) for f in fits),
            fits_with_negative_gains=sum(x > 0 for x in negfr), fits_with_negative_share_at_least_5pct=sum(x >= 0.05 for x in negfr), max_negative_fraction=max(negfr),
            max_negative_fraction_at=next(f"{f['width']} E{f['epoch']} {f['draw']}" for f in fits if float(f['negative_fraction']) == max(negfr)),
            lrs=sorted({f['lr'] for f in fits}))
check('fit bounds', an['fit_bounds'], dict(upper=fitq['upper_flags'], lower=fitq['lower_flags'], undefined=fitq['undefined']))
check('fit bounds all zero', [fitq['upper_flags'], fitq['lower_flags'], fitq['undefined']], [0, 0, 0])

# ------------------------------------------------------------------ primaries, sequence, censoring and readings
vals = dict(P1={d: turn(pts[(d, 32)]['p']) for d in DRAWS}, P2={d: turn(pts[(d, 24)]['p']) for d in DRAWS},
            P3={d: loc[(d, 8)][1] - loc[(d, 32)][1] for d in DRAWS})
kinds = dict(P1='turn', P2='turn', P3='shift'); epochs = dict(P1=[32], P2=[24], P3=[8, 32]); used = dict(P1=TURN, P2=TURN, P3=WIDTHS)
prim = {}
for k in ('P1', 'P3', 'P2'):
    t = tint([vals[k][d] for d in DRAWS]); s = an['primaries'][k]
    for d in DRAWS: check(f'{k} {d} value', vals[k][d], s['draw_values'][d])
    for f in ('mean', 'sd', 'se'): check(f'{k} {f}', t[f], s['interval'][f])
    for i in (0, 1): check(f'{k} interval {i}', t['interval'][i], s['interval']['interval'][i])
    check(f'{k} signs', [t['negative'], t['positive']], [s['interval']['negative'], s['interval']['positive']])
    max_p = max(pts[(d, e)]['p'][w] for d in DRAWS for e in epochs[k] for w in used[k])
    check(f'{k} no draw flagged (largest fit used {max_p:.4f} < 7.999)', max_p < 7.999, True)
    check(f'{k} S32 not required', s['S32'], dict(required=False, reason='NO_FLAGGED_DRAWS'))
    check(f'{k} degenerate flag', t['sd'] <= TOL, s['degenerate'])
    lab = label(kinds[k], t); check(f'{k} label', lab, s['label']); check(f'{k} primary label', lab, s['primary_label'])
    prim[k] = dict(label=lab, values=vals[k], **t)
check('t quantile df 3', T3, an['primaries']['P1']['interval']['t_critical'], 1e-8)
check('decision', an['decision'], {k: prim[k]['label'] for k in ('P1', 'P3', 'P2')})
open_, seq = True, {}
for k in ('P1', 'P3', 'P2'):
    ok = open_ and prim[k]['label'] == PRED[k]; seq[k] = dict(label=prim[k]['label'], predicted=PRED[k], read_as_confirmation=open_, confirmed=ok); open_ = ok
check('fixed sequence P1 -> P3 -> P2', an['sequence'], seq)
locs = {d: {f'E{e}': dict(rung_width=loc[(d, e)][0], location_log2=loc[(d, e)][1], kind=loc[(d, e)][2]) for e in (8, 32)} for d in DRAWS}
for d in DRAWS:
    for e in ('E8', 'E32'):
        s = an['primaries']['P3']['locations'][d][e]
        check(f'P3 {d} {e} location', [locs[d][e]['rung_width'], locs[d][e]['kind']], [s['rung_width'], s['kind']])
        check(f'P3 {d} {e} L', locs[d][e]['location_log2'], s['location_log2'])
cens = dict(e8_top=sum(locs[d]['E8']['rung_width'] == 768 for d in DRAWS), e8_bottom=sum(locs[d]['E8']['rung_width'] == 256 for d in DRAWS),
            e32_top=sum(locs[d]['E32']['rung_width'] == 768 for d in DRAWS), e32_bottom=sum(locs[d]['E32']['rung_width'] == 256 for d in DRAWS))
cens['bound'] = 'NOT_A_BOUND' if cens['e8_bottom'] or cens['e32_top'] else 'NOT_CENSORED' if not (cens['e8_top'] or cens['e32_bottom']) else 'LOWER_BOUND_IF_CURVES_CONTINUE'
check('P3 censoring counts and bound', an['primaries']['P3']['censoring'], cens)
# the P3 reading must carry the recomputed counts and the matching ending (PROTOCOL.md section 8)
p3_text = an['readings'][2]
check('P3 reading carries the recomputed counts', (f"At E8 the peak was at the top rung (768) in {cens['e8_top']} and at the bottom rung (256) in {cens['e8_bottom']} of 4 draws; "
                                                   f"at E32, at the top rung in {cens['e32_top']} and at the bottom rung in {cens['e32_bottom']}.") in p3_text, True)
check('P3 reading has the lower-bound ending', 'conservative lower bound on the shift, provided each censored curve continues' in p3_text, cens['bound'] == 'LOWER_BOUND_IF_CURVES_CONTINUE')
check('regime reading first', an['readings'][0].startswith('The late-epoch pattern is tested at E24 and E32'), True)
check('P2 reading quotes the power', 'Power stated in advance (four draws, 95%): 0.678 at the seen effect, 0.157 conservative, 0.247 halved.' in an['readings'][3], True)
check('text-check disclosure last', an['readings'][4].startswith('10 training articles in f01-f04 were used in September by the public-text check'), True)
check('text-check articles: 10 in the fresh groups', [len(fresh['text_check_v02']['training_articles_in_fresh_groups']), {g: len(v) for g, v in fresh['text_check_v02']['by_group'].items()}],
      [10, dict(f01=5, f02=2, f03=1, f04=2)])
check('fresh check overlaps all zero', fresh['overlaps'], dict(seen_training_articles=0, seen_training_articles_by_index=0, test_articles=0, validation_articles=0))

# ------------------------------------------------------------------ by-epoch secondaries
by = {}
for e in READOUTS:
    s = an['by_epoch'][f'E{e}']
    curve = {w: mean([pts[(d, e)]['p'][w] for d in DRAWS]) for w in WIDTHS}; gap = {w: mean([pts[(d, e)]['gap'][w] for d in DRAWS]) for w in WIDTHS}
    for i, w in enumerate(WIDTHS): check(f'E{e} curve {w}', curve[w], s['curve'][i]); check(f'E{e} gap {w}', gap[w], s['gap'][i])
    check(f'E{e} panel argmax', argmax(curve), s['argmax_width'])
    pda = {d: argmax(pts[(d, e)]['p']) for d in DRAWS}; check(f'E{e} per-draw argmax', pda, s['per_draw_argmax'])
    t = tint([turn(pts[(d, e)]['p']) for d in DRAWS])
    for f in ('mean', 'sd'): check(f'E{e} turn {f}', t[f], s['turn']['interval'][f])
    for i in (0, 1): check(f'E{e} turn interval {i}', t['interval'][i], s['turn']['interval']['interval'][i])
    check(f'E{e} turn signs', [t['negative'], t['positive']], [s['turn']['interval']['negative'], s['turn']['interval']['positive']])
    check(f'E{e} turn label', label('turn', t), s['turn']['label'])
    lm = mean([loc[(d, e)][1] for d in DRAWS]); check(f'E{e} location mean', lm, s['location_mean_log2'])
    by[f'E{e}'] = dict(curve=curve, gap=gap, argmax_width=argmax(curve), per_draw_argmax=pda, turn=dict(label=label('turn', t), **t),
                       location_mean_log2=lm, location_mean_width=2 ** lm, location_kinds={d: loc[(d, e)][2] for d in DRAWS},
                       p_steps={f'{WIDTHS[i]}->{WIDTHS[i + 1]}': curve[WIDTHS[i + 1]] - curve[WIDTHS[i]] for i in range(3)},
                       gap_rises_with_every_step=all(gap[WIDTHS[i + 1]] > gap[WIDTHS[i]] for i in range(3)))
avg = tint([mean([turn(pts[(d, e)]['p']) for e in AVERAGED]) for d in DRAWS]); s = an['epoch_averaged_turn']
for f in ('mean', 'sd'): check(f'epoch-averaged turn {f}', avg[f], s['interval'][f])
for i in (0, 1): check(f'epoch-averaged turn interval {i}', avg['interval'][i], s['interval']['interval'][i])
check('epoch-averaged turn label', label('turn', avg), s['label'])

# ------------------------------------------------------------------ losses
loss = an['losses']; vmin = {}
for w in WIDTHS:
    for e in READOUTS: check(f'gap {w} E{e} = validation - train', loss[f'{w}|E{e}']['gap'], loss[f'{w}|E{e}']['validation'] - loss[f'{w}|E{e}']['train'], 1e-12)
    series = [(0, loss[f'{w}|E0']['validation'])] + [(e, loss[f'{w}|E{e}']['validation']) for e in READOUTS]
    eb, vb = min(series, key=lambda x: (x[1], x[0])); check(f'{w} validation minimum', dict(epoch=eb, validation=vb), loss[f'{w}|validation_minimum'])
    vmin[str(w)] = dict(epoch=eb, validation=vb, E0_validation=loss[f'{w}|E0']['validation'], E32_train=loss[f'{w}|E32']['train'],
                        E32_validation=loss[f'{w}|E32']['validation'], E32_gap=loss[f'{w}|E32']['gap'], clip_fraction_mean=loss[f'{w}|clipping']['clip_fraction_mean'])

# ------------------------------------------------------------------ the seen draws d01-d10, for comparison (not part of the confirmation)
plan = load(PLANNING)
seen_rows = list(csv.DictReader((SEEN_A / 'POINTS.csv').open(encoding='utf-8', newline='')))
seen_pts = {(r['draw'], int(r['epoch'])): {w: float(r[f'p_{w}']) for w in WIDTHS} for r in seen_rows}
seen_an = load(SEEN_A / 'ANALYSIS.json')
seen = dict(planning_sha256=sha(PLANNING), points_sha256=sha(SEEN_A / 'POINTS.csv'), analysis_sha256=sha(SEEN_A / 'ANALYSIS.json'), by_epoch={})
for k, key in (('P1', 'P1_turn_E32'), ('P2', 'P2_turn_E24'), ('P3', 'P3_shift_E8_E32')):
    o = plan['observed'][key]; seen[k] = dict(mean=o['mean'], sd=o['sd'], interval_95_df9=o.get('interval_95'), negative=o.get('negative'), positive=o.get('positive'))
for k, e in (('P1', 32), ('P2', 24)):
    t = tint([turn(seen_pts[(d, e)]) for d in SEEN], T9); check(f'seen {k} recomputed from one-rate POINTS.csv', t['mean'], seen[k]['mean'], 1e-12)
t = tint([location(seen_pts[(d, 8)])[1] - location(seen_pts[(d, 32)])[1] for d in SEEN], T9)
check('seen P3 recomputed on 256-768 from one-rate POINTS.csv', t['mean'], seen['P3']['mean'], 1e-12); seen['P3']['interval_95_df9'] = t['interval']
for e in READOUTS:
    c = {w: mean([seen_pts[(d, e)][w] for d in SEEN]) for w in WIDTHS}
    seen['by_epoch'][f'E{e}'] = dict(argmax_256_768=argmax(c), per_draw_argmax_256_768={w: sum(argmax(seen_pts[(d, e)]) == w for d in SEEN) for w in WIDTHS})
sl = seen_an['losses']
seen['validation_minimum_epoch'] = {str(w): min([(0, sl[f'{w}|E0']['validation'])] + [(e, sl[f'{w}|E{e}']['validation']) for e in READOUTS], key=lambda x: (x[1], x[0]))[0] for w in WIDTHS}

# ------------------------------------------------------------------ operations and the power log
plog = [json.loads(x) for x in (ACT / 'POWER_LOG.jsonl').read_bytes().decode('utf-8').splitlines() if x.strip()]
arch = bench['benchmark']['architectures']
ops = dict(stage_seconds={s['stage']: s['seconds'] for s in term['stages']}, stage_status={s['stage']: s['status'] for s in term['stages']},
           worker_elapsed_seconds=term['elapsed_seconds'], owner_elapsed_seconds=rec['elapsed_seconds'], projected_stage_seconds=bench['caps']['projected_stage_seconds'],
           stage_cap_seconds=bench['caps']['stage_work_cap_seconds'], peaks=term['peaks'], peak_sampled_gib=term['peaks']['device_used_sampled'] / GIB,
           peak_rss_gib=term['peaks']['worker_peak_rss'] / GIB, startup_peak_sampled_gib={w: arch[w]['peaks']['device_used_sampled'] / GIB for w in arch},
           startup_768_margin_mib=(bench['startup']['fit_limit_bytes'] - arch['768']['peaks']['device_used_sampled']) / 2 ** 20,
           parameters={w: arch[w]['parameters'] for w in arch}, counts=term['counts'], inventory=term['inventory'],
           benchmark_states_deleted=len(bench['states']['deleted']), benchmark_deleted_bytes=bench['states']['deleted_bytes'], benchmark_state_errors=len(bench['states']['errors']),
           draw_states_deleted=sum(s['states_deleted'] for s in term['stages']), draw_state_errors=sum(s['state_deletion_errors'] for s in term['stages']),
           draw_deleted_bytes={d: load(RUN / d / 'STATES_DELETED.json')['deleted_bytes'] for d in DRAWS},
           gpu_gates=[g['verdict'] for g in rec['gpu_gates']], gpu_prestart=rec['gpu_prestart'], power_prestart=rec['power_prestart'], power_during_run=rec['power_during_run'],
           power_log=dict(lines=len(plog), not_ac=sum(x['power'] != 'AC' for x in plog), schemes=sorted({x['scheme_name'] for x in plog}),
                          errors=sum(x['error'] is not None for x in plog), battery_min=min(x['battery_percent'] for x in plog), first_utc=plog[0]['utc'], last_utc=plog[-1]['utc']),
           approval_created_local=appr['created_local'])
check('power log line count equals the receipt', ops['power_log']['lines'], rec['power_during_run']['samples'])
check('power log off-AC count equals the receipt', ops['power_log']['not_ac'], rec['power_during_run']['off_ac_samples'])
check('all stages COMPLETE', set(ops['stage_status'].values()), {'COMPLETE'})
check('every stage under its cap', all(v < ops['stage_cap_seconds'] for v in ops['stage_seconds'].values()), True)
check('state deletion errors', [ops['benchmark_state_errors'], ops['draw_state_errors']], [0, 0])
st = list(ops['stage_seconds'].values()); ops['stage_seconds_summary'] = dict(min=min(st), max=max(st), mean=mean(st))

out = dict(schema=1, purpose='Independent check of the sealed late-turn analysis and of the numbers quoted in RESULT.md', bindings=bind, terminal_flag=terminal_flag,
           t_quantile_df3=T3, t_quantile_df9=T9, problems=problems, verdict='PASS' if not problems else 'MISMATCH',
           primaries=prim, sequence=seq, censoring=cens, p3_locations=locs, readings=an['readings'], by_epoch=by, epoch_averaged_turn=dict(label=label('turn', avg), **avg),
           validation_minimum=vmin, fit_quality=fitq, seen_d01_d10=seen, operations=ops)
(HERE / 'RESULT_CHECK.json').write_bytes((json.dumps(out, indent=1, allow_nan=False) + '\n').encode('utf-8'))
print(out['verdict'], len(problems), 'problems'); [print(p) for p in problems[:20]]
