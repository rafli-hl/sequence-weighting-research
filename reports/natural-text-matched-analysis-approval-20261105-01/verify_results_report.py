"""The verifier of the matched-progress confirmation's results report, N7: it checks the report's numbers against the analysis output. Native Python 3.12 -I -B; stdlib only.

  python -I -B verify_results_report.py <ANALYSIS_DIR> <RESULT_DIR> <OWNER_DECISION_FILE>      -> RESULT_VERIFICATION.json in RESULT_DIR; exit 0 if everything holds, 1 if not

Written and tested on invented losses before any p*, gain or loss of this study was opened. It runs after make_results_report.py, opens nothing under work/runs (an audit hook in its own command line stops it if anything tries), and changes nothing but its own record. In real mode it refuses before it opens any output unless the owner decision file quotes the approval with the layout's hash and this file's, the analysis folder is the only one of the study, and the sealed source is unchanged. Its comparisons use no sealed module, and it loads the layout only afterwards, for the third part below. Its constants are its own, and the tests compare them with the sealed plan.

1. The outputs against themselves. From POINTS.csv alone, in code of its own: each target, bracket, weight, read position and contrast; each mean, interval and p-value, with the t tail integrated directly; the sign tests and leave-one-out intervals; each side, status and label; the sequence; NOT_OVERFIT; the rate effects; the by-readout tables; the panel means and losses; the bound counts. Each is compared with ANALYSIS.json and MATCHED.csv. Each reading is compared word for word with this file's copy of the sealed wording, under the recomputed labels and prefixes. The outputs' hashes must equal the exit receipt the owner's command wrote.
2. The report against the outputs. Every table in RESULT.md, in order: its header and every cell, against a value this file formats itself. Every reading, as quoted. The section 9 quotation against PROTOCOL.md. Outside tables and quotations, every number must be one of the plan's constants, listed here.
3. The report against the frozen layout: byte for byte what make_results_report.py writes from those outputs. So wording is covered too.

Not recomputed, and listed in its record: p* itself and the other fields of FITS.csv; the training and validation NLL in POINTS.csv, from each record.json, on which every target, bracket and matched contrast rests; the E0 losses; clipping; any refit at bound 32, which can move a label; and the record-against-array difference. They need the run files under work/runs/, which only the sealed analysis read."""
import csv, datetime as dt, hashlib, importlib.util, json, math, os, re, sys, time
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = Path(r'D:\sequence-weighting-research'); REPORTS = ROOT / 'reports'; SRC = ROOT / 'work/natural-text-matched-source-20261104-01'; LAYOUT = HERE / 'make_results_report.py'; INPUT_CHECK = HERE / 'check_run_inputs.py'; CHECKS = REPORTS / 'natural-text-matched-run-checks-20261104-01'

SUBJECT = '7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56'; ANALYSIS_SHA256 = '2108f0b287a0b355d20b3d6faedec6bd93d6ad1074f3f5da629b69e14e6ddf9c'; PROTOCOL_SHA256 = 'adf006ba144efccbf54710dc0c3ae56cba9b66d105c0d25624e5b8e1348dd23e'
M1_TERMINAL = '1392187d518d55ce9463fd7c687d258a791e7e1780d68e4be46b11de1337e65d'; M2_TERMINAL = '6ac3614815ce884dffbfb1b093188fb72699a636a24fbd9c7070b6b4fe8c3737'; MERGE_COMMIT = 'f3a2571029f4a0b4d0dc2ee974338e13996e11d8'; APPROVAL_ID = 'OWNER-20261105-MATCHED-ANALYSIS-01'; INPUT_CHECK_SHA256 = 'f88bd66444f84158fb9402a52d9ab691821dbc1a02e9f3932f26b9be57e505b3'; ANALYSIS_NAME = r'natural-text-matched-analysis-\d{8}-\d{2}'
VERIFY = dict(M1=CHECKS / 'RUN_M1_VERIFICATION.json', M2=CHECKS / 'RUN_M2_VERIFICATION.json'); FIGURES = REPORTS / 'natural-text-matched-seed-registry-20261104-01/REGISTRY_AND_PARTITION_CHECK.json'; ENGINE = REPORTS / 'natural-text-matched-engine-check-result-20261104-01/INPUTS_CHECK.json'; MERGE_CHECK = REPORTS / 'natural-text-matched-m1-approval-20261105-01/MERGE_CHECK.json'; APPROVALS = dict(M1=ROOT / 'work/natural-text-matched-activation-m1-20261104-01/APPROVAL_RECORD.json', M2=ROOT / 'work/natural-text-matched-activation-m2-20261104-01/APPROVAL_RECORD.json')
PINS = {VERIFY['M1']: '77c4277ed5375ca61c28babdc8340eb0ff1cb4483655b164b8682c15b5ba00e8', VERIFY['M2']: '2cab0b791f7cd50d5d600823484e1fcfe773579a2cc9c1df5fbc209038106278', FIGURES: '548f2b6a80bb8f88df17f176d67c790053bdcd0eefdfb477498f3b85f58d7765', ENGINE: '022591d909988e2fd3dddb65e202f54fe3cf12897956a6602d076d9feff35d27', MERGE_CHECK: '3f1c28652d229f6532301b308e40c0f2823e415f8b6208119272d8bdc7ad0c63', APPROVALS['M1']: '0635a05faaa9653018e3a87dbf46dfdf6e1062e2d1d57a07abfa8bc091e92869', APPROVALS['M2']: '16d2dc9228a33c2c9a9b4cc84274b216907641e5da1719fdcaa958b2163fc4c2'}
OUTPUTS = ('ANALYSIS.json', 'POINTS.csv', 'FITS.csv', 'MATCHED.csv'); INPUT_ITEMS = ('n_train', 'weights', 'weights_list', 'orders', 'pool_orders', 'tied_values', 'seeds', 'articles', 'sequence_indices', 'validation', 'pool')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); load = lambda p: json.loads(Path(p).read_bytes())

# The plan's constants, this file's own copy (the tests compare them with matched_plan and matched_analysis).
DRAWS = ('m01', 'm02', 'm03', 'm04', 'm05', 'm06'); WIDTHS = (512, 768); HIGH, LOW = 'lr3e-04', 'lr1e-04'; ARMS = ((512, HIGH), (512, LOW), (768, HIGH), (768, LOW))
READOUTS = (0.25, 0.5, 1, 2, 2.25, 2.5, 2.75, 3, 3.25, 3.5); MATCH_PATH = (2, 2.25, 2.5, 2.75, 3, 3.25, 3.5); FINAL, PREVIOUS = 3, 2; MIN_DRAWS, MIN_LOO = 5, 4; EPS = 1e-9; P_UPPER, P_LOWER = 7.999, 0.001; RECORD_LIMIT = 1e-3
SEQUENCE = ('P1', 'S1', 'S3', 'S4', 'S5', 'S2'); STATS = dict(P1=dict(kind='matched', key='train', tag=LOW, expected='ABOVE'), S1=dict(kind='matched', key='gap', tag=LOW, expected='ABOVE'), S3=dict(kind='fixed', key=None, tag=LOW, expected='BELOW'), S4=dict(kind='matched', key='train', tag=HIGH, expected='ABOVE'), S5=dict(kind='fixed', key=None, tag=HIGH, expected='ABOVE'), S2=dict(kind='matched', key='validation', tag=LOW, expected='ABOVE'))
PRIMARY_LABEL = dict(ABOVE='REVERSAL_CONFIRMED', BELOW='NOT_REVERSED', SPANS='INCONCLUSIVE'); UNREADABLE = ('UNAVAILABLE', 'SATURATED', 'SATURATION_SENSITIVE'); NOT_READ = 'NOT_READ'; NO_READING = ('UNDEFINED_FIT', 'TARGET_OUTSIDE_PATH', 'DRAW_MISSING')
GATE_OF = {LOW: 'rate_low', HIGH: 'rate_high'}; GATE_ARMS = dict(rate_low=((512, LOW), (768, LOW)), rate_high=((512, HIGH), (768, HIGH)))
POWER = dict(sd='0.0025', six_seen='>0.999', six_half='0.999', six_half_sd_upper='0.703', five_seen='>0.999', five_half='0.990', five_half_sd_upper='0.576')

