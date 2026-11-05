"""Frozen analysis of the matched-progress confirmation, N7 (stdlib only). Runs after Runs M1 and M2; never during them.

  python -I -B matched_analysis.py <RUN_M1_DIR> <RUN_M2_DIR> <NEW_OUT_DIR>      -> ANALYSIS.json, POINTS.csv, FITS.csv, MATCHED.csv

Every rule is fixed before any data exists (PROTOCOL.md). Gains are signed per-sequence training-loss reductions from each width's own E0;
p* is vendor/core.exponent on [0, 8] (text_analysis.fit, a byte copy); undefined fits stay undefined; draws are the only inference unit.
The gap at a readout is the validation NLL minus the training NLL of that readout (the worker's record).

Matching. Per draw, the target is the value of `key` (training NLL, gap or validation NLL) of 512 at E3. 768's p* is read along its own
readouts E2, E2.25, ..., E3.5: in the first interval, in readout order, whose two values hold the target, by linear interpolation between
the two bracketing readouts. A target outside that path makes the draw UNAVAILABLE for that statistic. A target equal to a readout's value
is held by the first interval that contains it; two equal values in an interval read at its earlier readout. The bracketing readouts of
each draw are reported.

The fixed sequence P1, S1, S3, S4, S5, S2 (owner decision 20261104-02). Each statistic is a t interval (95%, df = available draws - 1), UNAVAILABLE with fewer than 5
available draws. A step is read as a confirmation only while every earlier step is confirmed; a later step is reported with the
label NOT_READ, and the side of its interval stays in its status.
- P1, at 1e-4: p*(512, E3) - p*(768, matched on training NLL). REVERSAL_CONFIRMED if the interval is entirely above 0, NOT_REVERSED if
  entirely below 0, otherwise INCONCLUSIVE.
- S1, at 1e-4: the same, matched on the gap. Expected above 0.
- S3, at 1e-4: the fixed-update contrast p*(512, E3) - p*(768, E3). Expected below 0.
- S4, at 3e-4: matched on training NLL. Expected above 0. S5, at 3e-4: the fixed-update contrast. Expected above 0.
- S2, at 1e-4, last: matched on validation NLL. Expected above 0.
Secondary labels: CONFIRMED on the expected side, CONTRARY on the other, otherwise INCONCLUSIVE.

If a run did not complete, the completed draws are read only if P1 has at least 5 available draws. Otherwise nothing is read: the analysis
reports availability and its counts, and no value, interval, side, loss or fit. A draw with an undefined fit is unavailable, and the count of
each reason a draw has no reading is always reported. A run that stopped before any stage folder existed is not counted and not analysed, and
neither is a run that left no terminal: load() refuses both, because the next step there is the owner's or the study has closed.

Always reported, not gating: sign counts and the exact two-sided sign test, leave-one-draw-out intervals with at least 4 draws, NOT_OVERFIT,
the per-draw matched readouts, and how far each record's losses lie from the array blocks the fits use. Saturation (the few-epoch rule): a draw is flagged if a fit its statistic uses is >= 7.999, and those fits are refitted at bound 32;
an unresolved refit makes the statistic SATURATED, and a side that differs at bound 32 makes it SATURATION_SENSITIVE. Neither is read.
NOT_OVERFIT is per arm, from the interval of validation NLL at E3 minus E2; if it fails for an arm a reading uses, the label stands and the
reading is prefixed. Only the real runs are analysed: load() refuses a FIXTURE approval and any run folder other than the plan's, unless a
test passes allow_fixture=True.
"""
import csv, json, math, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import text_plan as plan
import text_analysis as ta
import fewepoch_plan as fp
import fewepoch_analysis as fa
import matched_plan as mp
import matched_worker as mw

EPS = ta.EPS
FINAL = mp.FINAL
DRAWS = mp.GROUPS
ARM_LIST = tuple((w, fp.rate_tag(r)) for w in sorted(mp.ARMS) for r in mp.ARMS[w])
MIN_LEAVE_ONE_OUT = 4                         # the interval over the remaining draws needs df >= 2
RECORD_LIMIT = 1e-3                           # records_against_arrays: above this, a record and its arrays do not describe the same readout
NO_READING = ('UNDEFINED_FIT', 'TARGET_OUTSIDE_PATH', 'DRAW_MISSING')    # why a draw has no reading of a statistic


