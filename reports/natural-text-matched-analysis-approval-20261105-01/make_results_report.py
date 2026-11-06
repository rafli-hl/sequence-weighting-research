"""The frozen layout of the matched-progress confirmation's results report, N7. Native Python 3.12 -I -B; stdlib and the sealed plan's constants only.

  python -I -B make_results_report.py <ANALYSIS_DIR> <NEW_OUT_DIR> <OWNER_DECISION_FILE>      -> RESULT.md in NEW_OUT_DIR

Written and tested on invented losses before any p*, gain or loss of this study was opened (PROTOCOL.md section 12, step 7). It runs only after the owner's sealed analysis, and after the owner's check_run_inputs.py. The order of the report: the NOT_OVERFIT verdicts per arm first; the primary; the fixed sequence; the sealed readings; what is always reported; the descriptive sections; the disclosures; operations; limitations; the check.

It opens nothing under work/runs: an audit hook in its own command line stops it if anything tries. It reads the four sealed outputs, the analysis's exit receipt, the owner-run input check, and saved records under reports/ and the activations. Every number from a record is in a table cell or in a quoted reading, and the wording around them holds only the constants of the plan. Labels, intervals and readings are reported as the sealed analysis produced them. This file computes no label and adds no reading; verify_results_report.py, a separate file, checks the numbers.

Real mode refuses before it opens the sealed outputs unless the owner decision file quotes, on one line, the owner's approving words with this layout's hash and the verifier's; the analysis folder is the only one of the study under reports/; and the sealed source is unchanged file by file. It then refuses if a saved record has changed or does not pass, if the outputs differ from the exit receipt, if the analysis does not bind the two real terminals, or if a record and its arrays differ by more than the limit: there, PROTOCOL.md section 8 says the owner decides what follows before anything is read."""
import csv, datetime as dt, hashlib, json, os, re, sys, time
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = Path(r'D:\sequence-weighting-research'); SRC = ROOT / 'work/natural-text-matched-source-20261104-01'
sys.path.insert(0, str(SRC)); sys.path.insert(1, str(SRC / 'vendor'))
import fewepoch_plan as fp
import matched_plan as mp

SUBJECT = '7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56'; ANALYSIS_SHA256 = '2108f0b287a0b355d20b3d6faedec6bd93d6ad1074f3f5da629b69e14e6ddf9c'
M1_TERMINAL = '1392187d518d55ce9463fd7c687d258a791e7e1780d68e4be46b11de1337e65d'; M2_TERMINAL = '6ac3614815ce884dffbfb1b093188fb72699a636a24fbd9c7070b6b4fe8c3737'; MERGE_COMMIT = 'f3a2571029f4a0b4d0dc2ee974338e13996e11d8'
APPROVAL_ID = 'OWNER-20261105-MATCHED-ANALYSIS-01'; INPUT_CHECK_SHA256 = 'f88bd66444f84158fb9402a52d9ab691821dbc1a02e9f3932f26b9be57e505b3'
REPORTS = ROOT / 'reports'; ANALYSIS_NAME = r'natural-text-matched-analysis-\d{8}-\d{2}'; CHECKS = REPORTS / 'natural-text-matched-run-checks-20261104-01'; VERIFIER = HERE / 'verify_results_report.py'
VERIFY = dict(M1=CHECKS / 'RUN_M1_VERIFICATION.json', M2=CHECKS / 'RUN_M2_VERIFICATION.json'); FIGURES = REPORTS / 'natural-text-matched-seed-registry-20261104-01/REGISTRY_AND_PARTITION_CHECK.json'; ENGINE = REPORTS / 'natural-text-matched-engine-check-result-20261104-01/INPUTS_CHECK.json'; MERGE_CHECK = REPORTS / 'natural-text-matched-m1-approval-20261105-01/MERGE_CHECK.json'; PR_RECORD = REPORTS / 'natural-text-matched-preparation-20261104-01/REGISTRATION_PR_RECORD.json'
APPROVALS = dict(M1=ROOT / mp.ACTIVATIONS['M1'] / 'APPROVAL_RECORD.json', M2=ROOT / mp.ACTIVATIONS['M2'] / 'APPROVAL_RECORD.json')
PINS = {VERIFY['M1']: '77c4277ed5375ca61c28babdc8340eb0ff1cb4483655b164b8682c15b5ba00e8', VERIFY['M2']: '2cab0b791f7cd50d5d600823484e1fcfe773579a2cc9c1df5fbc209038106278', FIGURES: '548f2b6a80bb8f88df17f176d67c790053bdcd0eefdfb477498f3b85f58d7765', ENGINE: '022591d909988e2fd3dddb65e202f54fe3cf12897956a6602d076d9feff35d27', MERGE_CHECK: '3f1c28652d229f6532301b308e40c0f2823e415f8b6208119272d8bdc7ad0c63', PR_RECORD: '1cabaa1ac942789cbb3f6f567cfbddc91e20e98d98db27952ecb2b6c03bc65e6', APPROVALS['M1']: '0635a05faaa9653018e3a87dbf46dfdf6e1062e2d1d57a07abfa8bc091e92869', APPROVALS['M2']: '16d2dc9228a33c2c9a9b4cc84274b216907641e5da1719fdcaa958b2163fc4c2'}
OUTPUTS = ('ANALYSIS.json', 'POINTS.csv', 'FITS.csv', 'MATCHED.csv'); INPUT_ITEMS = ('n_train', 'weights', 'weights_list', 'orders', 'pool_orders', 'tied_values', 'seeds', 'articles', 'sequence_indices', 'validation', 'pool')
DRAWS = tuple(mp.GROUPS); READOUTS = tuple(mp.READOUTS); FINAL = mp.FINAL; ARM_LIST = tuple((w, fp.rate_tag(r)) for w in sorted(mp.ARMS) for r in mp.ARMS[w]); UNREADABLE = tuple(mp.UNREADABLE)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); load = lambda p: json.loads(Path(p).read_bytes())


class RuleBroken(BaseException):
    """Not an Exception, so that nothing on the way can catch it."""