# The sealed wording of the readings, copied without importing it; the tests compare each with the sealed module.
SCOPE = 'The models are small (depth 4, 16.9 M and 34.7 M parameters) and this is one corpus family at one recipe. A reading is about the two widths and two rates on these draws. No reading claims a mechanism or a scaling law, and nothing about Jane Street\'s scale follows.'
LIMIT = "This does not show a capacity mechanism, and nothing about Jane Street's scale follows. Matching on training loss also removes any faster learning of the wider model, so neither axis is privileged."
REVERSAL = 'At 1e-4, p* at 512 at E3 is above p* at 768 read at the training NLL 512 reaches at E3 (REVERSAL_CONFIRMED).'
AXIS_SHOWN = 'At fixed updates at E3 on these draws, 768 is above 512, so on these draws the comparison axis reverses the 512-768 ordering at 1e-4.'
AXIS_NOT_SHOWN = 'At fixed updates at E3 on these draws, 768 is not shown above 512, so on these draws the ordering is not shown to reverse: 512 is above 768 at matched training NLL, and the fixed-update order is not established here.'
AXIS_SAME = 'At fixed updates at E3 on these draws, 512 is above 768 as well, so on these draws the ordering does not reverse: 512 is above 768 on both axes, which is contrary to the fixed-update order N6 found.'
AXIS_NOT_READ = "The fixed sequence stopped before S3, so the fixed-update contrast at E3 is reported and not read here, and this study does not confirm that the ordering reverses on these draws: 512 is above 768 at matched training NLL, and N6's fixed-update order is not confirmed on them."
NOT_REVERSED = "At 1e-4, p* at 512 at E3 is below p* at 768 read at the training NLL 512 reaches at E3 (NOT_REVERSED). N6's post-hoc figure, +0.0132, is not reproduced on these draws: matching on training NLL does not put 512 above 768 here."
INCONCLUSIVE = 'At 1e-4, the interval of p* at 512 at E3 minus p* at 768 read at the training NLL 512 reaches at E3 includes 0 (INCONCLUSIVE). This is not a claim of absence.'
UNAVAILABLE = 'P1 is UNAVAILABLE: fewer than 5 draws have a reading. It is not read, and it is not evidence either way.'
STEP_TEXT = dict(S1='S1, at 1e-4, matched on the gap', S3='S3, at 1e-4, the fixed-update contrast at E3', S4='S4, at 3e-4, matched on training NLL', S5='S5, at 3e-4, the fixed-update contrast at E3', S2='S2, at 1e-4, matched on validation NLL')
S3_CONFIRMED = "S3 replicates N6's fixed-budget result (RATE_DEPENDENT): after 3,072 updates at 1e-4, 768 is above 512. This is a fixed-budget fact. It does not say that the fall from 512 to 768 depends on the rate."
STEP_CONFIRMED = dict(S1='At 1e-4, p* at 512 at E3 is above p* at 768 read at the gap 512 reaches at E3.', S2='At 1e-4, p* at 512 at E3 is above p* at 768 read at the validation NLL 512 reaches at E3.', S3=S3_CONFIRMED, S4='At 3e-4, p* at 512 at E3 is above p* at 768 read at the training NLL 512 reaches at E3.', S5='At 3e-4, after 3,072 updates, 512 is above 768, as in N6. This is a fixed-budget fact.')
STEP_CONTRARY = 'The interval lies on the other side of 0 from the one expected.'; STEP_INCONCLUSIVE = 'The interval includes 0. This is not a claim of absence.'
SIDE_WORDS = dict(ABOVE='the interval lies above 0', BELOW='the interval lies below 0', SPANS='the interval includes 0', UNAVAILABLE='fewer than 5 draws have a reading', SATURATED='saturated', SATURATION_SENSITIVE='saturation-sensitive')
DISCLOSURE = "Data: never-assigned WikiText-103 training articles, excluding every article of N5 and N6 and their text duplicates and repeats inside the pool; new seeds; no new tuning. The validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies. The hypothesis came from a post-hoc reanalysis of N6 (reports/adversarial-review-20261104-01/RECOMPUTE_MATCHED.json), so N6 cannot confirm it. p* between readouts is a linear interpolation over a quarter of an epoch. A draw whose target lies outside 768's E2-E3.5 path is unavailable for that statistic, and such draws are not a random subset. Equal training NLL is not equal gain, because p* is fit to gains from each width's own E0. The t intervals assume normal draws, untested at five or six."
RECORDS_DIFFER = 'WARNING: a record and its arrays differ by more than the limit (records_against_arrays). This changes no label. The owner decides what follows, before anything here is read.'
POWER_LINE = f"Power stated in advance, from N6's spread (sd {POWER['sd']}) and the effect it was seen at (+0.0132), which is likely flattering: with six draws {POWER['six_seen']} at that effect and {POWER['six_half']} at half of it, and {POWER['six_half_sd_upper']} at half of it with the sd at its upper 95% limit; with five draws {POWER['five_seen']}, {POWER['five_half']} and {POWER['five_half_sd_upper']}."
# Every number the report's wording may hold, outside tables, quotations, file names and hashes. Each is a constant of the plan or the layout.
PROSE_ALLOWED = frozenset(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '32', '512', '768', '95%', '7.999', '+0.0132', '1,024', '0.15%', '1e-4', '3e-4'))


class RuleBroken(BaseException):
    """Not an Exception, so that nothing on the way can catch it."""


def install_guard():
    """From here on, in this process, nothing under a work/runs folder can be opened, listed or changed."""
    events = ('open', 'os.listdir', 'os.scandir', 'glob.glob', 'os.mkdir', 'os.rename', 'os.remove', 'os.rmdir', 'os.truncate', 'os.utime', 'os.chmod', 'os.link', 'os.symlink', 'shutil.copyfile', 'shutil.copytree', 'shutil.move', 'shutil.rmtree')
    def hook(event, args):
        if event in events and args and isinstance(args[0], (str, bytes, os.PathLike)) and re.search(r'/work/runs(/|$)', os.path.abspath(os.fsdecode(args[0])).replace('\\', '/').lower()): raise RuleBroken(f'The verifier opens nothing under work/runs: {event} {args[0]}')
    sys.addaudithook(hook)


def read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))


def num(x): return None if x in ('', None) else float(x)


# ------------------------------------------------------------------ statistics, in code of their own
def t_tail(t, df):
    """P(|T| >= |t|), integrated directly. With x = sqrt(df) tan u the density is proportional to cos^(df-1) u, so the tail is the integral of sin^(df-1) v over [0, atan(sqrt(df) / |t|)], over the same integral to pi / 2. There is no subtraction, so very small values keep their relative accuracy. Simpson's rule."""
    phi = math.atan2(math.sqrt(df), abs(t)); m = 4096; h = phi / m; whole = math.sqrt(math.pi) / 2 * math.exp(math.lgamma(df / 2) - math.lgamma((df + 1) / 2))
    return math.fsum((1 if i in (0, m) else 4 if i % 2 else 2) * math.sin(i * h) ** (df - 1) for i in range(m + 1)) * h / 3 / whole


_CRIT = {}
def t_crit(df):
    if df not in _CRIT:
        lo, hi = 0.0, 100.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if t_tail(mid, df) > 0.05: lo = mid
            else: hi = mid
        _CRIT[df] = (lo + hi) / 2
    return _CRIT[df]


def stat(values):
    n = len(values); m = math.fsum(values) / n; sd = math.sqrt(math.fsum((v - m) ** 2 for v in values) / (n - 1)); se = sd / math.sqrt(n); half = t_crit(n - 1) * se
    return dict(n=n, df=n - 1, mean=m, sd=sd, se=se, interval=[m - half, m + half], negative=sum(v < 0 for v in values), positive=sum(v > 0 for v in values))


def with_p(t):
    degenerate = t['sd'] <= EPS
    return dict(t, degenerate=degenerate, p=(0.0 if abs(t['mean']) > EPS else 1.0) if degenerate else t_tail(t['mean'] / t['se'], t['df']))


def side_of(t): return 'ABOVE' if t['interval'][0] > EPS else 'BELOW' if t['interval'][1] < -EPS else 'SPANS'


def sign_test(values):
    pos, neg = sum(v > 0 for v in values), sum(v < 0 for v in values); k = pos + neg
    return dict(positive=pos, negative=neg, p=None if k == 0 else min(1.0, 2 * sum(math.comb(k, i) for i in range(min(pos, neg) + 1)) / 2 ** k))


# ------------------------------------------------------------------ part 1: the outputs against themselves
def points_table(points):
    P = {}
    for r in points: P[r['draw'], int(r['width']), r['tag'], float(r['epoch'])] = dict(p=num(r['p']), gap=num(r['gap']), validation=num(r['validation']), train=num(r['train']))
    return P


def read_on_path(P, d, tag, key, target):
    """The protocol's section 4, from its words: the first interval in readout order whose two values hold the target; a tied interval reads at its earlier readout."""
    found, holding = None, 0
    for a, b in zip(MATCH_PATH, MATCH_PATH[1:]):
        x0, x1 = P[d, 768, tag, float(a)][key], P[d, 768, tag, float(b)][key]
        if min(x0, x1) <= target <= max(x0, x1):
            holding += 1
            if found is None: found = (a, b, x0, x1)
    values = [P[d, 768, tag, float(e)][key] for e in MATCH_PATH]; out = dict(target=target, path_min=min(values), path_max=max(values), intervals_holding_the_target=holding, status='TARGET_OUTSIDE_PATH')
    if found is None: return out
    a, b, x0, x1 = found; f = 0.0 if x1 == x0 else (target - x0) / (x1 - x0); p0, p1 = P[d, 768, tag, float(a)]['p'], P[d, 768, tag, float(b)]['p']
    out.update(between=[a, b], value_at_bracket=[x0, x1], weight=f, read_at_readout=a + f * (b - a), p_at_bracket=[p0, p1], status='UNDEFINED_FIT' if p0 is None or p1 is None else 'READ')
    if out['status'] == 'READ': out['p_read'] = (1 - f) * p0 + f * p1
    return out