# ------------------------------------------------------------------ loading
def load(runs, pins=mw.PINS, subject=None, allow_fixture=False):
    """Runs M1 and M2 (COMPLETE, FAILED or STOPPED_AT_STARTUP). Per draw and rate tag: its widths' E0 arrays, records and arrays, or None
    if the draw's stage did not complete. Unless allow_fixture (tests only), a FIXTURE approval and any run folder other than the plan's
    are refused."""
    m1, m2 = (Path(r) for r in runs); terms = {}
    for mode, r in (('M1', m1), ('M2', m2)):
        if not (r / 'TERMINAL.json').is_file(): raise ValueError(f'Run {mode} left no terminal: the analysis is not run')
        raw = (r / 'TERMINAL.json').read_bytes(); t = json.loads(raw)
        if t.get('kind') != 'matched' or t.get('mode') != mode: raise ValueError(f'Not a matched Run {mode}: {r}')
        if not allow_fixture and (str((t.get('bindings') or {}).get('approval_id', '')).upper().startswith('FIXTURE') or r.resolve() != mw.RUNS[mode].resolve()):
            raise ValueError('Only the real matched runs are analysed: a FIXTURE approval or another run folder is refused')
        if subject is not None and t.get('subject') != subject: raise ValueError('Run subject differs from this analysis source')
        if t.get('status') not in ('COMPLETE', 'FAILED', 'STOPPED_AT_STARTUP'): raise ValueError(f'Run {mode} ended {t.get("status")}')
        if t.get('counted_as_attempt') is not True: raise ValueError(f'Run {mode} stopped before any stage folder, so it is not counted and not analysed: the next step is the owner decision')
        bd = t.get('bindings') or {}
        if any(bd.get(k) != pins[k] for k in ('registry_sha256', 'partition_sha256', 'corpus_manifest_sha256', 'fewepoch_registry_sha256', 'peak_registry_sha256')):
            raise ValueError(f'Run {mode} was not bound to the pinned registry, partition and corpus')
        terms[mode] = (t, raw)
    if terms['M2'][0]['bindings'].get('run_m1_terminal_sha256') != mw.sha(terms['M1'][1]): raise ValueError('Run M2 was not admitted on this Run M1')
    draws = {}; want_arms = {str(w): list(r) for w, r in mp.ARMS.items()}
    for mode, r in (('M1', m1), ('M2', m2)):
        done = mw.completed_draws(terms[mode][0])
        for d in mp.RUN_STAGES[mode]:
            rp = r / f'{d}-RECEIPT.json'; complete = rp.exists() and json.loads(rp.read_bytes()).get('status') == 'COMPLETE'
            if complete != (d in done): raise ValueError(f"Run {mode}: the receipts differ from the terminal's stage records at {d}")
            if not complete: draws[d] = None; continue
            inp = json.loads((r / d / 'INPUTS.json').read_bytes()); pre = json.loads((r / d / 'PRETRAINED.json').read_bytes()); n = inp['n_train']
            if inp['arms'] != want_arms or inp['widths'] != sorted(mp.WIDTHS) or n != mp.N_TRAIN and not allow_fixture or inp['readouts'] != list(mp.READOUTS): raise ValueError('Draw inputs differ from the plan: ' + d)
            e0s = {}
            for w in mp.WIDTHS:
                b = pre[str(w)]['E0_arrays']; e0raw = (r / b['path']).read_bytes()
                if len(e0raw) != b['bytes'] or mw.sha(e0raw) != b['sha256'] or len(e0raw) != 4 * (n + plan.N_VALIDATION): raise ValueError('E0 binding differs: ' + b['path'])
                e0 = array('f'); e0.frombytes(e0raw); e0s[w] = e0
            per_tag = {}
            for w, tag in ARM_LIST:
                rec = json.loads((r / d / f'w{w}' / tag / 'record.json').read_bytes()); arr = (r / rec['arrays']['path']).read_bytes(); lr = next(x for x in mp.ARMS[w] if fp.rate_tag(x) == tag)
                if len(arr) != rec['arrays']['bytes'] or mw.sha(arr) != rec['arrays']['sha256']: raise ValueError('Array binding differs: ' + rec['arrays']['path'])
                if rec['layout']['block_epochs'] != list(mp.READOUTS) or rec['layout']['train_rows'] != n or rec['layout']['validation_rows'] != plan.N_VALIDATION or rec['lr'] != lr or rec['width'] != w or rec['tag'] != tag:
                    raise ValueError('Record layout differs: ' + rec['arrays']['path'])
                per_tag.setdefault(tag, dict(weights=inp['weights'], n=n, widths={}))['widths'][w] = dict(e0=e0s[w], raw=arr, record=rec)
            draws[d] = per_tag
    return dict(draws=draws, terminals={m: dict(status=terms[m][0]['status'], sha256=mw.sha(terms[m][1])) for m in terms})