def install_guard():
    """From here on, in this process, nothing under a work/runs folder can be opened, listed or changed."""
    events = ('open', 'os.listdir', 'os.scandir', 'glob.glob', 'os.mkdir', 'os.rename', 'os.remove', 'os.rmdir', 'os.truncate', 'os.utime', 'os.chmod', 'os.link', 'os.symlink', 'shutil.copyfile', 'shutil.copytree', 'shutil.move', 'shutil.rmtree')
    def hook(event, args):
        if event in events and args and isinstance(args[0], (str, bytes, os.PathLike)) and re.search(r'/work/runs(/|$)', os.path.abspath(os.fsdecode(args[0])).replace('\\', '/').lower()): raise RuleBroken(f'The results report opens nothing under work/runs: {event} {args[0]}')
    sys.addaudithook(hook)


def read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))


# ------------------------------------------------------------------ formats
MINUS = '\u2212'
def s(x, d=5): return 'undefined' if x is None else f'{x:+.{d}f}'.replace('-', MINUS)
def u(x, d=4): return 'undefined' if x is None else f'{x:.{d}f}'.replace('-', MINUS)
def iv(t, d=5): return f'[{s(t["interval"][0], d)}, {s(t["interval"][1], d)}]'
def pv(x): return 'undefined' if x is None else ('0' if x == 0 else f'{x:.2e}'.replace('-', MINUS) if x < 0.001 else f'{x:.4f}')
def spv(x): return 'undefined' if x is None else f'{x:.5f}'
def pct(x, d=2): return f'{100 * x:.{d}f}%'
def table(head, rows): return '\n'.join(['| ' + ' | '.join(str(x) for x in head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])
def ep(e): return f'E{e}'
def rate_name(tag): return '3e-4' if tag == mp.TAG_HIGH else '1e-4'
def arm(w, tag): return f'{w} at {rate_name(tag)}'
def field(r, key, f): return 'none' if key not in r else f(r[key])
def yes(x): return 'yes' if x else 'no'
def join(items): return ', '.join(items) or 'none'


DEFINITION = dict(P1='p\\*(512, E3) \u2212 p\\*(768, read at the training NLL 512 reaches at E3), at 1e-4', S1='p\\*(512, E3) \u2212 p\\*(768, read at the gap 512 reaches at E3), at 1e-4', S3='p\\*(512, E3) \u2212 p\\*(768, E3), at 1e-4: the fixed-update contrast', S4='p\\*(512, E3) \u2212 p\\*(768, read at the training NLL 512 reaches at E3), at 3e-4', S5='p\\*(512, E3) \u2212 p\\*(768, E3), at 3e-4: the fixed-update contrast', S2='p\\*(512, E3) \u2212 p\\*(768, read at the validation NLL 512 reaches at E3), at 1e-4')
SIDE_NAME = dict(ABOVE='above 0', BELOW='below 0')
QUANTITY = dict(p='p\\*', validation='Validation NLL', train='Training NLL', gap='Gap')
STEPS_AT = {mp.TAG_LOW: 'P1, S1, S3, S2', mp.TAG_HIGH: 'S4, S5'}; GATE_OF = {mp.TAG_LOW: 'rate_low', mp.TAG_HIGH: 'rate_high'}
ITEM_NAME = dict(n_train='N', weights='Weights, recorded hash', weights_list='Weights, the list the fits use', orders='Orders', pool_orders='Pool orders', tied_values='Tied values', seeds='Seeds', articles='Articles', sequence_indices='Sequence indices', validation='Validation', pool='Pool')


def gate_cell(no, name, label):
    if label in UNREADABLE or label == mp.NOT_READ: return 'not read'
    failing = no['failing'][GATE_OF[mp.STATISTICS[name]['first'][1]]]
    return f'**no: {join(failing)}**' if failing else 'yes'


def number_rows(S, names):
    rows = []
    for k in names:
        c = S[k]; t = c.get('interval'); sg = c['sign_test']
        rows.append((f'**{k}**', f'{len(c["available"])} of {len(DRAWS)}', c['status'], s(t['mean']) if t else 'none', iv(t) if t else 'none', t['df'] if t else 'none', pv(t['p']) if t else 'none', f'{sg["negative"]}/{sg["positive"]}', spv(sg['p']), join(c.get('flagged', [])) if t else 'none'))
    return table(['Step', 'Draws with a reading', 'Status', 'Mean', '95% interval', 'df', 'p, unadjusted', 'Draws < 0 / > 0', 'Exact sign test, p', 'Draws flagged at p\\* \u2265 7.999'], rows)


def match_rows(S, name):
    rows = []
    for d in DRAWS:
        r = S[name]['rows'][d]
        rows.append((d, r['status'], field(r, 'target', u), f'[{u(r["path_min"])}, {u(r["path_max"])}]' if 'path_min' in r else 'none', f'E{r["between"][0]} to E{r["between"][1]}' if 'between' in r else 'none', field(r, 'weight', u), field(r, 'read_at_readout', lambda x: f'E{x:.3f}'), field(r, 'intervals_holding_the_target', str), field(r, 'p_first', lambda x: u(x, 5)), field(r, 'p_read', lambda x: u(x, 5)), field(r, 'value', s)))
    return table(['Draw', 'Status', 'Target: 512 at E3', "768's path, E2 to E3.5: lowest, highest", 'Bracket', 'Weight', 'Read at', 'Intervals holding the target', 'p\\* of 512 at E3', 'p\\* of 768 as read', 'Contrast'], rows)


def expected_note(c): return SIDE_NAME[c['expected']]


# ------------------------------------------------------------------ the report
def render(A, points, fits, ctx):
    fx = ctx['fixture']; tag = ' (invented losses)' if fx else ''; out = []; add = out.append; no = A['not_overfit']; L = A['losses']; S = A['statistics']; by = A['by_readout']; dec = A['decision']; E3 = ep(FINAL)
    P = {(r['draw'], int(r['width']), r['tag'], float(r['epoch'])): r for r in points}; f = lambda x: None if x in ('', None) else float(x); pa = lambda d, w, t, e, k='p': f(P[d, w, t, float(e)][k])
    add('# Matched-progress confirmation: result' + (' **INVENTED LOSSES, NOT A RESULT**' if fx else ''))
    add('')
    if fx: add('> **INVENTED LOSSES. NOT A RESULT.** This is the frozen layout, filled from invented run folders written by the tests. Its labels and numbers say nothing about the study. The operations and the disclosures in sections 7a, 7f and 8 are the real records; sections 7b, 7c and 7g come from invented records, and so does the table of hashes for the analysis outputs.\n')
    add(f'**Written:** {ctx["written"]}. **Status:** Runs M1 and M2 are COMPLETE and the sealed analysis is {A["status"]}. The owner ran it, under approval {APPROVAL_ID} (`{ctx["decision"]}`), and reports one run. The order and wording of this report were fixed before any outcome was opened, and its labels, intervals and readings are the sealed analysis\'s, as produced. **Measured results are in sections 1 to 3, 5, 6 and 8, and section 4 quotes the sealed readings. Nothing here claims a mechanism or a scaling law.**')
    add('')
    add('**Check:** `RESULT_VERIFICATION.json`, written by `verify_results_report.py` after this report. A copy of this report without a passing check beside it has not been checked (section 10).')
    add('')
    add(table(['Record', 'SHA-256'], [(f'`{k}`', f'`{v}`') for k, v in ctx['records'].items()]))
    add('')
    # ---- 1
    add(f'## 1. NOT_OVERFIT per arm, the manipulation check{tag}')
    add('')
    add('Per arm, per draw, \u0394 = validation NLL at E3 minus at E2. The verdict is per arm, from the interval of the mean \u0394 over the draws: below 0 gives NOT_OVERFIT, above 0 OVERFIT, otherwise PLATEAU. It gates no label. If an arm a reading uses fails, the label stands and its reading is prefixed. No remedy is allowed: no re-run, data increase or replacement draw.')
    add('')
    rows = []
    for w, t in ARM_LIST:
        v = no['arms'][f'{w}|{t}']; i = v['interval']; low = min([(L[f'{w}|E0']['validation'], 'E0')] + [(L[f'{w}|{t}'][ep(e)]['validation'], ep(e)) for e in READOUTS])
        rows.append((arm(w, t), STEPS_AT[t], f'**{v["label"]}**', s(i['mean'], 4), iv(i, 4), i['df'], f'{i["negative"]}/{i["n"]}', s(by[E3]['panel'][f'{w}|{t}']['gap'], 4), f'{u(low[0])} ({low[1]})'))
    add(table(['Arm', 'Steps at this rate', 'Verdict', 'Mean \u0394', '95% interval', 'df', 'Draws \u0394 < 0', 'Mean gap at E3', 'Lowest mean validation NLL (readout)'], rows))
    add('')
    add(table(['Rate', 'Arms', 'All NOT_OVERFIT', 'Arms that fail'], [(k, ', '.join(arm(*a) for a in mp.GATE_ARMS[k]), yes(no['gates'][k]), join(no['failing'][k])) for k in mp.GATE_ARMS]))
    add('')
    add('**\u0394 per draw,** from `POINTS.csv`, because `ANALYSIS.json` keeps the interval and not the values:')
    add('')
    add(table(['Arm'] + list(DRAWS), [[arm(w, t)] + [s(pa(d, w, t, FINAL, 'validation') - pa(d, w, t, mp.PREVIOUS, 'validation'), 4) for d in DRAWS] for w, t in ARM_LIST]))
    add('')
    # ---- 2
    add(f'## 2. The primary, P1{tag}')
    add('')
    add(f'**Label: {dec["P1"]}.** At 1e-4, per draw: p\\*(512, E3) \u2212 p\\*(768, read at the training NLL 512 reaches at E3). REVERSAL_CONFIRMED if the 95% interval lies entirely above 0, NOT_REVERSED if entirely below, INCONCLUSIVE otherwise, and UNAVAILABLE with fewer than 5 draws (`PROTOCOL.md` section 5). Saturation can make it SATURATED or SATURATION_SENSITIVE, and neither is read (section 8 there). **The label needs only P1.** Whether the ordering reverses on these draws also needs S3, confirmed in the sequence, which is why the sealed reading in section 4 has several forms.')
    add('')
    add(number_rows(S, ('P1',)))
    add('')
    add('**Per draw,** with the bracket on 768\'s readouts. The reading comes from the first interval in readout order whose two values hold the target:')
    add('')
    add(match_rows(S, 'P1'))
    add('')
    pw = A['power_stated_in_advance']
    add('**Power stated in advance,** the chance that P1 reads REVERSAL_CONFIRMED, from N6\'s spread and the effect it was seen at, +0.0132. That effect selected this hypothesis, so it is likely flattering. It is a plan, not a result:')
    add('')
    add(table(['Draws available', 'Spread used, sd', 'At the effect seen', 'At half of it', 'At half of it, with the sd at its upper 95% limit'], [('6', pw['sd'], pw['six_seen'], pw['six_half'], pw['six_half_sd_upper']), ('5', pw['sd'], pw['five_seen'], pw['five_half'], pw['five_half_sd_upper'])]))
    add('')
    # ---- 3
    add(f'## 3. The fixed sequence{tag}')
    add('')
    add('P1, S1, S3, S4, S5, S2, in this order. A step is read as a confirmation only while every earlier step is confirmed. A step the sequence does not reach has the label NOT_READ, whatever its interval, and the side of its interval stays in the table (`PROTOCOL.md` section 6).')
    add('')
    seq = {r['step']: r for r in A['sequence']}
    add(table(['Step', 'Per draw', 'Confirmed if the interval lies', 'Label', 'Status of its interval', 'Read as a confirmation', 'Confirmed', 'Arms at this rate all NOT_OVERFIT'], [(f'**{k}**', DEFINITION[k], expected_note(S[k]), f'**{seq[k]["label"]}**', seq[k]['status'], yes(seq[k]['read_as_confirmation']), yes(seq[k]['confirmed']), gate_cell(no, k, seq[k]['label'])) for k in mp.SEQUENCE]))
    add('')
    add(table(['Confirmed through'], [(dec['confirmed_through'] or 'none',)]))
    add('')
    add(number_rows(S, mp.SEQUENCE))
    add('')
    add('**The contrast per draw.** A draw without a value shows why:')
    add('')
    add(table(['Draw'] + list(mp.SEQUENCE), [[d] + [(s(S[k]['rows'][d]['value']) if 'value' in S[k]['rows'][d] else S[k]['rows'][d]['status']) for k in mp.SEQUENCE] for d in DRAWS]))
    add('')
    add('**p\\* at E3 per draw, and the panel mean,** which S3 and S5 use directly:')
    add('')
    add(table(['Draw'] + [arm(w, t) for w, t in ARM_LIST], [[d] + [u(pa(d, w, t, FINAL), 5) for w, t in ARM_LIST] for d in DRAWS] + [['**Mean**'] + [u(by[E3]['panel'][f'{w}|{t}']['p'], 5) for w, t in ARM_LIST]]))
    add('')
    for k in ('S1', 'S4', 'S2'):
        add(f'**{k} per draw:** {DEFINITION[k]}.')
        add('')
        add(match_rows(S, k))
        add('')
    # ---- 4
    add('## 4. The sealed readings')
    add('')
    add('Quoted exactly from `ANALYSIS.json`:')
    add('')
    for i, text in enumerate(A['readings'], 1): add(f'{i}. "{text}"')
    add('')
    # ---- 5
    add(f'## 5. Always reported, not gating{tag}')
    add('')
    add('### 5a. Draws without a reading'); add('')
    add(table(['Step', 'Undefined fit', 'Target outside the path', 'Draw missing', 'Draws'], [(k, dec['unavailable_counts'][k]['UNDEFINED_FIT'], dec['unavailable_counts'][k]['TARGET_OUTSIDE_PATH'], dec['unavailable_counts'][k]['DRAW_MISSING'], join(S[k]['unavailable'])) for k in mp.SEQUENCE]))
    add('')
    add('Draws whose target lies outside 768\'s path are not a random subset of the draws.')
    add('')
    add('### 5b. Leaving out one draw at a time'); add('')
    add('The interval over the remaining draws, for every statistic with at least 4 draws. The sign tests are in section 3.')
    add('')
    rows = []
    for k in mp.SEQUENCE:
        loo = S[k].get('leave_one_out')
        if not loo: rows.append((k, 'none', 'none', 'none', 'none', 'none')); continue
        rows += [(k, d, s(x['mean']), f'[{s(x["interval"][0])}, {s(x["interval"][1])}]', x['df'], x['side']) for d, x in loo.items()]
    add(table(['Step', 'Draw left out', 'Mean', '95% interval', 'df', 'Side'], rows))
    add('')
    add('### 5c. Saturation'); add('')
    add('A draw is flagged if a fit its statistic uses is at or above 7.999, and those fits are refitted at bound 32. An unresolved refit makes the statistic SATURATED, and a side that differs at bound 32 makes it SATURATION_SENSITIVE. Neither is read.')
    add('')
    rows = []
    for k in mp.SEQUENCE:
        x = S[k].get('S32'); t32 = (x or {}).get('interval')
        rows.append((k, join(S[k].get('flagged', [])) if 'flagged' in S[k] else 'none', 'none' if x is None else yes(x['required']), field(x or {}, 'computable', yes), field(x or {}, 'unresolved_refits', str), S[k].get('side', 'none'), (x or {}).get('side', 'none'), s(t32['mean']) if t32 else 'none', iv(t32) if t32 else 'none'))
    add(table(['Step', 'Flagged draws', 'Refit needed', 'Computable', 'Unresolved refits', 'Side at bound 8', 'Side at bound 32', 'Mean at bound 32', 'Interval at bound 32'], rows))
    add('')
    add('### 5d. Records against arrays'); add('')
    ra = A['records_against_arrays']
    add(table(['Measure', 'Value'], [("Largest difference between a record's loss and the mean of the array block the fits use", f'{ra["max_absolute_difference"]:.2e}'.replace('-', MINUS)), ('Limit', f'{ra["limit"]:g}'), ('Within the limit', yes(ra['within_limit']))]))
    add('')
    # ---- 6
    add(f'## 6. Descriptive{tag}')
    add('')
    add('Non-gating, with no multiplicity adjustment (`PROTOCOL.md` section 9).')
    add('')
    add('### 6a. By readout, the fixed-update contrast 512 \u2212 768'); add('')
    cell = lambda c: ('undefined', 'undefined') if c is None else (s(c['interval']['mean']), iv(c['interval']))
    add(table(['Readout', '1e-4, mean', '1e-4, 95% interval', '3e-4, mean', '3e-4, 95% interval'], [[ep(e)] + list(cell(by[ep(e)]['contrasts']['D4'])) + list(cell(by[ep(e)]['contrasts']['D2'])) for e in READOUTS]))
    add('')
    add('### 6b. Panel means, per arm and readout'); add('')
    add('**p\\*:**'); add('')
    add(table(['Arm'] + [ep(e) for e in READOUTS], [[arm(w, t)] + [u(by[ep(e)]['panel'][f'{w}|{t}']['p'], 5) for e in READOUTS] for w, t in ARM_LIST]))
    add('')
    add('**Gap,** validation NLL minus training NLL. The E0 gap is each width\'s offset, which both of its arms share:'); add('')
    add(table(['Arm', 'E0'] + [ep(e) for e in READOUTS], [[arm(w, t), s(L[f'{w}|E0']['validation'] - L[f'{w}|E0']['train'], 4)] + [s(by[ep(e)]['panel'][f'{w}|{t}']['gap'], 4) for e in READOUTS] for w, t in ARM_LIST]))
    add('')
    for key, title in (('train', 'Training NLL'), ('validation', 'Validation NLL')):
        add(f'**{title},** in nats per token:'); add('')
        add(table(['Arm', 'E0'] + [ep(e) for e in READOUTS], [[arm(w, t), u(L[f'{w}|E0'][key])] + [u(by[ep(e)]['panel'][f'{w}|{t}'][key]) for e in READOUTS] for w, t in ARM_LIST]))
        add('')
    add('### 6c. The rate effects at E3: 1e-4 minus 3e-4'); add('')
    RE = A['rate_effects']; digits = lambda k: 5 if k == 'p' else 4; rows = []
    for w in mp.WIDTHS:
        for k in ('p', 'validation', 'train', 'gap'):
            x = RE[str(w)][k]; rows.append((w, QUANTITY[k], 'undefined', 'undefined', 'undefined') if x is None else (w, QUANTITY[k], s(x['interval']['mean'], digits(k)), iv(x['interval'], digits(k)), f'{x["interval"]["negative"]}/{x["interval"]["positive"]}'))
    add(table(['Width', 'Quantity', 'Mean', '95% interval', 'Draws < 0 / > 0'], rows))
    add('')
    add('**Per draw:**'); add('')
    add(table(['Width', 'Quantity'] + list(DRAWS), [[w, QUANTITY[k]] + [s(RE[str(w)][k]['values'][d], digits(k)) if RE[str(w)][k] else 'undefined' for d in DRAWS] for w in mp.WIDTHS for k in ('p', 'validation', 'train', 'gap')]))
    add('')
    add('### 6d. Clipping'); add('')
    add('Means are weighted by updates, because the fourth epoch is short.'); add('')
    add(table(['Arm', 'Mean clip fraction', 'Mean gradient norm', 'Largest gradient norm'], [(arm(w, t), u(L[f'{w}|{t}']['clipping']['clip_fraction_mean'], 3), u(L[f'{w}|{t}']['clipping']['gradient_norm_mean'], 3), u(L[f'{w}|{t}']['clipping']['gradient_norm_max'], 3)) for w, t in ARM_LIST]))
    add('')
    defined = [x for x in fits if x['p'] not in ('', None)]; ps = [float(x['p']) for x in defined]; reasons = {}
    for x in fits:
        if x['p'] in ('', None): reasons[x['reason']] = reasons.get(x['reason'], 0) + 1
    worst = max(fits, key=lambda x: float(x['negative_fraction'])); ratio = [float(x['objective']) / float(x['J0']) for x in defined if float(x['J0']) > 0]; fb = A['fit_bounds']
    add('### 6e. Fit quality (`FITS.csv`)'); add('')
    add(table(['Measure', 'Value'], [('Fits', len(fits)), ('Defined fits', len(ps)), ('Smallest p\\*', u(min(ps), 3) if ps else 'none'), ('Largest p\\*', u(max(ps), 3) if ps else 'none'), ('At the upper bound', fb['upper']), ('At the lower bound', fb['lower']), ('Undefined fits', fb['undefined']), ('Reasons a fit is undefined', join(f'{k}: {v}' for k, v in reasons.items())), ('Smallest total gain, signed', u(min(float(x['total_gain']) for x in fits), 1)), ('Fits with any sequence of negative gain', sum(float(x['negative_fraction']) > 0 for x in fits)), ('Fits with 5% or more of sequences at negative gain', sum(float(x['negative_fraction']) >= 0.05 for x in fits)), ('Largest share of sequences at negative gain', pct(float(worst['negative_fraction']), 1)), ('Where that is', f'{worst["draw"]}, {arm(int(worst["width"]), worst["tag"])}, E{worst["epoch"]}'), ('Lowest objective at p\\* over the objective at p = 0', u(min(ratio), 3) if ratio else 'none'), ('Highest objective at p\\* over the objective at p = 0', u(max(ratio), 3) if ratio else 'none')]))
    add('')
    # ---- 7
    add('## 7. Disclosures')
    add('')
    add('Their wording was fixed before any outcome was opened. The figures depend on the corpus manifest, the partition, the weights and the status records, and on no loss.')
    add('')
    add('### 7a. The fresh rule, and identical text'); add('')
    fig = ctx['figures']; pool = fig['pool']; pg = fig['per_group']; dis = fig['disclosure']; it = dis['identical_text']; tl = dis['titles']
    add(table(['Figure', 'Value'], [('Eligible articles', f'{pool["eligible_articles"]:,}'), ('Assigned in N5 and N6, and out', f'{pool["assigned_articles"]:,}'), ('Text duplicates of assigned articles, and out', pool['removed_text_duplicates_of_assigned']), ('Copies of texts repeated inside the pool, and out', pool['removed_repeats_inside_the_pool']), ('Sets of those repeats', pool['sets_of_repeats_inside_the_pool']), ('Fresh articles', f'{pool["fresh_articles"]:,}'), ('Fresh sequences', f'{pool["fresh_sequences"]:,}'), ('Articles the six groups use', f'{sum(pg[d]["articles"] for d in DRAWS):,}'), ('Articles left over', f'{fig["left_over_articles"]:,}'), ('Identical text: sets across the fresh groups', it['sets_across_fresh_groups']), ('Identical text: fresh texts equal to an assigned article\'s', it['fresh_texts_equal_to_an_assigned_article']), ('Identical text: repeated inside a group', it['repeated_inside_a_group']), ('Titles shared across the fresh groups', tl['sets_across_fresh_groups']), ('Fresh articles sharing a title with an assigned article, with a different text', tl['fresh_articles_sharing_a_title_with_an_assigned_article'])]))
    add('')
    add(table(['Group', 'Articles', 'Sequences used'], [(d, pg[d]['articles'], f'{pg[d]["sequences"]:,}') for d in DRAWS]))
    add('')
    add('**Not measured: exact token sequences and 64-token runs,** which N6\'s disclosure measured. They would have read the corpus\'s split files, and the owner-run draw could open only the manifest. So how far token runs recur across m01\u2013m06, N5, N6, the validation set and the pool is not known here. For scale, N6\'s groups had 64-token runs recurring in another fresh group at a mean of 0.15%. That is N6\'s figure, not a measurement of these draws.')
    add('')
    add('**Limit.** The draws are treated as independent in every interval and test above. These figures do not measure how far that is true.')
    add('')
    add('### 7b. Tied weights, on real Torch'); add('')
    add('The weights are used exactly as drawn, with at most n / 1,024 tied values. Tied values means n minus the number of distinct values. **Counted from each draw\'s own `INPUTS.json`,** by the owner-run `check_run_inputs.py`, because the assistant opens nothing under `work/runs/`.')
    add('')
    ri = ctx['inputs']; engine = ctx['engine']['draws']; ties = dis['tied_weights']['by_group']
    add(table(['Draw', 'In the run', 'Real-engine check, real Torch', 'Stdlib draw, before and after division by numpy\'s mean', 'Limit'], [(d, ri['draws'][d]['tied_values_in_the_run'], engine[d]['tied_values'], f'{ties[d]["before_division"]} and {ties[d]["after_division_numpy_mean"]}', int(engine[d]['limit'])) for d in DRAWS]))
    add('')
    add('**The order of tied entries.** The estimator\'s stable sort keeps them in ascending sequence index, so p\\* repeats for the same inputs on the same Python and libm. How much the order of ties moves p\\* on these real gains is not measured: the frozen analysis has no such step.')
    add('')
    add('### 7c. Each draw\'s inputs against the real-engine check'); add('')
    add('The sealed analysis does not compare these, so the owner-run `check_run_inputs.py` does, from each draw\'s `INPUTS.json`: the recorded hashes of the weights, orders and pool orders against the real-Torch check; the list of weights itself, which is what the fits use, rehashed against the same check; seeds against the registry; articles and sequence indices against the partition; validation and pool against N6\'s native hashes. The six training hashes have no reference, because the real-engine check ran on synthetic tokens, so only their being distinct is checked.')
    add('')
    add(table(['Draw'] + [ITEM_NAME[k] for k in INPUT_ITEMS], [[d] + [('**differs**' if ri['draws'][d]['items'][k] != 'equal' else 'equal') for k in INPUT_ITEMS] for d in DRAWS]))
    add('')
    add(table(['Measure', 'Value'], [('Comparisons', ri['comparisons']), ('Differences', len(ri['differences'])), ('The six training hashes are distinct', yes(ri['training_hashes_distinct']))]))
    add('')
    add('### 7d. The hypothesis and the rates'); add('')
    add('- **The hypothesis is post hoc.** It came from a reanalysis of N6 (`reports/adversarial-review-20261104-01/RECOMPUTE_MATCHED.json`), so N6 and its draws cannot confirm it, and they are excluded here.')
    add('- **The rates were not chosen again.** 3e-4 is the rate the few-epoch study selected on t00, and 1e-4 is 768\'s lowest validation NLL on t00 among the five rates tried. p\\* entered neither.')
    add('- **The target is 512\'s value at E3,** and the axis matters. Matching on training NLL is not matching on gain: see the limitation "Equal training NLL is not equal gain" in section 9.')
    add('')
    add('### 7e. Shared items, and one analysis'); add('')
    add('- **Shared by design:** the validation set, the pre-training pool and the tokenizer are those of N6, and every draw shares them.')
    add('- **One analysis.** The owner reports running it once, and the command\'s claim file stops a second run through that command. A run by another route would not be seen. This report reads its outputs and does not re-run it.')
    add('- **One breach of the rule on `work/runs/`, by the assistant, before the analysis.** One search from the project root, with a filter on four file names, will have walked folders there. It printed counts per file and named nothing there. Draw folders hold none of those names, so no draw file was opened and no outcome was seen. Details: `reports/natural-text-matched-m1-result-20261105-01/RESULT.md`.')
    add('')
    add('### 7f. The public registration, before any data'); add('')
    mc = ctx['merge']
    add('The protocol, the sealed source, the seed registry with its draw and exclusions, the partition and the real-engine check\'s hashes were published and merged before any activation, and the builder refused without them. Each run\'s approval record names the merge commit. **What it does not show:** the layout of this report was frozen later, by the owner\'s approval of the analysis, and is not in that pull request. **The losses already existed when this layout was frozen.** That they were unopened rests on local records and the owner\'s word, and the public record cannot show it.')
    add('')
    add(table(['Item', 'Value'], [('Pull request', mc['pull_request']['url']), ('Merged at', mc['pull_request']['merged_at']), ('Merge commit', f'`{mc["pull_request"]["merge_commit_sha"]}`'), ('Source subject at that commit', f'`{mc["subject_at_the_commit"]}`'), ('Package files, local and public', f'{mc["package"]["local_files"]} and {mc["package"]["public_files"]}'), ('Package files that differ', len(mc['package']['files_that_differ'])), ('Run M1\'s approval record names that commit', yes(ctx['approvals']['M1']['public_registration']['merge_commit'] == mc['pull_request']['merge_commit_sha'])), ('Run M2\'s approval record names that commit', yes(ctx['approvals']['M2']['public_registration']['merge_commit'] == mc['pull_request']['merge_commit_sha']))]))
    add('')
    add('### 7g. Where the analysis ran'); add('')
    add('On the owner\'s machine, by the owner, with native Windows Python and the standard library only: no WSL, Torch or GPU. From the command\'s exit receipt:')
    add('')
    rc = ctx['receipt']
    add(table(['Item', 'Value'], [('Python', f'`{rc["python_path"]}`'), ('Python version', rc['python_version']), ('Operating system', rc['operating_system']), ('Started, UTC', rc['started_utc']), ('Ended, UTC', rc['ended_utc']), ('Seconds, by the command\'s clock', f'{rc["seconds"]:,.1f}'), ('Exit code', rc['exit_code'])]))
    add('')
    # ---- 8
    add('## 8. Operations (measured, from the status records)')
    add('')
    v1, v2 = ctx['verify']['M1'], ctx['verify']['M2']; m1, m2 = v1['measured'], v2['measured']; gates = lambda v: ', '.join(f'{g[0]} {g[1]} at check {g[2]}' for g in v['checks']['every completed draw passed its gate, and the gate files equal the receipt']['detail']['gates']); off = lambda v: v['checks']['on AC throughout']['detail']['off_ac_samples']
    add(table(['Measure', 'Run M1', 'Run M2'], [('Ended', v1['ended'], v2['ended']), ('Per-run check', f'{v1["passed"]} of {v1["total"]}', f'{v2["passed"]} of {v2["total"]}'), ('Draws, by the worker\'s clock', ', '.join(f'{d} {x:,.1f} s' for d, x in m1['stage_seconds'].items()), ', '.join(f'{d} {x:,.1f} s' for d, x in m2['stage_seconds'].items())), ('Worker elapsed', f'{m1["worker_elapsed_seconds"]:,.0f} s', f'{m2["worker_elapsed_seconds"]:,.0f} s'), ('Owner elapsed, Windows clock', f'{m1["owner_elapsed_seconds"]:,.0f} s', f'{m2["owner_elapsed_seconds"]:,.0f} s'), ('Windows over the worker\'s clock', f'{m1["windows_over_worker_clock"]:.3f}', f'{m2["windows_over_worker_clock"]:.3f}'), ('Worker peak memory', f'{m1["peaks"]["worker_peak_rss"] / 1e9:.2f} GB', f'{m2["peaks"]["worker_peak_rss"] / 1e9:.2f} GB'), ('GPU peak, sampled', f'{m1["peaks"]["device_used_sampled"]:,} bytes', f'{m2["peaks"]["device_used_sampled"]:,} bytes'), ('Kept output', f'{m1["inventory"]["bytes"]:,} bytes, {m1["inventory"]["files"]} files', f'{m2["inventory"]["bytes"]:,} bytes, {m2["inventory"]["files"]} files'), ('Gate before each draw', gates(v1), gates(v2)), ('Power readings off AC', off(v1), off(v2)), ('Battery, first to last', f'{m1["battery_percent"]["first"]}% to {m1["battery_percent"]["last"]}%', f'{m2["battery_percent"]["first"]}% to {m2["battery_percent"]["last"]}%')]))
    add('')
    add('**The causes of the slow worker clock, of the rise in its ratio between the runs, and of the changes in draw time are not established.**')
    add('')
    # ---- 9
    add('## 9. Limitations')
    add('')
    add('Quoted from `PROTOCOL.md` section 11, stated in advance:')
    add('')
    add(ctx['limitations'])
    add('')
    # ---- 10
    add('## 10. How these numbers were checked')
    add('')
    add('`verify_results_report.py` is a separate file with code of its own. Its comparisons use no sealed module, it loads this layout only afterwards, to compare bytes, and it writes `RESULT_VERIFICATION.json` beside this report.')
    add('')
    add('- **Recomputed from `POINTS.csv`, in code of its own:** each target, bracket, weight and read position; each contrast; each mean, interval and p-value, with the t tail integrated directly; the sign tests; the leave-one-out intervals; each side, status and label; the sequence; NOT_OVERFIT; the rate effects; the by-readout tables; the panel means and losses at each readout; and the bound counts. Each is compared with `ANALYSIS.json` and `MATCHED.csv`.')
    add('- **The readings:** each is compared, word for word, with the verifier\'s copy of the sealed wording, under the recomputed labels and prefixes.')
    add('- **This report against those outputs:** every table cell is compared with a value the verifier formats itself, and every number outside a table must be one of the plan\'s constants. This report must also equal, byte for byte, what the frozen layout writes from those outputs.')
    add('- **The outputs against the run:** their hashes must equal those the owner\'s command recorded when the analysis ended, in `ANALYSIS_EXIT_RECEIPT.json`.')
    add('- **Not recomputed, and reported as produced:** p\\* itself and the other fields of `FITS.csv`; the training and validation NLL in `POINTS.csv`, from each `record.json`, on which every target, bracket and matched contrast rests; the E0 losses; clipping; any refit at bound 32, which can move a label; and the record-against-array difference. They need the run files under `work/runs/`, which only the sealed analysis read. So this check cannot find an error inside the sealed analysis\'s reading of those files: a wrong value that stays consistent with the rest would pass. The suite compared that reading with an independent recomputation on invented losses only.')
    add('')
    return '\n'.join(out)


# ------------------------------------------------------------------ one report
def real_gate(analysis_dir, decision):
    """Real mode, before anything else: the owner's approval quoted in a decision file under reports/, on one line with this layout's hash and the verifier's; the only analysis folder of the study under reports/; and the sealed source, file by file."""
    d = Path(decision).resolve(); a = Path(analysis_dir).resolve()
    if not d.is_file(): raise SystemExit('The owner decision file does not exist')
    approving = re.search(rf'^> I approve {re.escape(APPROVAL_ID)}\b.*$', d.read_bytes().decode('utf-8'), re.M) if d.parent.parent == REPORTS.resolve() and d.parent.name.startswith('natural-text-ladder-owner-decisions-') else None
    if approving is None: raise SystemExit(f'The owner decision file does not record approval {APPROVAL_ID}')
    if sha(__file__) not in approving.group(0) or sha(VERIFIER) not in approving.group(0): raise SystemExit('The owner decision file does not name this layout and its verifier by their hashes')
    if a.parent != REPORTS.resolve() or not re.fullmatch(ANALYSIS_NAME, a.name): raise SystemExit('The analysis folder is not the study output under reports/')
    if [p.resolve() for p in REPORTS.iterdir() if p.is_dir() and re.fullmatch(ANALYSIS_NAME, p.name)] != [a]: raise SystemExit('The analysis folder is not the only one of the study')
    manifest = load(SRC / 'SOURCE_SUBJECT.json')
    if sha(SRC / 'SOURCE_SUBJECT.json') != SUBJECT or sha(SRC / 'matched_analysis.py') != ANALYSIS_SHA256 or any(sha(SRC / f['path']) != f['sha256'] for f in manifest['files']): raise SystemExit('The sealed source changed')


def saved_records():
    """Every saved record behind the disclosures and operations: its pinned hash, and a passing verdict for each that carries one."""
    for path, want in PINS.items():
        if sha(path) != want: raise SystemExit(f'A saved record changed: {Path(path).name}')
    rec = dict(figures=load(FIGURES), engine=load(ENGINE), merge=load(MERGE_CHECK), pr=load(PR_RECORD), verify={m: load(VERIFY[m]) for m in VERIFY}, approvals={m: load(APPROVALS[m]) for m in APPROVALS}); e = rec['engine']
    if not (rec['figures']['all_pass'] and rec['merge']['all_agree'] and rec['pr']['state'] == 'MERGED' and rec['pr']['merge_commit'] == MERGE_COMMIT and rec['merge']['pull_request']['merge_commit_sha'] == MERGE_COMMIT and rec['merge']['subject_at_the_commit'] == SUBJECT and all(v['all_pass'] and v['ended'] == 'COMPLETE' for v in rec['verify'].values()) and e['status'] == 'PASS' and e['fixture'] is False and e['loss_read'] is False and all(e['draws'][d]['status'] == 'PASS' for d in DRAWS)): raise SystemExit('A saved record does not pass')
    return rec


def limitations():
    t = (SRC / 'PROTOCOL.md').read_bytes().decode('utf-8').replace('\r\n', '\n'); return t[t.index('## 11. Limitations stated in advance\n') + len('## 11. Limitations stated in advance\n'):t.index('## 12. Operations and failure policy')].strip('\n')


def assemble(analysis_dir, decision, checks_dir=CHECKS, fixture=False, written=None):
    """The report's text, and what it was made from. No gate and no write: build() gates, and the verifier calls this to compare bytes."""
    analysis_dir, decision, checks_dir = Path(analysis_dir), Path(decision), Path(checks_dir); saved = saved_records(); A = load(analysis_dir / 'ANALYSIS.json'); receipt = load(checks_dir / 'ANALYSIS_EXIT_RECEIPT.json'); inputs = load(checks_dir / 'RUN_INPUTS_CHECK.json')
    if A.get('status') != 'COMPLETE' or A.get('closed_by_failure') is not False: raise SystemExit(f'The analysis is {A.get("status")}: this layout assumes six complete draws; report by hand under an owner decision')
    if not A['records_against_arrays']['within_limit']: raise SystemExit('A record and its arrays differ by more than the limit: PROTOCOL.md section 8 leaves what follows to the owner, before anything is read')
    if receipt.get('exit_code') != 0 or receipt.get('outputs') != {n: sha(analysis_dir / n) for n in OUTPUTS}: raise SystemExit('The outputs differ from the exit receipt of the analysis')
    if inputs.get('analysis_json_sha256') != sha(analysis_dir / 'ANALYSIS.json') or (not fixture and inputs.get('check_sha256') != INPUT_CHECK_SHA256): raise SystemExit('The input check is not of this analysis, or not by the frozen script')
    records = {n: sha(analysis_dir / n) for n in OUTPUTS}; records.update({'Run M1 TERMINAL.json': A['terminals']['M1']['sha256'], 'Run M2 TERMINAL.json': A['terminals']['M2']['sha256'], 'RUN_M1_VERIFICATION.json': sha(VERIFY['M1']), 'RUN_M2_VERIFICATION.json': sha(VERIFY['M2']), 'ANALYSIS_EXIT_RECEIPT.json': sha(checks_dir / 'ANALYSIS_EXIT_RECEIPT.json'), 'RUN_INPUTS_CHECK.json': sha(checks_dir / 'RUN_INPUTS_CHECK.json'), 'SOURCE_SUBJECT.json': sha(SRC / 'SOURCE_SUBJECT.json'), 'matched_analysis.py': sha(SRC / 'matched_analysis.py'), 'this layout, make_results_report.py': sha(__file__), 'the verifier, verify_results_report.py': sha(VERIFIER), 'owner decision': sha(decision)})
    ctx = dict(saved, fixture=fixture, written=written or time.strftime('%d %b %Y'), decision=decision.relative_to(ROOT).as_posix() if decision.is_relative_to(ROOT) else str(decision), records=records, receipt=receipt, inputs=inputs, limitations=limitations())
    return render(A, read_csv(analysis_dir / 'POINTS.csv'), read_csv(analysis_dir / 'FITS.csv'), ctx), A


def build(analysis_dir, out_dir, decision, checks_dir=CHECKS, fixture=False):
    analysis_dir, out_dir = Path(analysis_dir), Path(out_dir)
    if out_dir.exists(): raise SystemExit('The output folder exists')
    if not fixture: real_gate(analysis_dir, decision)
    elif Path(analysis_dir).resolve().parent == REPORTS.resolve(): raise SystemExit('Fixture mode refuses a folder under reports/')
    if not Path(decision).is_file(): raise SystemExit('The owner decision file does not exist')
    text, A = assemble(analysis_dir, decision, checks_dir, fixture)
    if not fixture:
        t = A['terminals']; merged = dt.datetime.fromisoformat(load(MERGE_CHECK)['pull_request']['merged_at'].replace('Z', '+00:00')).timestamp()
        if t != dict(M1=dict(status='COMPLETE', sha256=M1_TERMINAL), M2=dict(status='COMPLETE', sha256=M2_TERMINAL)): raise SystemExit('ANALYSIS.json does not bind the real terminals of Runs M1 and M2')
        if (analysis_dir / 'ANALYSIS.json').stat().st_mtime <= merged: raise SystemExit('ANALYSIS.json is older than the public registration')
    out_dir.mkdir(parents=False, exist_ok=False); (out_dir / 'RESULT.md').write_bytes(text.encode('utf-8'))
    return text


if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit('usage: make_results_report.py <ANALYSIS_DIR> <NEW_OUT_DIR> <OWNER_DECISION_FILE>')
    install_guard(); build(sys.argv[1], sys.argv[2], sys.argv[3]); print('Written:', Path(sys.argv[2]) / 'RESULT.md', 'sha256', sha(Path(sys.argv[2]) / 'RESULT.md')); print('Now run verify_results_report.py. Until it passes, this report has not been checked.')