def own_row(P, d, name):
    c = STATS[name]; tag = c['tag']; first = P[d, 512, tag, float(FINAL)]['p']
    if c['kind'] == 'matched': r = read_on_path(P, d, tag, c['key'], P[d, 512, tag, float(FINAL)][c['key']])
    else:
        p = P[d, 768, tag, float(FINAL)]['p']; r = dict(status='READ', p_read=p, read_at_readout=FINAL) if p is not None else dict(status='UNDEFINED_FIT', read_at_readout=FINAL)
    r['p_first'] = first
    if first is None and r['status'] == 'READ': r['status'] = 'UNDEFINED_FIT'
    if r['status'] == 'READ': r['value'] = first - r['p_read']
    return r


def own_flagged(P, name, rows):
    c = STATS[name]; tag = c['tag']; out = []
    for d, r in rows.items():
        if r['status'] != 'READ': continue
        second = r['between'] if c['kind'] == 'matched' else [FINAL]
        if P[d, 512, tag, float(FINAL)]['p'] >= P_UPPER or any(P[d, 768, tag, float(e)]['p'] >= P_UPPER for e in second): out.append(d)
    return out


def own_statistics(P, A):
    """Each statistic from POINTS.csv. A refit at bound 32 needs the arrays, so its fields come from ANALYSIS.json; everything that follows from them is recomputed."""
    own = {}
    for name in SEQUENCE:
        rows = {d: own_row(P, d, name) for d in DRAWS}; available = [d for d in DRAWS if rows[d]['status'] == 'READ']; values = {d: rows[d]['value'] for d in available}; x = dict(rows=rows, available=available, values=values, unavailable={d: rows[d]['status'] for d in DRAWS if d not in available}, unavailable_counts={why: sum(rows[d]['status'] == why for d in DRAWS) for why in NO_READING}, sign_test=sign_test(list(values.values())))
        if len(available) >= MIN_LOO:
            x['leave_one_out'] = {}
            for d in values:
                t = stat([v for k, v in values.items() if k != d]); sd = side_of(t); x['leave_one_out'][d] = dict(mean=t['mean'], interval=t['interval'], df=t['df'], side=sd, excludes_zero=sd != 'SPANS')
        if len(available) < MIN_DRAWS: x.update(status='UNAVAILABLE', label0='UNAVAILABLE'); own[name] = x; continue
        t = with_p(stat(list(values.values()))); sd = side_of(t); flagged = own_flagged(P, name, rows); status = sd; x.update(interval=t, side=sd, flagged=flagged)
        if flagged:
            s32 = A['statistics'][name].get('S32') or {}
            if not s32.get('computable'): status = 'SATURATED'
            elif s32.get('side') != sd: status = 'SATURATION_SENSITIVE'
        label0 = status if status in UNREADABLE else PRIMARY_LABEL[status] if name == 'P1' else 'INCONCLUSIVE' if status == 'SPANS' else 'CONFIRMED' if status == STATS[name]['expected'] else 'CONTRARY'
        x.update(status=status, label0=label0); own[name] = x
    return own


def own_sequence(own):
    out, reached = [], True
    for name in SEQUENCE:
        confirmed = reached and own[name]['label0'] == ('REVERSAL_CONFIRMED' if name == 'P1' else 'CONFIRMED'); out.append(dict(step=name, label=own[name]['label0'] if reached else NOT_READ, status=own[name]['status'], read_as_confirmation=reached, confirmed=confirmed)); reached = confirmed
    return out


def own_not_overfit(P):
    arms = {}
    for w, t in ARMS:
        i = stat([P[d, w, t, float(FINAL)]['validation'] - P[d, w, t, float(PREVIOUS)]['validation'] for d in DRAWS]); arms[f'{w}|{t}'] = dict(interval=i, label='NOT_OVERFIT' if i['interval'][1] < -EPS else 'OVERFIT' if i['interval'][0] > EPS else 'PLATEAU')
    return dict(arms=arms, all_arms=all(v['label'] == 'NOT_OVERFIT' for v in arms.values()), gates={k: all(arms[f'{w}|{t}']['label'] == 'NOT_OVERFIT' for w, t in v) for k, v in GATE_ARMS.items()}, failing={k: [f'{w} at {t}' for w, t in v if arms[f'{w}|{t}']['label'] != 'NOT_OVERFIT'] for k, v in GATE_ARMS.items()})


def own_readings(own, seq, no, within_limit):
    """The sealed wording, word for word, for these labels. Both runs are COMPLETE here, or the layout would have refused."""
    p1 = own['P1']; without = ', '.join(f'{d} ({r})' for d, r in p1['unavailable'].items()) or 'none'; counts = '; '.join(f"{k} {', '.join(str(own[k]['unavailable_counts'][why]) for why in NO_READING)}" for k in SEQUENCE); by = {r['step']: r for r in seq}
    out = [SCOPE] + ([] if within_limit else [RECORDS_DIFFER]) + [f'P1 has a reading on {len(p1["available"])} of {len(DRAWS)} draws; without one: {without}.', f'Draws without a reading, by statistic (undefined fit, target outside the path, draw missing): {counts}.']
    def prefix(label, gate):
        failing = no['failing'][gate]
        return f"{label} is not read as a few-epoch test: {', '.join(failing)} not still improving from E2 to E3 (NOT_OVERFIT failed). " if failing else ''
    label = by['P1']['label']
    if label == 'REVERSAL_CONFIRMED':
        axis = AXIS_NOT_READ if not by['S3']['read_as_confirmation'] else AXIS_SHOWN if own['S3']['status'] == 'BELOW' else AXIS_SAME if own['S3']['status'] == 'ABOVE' else AXIS_NOT_SHOWN
        out.append(prefix(label, 'rate_low') + REVERSAL + ' ' + axis + ' ' + LIMIT)
    elif label == 'NOT_REVERSED': out.append(prefix(label, 'rate_low') + NOT_REVERSED)
    elif label == 'INCONCLUSIVE': out.append(prefix(label, 'rate_low') + INCONCLUSIVE + ' ' + POWER_LINE)
    elif label == 'UNAVAILABLE': out.append(UNAVAILABLE)
    else: out.append(f'P1 is {label}: it is not read.')
    for name in SEQUENCE[1:]:
        row = by[name]; lab = row['label']; head = STEP_TEXT[name]; stops = '' if name == SEQUENCE[-1] else ' The sequence stops here.'
        if not row['read_as_confirmation']: out.append(f"{head}: {SIDE_WORDS[row['status']]}. Reported and not read as a confirmation, because an earlier step of the fixed sequence is not confirmed.")
        elif lab in UNREADABLE: out.append(f'{head}: {lab}. It is not read.{stops}')
        else: out.append(prefix(name, GATE_OF[STATS[name]['tag']]) + f'{head}: {lab}. ' + (STEP_CONFIRMED[name] if lab == 'CONFIRMED' else (STEP_CONTRARY if lab == 'CONTRARY' else STEP_INCONCLUSIVE) + stops))
    out.append(DISCLOSURE)
    return out