def readout(t, e, key): return next(x[key] for x in t['record']['readouts'] if x['epoch'] == e)
def gap_of(t, e): return readout(t, e, 'validation_loss') - readout(t, e, 'train_loss')


def points(data):
    """per[d][(width, tag)][e] = dict(p, gap, validation, train), or per[d] = None for a missing draw."""
    per = {}
    for d in DRAWS:
        dd = data['draws'].get(d)
        if dd is None: per[d] = None; continue
        per[d] = {}
        for w, tag in ARM_LIST:
            arm = dd[tag]; t = arm['widths'][w]
            per[d][(w, tag)] = {e: dict(p=ta.fit(arm, w, e)['p'], gap=gap_of(t, e), validation=readout(t, e, 'validation_loss'), train=readout(t, e, 'train_loss')) for e in mp.READOUTS}
    return per


def records_against_arrays(data):
    """The largest absolute difference, over every readout of every arm, between a record's loss and the mean of the array block the fits
    use. Reported and not gating; above the limit, the readings say so first."""
    worst = 0.0
    for dd in data['draws'].values():
        for arm in (dd or {}).values():
            for t in arm['widths'].values():
                for x in t['record']['readouts']:
                    for split, key in (('train', 'train_loss'), ('validation', 'validation_loss')):
                        b = ta.block(t, x['epoch'], split); worst = max(worst, abs(math.fsum(b) / len(b) - x[key]))
    return dict(max_absolute_difference=worst, limit=RECORD_LIMIT, within_limit=worst <= RECORD_LIMIT)


# ------------------------------------------------------------------ matching
def read_along(path_rows, target):
    """path_rows: (readout, value, p) in readout order along MATCH_PATH. The first interval whose two values hold the target gives the
    reading. Returns TARGET_OUTSIDE_PATH, or the bracket with UNDEFINED_FIT if a bracketing p* is undefined, or READ."""
    hits = [(a, b) for a, b in zip(path_rows, path_rows[1:]) if min(a[1], b[1]) <= target <= max(a[1], b[1])]
    values = [r[1] for r in path_rows]
    base = dict(target=target, path_min=min(values), path_max=max(values), intervals_holding_the_target=len(hits))
    if not hits: return dict(base, status='TARGET_OUTSIDE_PATH')
    (e0, x0, p0), (e1, x1, p1) = hits[0]; w = 0.0 if x1 == x0 else (target - x0) / (x1 - x0)
    base.update(between=[e0, e1], value_at_bracket=[x0, x1], weight=w, read_at_readout=e0 + w * (e1 - e0), p_at_bracket=[p0, p1])
    if p0 is None or p1 is None: return dict(base, status='UNDEFINED_FIT')
    return dict(base, status='READ', p_read=p0 + w * (p1 - p0))


def draw_row(per_d, spec):
    """One draw of one statistic: the reading of the second arm, and the contrast with the first arm at E3."""
    a, b = spec['first'], spec['second']; p_first = per_d[a][FINAL]['p']
    if spec['kind'] == 'matched':
        rows = [(e, per_d[b][e][spec['key']], per_d[b][e]['p']) for e in mp.MATCH_PATH]; r = read_along(rows, per_d[a][FINAL][spec['key']])
    else:
        p = per_d[b][FINAL]['p']; r = dict(status='READ', p_read=p, read_at_readout=FINAL) if p is not None else dict(status='UNDEFINED_FIT', read_at_readout=FINAL)
    r = dict(r, p_first=p_first)
    if p_first is None and r['status'] == 'READ': r['status'] = 'UNDEFINED_FIT'
    if r['status'] == 'READ': r['value'] = p_first - r['p_read']
    return r


def fits_used(spec, row):
    """The (arm, readout) fits a read draw uses."""
    second = [(spec['second'], e) for e in row['between']] if spec['kind'] == 'matched' else [(spec['second'], FINAL)]
    return [(spec['first'], FINAL)] + second


# ------------------------------------------------------------------ the statistics and their labels
def side(t):
    if t['interval'][0] > EPS: return 'ABOVE'
    if t['interval'][1] < -EPS: return 'BELOW'
    return 'SPANS'