def outputs_against_themselves(A, points, fits, matched):
    """Returns (mismatches, comparisons, own). Tolerances: 1e-9 on values, in relative terms on p-values, 1e-7 on the critical values and limits, whose sealed table has nine decimals."""
    bad = []; count = [0]
    def eq(name, a, b, tol=1e-9):
        count[0] += 1
        if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, (str, list, dict)) or isinstance(b, (str, list, dict)): same = a == b
        else: same = abs(a - b) <= tol
        if not same: bad.append(dict(item=name, in_the_output=a, recomputed=b))
    def eq_p(name, a, b):
        count[0] += 1
        if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-6 * max(abs(a), abs(b))): bad.append(dict(item=name, in_the_output=a, recomputed=b))
    def interval(name, x, o):
        for k in ('n', 'df', 'mean', 'sd', 'se', 'negative', 'positive'): eq(f'{name}.{k}', x.get(k), o[k])
        eq(f'{name}.t_critical', x.get('t_critical'), t_crit(o['df']), 1e-7); eq(f'{name}.low', x['interval'][0], o['interval'][0], 1e-7); eq(f'{name}.high', x['interval'][1], o['interval'][1], 1e-7)
    P = points_table(points)
    eq('POINTS.csv rows', len(points), len(DRAWS) * len(ARMS) * len(READOUTS)); eq('POINTS.csv keys', sorted(P), sorted((d, w, t, float(e)) for d in DRAWS for w, t in ARMS for e in READOUTS)); eq('FITS.csv rows', len(fits), len(points)); eq('MATCHED.csv rows', len(matched), len(SEQUENCE) * len(DRAWS))
    if bad: return bad, count[0], None
    for r in points: eq(f'POINTS {r["draw"]} {r["width"]} {r["tag"]} E{r["epoch"]}: gap is validation minus train', num(r['gap']), num(r['validation']) - num(r['train']), 1e-12)
    eq('status', A['status'], 'COMPLETE'); eq('closed_by_failure', A['closed_by_failure'], False); eq('terminals: both runs COMPLETE', [A['terminals']['M1']['status'], A['terminals']['M2']['status']], ['COMPLETE', 'COMPLETE']); eq('draws_available', A['draws_available'], list(DRAWS)); eq('arms', A['arms'], {'768': [3e-4, 1e-4], '512': [3e-4, 1e-4]}); eq('readouts', A['readouts'], list(READOUTS)); eq('match_path', A['match_path'], list(MATCH_PATH)); eq('power_stated_in_advance', A['power_stated_in_advance'], POWER)
    # FITS.csv
    upper = lower = undefined = 0
    for r in fits:
        key = (r['draw'], int(r['width']), r['tag'], float(r['epoch'])); name = f'FITS {key}'; p = num(r['p']); eq(name + '.p against POINTS.csv', p, P[key]['p'], 0.0) if key in P else bad.append(dict(item=name, in_the_output='row', recomputed=None))
        if p is None: undefined += 1; eq(name + '.reason is given', bool(r['reason']), True)
        else: upper += p >= P_UPPER; lower += p <= P_LOWER; eq(name + '.upper', r['upper'], str(p >= P_UPPER)); eq(name + '.lower', r['lower'], str(p <= P_LOWER))
    eq('fit_bounds', A['fit_bounds'], dict(upper=upper, lower=lower, undefined=undefined))
    # the statistics
    own = own_statistics(P, A); S = A['statistics']; M = {(r['statistic'], r['draw']): r for r in matched}
    eq('statistics', sorted(S), sorted(SEQUENCE))
    for name in SEQUENCE:
        c = S[name]; o = own[name]; tag = f'statistic {name}'; eq(tag + '.kind', c['kind'], STATS[name]['kind']); eq(tag + '.key', c['key'], STATS[name]['key']); eq(tag + '.first', c['first'], [512, STATS[name]['tag']]); eq(tag + '.second', c['second'], [768, STATS[name]['tag']]); eq(tag + '.expected', c['expected'], STATS[name]['expected']); eq(tag + '.available', c['available'], o['available']); eq(tag + '.unavailable', c['unavailable'], o['unavailable']); eq(tag + '.unavailable_counts', c['unavailable_counts'], o['unavailable_counts']); eq(tag + '.sign_test.positive', c['sign_test']['positive'], o['sign_test']['positive']); eq(tag + '.sign_test.negative', c['sign_test']['negative'], o['sign_test']['negative']); eq_p(tag + '.sign_test.p', c['sign_test']['p'], o['sign_test']['p']); eq(tag + '.status', c['status'], o['status']); eq(tag + '.values keys', sorted(c['values']), sorted(o['values']))
        for d in DRAWS:
            x, y = c['rows'][d], o['rows'][d]; t2 = f'{tag} {d}'; eq(t2 + ' fields', sorted(x), sorted(y))
            for k in sorted(set(x) & set(y)):
                if isinstance(y[k], list): eq(f'{t2}.{k}', [v if v is None else round(v, 12) for v in x[k]], [v if v is None else round(v, 12) for v in y[k]])
                else: eq(f'{t2}.{k}', x[k], y[k])
            row = M[name, d]; eq(t2 + ' MATCHED.csv status', row['status'], y['status'])
            for k, v in (('target', y.get('target')), ('between_low', (y.get('between') or [None, None])[0]), ('between_high', (y.get('between') or [None, None])[1]), ('weight', y.get('weight')), ('read_at_readout', y.get('read_at_readout')), ('intervals_holding_the_target', y.get('intervals_holding_the_target')), ('p_first', y.get('p_first')), ('p_read', y.get('p_read')), ('value', y.get('value'))): eq(f'{t2} MATCHED.csv {k}', num(row[k]), None if v is None else float(v))
            if d in o['values']: eq(f'{tag}.values.{d}', c['values'][d], o['values'][d])
        eq(tag + '.leave_one_out keys', sorted(c.get('leave_one_out', {})), sorted(o.get('leave_one_out', {})))
        for d, y in o.get('leave_one_out', {}).items():
            x = c['leave_one_out'][d]; eq(f'{tag} leaving out {d}: mean', x['mean'], y['mean']); eq(f'{tag} leaving out {d}: low', x['interval'][0], y['interval'][0], 1e-7); eq(f'{tag} leaving out {d}: high', x['interval'][1], y['interval'][1], 1e-7); eq(f'{tag} leaving out {d}: df', x['df'], y['df']); eq(f'{tag} leaving out {d}: side', x['side'], y['side']); eq(f'{tag} leaving out {d}: excludes_zero', x['excludes_zero'], y['excludes_zero'])
        eq(tag + '.has an interval', 'interval' in c, 'interval' in o)
        if 'interval' in o and 'interval' in c:
            interval(tag, c['interval'], o['interval']); eq_p(tag + '.p', c['interval']['p'], o['interval']['p']); eq(tag + '.degenerate', c['interval']['degenerate'], o['interval']['degenerate']); eq(tag + '.side', c['side'], o['side']); eq(tag + '.flagged', c['flagged'], o['flagged']); eq(tag + '.S32.required', c['S32']['required'], bool(o['flagged']))
    # the sequence, the decision, the readings
    seq = own_sequence(own); eq('sequence', A['sequence'], seq)
    for name in SEQUENCE: eq(f'statistic {name}.label', S[name]['label'], next(r['label'] for r in seq if r['step'] == name))
    confirmed = [r['step'] for r in seq if r['confirmed']]; dec = A['decision']; eq('decision.P1', dec['P1'], seq[0]['label']); eq('decision.labels', dec['labels'], {r['step']: r['label'] for r in seq}); eq('decision.sides', dec['sides'], {k: own[k]['status'] for k in SEQUENCE}); eq('decision.unavailable_counts', dec['unavailable_counts'], {k: own[k]['unavailable_counts'] for k in SEQUENCE}); eq('decision.confirmed_through', dec['confirmed_through'], confirmed[-1] if confirmed else None)
    # NOT_OVERFIT
    no = own_not_overfit(P); x = A['not_overfit']; eq('not_overfit.status', x['status'], 'COMPUTED'); eq('not_overfit.draws', x['draws'], list(DRAWS)); eq('not_overfit.all_arms', x['all_arms'], no['all_arms']); eq('not_overfit.gates', x['gates'], no['gates']); eq('not_overfit.failing', x['failing'], no['failing'])
    for k, v in no['arms'].items(): interval(f'not_overfit {k}', x['arms'][k]['interval'], v['interval']); eq(f'not_overfit {k}.label', x['arms'][k]['label'], v['label'])
    # the rate effects, by readout, the panel and the losses
    for w in WIDTHS:
        for k in ('p', 'validation', 'train', 'gap'):
            hi, lo = [P[d, w, HIGH, float(FINAL)][k] for d in DRAWS], [P[d, w, LOW, float(FINAL)][k] for d in DRAWS]; v = None if any(a is None for a in hi + lo) else {d: b - a for d, a, b in zip(DRAWS, hi, lo)}; c = A['rate_effects'][str(w)][k]; name = f'rate_effects {w}.{k}'
            if v is None or c is None: eq(name, c, v); continue
            for d in DRAWS: eq(f'{name}.{d}', c['values'][d], v[d])
            interval(name, c['interval'], stat(list(v.values())))
    for e in READOUTS:
        row = A['by_readout'][f'E{e}']; fe = float(e)
        for name, tag in (('D4', LOW), ('D2', HIGH)):
            a, b = [P[d, 512, tag, fe]['p'] for d in DRAWS], [P[d, 768, tag, fe]['p'] for d in DRAWS]; v = None if any(x_ is None for x_ in a + b) else {d: p - q for d, p, q in zip(DRAWS, a, b)}; c = row['contrasts'][name]; nm = f'by_readout E{e}.{name}'
            if v is None or c is None: eq(nm, c, v); continue
            for d in DRAWS: eq(f'{nm}.{d}', c['values'][d], v[d])
            interval(nm, c['interval'], stat(list(v.values())))
        for w, t in ARMS:
            for k in ('p', 'gap', 'validation', 'train'):
                vals = [P[d, w, t, fe][k] for d in DRAWS]; eq(f'by_readout E{e}.panel {w}|{t}.{k}', row['panel'][f'{w}|{t}'][k], None if any(x_ is None for x_ in vals) else math.fsum(vals) / len(vals))
            for k in ('train', 'validation'): eq(f'losses {w}|{t}.E{e}.{k}', A['losses'][f'{w}|{t}'][f'E{e}'][k], math.fsum(P[d, w, t, fe][k] for d in DRAWS) / len(DRAWS))
    # records against arrays: its limit and verdict, and the readings word for word
    ra = A['records_against_arrays']; eq('records_against_arrays.limit', ra['limit'], RECORD_LIMIT); eq('records_against_arrays.within_limit', ra['within_limit'], ra['max_absolute_difference'] <= RECORD_LIMIT)
    want = own_readings(own, seq, no, ra['within_limit']); rd = A['readings']; eq('readings: the number', len(rd), len(want))
    for i in range(max(len(rd), len(want))): eq(f'reading {i + 1}', rd[i] if i < len(rd) else None, want[i] if i < len(want) else None)
    return bad, count[0], dict(own=own, seq=seq, no=no, P=P)


# ------------------------------------------------------------------ part 2: the report against the outputs
MINUS = '\u2212'
def s_(x, d=5): return 'undefined' if x is None else f'{x:+.{d}f}'.replace('-', MINUS)
def u_(x, d=4): return 'undefined' if x is None else f'{x:.{d}f}'.replace('-', MINUS)
def iv_(lo, hi, d=5): return f'[{s_(lo, d)}, {s_(hi, d)}]'
def ivt(t, d=5): return iv_(t['interval'][0], t['interval'][1], d)
def p_(x): return 'undefined' if x is None else ('0' if x == 0 else f'{x:.2e}'.replace('-', MINUS) if x < 0.001 else f'{x:.4f}')
def yn(x): return 'yes' if x else 'no'
def names(x): return ', '.join(x) or 'none'
def rate(t): return '3e-4' if t == HIGH else '1e-4'
def arm_(w, t): return f'{w} at {rate(t)}'
def E(e): return f'E{e}'


NUMBER_HEAD = ('Step', 'Draws with a reading', 'Status', 'Mean', '95% interval', 'df', 'p, unadjusted', 'Draws < 0 / > 0', 'Exact sign test, p', 'Draws flagged at p\\* \u2265 7.999')
MATCH_HEAD = ('Draw', 'Status', 'Target: 512 at E3', "768's path, E2 to E3.5: lowest, highest", 'Bracket', 'Weight', 'Read at', 'Intervals holding the target', 'p\\* of 512 at E3', 'p\\* of 768 as read', 'Contrast')
ITEM_NAME = dict(n_train='N', weights='Weights, recorded hash', weights_list='Weights, the list the fits use', orders='Orders', pool_orders='Pool orders', tied_values='Tied values', seeds='Seeds', articles='Articles', sequence_indices='Sequence indices', validation='Validation', pool='Pool')
DEFINE = dict(P1='p\\*(512, E3) \u2212 p\\*(768, read at the training NLL 512 reaches at E3), at 1e-4', S1='p\\*(512, E3) \u2212 p\\*(768, read at the gap 512 reaches at E3), at 1e-4', S3='p\\*(512, E3) \u2212 p\\*(768, E3), at 1e-4: the fixed-update contrast', S4='p\\*(512, E3) \u2212 p\\*(768, read at the training NLL 512 reaches at E3), at 3e-4', S5='p\\*(512, E3) \u2212 p\\*(768, E3), at 3e-4: the fixed-update contrast', S2='p\\*(512, E3) \u2212 p\\*(768, read at the validation NLL 512 reaches at E3), at 1e-4')


def number_table(title, S, steps):
    rows = []
    for k in steps:
        c = S[k]; t = c.get('interval'); sg = c['sign_test']
        rows.append((f'**{k}**', f'{len(c["available"])} of 6', c['status'], s_(t['mean']) if t else 'none', ivt(t) if t else 'none', str(t['df']) if t else 'none', p_(t['p']) if t else 'none', f'{sg["negative"]}/{sg["positive"]}', 'undefined' if sg['p'] is None else f'{sg["p"]:.5f}', names(c.get('flagged', [])) if t else 'none'))
    return (title, NUMBER_HEAD, rows)


def match_table(title, S, name):
    rows = []; pick = lambda r, k, f: f(r[k]) if k in r else 'none'
    for d in DRAWS:
        r = S[name]['rows'][d]
        rows.append((d, r['status'], pick(r, 'target', u_), f'[{u_(r["path_min"])}, {u_(r["path_max"])}]' if 'path_min' in r else 'none', f'E{r["between"][0]} to E{r["between"][1]}' if 'between' in r else 'none', pick(r, 'weight', u_), pick(r, 'read_at_readout', lambda x: f'E{x:.3f}'), pick(r, 'intervals_holding_the_target', str), pick(r, 'p_first', lambda x: u_(x, 5)), pick(r, 'p_read', lambda x: u_(x, 5)), pick(r, 'value', s_)))
    return (title, MATCH_HEAD, rows)