def sign_test(values):
    """The exact two-sided sign test; zeros are dropped. None if every value is zero."""
    pos, neg = sum(v > 0 for v in values), sum(v < 0 for v in values); n = pos + neg
    if n == 0: return dict(positive=pos, negative=neg, p=None)
    return dict(positive=pos, negative=neg, p=min(1.0, 2 * math.fsum(math.comb(n, k) for k in range(min(pos, neg) + 1)) / 2 ** n))


def leave_one_out(values):
    """values: {draw: value}. The interval over the remaining draws, leaving out each draw in turn."""
    out = {}
    for d in values:
        t = ta.tint([v for k, v in values.items() if k != d]); s = side(t); out[d] = dict(mean=t['mean'], interval=t['interval'], df=t['df'], side=s, excludes_zero=s != 'SPANS')
    return out


def refit_value(data, spec, d, row):
    """The draw's contrast with its fits at bound 32. Returns (value or None, unresolved fits)."""
    ps, unresolved = {}, 0
    for (w, tag), e in fits_used(spec, row):
        arm = data['draws'][d][tag]; r = ta.exponent_upper(arm['weights'], ta.gains(arm, w, e), ta.S32_UPPER); ps[((w, tag), e)] = r['p']; unresolved += r['p'] is None or r['p'] >= ta.S32_UPPER - 0.001
    if any(p is None for p in ps.values()): return None, unresolved
    first = ps[(spec['first'], FINAL)]
    if spec['kind'] == 'matched':
        p0, p1 = (ps[(spec['second'], e)] for e in row['between']); return first - (p0 + row['weight'] * (p1 - p0)), unresolved
    return first - ps[(spec['second'], FINAL)], unresolved


def statistic(data, per, name):
    """One statistic of the sequence: its per-draw rows, interval, unadjusted p, side and label, under the availability and saturation rules."""
    spec = mp.STATISTICS[name]; rows = {d: (dict(status='DRAW_MISSING') if per[d] is None else draw_row(per[d], spec)) for d in DRAWS}
    available = [d for d in DRAWS if rows[d]['status'] == 'READ']; out = dict(kind=spec['kind'], key=spec['key'], first=list(spec['first']), second=list(spec['second']), expected=spec['expected'], rows=rows, available=available, unavailable={d: rows[d]['status'] for d in DRAWS if d not in available}, unavailable_counts={why: sum(rows[d]['status'] == why for d in DRAWS) for why in NO_READING})
    vals = {d: rows[d]['value'] for d in available}; out.update(values=vals, sign_test=sign_test(list(vals.values())))
    if len(available) >= MIN_LEAVE_ONE_OUT: out['leave_one_out'] = leave_one_out(vals)
    if len(available) < mp.MIN_DRAWS: return dict(out, status='UNAVAILABLE', label='UNAVAILABLE')
    t = fa.test(list(vals.values())); s = side(t)
    out.update(status=s, side=s, interval=t)
    flagged = [d for d in available if any(per[d][arm][e]['p'] >= plan.P_UPPER for arm, e in fits_used(spec, rows[d]))]; out['flagged'] = flagged
    if not flagged: out['S32'] = dict(required=False, reason='NO_FLAGGED_DRAWS')
    else:
        v32, unresolved = dict(vals), 0
        for d in flagged: v32[d], u = refit_value(data, spec, d, rows[d]); unresolved += u
        computable = not unresolved and all(v is not None for v in v32.values()); out['S32'] = dict(required=True, computable=computable, unresolved_refits=unresolved)
        if not computable: out['status'] = 'SATURATED'
        else:
            t32 = fa.test(list(v32.values())); s32 = side(t32); out['S32'].update(interval=t32, side=s32)
            if s32 != s: out['status'] = 'SATURATION_SENSITIVE'
    return dict(out, label=label_of(name, out['status']))


def label_of(name, status):
    if status in mp.UNREADABLE: return status
    if name == mp.PRIMARY: return mp.PRIMARY_LABELS[status]
    return 'INCONCLUSIVE' if status == 'SPANS' else 'CONFIRMED' if status == mp.STATISTICS[name]['expected'] else 'CONTRARY'


def is_confirmed(name, label): return label == ('REVERSAL_CONFIRMED' if name == mp.PRIMARY else 'CONFIRMED')