def expected_tables(A, P, fits, ctx):
    """Every table of the report, in order: (title, header, rows), each cell a string this file formats itself. The report's tables are compared with these, cell by cell."""
    S = A['statistics']; no = A['not_overfit']; by = A['by_readout']; L = A['losses']; dec = A['decision']; T = []; E3 = E(FINAL); add = T.append
    add(('records', ('Record', 'SHA-256'), [(f'`{k}`', f'`{v}`') for k, v in ctx['records'].items()]))
    # 1
    rows = []
    for w, t in ARMS:
        v = no['arms'][f'{w}|{t}']; i = v['interval']; cands = [(L[f'{w}|E0']['validation'], 'E0')] + [(L[f'{w}|{t}'][E(e)]['validation'], E(e)) for e in READOUTS]; lo = min(cands)
        rows.append((arm_(w, t), 'P1, S1, S3, S2' if t == LOW else 'S4, S5', f'**{v["label"]}**', s_(i['mean'], 4), ivt(i, 4), str(i['df']), f'{i["negative"]}/{i["n"]}', s_(by[E3]['panel'][f'{w}|{t}']['gap'], 4), f'{u_(lo[0])} ({lo[1]})'))
    add(('NOT_OVERFIT per arm', ('Arm', 'Steps at this rate', 'Verdict', 'Mean \u0394', '95% interval', 'df', 'Draws \u0394 < 0', 'Mean gap at E3', 'Lowest mean validation NLL (readout)'), rows))
    add(('NOT_OVERFIT per rate', ('Rate', 'Arms', 'All NOT_OVERFIT', 'Arms that fail'), [(k, ', '.join(arm_(*a) for a in GATE_ARMS[k]), yn(no['gates'][k]), names(no['failing'][k])) for k in ('rate_low', 'rate_high')]))
    add(('NOT_OVERFIT per draw', ('Arm',) + DRAWS, [[arm_(w, t)] + [s_(P[d, w, t, float(FINAL)]['validation'] - P[d, w, t, float(PREVIOUS)]['validation'], 4) for d in DRAWS] for w, t in ARMS]))
    # 2
    add(number_table('P1 numbers', S, ('P1',))); add(match_table('P1 per draw', S, 'P1')); pw = A['power_stated_in_advance']
    add(('power', ('Draws available', 'Spread used, sd', 'At the effect seen', 'At half of it', 'At half of it, with the sd at its upper 95% limit'), [('6', pw['sd'], pw['six_seen'], pw['six_half'], pw['six_half_sd_upper']), ('5', pw['sd'], pw['five_seen'], pw['five_half'], pw['five_half_sd_upper'])]))
    # 3
    seq = {r['step']: r for r in A['sequence']}; rows = []
    for k in SEQUENCE:
        label = seq[k]['label']; failing = no['failing'][GATE_OF[STATS[k]['tag']]]; gate = 'not read' if label in UNREADABLE or label == NOT_READ else f'**no: {names(failing)}**' if failing else 'yes'
        rows.append((f'**{k}**', DEFINE[k], 'above 0' if STATS[k]['expected'] == 'ABOVE' else 'below 0', f'**{label}**', str(seq[k]['status']), yn(seq[k]['read_as_confirmation']), yn(seq[k]['confirmed']), gate))
    add(('sequence', ('Step', 'Per draw', 'Confirmed if the interval lies', 'Label', 'Status of its interval', 'Read as a confirmation', 'Confirmed', 'Arms at this rate all NOT_OVERFIT'), rows))
    add(('confirmed through', ('Confirmed through',), [(dec['confirmed_through'] or 'none',)]))
    add(number_table('sequence numbers', S, SEQUENCE))
    add(('contrast per draw', ('Draw',) + SEQUENCE, [[d] + [(s_(S[k]['rows'][d]['value']) if 'value' in S[k]['rows'][d] else S[k]['rows'][d]['status']) for k in SEQUENCE] for d in DRAWS]))
    add(('p* at E3', ('Draw',) + tuple(arm_(w, t) for w, t in ARMS), [[d] + [u_(P[d, w, t, float(FINAL)]['p'], 5) for w, t in ARMS] for d in DRAWS] + [['**Mean**'] + [u_(by[E3]['panel'][f'{w}|{t}']['p'], 5) for w, t in ARMS]]))
    for k in ('S1', 'S4', 'S2'): add(match_table(f'{k} per draw', S, k))
    # 5
    add(('no reading', ('Step', 'Undefined fit', 'Target outside the path', 'Draw missing', 'Draws'), [(k, str(dec['unavailable_counts'][k]['UNDEFINED_FIT']), str(dec['unavailable_counts'][k]['TARGET_OUTSIDE_PATH']), str(dec['unavailable_counts'][k]['DRAW_MISSING']), names(S[k]['unavailable'])) for k in SEQUENCE]))
    rows = []
    for k in SEQUENCE:
        loo = S[k].get('leave_one_out')
        if not loo: rows.append((k, 'none', 'none', 'none', 'none', 'none')); continue
        rows += [(k, d, s_(x['mean']), iv_(x['interval'][0], x['interval'][1]), str(x['df']), x['side']) for d, x in loo.items()]
    add(('leave one out', ('Step', 'Draw left out', 'Mean', '95% interval', 'df', 'Side'), rows))
    rows = []
    for k in SEQUENCE:
        c = S[k]; x = c.get('S32'); t32 = (x or {}).get('interval')
        rows.append((k, names(c['flagged']) if 'flagged' in c else 'none', 'none' if x is None else yn(x['required']), yn(x['computable']) if x and 'computable' in x else 'none', str(x['unresolved_refits']) if x and 'unresolved_refits' in x else 'none', c.get('side', 'none'), (x or {}).get('side', 'none'), s_(t32['mean']) if t32 else 'none', ivt(t32) if t32 else 'none'))
    add(('saturation', ('Step', 'Flagged draws', 'Refit needed', 'Computable', 'Unresolved refits', 'Side at bound 8', 'Side at bound 32', 'Mean at bound 32', 'Interval at bound 32'), rows))
    ra = A['records_against_arrays']; add(('records against arrays', ('Measure', 'Value'), [("Largest difference between a record's loss and the mean of the array block the fits use", f'{ra["max_absolute_difference"]:.2e}'.replace('-', MINUS)), ('Limit', '0.001'), ('Within the limit', yn(ra['within_limit']))]))
    # 6
    pair = lambda c: ['undefined', 'undefined'] if c is None else [s_(c['interval']['mean']), ivt(c['interval'])]
    add(('by readout', ('Readout', '1e-4, mean', '1e-4, 95% interval', '3e-4, mean', '3e-4, 95% interval'), [[E(e)] + pair(by[E(e)]['contrasts']['D4']) + pair(by[E(e)]['contrasts']['D2']) for e in READOUTS]))
    heads = tuple(E(e) for e in READOUTS)
    add(('panel p*', ('Arm',) + heads, [[arm_(w, t)] + [u_(by[E(e)]['panel'][f'{w}|{t}']['p'], 5) for e in READOUTS] for w, t in ARMS]))
    add(('panel gap', ('Arm', 'E0') + heads, [[arm_(w, t), s_(L[f'{w}|E0']['validation'] - L[f'{w}|E0']['train'], 4)] + [s_(by[E(e)]['panel'][f'{w}|{t}']['gap'], 4) for e in READOUTS] for w, t in ARMS]))
    for key in ('train', 'validation'): add((f'panel {key}', ('Arm', 'E0') + heads, [[arm_(w, t), u_(L[f'{w}|E0'][key])] + [u_(by[E(e)]['panel'][f'{w}|{t}'][key]) for e in READOUTS] for w, t in ARMS]))
    RE = A['rate_effects']; Q = dict(p='p\\*', validation='Validation NLL', train='Training NLL', gap='Gap'); dg = lambda k: 5 if k == 'p' else 4; rows = []
    for w in WIDTHS:
        for k in ('p', 'validation', 'train', 'gap'):
            x = RE[str(w)][k]; rows.append((str(w), Q[k], 'undefined', 'undefined', 'undefined') if x is None else (str(w), Q[k], s_(x['interval']['mean'], dg(k)), ivt(x['interval'], dg(k)), f'{x["interval"]["negative"]}/{x["interval"]["positive"]}'))
    add(('rate effects', ('Width', 'Quantity', 'Mean', '95% interval', 'Draws < 0 / > 0'), rows))
    add(('rate effects per draw', ('Width', 'Quantity') + DRAWS, [[str(w), Q[k]] + [s_(RE[str(w)][k]['values'][d], dg(k)) if RE[str(w)][k] else 'undefined' for d in DRAWS] for w in WIDTHS for k in ('p', 'validation', 'train', 'gap')]))
    add(('clipping', ('Arm', 'Mean clip fraction', 'Mean gradient norm', 'Largest gradient norm'), [(arm_(w, t), u_(L[f'{w}|{t}']['clipping']['clip_fraction_mean'], 3), u_(L[f'{w}|{t}']['clipping']['gradient_norm_mean'], 3), u_(L[f'{w}|{t}']['clipping']['gradient_norm_max'], 3)) for w, t in ARMS]))
    defined = [x for x in fits if x['p'] != '']; ps = [float(x['p']) for x in defined]; why = {}
    for x in fits:
        if x['p'] == '': why[x['reason']] = why.get(x['reason'], 0) + 1
    neg = [float(x['negative_fraction']) for x in fits]; worst = next(x for x in fits if float(x['negative_fraction']) == max(neg)); ratio = [float(x['objective']) / float(x['J0']) for x in defined if float(x['J0']) > 0]; fb = A['fit_bounds']
    add(('fit quality', ('Measure', 'Value'), [('Fits', str(len(fits))), ('Defined fits', str(len(ps))), ('Smallest p\\*', u_(min(ps), 3) if ps else 'none'), ('Largest p\\*', u_(max(ps), 3) if ps else 'none'), ('At the upper bound', str(fb['upper'])), ('At the lower bound', str(fb['lower'])), ('Undefined fits', str(fb['undefined'])), ('Reasons a fit is undefined', names([f'{k}: {v}' for k, v in why.items()])), ('Smallest total gain, signed', u_(min(float(x['total_gain']) for x in fits), 1)), ('Fits with any sequence of negative gain', str(sum(v > 0 for v in neg))), ('Fits with 5% or more of sequences at negative gain', str(sum(v >= 0.05 for v in neg))), ('Largest share of sequences at negative gain', f'{100 * max(neg):.1f}%'), ('Where that is', f'{worst["draw"]}, {arm_(int(worst["width"]), worst["tag"])}, E{worst["epoch"]}'), ('Lowest objective at p\\* over the objective at p = 0', u_(min(ratio), 3) if ratio else 'none'), ('Highest objective at p\\* over the objective at p = 0', u_(max(ratio), 3) if ratio else 'none')]))
    # 7
    fg = ctx['figures']; pool = fg['pool']; pg = fg['per_group']; dis = fg['disclosure']; it = dis['identical_text']; tl = dis['titles']
    add(('fresh rule', ('Figure', 'Value'), [('Eligible articles', f'{pool["eligible_articles"]:,}'), ('Assigned in N5 and N6, and out', f'{pool["assigned_articles"]:,}'), ('Text duplicates of assigned articles, and out', str(pool['removed_text_duplicates_of_assigned'])), ('Copies of texts repeated inside the pool, and out', str(pool['removed_repeats_inside_the_pool'])), ('Sets of those repeats', str(pool['sets_of_repeats_inside_the_pool'])), ('Fresh articles', f'{pool["fresh_articles"]:,}'), ('Fresh sequences', f'{pool["fresh_sequences"]:,}'), ('Articles the six groups use', f'{sum(pg[d]["articles"] for d in DRAWS):,}'), ('Articles left over', f'{fg["left_over_articles"]:,}'), ('Identical text: sets across the fresh groups', str(it['sets_across_fresh_groups'])), ("Identical text: fresh texts equal to an assigned article's", str(it['fresh_texts_equal_to_an_assigned_article'])), ('Identical text: repeated inside a group', str(it['repeated_inside_a_group'])), ('Titles shared across the fresh groups', str(tl['sets_across_fresh_groups'])), ('Fresh articles sharing a title with an assigned article, with a different text', str(tl['fresh_articles_sharing_a_title_with_an_assigned_article']))]))
    add(('groups', ('Group', 'Articles', 'Sequences used'), [(d, str(pg[d]['articles']), f'{pg[d]["sequences"]:,}') for d in DRAWS]))
    ri = ctx['inputs']; eng = ctx['engine']['draws']; ties = dis['tied_weights']['by_group']
    add(('tied weights', ('Draw', 'In the run', 'Real-engine check, real Torch', "Stdlib draw, before and after division by numpy's mean", 'Limit'), [(d, str(ri['draws'][d]['tied_values_in_the_run']), str(eng[d]['tied_values']), f'{ties[d]["before_division"]} and {ties[d]["after_division_numpy_mean"]}', str(int(eng[d]['limit']))) for d in DRAWS]))
    add(('inputs', ('Draw',) + tuple(ITEM_NAME[k] for k in INPUT_ITEMS), [[d] + [('equal' if ri['draws'][d]['items'][k] == 'equal' else '**differs**') for k in INPUT_ITEMS] for d in DRAWS]))
    add(('input comparisons', ('Measure', 'Value'), [('Comparisons', str(ri['comparisons'])), ('Differences', str(len(ri['differences']))), ('The six training hashes are distinct', yn(ri['training_hashes_distinct']))]))
    mc = ctx['merge']['pull_request']; pk = ctx['merge']['package']; commit = mc['merge_commit_sha']
    add(('registration', ('Item', 'Value'), [('Pull request', mc['url']), ('Merged at', mc['merged_at']), ('Merge commit', f'`{commit}`'), ('Source subject at that commit', f'`{ctx["merge"]["subject_at_the_commit"]}`'), ('Package files, local and public', f'{pk["local_files"]} and {pk["public_files"]}'), ('Package files that differ', str(len(pk['files_that_differ']))), ("Run M1's approval record names that commit", yn(ctx['approvals']['M1']['public_registration']['merge_commit'] == commit)), ("Run M2's approval record names that commit", yn(ctx['approvals']['M2']['public_registration']['merge_commit'] == commit))]))
    rc = ctx['receipt']
    add(('where it ran', ('Item', 'Value'), [('Python', f'`{rc["python_path"]}`'), ('Python version', rc['python_version']), ('Operating system', rc['operating_system']), ('Started, UTC', rc['started_utc']), ('Ended, UTC', rc['ended_utc']), ("Seconds, by the command's clock", f'{rc["seconds"]:,.1f}'), ('Exit code', str(rc['exit_code']))]))
    # 8
    v1, v2 = ctx['verify']['M1'], ctx['verify']['M2']; a1, a2 = v1['measured'], v2['measured']; gt = lambda v: ', '.join(f'{g[0]} {g[1]} at check {g[2]}' for g in v['checks']['every completed draw passed its gate, and the gate files equal the receipt']['detail']['gates']); off = lambda v: str(v['checks']['on AC throughout']['detail']['off_ac_samples']); secs = lambda a: ', '.join(f'{d} {x:,.1f} s' for d, x in a['stage_seconds'].items())
    add(('operations', ('Measure', 'Run M1', 'Run M2'), [('Ended', v1['ended'], v2['ended']), ('Per-run check', f'{v1["passed"]} of {v1["total"]}', f'{v2["passed"]} of {v2["total"]}'), ("Draws, by the worker's clock", secs(a1), secs(a2)), ('Worker elapsed', f'{a1["worker_elapsed_seconds"]:,.0f} s', f'{a2["worker_elapsed_seconds"]:,.0f} s'), ('Owner elapsed, Windows clock', f'{a1["owner_elapsed_seconds"]:,.0f} s', f'{a2["owner_elapsed_seconds"]:,.0f} s'), ("Windows over the worker's clock", f'{a1["windows_over_worker_clock"]:.3f}', f'{a2["windows_over_worker_clock"]:.3f}'), ('Worker peak memory', f'{a1["peaks"]["worker_peak_rss"] / 1e9:.2f} GB', f'{a2["peaks"]["worker_peak_rss"] / 1e9:.2f} GB'), ('GPU peak, sampled', f'{a1["peaks"]["device_used_sampled"]:,} bytes', f'{a2["peaks"]["device_used_sampled"]:,} bytes'), ('Kept output', f'{a1["inventory"]["bytes"]:,} bytes, {a1["inventory"]["files"]} files', f'{a2["inventory"]["bytes"]:,} bytes, {a2["inventory"]["files"]} files'), ('Gate before each draw', gt(v1), gt(v2)), ('Power readings off AC', off(v1), off(v2)), ('Battery, first to last', f'{a1["battery_percent"]["first"]}% to {a1["battery_percent"]["last"]}%', f'{a2["battery_percent"]["first"]}% to {a2["battery_percent"]["last"]}%')]))
    return T


def report_tables(text):
    """Every table in the text, in order, with the line each starts on: runs of lines that begin with '|'."""
    out = []; cur = None
    for i, line in enumerate(text.split('\n'), 1):
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cur is None: cur = dict(line=i, head=cells, sep=None, rows=[])
            elif cur['sep'] is None: cur['sep'] = cells
            else: cur['rows'].append(cells)
        elif cur is not None: out.append(cur); cur = None
    if cur is not None: out.append(cur)
    return out


NUMBER = re.compile(r'(?<![\w.\-/\\+\u2212])[+\u2212-]?\d+(?:,\d{3})*(?:\.\d+)?(?:e[+\u2212-]?\d+)?%?(?![\w/\\\-]|\.\d)')
def report_against_outputs(text, A, P, fits, ctx, limitations):
    """Returns (mismatches, counts): every table against this file's own cells, the readings as quoted, the quotation of section 11, and every number in the wording."""
    bad = []; cells = [0]; tokens = [0]; want = expected_tables(A, P, fits, ctx); got = report_tables(text)
    if len(want) != len(got): bad.append(dict(item='the number of tables', report=len(got), expected=len(want)))
    for (title, head, rows), t in zip(want, got):
        if t['head'] != [str(x) for x in head]: bad.append(dict(item=f'table "{title}", line {t["line"]}: the header', report=t['head'], expected=list(head)))
        if len(t['rows']) != len(rows): bad.append(dict(item=f'table "{title}", line {t["line"]}: the number of rows', report=len(t['rows']), expected=len(rows))); continue
        for r, (a, b) in enumerate(zip(t['rows'], rows)):
            if len(a) != len(b): bad.append(dict(item=f'table "{title}", row {r + 1}: the number of cells', report=len(a), expected=len(b))); continue
            for c, (x, y) in enumerate(zip(a, b)):
                cells[0] += 1
                if x != str(y): bad.append(dict(item=f'table "{title}", row {r + 1}, column "{head[c]}"', report=x, expected=str(y)))
    if not text.startswith('# Matched-progress confirmation: result'): bad.append(dict(item='the title', report=text[:60], expected='# Matched-progress confirmation: result'))
    sections = re.split(r'(?m)^## ', text); by = {s.split('\n', 1)[0]: s for s in sections}; four = by.get('4. The sealed readings', ''); quoted = re.findall(r'(?m)^(\d+)\. "(.*)"$', four)
    if [q[1] for q in quoted] != A['readings'] or [int(q[0]) for q in quoted] != list(range(1, len(A['readings']) + 1)): bad.append(dict(item='the readings as quoted', report=[q[1][:60] for q in quoted], expected=[r[:60] for r in A['readings']]))
    nine = by.get('9. Limitations', '')
    if limitations not in nine: bad.append(dict(item='the quotation of PROTOCOL.md section 11', report=nine[:80], expected=limitations[:80]))
    m = re.search(r'(?m)^\*\*Label: ([A-Z_]+)\.\*\*', by.get(next((k for k in by if k.startswith('2. The primary, P1')), ''), ''))
    if m is None or m.group(1) != A['decision']['P1']: bad.append(dict(item='the label in section 2', report=m and m.group(1), expected=A['decision']['P1']))
    if f'the sealed analysis is {A["status"]}.' not in text: bad.append(dict(item='the status in the first paragraph', report=None, expected=A['status']))
    # every number in the wording: outside tables, quotations, code spans and links, each must be one of the plan's constants
    for name, sec in by.items():
        if name.startswith('4. The sealed readings'): continue
        body = sec.replace(limitations, '') if name.startswith('9. Limitations') else sec
        for i, line in enumerate(body.split('\n')):
            if line.startswith('|'): continue
            plain = re.sub(r'`[^`]*`', ' ', line); plain = re.sub(r'^\*\*Written:\*\* \d{1,2} [A-Z][a-z]{2} \d{4}\.', ' ', plain)
            for tok in NUMBER.findall(plain):
                tokens[0] += 1
                if tok not in PROSE_ALLOWED: bad.append(dict(item=f'a number in the wording of section "{name[:40]}"', report=tok, expected='one of the constants', line=line[:120]))
    return bad, dict(tables=len(got), cells=cells[0], numbers_in_the_wording=tokens[0], readings=len(quoted))


# ------------------------------------------------------------------ gates and records
def real_gate(analysis_dir, decision):
    """The owner's approval quoted on one line with the layout's hash and this file's; the only analysis folder of the study; the sealed source, file by file; the frozen input check."""
    d = Path(decision).resolve(); a = Path(analysis_dir).resolve(); problems = []
    approving = re.search(rf'^> I approve {re.escape(APPROVAL_ID)}\b.*$', d.read_bytes().decode('utf-8'), re.M) if d.is_file() and d.parent.parent == REPORTS.resolve() and d.parent.name.startswith('natural-text-ladder-owner-decisions-') else None
    if approving is None: problems.append(f'The owner decision file does not record approval {APPROVAL_ID}')
    elif sha(__file__) not in approving.group(0) or sha(LAYOUT) not in approving.group(0): problems.append('The owner decision file does not name the layout and this verifier by their hashes')
    if a.parent != REPORTS.resolve() or not re.fullmatch(ANALYSIS_NAME, a.name) or [p.resolve() for p in REPORTS.iterdir() if p.is_dir() and re.fullmatch(ANALYSIS_NAME, p.name)] != [a]: problems.append('The analysis folder is not the only study output under reports/')
    manifest = load(SRC / 'SOURCE_SUBJECT.json')
    if sha(SRC / 'SOURCE_SUBJECT.json') != SUBJECT or sha(SRC / 'matched_analysis.py') != ANALYSIS_SHA256 or sha(SRC / 'PROTOCOL.md') != PROTOCOL_SHA256 or any(sha(SRC / f['path']) != f['sha256'] for f in manifest['files']): problems.append('The sealed source changed')
    if sha(INPUT_CHECK) != INPUT_CHECK_SHA256: problems.append('The input check script changed')
    return problems