def sequence(stats):
    """The fixed sequence: a step is read as a confirmation only while every earlier step is confirmed. A step it does not reach has the
    label NOT_READ, whatever its interval; the side stays in its status."""
    out, reached = [], True
    for name in mp.SEQUENCE:
        confirmed = reached and is_confirmed(name, stats[name]['label']); out.append(dict(step=name, label=stats[name]['label'] if reached else mp.NOT_READ, status=stats[name].get('status'), read_as_confirmation=reached, confirmed=confirmed)); reached = confirmed
    return out


def not_overfit(data):
    avail = [d for d in DRAWS if data['draws'].get(d) is not None]
    if len(avail) < mp.MIN_DRAWS: return dict(status='UNAVAILABLE', draws=avail)
    out = {}
    for w, tag in ARM_LIST:
        dv = [readout(data['draws'][d][tag]['widths'][w], FINAL, 'validation_loss') - readout(data['draws'][d][tag]['widths'][w], mp.PREVIOUS, 'validation_loss') for d in avail]
        t = ta.tint(dv); out[f'{w}|{tag}'] = dict(interval=t, label='NOT_OVERFIT' if t['interval'][1] < -EPS else 'OVERFIT' if t['interval'][0] > EPS else 'PLATEAU')
    gates = {k: all(out[f'{w}|{tag}']['label'] == 'NOT_OVERFIT' for w, tag in v) for k, v in mp.GATE_ARMS.items()}
    return dict(status='COMPUTED', draws=avail, arms=out, all_arms=all(v['label'] == 'NOT_OVERFIT' for v in out.values()), gates=gates, failing={k: [f'{w} at {tag}' for w, tag in v if out[f'{w}|{tag}']['label'] != 'NOT_OVERFIT'] for k, v in mp.GATE_ARMS.items()})


# ------------------------------------------------------------------ readings (PROTOCOL.md section 7)
SCOPE = ('The models are small (depth 4, 16.9 M and 34.7 M parameters) and this is one corpus family at one recipe. A reading is about the two widths and two rates on these draws. '
         "No reading claims a mechanism or a scaling law, and nothing about Jane Street's scale follows.")
LIMIT = ("This does not show a capacity mechanism, and nothing about Jane Street's scale follows. Matching on training loss also removes any faster learning of the wider model, so neither axis is privileged.")
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
STEP_CONFIRMED = dict(S1='At 1e-4, p* at 512 at E3 is above p* at 768 read at the gap 512 reaches at E3.', S2='At 1e-4, p* at 512 at E3 is above p* at 768 read at the validation NLL 512 reaches at E3.', S3=S3_CONFIRMED,
                      S4='At 3e-4, p* at 512 at E3 is above p* at 768 read at the training NLL 512 reaches at E3.', S5='At 3e-4, after 3,072 updates, 512 is above 768, as in N6. This is a fixed-budget fact.')
STEP_CONTRARY = 'The interval lies on the other side of 0 from the one expected.'
STEP_INCONCLUSIVE = 'The interval includes 0. This is not a claim of absence.'
SIDE_WORDS = dict(ABOVE='the interval lies above 0', BELOW='the interval lies below 0', SPANS='the interval includes 0', UNAVAILABLE='fewer than 5 draws have a reading', SATURATED='saturated', SATURATION_SENSITIVE='saturation-sensitive')
CLOSED = 'A run did not complete, and P1 has fewer than 5 available draws, so the completed draws are not read and the study closes UNAVAILABLE. This is not evidence either way.'
RECORDS_DIFFER = 'WARNING: a record and its arrays differ by more than the limit (records_against_arrays). This changes no label. The owner decides what follows, before anything here is read.'
DISCLOSURE = ("Data: never-assigned WikiText-103 training articles, excluding every article of N5 and N6 and their text duplicates and repeats inside the pool; new seeds; no new tuning. The validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies. "
              "The hypothesis came from a post-hoc reanalysis of N6 (reports/adversarial-review-20261104-01/RECOMPUTE_MATCHED.json), so N6 cannot confirm it. p* between readouts is a linear interpolation over a quarter of an epoch. A draw whose target lies outside 768's E2-E3.5 path is unavailable for that statistic, and such draws are not a random subset. "
              "Equal training NLL is not equal gain, because p* is fit to gains from each width's own E0. The t intervals assume normal draws, untested at five or six.")


def power_line():
    p = mp.POWER
    return (f"Power stated in advance, from N6's spread (sd {p['sd']}) and the effect it was seen at (+0.0132), which is likely flattering: with six draws {p['six_seen']} at that effect and {p['six_half']} at half of it, and {p['six_half_sd_upper']} at half of it with the sd at its upper 95% limit; "
            f"with five draws {p['five_seen']}, {p['five_half']} and {p['five_half_sd_upper']}.")


def axis_line(stats, seq):
    """Whether the ordering reverses on these draws: P1 with S3, as the sequence reads it."""
    if not next(r for r in seq if r['step'] == 'S3')['read_as_confirmation']: return AXIS_NOT_READ
    status = stats['S3'].get('status')
    return AXIS_SHOWN if status == 'BELOW' else AXIS_SAME if status == 'ABOVE' else AXIS_NOT_SHOWN


def draws_line(stats, terminals):
    p1 = stats['P1']; without = ', '.join(f'{d} ({r})' for d, r in p1['unavailable'].items()) or 'none'
    ended = [f"Run {m} ended {t['status']}" for m, t in terminals.items() if t['status'] != 'COMPLETE']
    return f"P1 has a reading on {len(p1['available'])} of {len(DRAWS)} draws; without one: {without}." + (' ' + '; '.join(ended) + ': a draw lost to a failure is not a random draw.' if ended else '')


def counts_line(stats):
    rows = '; '.join(f"{k} {', '.join(str(stats[k]['unavailable_counts'][why]) for why in NO_READING)}" for k in mp.SEQUENCE)
    return f'Draws without a reading, by statistic (undefined fit, target outside the path, draw missing): {rows}.'


def readings(stats, seq, gate, terminals, records):
    out = [SCOPE] + ([] if records['within_limit'] else [RECORDS_DIFFER]) + [draws_line(stats, terminals), counts_line(stats)]
    def prefix(label, *keys):
        failing = [x for k in keys for x in gate['failing'][k]] if gate.get('status') == 'COMPUTED' else []
        return f"{label} is not read as a few-epoch test: {', '.join(failing)} not still improving from E2 to E3 (NOT_OVERFIT failed). " if failing else ''
    label = stats['P1']['label']
    if label == 'REVERSAL_CONFIRMED': out.append(prefix(label, 'rate_low') + REVERSAL + ' ' + axis_line(stats, seq) + ' ' + LIMIT)
    elif label == 'NOT_REVERSED': out.append(prefix(label, 'rate_low') + NOT_REVERSED)
    elif label == 'INCONCLUSIVE': out.append(prefix(label, 'rate_low') + INCONCLUSIVE + ' ' + power_line())
    elif label == 'UNAVAILABLE': out.append(UNAVAILABLE)
    else: out.append(f'P1 is {label}: it is not read.')
    for row in seq[1:]:
        name = row['step']; lab = row['label']; head = STEP_TEXT[name]; rates = 'rate_low' if mp.STATISTICS[name]['first'][1] == mp.TAG_LOW else 'rate_high'; stops = '' if name == mp.SEQUENCE[-1] else ' The sequence stops here.'
        if not row['read_as_confirmation']: out.append(f"{head}: {SIDE_WORDS[row['status']]}. Reported and not read as a confirmation, because an earlier step of the fixed sequence is not confirmed.")
        elif lab in mp.UNREADABLE: out.append(f'{head}: {lab}. It is not read.{stops}')
        else: out.append(prefix(name, rates) + f'{head}: {lab}. ' + (STEP_CONFIRMED[name] if lab == 'CONFIRMED' else (STEP_CONTRARY if lab == 'CONTRARY' else STEP_INCONCLUSIVE) + stops))
    out.append(DISCLOSURE)
    return out


# ------------------------------------------------------------------ descriptive sections (non-gating; no multiplicity adjustment)
def by_readout(per, avail):
    """Per readout: the fixed-update contrasts with unadjusted intervals, and the panel means per arm."""
    out = {}
    pairs = dict(D4=((512, mp.TAG_LOW), (768, mp.TAG_LOW)), D2=((512, mp.TAG_HIGH), (768, mp.TAG_HIGH)))
    for e in mp.READOUTS:
        row = dict(contrasts={})
        for name, (a, b) in pairs.items():
            vals = {d: (per[d][a][e]['p'] - per[d][b][e]['p']) if per[d][a][e]['p'] is not None and per[d][b][e]['p'] is not None else None for d in avail}
            row['contrasts'][name] = None if any(v is None for v in vals.values()) or len(vals) < 3 else dict(values=vals, interval=ta.tint(list(vals.values())))
        row['panel'] = {f'{w}|{tag}': {k: (None if any(per[d][(w, tag)][e][k] is None for d in avail) else math.fsum(per[d][(w, tag)][e][k] for d in avail) / len(avail)) for k in ('p', 'gap', 'validation', 'train')} for w, tag in ARM_LIST}
        out[f'E{e}'] = row
    return out