def saved_records():
    problems = [f'A saved record changed: {Path(p).name}' for p, want in PINS.items() if sha(p) != want]
    rec = dict(figures=load(FIGURES), engine=load(ENGINE), merge=load(MERGE_CHECK), verify={m: load(VERIFY[m]) for m in VERIFY}, approvals={m: load(APPROVALS[m]) for m in APPROVALS}); e = rec['engine']
    if not (rec['figures']['all_pass'] and rec['merge']['all_agree'] and rec['merge']['pull_request']['merge_commit_sha'] == MERGE_COMMIT and rec['merge']['subject_at_the_commit'] == SUBJECT and all(v['all_pass'] and v['ended'] == 'COMPLETE' for v in rec['verify'].values()) and rec['verify']['M1']['terminal_sha256'] == M1_TERMINAL and rec['verify']['M2']['terminal_sha256'] == M2_TERMINAL and e['status'] == 'PASS' and e['fixture'] is False and e['loss_read'] is False and all(e['draws'][d]['status'] == 'PASS' for d in DRAWS)): problems.append('A saved record does not pass')
    return rec, problems


def load_layout():
    spec = importlib.util.spec_from_file_location('make_results_report', LAYOUT); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def verify(analysis_dir, result_dir, decision, checks_dir=CHECKS, fixture=False, write=True):
    analysis_dir, result_dir, decision, checks_dir = Path(analysis_dir), Path(result_dir), Path(decision), Path(checks_dir); t0 = time.time(); problems = [] if fixture else real_gate(analysis_dir, decision); not_recomputed = 'p* itself and the other fields of FITS.csv; the training and validation NLL in POINTS.csv, from each record.json, on which every target, bracket and matched contrast rests; the E0 losses; clipping; any refit at bound 32, which can move a label; and the record-against-array difference: they need the run files under work/runs/, which only the sealed analysis read'
    if problems:
        rec = dict(schema=1, purpose="The verifier of the results report: the report's numbers against the analysis output", fixture=fixture, status='FAIL', refused_before_opening_the_outputs=True, problems=problems, outputs_against_themselves=dict(comparisons=0, mismatches=[]), report_against_outputs=dict(mismatches=[]), report_equals_the_frozen_layouts_output=False, layout_error=None, not_recomputed=not_recomputed, seconds=round(time.time() - t0, 1))
        if write and result_dir.is_dir():
            path = result_dir / 'RESULT_VERIFICATION.json'
            if path.exists(): path = result_dir / f"RESULT_VERIFICATION-{time.strftime('%Y%m%d-%H%M%S')}.json"
            path.write_bytes((json.dumps(rec, indent=1, default=str) + '\n').encode('utf-8'))
        return rec
    saved, more = saved_records(); problems += more
    A = load(analysis_dir / 'ANALYSIS.json'); points, fits, matched = read_csv(analysis_dir / 'POINTS.csv'), read_csv(analysis_dir / 'FITS.csv'), read_csv(analysis_dir / 'MATCHED.csv'); text = (result_dir / 'RESULT.md').read_bytes().decode('utf-8'); receipt, inputs = load(checks_dir / 'ANALYSIS_EXIT_RECEIPT.json'), load(checks_dir / 'RUN_INPUTS_CHECK.json')
    if receipt.get('exit_code') != 0: problems.append('The analysis did not exit 0')
    outputs_now = {n: sha(analysis_dir / n) for n in OUTPUTS}
    if receipt.get('outputs') != outputs_now: problems.append('The outputs differ from the exit receipt of the analysis')
    if sorted(p.name for p in analysis_dir.iterdir()) != sorted(OUTPUTS): problems.append('The analysis folder holds other files than the four outputs')
    if inputs.get('analysis_json_sha256') != outputs_now['ANALYSIS.json']: problems.append('The input check is not of this analysis')
    if inputs.get('status') != 'PASS' or inputs.get('differences'): problems.append(f"The input check found differences: {inputs.get('differences')}")
    if inputs.get('comparisons') != 67 or sorted(inputs.get('draws', {})) != list(DRAWS) or any(inputs['draws'][d]['items'] != {k: 'equal' for k in INPUT_ITEMS} or inputs['draws'][d]['tied_values_in_the_run'] != saved['engine']['draws'][d]['tied_values'] or inputs['draws'][d]['hashes']['weights'] != saved['engine']['draws'][d]['weights_hash'] or inputs['draws'][d]['hashes']['weights_list'] != saved['engine']['draws'][d]['weights_hash'] or inputs['draws'][d]['hashes']['orders'] != saved['engine']['draws'][d]['orders_hash'] or inputs['draws'][d]['hashes']['pool_orders'] != saved['engine']['draws'][d]['pool_orders_hash'] for d in DRAWS if d in inputs.get('draws', {})): problems.append('The input check does not hold its comparisons')
    if not fixture:
        if receipt.get('approval_id') != APPROVAL_ID or receipt.get('analysis_sha256') != ANALYSIS_SHA256: problems.append('The exit receipt is not of this approval')
        if inputs.get('check_sha256') != INPUT_CHECK_SHA256: problems.append('The input check is not by the frozen script')
        if A.get('terminals') != dict(M1=dict(status='COMPLETE', sha256=M1_TERMINAL), M2=dict(status='COMPLETE', sha256=M2_TERMINAL)): problems.append('ANALYSIS.json does not bind the real terminals')
        if (analysis_dir / 'ANALYSIS.json').stat().st_mtime <= dt.datetime.fromisoformat(saved['merge']['pull_request']['merged_at'].replace('Z', '+00:00')).timestamp(): problems.append('ANALYSIS.json is older than the public registration')
    bad1, compared, own = outputs_against_themselves(A, points, fits, matched); bad2 = []; counts = {}; same = False; layout_error = None
    if own is not None:
        protocol = (SRC / 'PROTOCOL.md').read_bytes().decode('utf-8').replace('\r\n', '\n'); head = '## 11. Limitations stated in advance\n'; limitations = protocol[protocol.index(head) + len(head):protocol.index('## 12. Operations and failure policy')].strip('\n')
        records = {n: outputs_now[n] for n in OUTPUTS}; records.update({'Run M1 TERMINAL.json': A['terminals']['M1']['sha256'], 'Run M2 TERMINAL.json': A['terminals']['M2']['sha256'], 'RUN_M1_VERIFICATION.json': sha(VERIFY['M1']), 'RUN_M2_VERIFICATION.json': sha(VERIFY['M2']), 'ANALYSIS_EXIT_RECEIPT.json': sha(checks_dir / 'ANALYSIS_EXIT_RECEIPT.json'), 'RUN_INPUTS_CHECK.json': sha(checks_dir / 'RUN_INPUTS_CHECK.json'), 'SOURCE_SUBJECT.json': sha(SRC / 'SOURCE_SUBJECT.json'), 'matched_analysis.py': sha(SRC / 'matched_analysis.py'), 'this layout, make_results_report.py': sha(LAYOUT), 'the verifier, verify_results_report.py': sha(__file__), 'owner decision': sha(decision)})
        ctx = dict(saved, records=records, receipt=receipt, inputs=inputs); bad2, counts = report_against_outputs(text, A, own['P'], fits, ctx, limitations)
        m = re.search(r'\*\*Written:\*\* (\d{1,2} [A-Z][a-z]{2} \d{4})\.', text)
        try: rendered, _ = load_layout().assemble(analysis_dir, decision, checks_dir, fixture, m.group(1) if m else None); same = rendered == text
        except (SystemExit, Exception) as e: layout_error = repr(e)
    ok = not problems and not bad1 and not bad2 and same
    rec = dict(schema=1, purpose="The verifier of the results report: the report's numbers against the analysis output", fixture=fixture, status='PASS' if ok else 'FAIL', problems=problems, outputs_against_themselves=dict(comparisons=compared, mismatches=bad1), report_against_outputs=dict(counts, mismatches=bad2), report_equals_the_frozen_layouts_output=same, layout_error=layout_error, not_recomputed=not_recomputed, hashes=dict(result=sha(result_dir / 'RESULT.md'), verifier=sha(__file__), layout=sha(LAYOUT), outputs=outputs_now), t_critical={str(k): v for k, v in sorted(_CRIT.items())}, seconds=round(time.time() - t0, 1))
    if write:
        path = result_dir / 'RESULT_VERIFICATION.json'
        if path.exists(): path = result_dir / f"RESULT_VERIFICATION-{time.strftime('%Y%m%d-%H%M%S')}.json"
        path.write_bytes((json.dumps(rec, indent=1, default=str) + '\n').encode('utf-8'))
    return rec


if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit('usage: verify_results_report.py <ANALYSIS_DIR> <RESULT_DIR> <OWNER_DECISION_FILE>')
    install_guard(); rec = verify(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(dict(status=rec['status'], problems=rec['problems'], comparisons=rec['outputs_against_themselves']['comparisons'], report=dict(tables=rec['report_against_outputs'].get('tables'), cells=rec['report_against_outputs'].get('cells'), numbers_in_the_wording=rec['report_against_outputs'].get('numbers_in_the_wording')), report_equals_the_frozen_layouts_output=rec['report_equals_the_frozen_layouts_output'], mismatches=len(rec['outputs_against_themselves']['mismatches']) + len(rec['report_against_outputs']['mismatches']), seconds=rec['seconds']), indent=1))
    raise SystemExit(0 if rec['status'] == 'PASS' else 1)