def rate_effects(per, avail):
    """Per width, 1e-4 minus 3e-4 at E3: p*, validation NLL, training NLL and the gap."""
    out = {}
    for w in mp.WIDTHS:
        lo, hi = (w, mp.TAG_LOW), (w, mp.TAG_HIGH); out[str(w)] = {}
        for k in ('p', 'validation', 'train', 'gap'):
            vals = {d: (per[d][lo][FINAL][k] - per[d][hi][FINAL][k]) if per[d][lo][FINAL][k] is not None and per[d][hi][FINAL][k] is not None else None for d in avail}
            out[str(w)][k] = None if any(v is None for v in vals.values()) or len(vals) < 3 else dict(values=vals, interval=ta.tint(list(vals.values())))
    return out


def losses(data, avail):
    out = {}
    if not avail: return out
    dds = [data['draws'][d] for d in avail]
    for w, tag in ARM_LIST:
        ts = [dd[tag]['widths'][w] for dd in dds]; ep = [x for t in ts for x in t['record']['epochs']]; key = f'{w}|{tag}'
        out[key] = {f'E{e}': dict(train=math.fsum(readout(t, e, 'train_loss') for t in ts) / len(ts), validation=math.fsum(readout(t, e, 'validation_loss') for t in ts) / len(ts)) for e in mp.READOUTS}
        out[key]['clipping'] = dict(clip_fraction_mean=math.fsum(x['clip_fraction'] * x['updates'] for x in ep) / sum(x['updates'] for x in ep), gradient_norm_mean=math.fsum(x['gradient_norm_mean'] * x['updates'] for x in ep) / sum(x['updates'] for x in ep), gradient_norm_max=max(x['gradient_norm_max'] for x in ep))
    for w in mp.WIDTHS:
        e0 = [dd[mp.TAG_HIGH]['widths'][w]['e0'] for dd in dds]; n = dds[0][mp.TAG_HIGH]['n']
        out[f'{w}|E0'] = dict(train=math.fsum(math.fsum(a[:n]) / n for a in e0) / len(e0), validation=math.fsum(math.fsum(a[n:]) / (len(a) - n) for a in e0) / len(e0))
    return out


def matched_rows(stats):
    """MATCHED.csv: every draw of every statistic, with its bracket."""
    table = []
    for name in mp.SEQUENCE:
        for d in DRAWS:
            r = stats[name]['rows'][d]; between = r.get('between') or [None, None]
            table.append(dict(statistic=name, draw=d, status=r['status'], target=r.get('target'), between_low=between[0], between_high=between[1], weight=r.get('weight'), read_at_readout=r.get('read_at_readout'), intervals_holding_the_target=r.get('intervals_holding_the_target'), p_first=r.get('p_first'), p_read=r.get('p_read'), value=r.get('value')))
    return table


def closed_by_failure(stats, terminals):
    """A run that did not complete: the completed draws are read only if P1 has at least 5 available draws (owner decision 20261104-02)."""
    return any(t['status'] != 'COMPLETE' for t in terminals.values()) and len(stats['P1']['available']) < mp.MIN_DRAWS


def closed_result(data, stats, avail, per):
    """Nothing is read. Availability and its counts leave this function; no value, interval, side, loss or fit does."""
    kept = {name: dict(kind=s['kind'], key=s['key'], first=s['first'], second=s['second'], expected=s['expected'], rows={d: dict(status=r['status']) for d, r in s['rows'].items()}, available=s['available'], unavailable=s['unavailable'], unavailable_counts=s['unavailable_counts'], status='UNAVAILABLE' if name == mp.PRIMARY else mp.NOT_READ, label='UNAVAILABLE' if name == mp.PRIMARY else mp.NOT_READ) for name, s in stats.items()}
    seq = [dict(step=name, label=kept[name]['label'], status=None, read_as_confirmation=name == mp.PRIMARY, confirmed=False) for name in mp.SEQUENCE]; undefined = sum(per[d][arm][e]['p'] is None for d in avail for arm in ARM_LIST for e in mp.READOUTS)
    return dict(status='UNAVAILABLE', closed_by_failure=True, terminals=data['terminals'], draws_available=avail, arms={str(w): list(r) for w, r in mp.ARMS.items()}, readouts=list(mp.READOUTS), match_path=list(mp.MATCH_PATH), decision=dict(P1='UNAVAILABLE', labels={k: v['label'] for k, v in kept.items()}, sides={k: None for k in kept}, unavailable_counts={k: v['unavailable_counts'] for k, v in kept.items()}, confirmed_through=None), sequence=seq, statistics=kept,
                readings=[SCOPE, CLOSED, draws_line(stats, data['terminals']), counts_line(stats), DISCLOSURE], fit_bounds=dict(undefined=undefined), power_stated_in_advance=dict(mp.POWER), note='A run did not complete and P1 has fewer than 5 available draws: nothing is read.')


def analyse(runs, **kw):
    ta._FITS.clear(); data = load(runs, **kw); avail = [d for d in DRAWS if data['draws'].get(d) is not None]
    full = {d: (data['draws'][d] if d in avail else None) for d in DRAWS}; per = points(dict(data, draws=full))
    stats = {name: statistic(data, per, name) for name in mp.SEQUENCE}
    if closed_by_failure(stats, data['terminals']): return closed_result(data, stats, avail, per), [], []
    gate = not_overfit(data); seq = sequence(stats); fits, rows = [], []; records = records_against_arrays(data)
    for row in seq: stats[row['step']]['label'] = row['label']
    for d in avail:
        for w, tag in ARM_LIST:
            arm = data['draws'][d][tag]
            for e in mp.READOUTS:
                fits.append(dict(draw=d, width=w, tag=tag, epoch=e, **ta.fit(arm, w, e))); v = per[d][(w, tag)][e]; rows.append(dict(draw=d, width=w, tag=tag, epoch=e, p=v['p'], gap=v['gap'], validation=v['validation'], train=v['train']))
    bound = dict(upper=sum(bool(f.get('upper')) for f in fits), lower=sum(bool(f.get('lower')) for f in fits), undefined=sum(f['p'] is None for f in fits))
    confirmed = [r['step'] for r in seq if r['confirmed']]
    result = dict(status='COMPLETE' if len(avail) == len(DRAWS) else 'PARTIAL_UNAVAILABLE_DRAWS' if avail else 'UNAVAILABLE', closed_by_failure=False, terminals=data['terminals'], draws_available=avail, arms={str(w): list(r) for w, r in mp.ARMS.items()}, readouts=list(mp.READOUTS), match_path=list(mp.MATCH_PATH),
                  decision=dict(P1=stats['P1']['label'], labels={k: v['label'] for k, v in stats.items()}, sides={k: v['status'] for k, v in stats.items()}, unavailable_counts={k: v['unavailable_counts'] for k, v in stats.items()}, confirmed_through=confirmed[-1] if confirmed else None), sequence=seq, statistics=stats, readings=readings(stats, seq, gate, data['terminals'], records), records_against_arrays=records, not_overfit=gate, power_stated_in_advance=dict(mp.POWER), fit_bounds=bound, losses=losses(data, avail),
                  note='P1 is the pre-registered primary; S1 to S5 are read as confirmations only as the fixed sequence allows, and a step it does not reach has the label NOT_READ, with the side of its interval in its status; NOT_OVERFIT, the leave-one-out intervals, the sign tests and every other section are reported and do not gate.')
    if avail: result.update(rate_effects=rate_effects(per, avail), by_readout=by_readout(per, avail))
    return result, rows, fits


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit('usage: matched_analysis.py <RUN_M1_DIR> <RUN_M2_DIR> <NEW_OUT_DIR>')
    m1, m2, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    subject = mw.sha((HERE / 'SOURCE_SUBJECT.json').read_bytes()) if (HERE / 'SOURCE_SUBJECT.json').exists() else None
    result, rows, fits = analyse((m1, m2), subject=subject)
    out.mkdir(parents=False, exist_ok=False)
    (out / 'ANALYSIS.json').write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    write_csv(out / 'POINTS.csv', rows); write_csv(out / 'FITS.csv', fits); write_csv(out / 'MATCHED.csv', matched_rows(result['statistics']))
    print(json.dumps(dict(status=result['status'], decision=result['decision'], not_overfit=(result.get('not_overfit') or {}).get('gates'), records_against_arrays=result.get('records_against_arrays')), indent=1))
