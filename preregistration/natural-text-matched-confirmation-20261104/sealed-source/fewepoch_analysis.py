"""Frozen analysis of the few-epoch, data-rich width ladder (stdlib only). Runs after Runs B1 and B2; never during them.

  python -I -B fewepoch_analysis.py <RUN_B1_DIR> <RUN_B2_DIR> <NEW_OUT_DIR>      -> ANALYSIS.json, POINTS.csv, FITS.csv

Every rule is fixed before any outcome (PROTOCOL.md; owner decisions 20261101-02). Gains are signed per-sequence training-loss
reductions from each width's own E0; p* is vendor/core.exponent on [0, 8] (text_analysis.fit, a byte copy); undefined fits
stay undefined; the ten draws are the only inference unit (df 9). The gap at a readout is the validation NLL minus the
training NLL of that readout (the worker's record). Primaries, under Holm's step-down at family-wise 5% (two-sided t tests):
- M: per draw, the mean over 101 equally spaced gap levels of the common range [max of the two minima, min of the two maxima]
  of p*(768) - p*(384), each width's p* read along its readouts E0.25-E3 at the first crossing of the level (linear
  interpolation within that segment); undefined if any of the ten fits is undefined, if the common range is empty or a single
  point, or if a level is not crossed;
- FALL: the OLS slope of p* on log2 width over 384, 512, 768 at E3;
- RISE: the OLS slope of p* on log2 width over 64-384 at E3.
A rejected primary is labelled by the sign of its mean; otherwise NOT_DETECTED (M) or INCONCLUSIVE. A missing draw makes a
primary UNAVAILABLE, an undefined statistic UNDEFINED; both enter Holm with p = 1. Saturation (the S32 part of revision 05's
rule; the SD sensitivity is not used, each primary being one point per draw; review 1, findings 1 and 11): a draw is flagged if
any fit its statistic uses is >= 7.999, and its fits are refitted at bound 32. A primary with an unresolved refit (or an
undefined refitted statistic) is SATURATED and enters both Holm runs with p = 1. If any primary is flagged, Holm is re-run with
the flagged primaries' bound-32 p-values; every primary whose label differs between the two runs is SATURATION_SENSITIVE.
NOT_OVERFIT: per width, the df-9
interval of validation NLL at E3 minus E2; a primary is read as a few-epoch test only if every width it uses is NOT_OVERFIT.
Only the real runs are analysed: load() refuses a FIXTURE approval and any run folder other than the plan's, unless a test
passes allow_fixture=True.
"""
import csv, json, math, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import text_plan as plan
import text_analysis as ta
import fewepoch_plan as fp
import fewepoch_worker as fw

EPS = ta.EPS
XS = {w: math.log2(w) for w in fp.WIDTHS}
UNREADABLE = ('UNAVAILABLE', 'UNDEFINED', 'SATURATED', 'SATURATION_SENSITIVE')
FINAL = fp.FINAL


# ------------------------------------------------------------------ t p-values (regularized incomplete beta; stdlib)
def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0; c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300); h = d
    for m in range(1, 1000):
        m2 = 2 * m; aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > 1e-300 else 1e-300); c = 1.0 + aa / c; c = c if abs(c) > 1e-300 else 1e-300; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > 1e-300 else 1e-300); c = 1.0 + aa / c; c = c if abs(c) > 1e-300 else 1e-300; de = d * c; h *= de
        if abs(de - 1.0) < 1e-15: return h
    raise ArithmeticError('Incomplete beta did not converge')


def betai(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1.0 - bt * _betacf(b, a, 1 - x) / b


def p_two_sided(t, df): return betai(df / 2, 0.5, df / (df + t * t))


def test(values):
    """The df n-1 interval (text_analysis.tint) and the two-sided p-value of the mean; degenerate if sd <= EPS."""
    t = ta.tint(values); degenerate = t['sd'] <= EPS
    p = (0.0 if abs(t['mean']) > EPS else 1.0) if degenerate else p_two_sided(t['mean'] / t['se'], t['df'])
    return dict(t, p=p, degenerate=degenerate)


def holm(pvalues):
    """Holm's step-down over FAMILY at ALPHA: ordered by p (ties in FAMILY order), rejected while p <= ALPHA / (m - i)."""
    order = sorted(fp.FAMILY, key=lambda k: (pvalues[k], fp.FAMILY.index(k))); m = len(order); out = {}; open_ = True; adj = 0.0
    for i, k in enumerate(order):
        threshold = fp.ALPHA / (m - i); rejected = open_ and pvalues[k] <= threshold; adj = max(adj, min(1.0, (m - i) * pvalues[k]))
        out[k] = dict(p=pvalues[k], step=i + 1, threshold=threshold, rejected=rejected, holm_adjusted_p=adj)
        open_ = rejected
    return out


def labels_from(tests, readable):
    """Holm labels: rejected -> the direction of the mean; otherwise the third label. Unreadable primaries enter with p = 1."""
    h = holm({k: (tests[k]['p'] if readable.get(k) else 1.0) for k in fp.FAMILY}); out = {}
    for k in fp.FAMILY:
        below, above, other = fp.LABELS[k]
        out[k] = (below if tests[k]['mean'] < 0 else above) if readable.get(k) and h[k]['rejected'] else other
    return out, h


# ------------------------------------------------------------------ the matched-gap contrast
def at_gap(gaps, ps, G):
    """First crossing of level G along the readout path; linear interpolation of p* within that segment."""
    for k in range(len(gaps) - 1):
        a, b = gaps[k], gaps[k + 1]
        if min(a, b) <= G <= max(a, b): return ps[k] if a == b else ps[k] + (G - a) / (b - a) * (ps[k + 1] - ps[k])
    return None


def matched(g384, p384, g768, p768, levels=fp.M_LEVELS):
    """Undefined if the common range is empty or a single point, or if a level is not crossed (review 1, finding 2)."""
    lo, hi = max(min(g384), min(g768)), min(max(g384), max(g768))
    if not hi > lo: return dict(value=None, lo=lo, hi=hi, reason='NO_COMMON_GAP_RANGE')
    lv = [lo + (hi - lo) * j / (levels - 1) for j in range(levels)]; lv[0], lv[-1] = lo, hi
    pairs = [(at_gap(g768, p768, G), at_gap(g384, p384, G)) for G in lv]
    if any(a is None or b is None for a, b in pairs): return dict(value=None, lo=lo, hi=hi, reason='NO_CROSSING')
    return dict(value=math.fsum(a - b for a, b in pairs) / levels, lo=lo, hi=hi, reason=None)


# ------------------------------------------------------------------ loading
def load(runs, pins=fw.PINS, subject=None, allow_fixture=False):
    """Runs B1 and B2 (COMPLETE, FAILED or STOPPED_AT_STARTUP). Per draw: its widths' E0 arrays, records and arrays, or None
    if the draw's stage did not complete. Unless allow_fixture (tests only), a FIXTURE approval and any run folder other than
    the plan's are refused."""
    b1, b2 = (Path(r) for r in runs); terms = {}
    for mode, r in (('B1', b1), ('B2', b2)):
        raw = (r / 'TERMINAL.json').read_bytes(); t = json.loads(raw)
        if t.get('kind') != 'fewepoch' or t.get('mode') != mode: raise ValueError(f'Not a few-epoch Run {mode}: {r}')
        if not allow_fixture and (str((t.get('bindings') or {}).get('approval_id', '')).upper().startswith('FIXTURE') or r.resolve() != fw.RUNS[mode].resolve()):
            raise ValueError('Only the real few-epoch runs are analysed: a FIXTURE approval or another run folder is refused')
        if subject is not None and t.get('subject') != subject: raise ValueError('Run subject differs from this analysis source')
        if t.get('status') not in ('COMPLETE', 'FAILED', 'STOPPED_AT_STARTUP'): raise ValueError(f'Run {mode} ended {t.get("status")}')
        bd = t.get('bindings') or {}
        if (bd.get('registry_sha256'), bd.get('partition_sha256'), bd.get('corpus_manifest_sha256')) != (pins['registry_sha256'], pins['partition_sha256'], pins['corpus_manifest_sha256']):
            raise ValueError(f'Run {mode} was not bound to the pinned registry, partition and corpus')
        terms[mode] = (t, raw)
    t1, t2 = terms['B1'][0], terms['B2'][0]
    if t2['bindings'].get('run_b1_terminal_sha256') != fw.sha(terms['B1'][1]): raise ValueError('Run B2 was not admitted on this Run B1')
    if any(t1['bindings'].get(k) != t2['bindings'].get(k) for k in ('lr_selection_sha256', 'run_a_terminal_sha256')) or t1.get('learning_rate') != t2.get('learning_rate'):
        raise ValueError('Runs B1 and B2 differ in their rate selection')
    lr = t1.get('learning_rate'); draws = {}
    for mode, r in (('B1', b1), ('B2', b2)):
        for d in fp.RUN_STAGES[mode]:
            rp = r / f'{d}-RECEIPT.json'
            if not rp.exists() or json.loads(rp.read_bytes()).get('status') != 'COMPLETE': draws[d] = None; continue
            inp = json.loads((r / d / 'INPUTS.json').read_bytes()); pre = json.loads((r / d / 'PRETRAINED.json').read_bytes()); n = inp['n_train']
            if inp['rates'] != [lr] or inp['widths'] != list(fp.WIDTHS) or n != fp.N_TRAIN and not allow_fixture or inp['readouts'] != list(fp.READOUTS): raise ValueError('Draw inputs differ from the plan: ' + d)
            widths = {}
            for w in fp.WIDTHS:
                rec = json.loads((r / d / f'w{w}' / fp.SELECTED_TAG / 'record.json').read_bytes()); arr = (r / rec['arrays']['path']).read_bytes()
                if len(arr) != rec['arrays']['bytes'] or fw.sha(arr) != rec['arrays']['sha256']: raise ValueError('Array binding differs: ' + rec['arrays']['path'])
                if rec['layout']['block_epochs'] != list(fp.READOUTS) or rec['layout']['train_rows'] != n or rec['layout']['validation_rows'] != plan.N_VALIDATION or rec['lr'] != lr or rec['width'] != w:
                    raise ValueError('Record layout differs: ' + rec['arrays']['path'])
                e0raw = (r / pre[str(w)]['E0_arrays']['path']).read_bytes(); b = pre[str(w)]['E0_arrays']
                if len(e0raw) != b['bytes'] or fw.sha(e0raw) != b['sha256'] or len(e0raw) != 4 * (n + plan.N_VALIDATION): raise ValueError('E0 binding differs: ' + b['path'])
                e0 = array('f'); e0.frombytes(e0raw)
                widths[w] = dict(e0=e0, raw=arr, record=rec)
            draws[d] = dict(weights=inp['weights'], n=n, widths=widths)
    return dict(draws=draws, terminals={m: dict(status=terms[m][0]['status'], sha256=fw.sha(terms[m][1])) for m in terms}, learning_rate=lr)


def readout(t, e, key): return next(x[key] for x in t['record']['readouts'] if x['epoch'] == e)
def gap_of(t, e): return readout(t, e, 'validation_loss') - readout(t, e, 'train_loss')


def points(data):
    per = {}
    for d in fp.DRAWS:
        dd = data['draws'].get(d)
        per[d] = None if dd is None else {e: dict(p=[ta.fit(dd, w, e)['p'] for w in fp.WIDTHS], gap=[gap_of(dd['widths'][w], e) for w in fp.WIDTHS]) for e in fp.READOUTS}
    return per


IDX = {w: i for i, w in enumerate(fp.WIDTHS)}


def slope(ps, widths):
    ys = [ps[IDX[w]] for w in widths]
    return None if any(v is None for v in ys) else ta.ols_slope([XS[w] for w in widths], ys)


def statistic(name, pd):
    """pd: {readout: dict(p, gap)} of one draw. Returns (value or None, detail)."""
    if name == 'FALL': return slope(pd[FINAL]['p'], fp.FALL_WIDTHS), None
    if name == 'RISE': return slope(pd[FINAL]['p'], fp.RISE_WIDTHS), None
    i3, i7 = IDX[384], IDX[768]; p3 = [pd[e]['p'][i3] for e in fp.READOUTS]; p7 = [pd[e]['p'][i7] for e in fp.READOUTS]
    if any(v is None for v in p3 + p7): return None, dict(reason='UNDEFINED_FIT')
    m = matched([pd[e]['gap'][i3] for e in fp.READOUTS], p3, [pd[e]['gap'][i7] for e in fp.READOUTS], p7)
    return m['value'], m


def used(name): return [(e, w) for e in (fp.READOUTS if name == 'M' else (FINAL,)) for w in fp.GATE_WIDTHS[name]]


def primaries(data, per):
    """The three primaries, Holm and the saturation rule."""
    out, tests, readable, s32 = {}, {}, {}, {}
    for name in fp.FAMILY:
        missing = [d for d in fp.DRAWS if per[d] is None]
        if missing: out[name] = dict(label='UNAVAILABLE', missing=missing); tests[name] = dict(mean=0.0, p=1.0); continue
        vals, details = {}, {}
        for d in fp.DRAWS: vals[d], details[d] = statistic(name, per[d])
        undefined = [d for d in fp.DRAWS if vals[d] is None]
        if undefined: out[name] = dict(label='UNDEFINED', undefined=undefined, details=details); tests[name] = dict(mean=0.0, p=1.0); continue
        t = test([vals[d] for d in fp.DRAWS]); tests[name] = t; readable[name] = True
        flagged = [d for d in fp.DRAWS if any(per[d][e]['p'][IDX[w]] >= plan.P_UPPER for e, w in used(name))]
        out[name] = dict(values=vals, details=details if name == 'M' else None, interval=t, flagged=flagged)
        if flagged:
            v32, unresolved = dict(vals), 0
            for d in flagged:
                dd = data['draws'][d]; pd = {e: dict(p=list(per[d][e]['p']), gap=per[d][e]['gap']) for e in fp.READOUTS}
                for e, w in used(name):
                    r = ta.exponent_upper(dd['weights'], ta.gains(dd, w, e), ta.S32_UPPER); pd[e]['p'][IDX[w]] = r['p']
                    unresolved += r['p'] is None or r['p'] >= ta.S32_UPPER - 0.001
                v32[d] = statistic(name, pd)[0]
            s32[name] = dict(computable=not unresolved and all(v is not None for v in v32.values()), unresolved_refits=unresolved, values=v32)
            if s32[name]['computable']: s32[name]['interval'] = test([v32[d] for d in fp.DRAWS])
    # The saturation rule under Holm (review 1, finding 1): a SATURATED primary enters both runs with p = 1; the re-run uses
    # the flagged primaries' bound-32 p-values; every primary whose label changes is SATURATION_SENSITIVE.
    saturated = {k for k, s in s32.items() if not s['computable']}
    rd = {k: True for k in readable if k not in saturated}
    base, h = labels_from(tests, rd)
    family32 = dict(required=False, reason='NO_FLAGGED_DRAWS')
    if s32:
        t32 = {k: (s32[k]['interval'] if k in s32 and s32[k]['computable'] else tests[k]) for k in fp.FAMILY}; lab32, h32 = labels_from(t32, rd)
        family32 = dict(required=True, flagged_primaries=sorted(s32), saturated=sorted(saturated), labels=lab32, holm=h32)
    for name in fp.FAMILY:
        if name not in readable: out[name].update(holm=h[name]); continue
        out[name].update(primary_label=None if name in saturated else base[name], bound8_p=tests[name]['p'], holm=h[name], S32=dict(required=False, reason='NO_FLAGGED_DRAWS') if name not in s32 else dict(required=True, **{k: v for k, v in s32[name].items() if k != 'values'}))
        out[name]['label'] = ('SATURATED' if name in saturated else 'SATURATION_SENSITIVE' if s32 and lab32[name] != base[name] else base[name])
    out['_saturation_rerun'] = family32
    return out


def not_overfit(data):
    if any(data['draws'].get(d) is None for d in fp.DRAWS): return dict(status='UNAVAILABLE')
    out = {}
    for w in fp.WIDTHS:
        dv = [readout(data['draws'][d]['widths'][w], FINAL, 'validation_loss') - readout(data['draws'][d]['widths'][w], fp.PREVIOUS, 'validation_loss') for d in fp.DRAWS]
        t = ta.tint(dv); out[str(w)] = dict(interval=t, label='NOT_OVERFIT' if t['interval'][1] < -EPS else 'OVERFIT' if t['interval'][0] > EPS else 'PLATEAU')
    gates = {k: all(out[str(w)]['label'] == 'NOT_OVERFIT' for w in fp.GATE_WIDTHS[k]) for k in fp.FAMILY}
    return dict(status='COMPUTED', widths=out, all_widths=all(v['label'] == 'NOT_OVERFIT' for v in out.values()), gates=gates,
                failing={k: [w for w in fp.GATE_WIDTHS[k] if out[str(w)]['label'] != 'NOT_OVERFIT'] for k in fp.FAMILY})


# ------------------------------------------------------------------ readings (PROTOCOL.md section 8)
REGIME = ('The few-epoch question is read only where every width a primary uses was still improving its validation loss from E2 to E3 (NOT_OVERFIT). '
          'The models are small (0.73-34.7 M parameters, depth 4) and see far fewer tokens per parameter than compute-optimal training; '
          '"closer to Jane Street\'s setting" means 3 epochs and no detected overfitting, nothing more.')
CONFOUND = ('At matched gap the larger width has had fewer epochs, so a nonzero M is also what p* gives if it depends on training progress rather than on the gap '
            '(stated in advance; in the planning fixtures an epoch-only curve read CAPACITY_BEYOND_MEMORIZATION in 96-99% of replicates).')
TEXT = dict(
    M={'CAPACITY_BEYOND_MEMORIZATION': 'M: at matched train-validation gap, p* at 768 is below p* at 384 (CAPACITY_BEYOND_MEMORIZATION). This contradicts the memorization-only account, which predicts NOT_DETECTED. It is not by itself evidence of a capacity effect. ' + CONFOUND,
       'CAPACITY_ABOVE_MEMORIZATION': 'M: at matched train-validation gap, p* at 768 is above p* at 384 (CAPACITY_ABOVE_MEMORIZATION). This contradicts the memorization-only account, which predicts NOT_DETECTED. It is not by itself evidence of a capacity effect. ' + CONFOUND,
       'NOT_DETECTED': 'M: no difference between 768 and 384 at matched gap is detected with ten draws (NOT_DETECTED), as the memorization-only account predicts. This is not a claim of absence.'},
    FALL={'TURNS_DOWN': 'FALL: at E3, p* falls with width over 384-768 (TURNS_DOWN): the fall seen late in the overfit regime also appears in this few-epoch regime, at this scale.',
          'CONTINUES_RISING': 'FALL: at E3, p* rises with width over 384-768 (CONTINUES_RISING): no turn-down within this ladder. This matches the memorization-only prediction, and also Jane Street\'s pattern with a peak above 768; the study cannot separate the two.',
          'INCONCLUSIVE': 'FALL: no fall or rise over 384-768 is detected at E3 with ten draws (INCONCLUSIVE). This is not a claim of absence.'},
    RISE={'RISES': 'RISE: at E3, p* rises with width over 64-384 (RISES), as both accounts predict.',
          'FALLS': 'RISE: at E3, p* falls with width over 64-384 (FALLS), contrary to both accounts.',
          'INCONCLUSIVE': 'RISE: no rise or fall over 64-384 is detected at E3 with ten draws (INCONCLUSIVE). This is not a claim of absence.'})
HOLM = 'Labels follow Holm\'s step-down over M, FALL and RISE at family-wise 5% (two-sided t tests, ten draws); every primary\'s Holm-adjusted p-value is reported.'
DISCLOSURE = ('Data: WikiText-103 raw training articles, excluding every article equal by title or text to a WikiText-2 article; the tokenizer, the validation set and the '
              'pre-training pool are those of the earlier natural-text studies. The common rate was chosen on the tuning draw t00 by validation NLL only.')


def readings(prims, gate, e0_gap=None):
    out = [REGIME, HOLM]
    for k in fp.FAMILY:
        lab = prims[k]['label']; pw = fp.POWER[k]
        if lab in UNREADABLE: text = f'{k} is {lab}: it is not read.'
        else:
            text = TEXT[k][lab]
            if lab in ('NOT_DETECTED', 'INCONCLUSIVE'):
                text += f" Power stated in advance (ten draws, Holm; from effects seen in the overfit regime of the earlier studies): {pw['seen']} at the seen effect, {pw['half']} at half of it."
            if gate.get('status') == 'COMPUTED' and not gate['gates'][k]:
                text = f"{k} ({lab}) is not read as a few-epoch test: width(s) {', '.join(str(w) for w in gate['failing'][k])} were not still improving from E2 to E3 (NOT_OVERFIT failed). " + text
            if prims[k]['interval']['degenerate']: text += ' All ten draw values are equal to within 1e-9, so the interval is that single value; the p-value is 0 for a nonzero value and 1 for zero.'
            if k == 'M' and e0_gap: text += f" The gap includes each width's E0 offset (training articles from WikiText-103, validation from WikiText-2's validation split); mean E0 gap: 384 {e0_gap['384']:.4f}, 768 {e0_gap['768']:.4f}."
        out.append(text)
    read = lambda k: gate.get('status') == 'COMPUTED' and gate['gates'][k]
    if prims['FALL']['label'] == 'TURNS_DOWN' and prims['RISE']['label'] == 'RISES' and read('FALL') and read('RISE'):
        out.append('FALL and RISE together: an interior p* peak at E3 within 64-768.')
    out.append(DISCLOSURE)
    return out


# ------------------------------------------------------------------ secondaries (non-gating)
def by_readout(per):
    out = {}
    if any(per[d] is None for d in fp.DRAWS): return dict(status='UNAVAILABLE')
    for e in fp.READOUTS:
        pts = {d: per[d][e] for d in fp.DRAWS}
        if any(v is None for p in pts.values() for v in p['p']): out[f'E{e}'] = dict(label='UNDEFINED'); continue
        curve = [math.fsum(pts[d]['p'][k] for d in fp.DRAWS) / len(fp.DRAWS) for k in range(len(fp.WIDTHS))]
        gaps = [math.fsum(pts[d]['gap'][k] for d in fp.DRAWS) / len(fp.DRAWS) for k in range(len(fp.WIDTHS))]
        argmax = lambda c: fp.WIDTHS[max(range(len(c)), key=lambda k: (c[k], -k))]
        locs = {d: ta.peak_location(pts[d]['p'], [XS[w] for w in fp.WIDTHS]) for d in fp.DRAWS}
        fall = ta.tint([slope(pts[d]['p'], fp.FALL_WIDTHS) for d in fp.DRAWS]); rise = ta.tint([slope(pts[d]['p'], fp.RISE_WIDTHS) for d in fp.DRAWS])
        out[f'E{e}'] = dict(curve=curve, gap=gaps, argmax_width=argmax(curve), per_draw_argmax={d: argmax(pts[d]['p']) for d in fp.DRAWS}, fall=fall, rise=rise,
                            location_log2={d: v[1] for d, v in locs.items()}, location_kind={d: v[2] for d, v in locs.items()})
    return out


def shift(per):
    """The peak shift across readouts (secondary): per draw the OLS slope of the peak location on log2 readout, with the
    pre-registered censoring statement (PROTOCOL.md section 7)."""
    if any(per[d] is None for d in fp.DRAWS) or any(v is None for d in fp.DRAWS for e in fp.READOUTS for v in per[d][e]['p']): return dict(label='UNAVAILABLE_OR_UNDEFINED')
    le = [math.log2(e) for e in fp.READOUTS]; mean_le = math.fsum(le) / len(le); xs = [XS[w] for w in fp.WIDTHS]
    vals, top, bottom = {}, {f'E{e}': 0 for e in fp.READOUTS}, {f'E{e}': 0 for e in fp.READOUTS}; conservative = overstating = 0
    for d in fp.DRAWS:
        locs = [ta.peak_location(per[d][e]['p'], xs) for e in fp.READOUTS]; vals[d] = ta.ols_slope(le, [l[1] for l in locs])
        for e, x, l in zip(fp.READOUTS, le, locs):
            if l[0] == len(xs) - 1: top[f'E{e}'] += 1; conservative += x < mean_le; overstating += x >= mean_le
            if l[0] == 0: bottom[f'E{e}'] += 1; conservative += x >= mean_le; overstating += x < mean_le
    t = ta.tint(list(vals.values())); lab = ta.direction(t)
    if conservative == overstating == 0: cens = 'No location is at a ladder end, so the slope is not censored.'
    elif overstating == 0: cens = ('Every ladder-end location is at 768 before the mean log2 readout or at 64 after it, so the slope is conservative for MOVES_SMALLER, '
                                   'provided those curves continue beyond the ladder end in the direction they leave it.')
    else: cens = 'Some ladder-end location is at 768 at E1-E3 or at 64 at E0.25-E0.5, which can overstate a shift to smaller widths.'
    return dict(label=lab, interval=t, values=vals, locations_at_768=top, locations_at_64=bottom, conservative_points=conservative, overstating_points=overstating, censoring=cens,
                note='Secondary (owner decisions 20261101-02): not part of the Holm family.')


def losses(data):
    out = {}
    avail = [data['draws'][d] for d in fp.DRAWS if data['draws'].get(d) is not None]
    if not avail: return out
    for w in fp.WIDTHS:
        for e in fp.READOUTS:
            tr = math.fsum(readout(dd['widths'][w], e, 'train_loss') for dd in avail) / len(avail); va = math.fsum(readout(dd['widths'][w], e, 'validation_loss') for dd in avail) / len(avail)
            out[f'{w}|E{e}'] = dict(train=tr, validation=va, gap=va - tr, n=len(avail))
        e0 = [dd['widths'][w]['e0'] for dd in avail]; n = avail[0]['n']
        out[f'{w}|E0'] = dict(train=math.fsum(math.fsum(a[:n]) / n for a in e0) / len(e0), validation=math.fsum(math.fsum(a[n:]) / (len(a) - n) for a in e0) / len(e0))
        series = [(0, out[f'{w}|E0']['validation'])] + [(e, out[f'{w}|E{e}']['validation']) for e in fp.READOUTS]
        out[f'{w}|validation_minimum'] = dict(zip(('epoch', 'validation'), min(series, key=lambda x: (x[1], x[0]))))
        ep = [x for dd in avail for x in dd['widths'][w]['record']['epochs']]
        out[f'{w}|clipping'] = dict(clip_fraction_mean=math.fsum(x['clip_fraction'] for x in ep) / len(ep), gradient_norm_mean=math.fsum(x['gradient_norm_mean'] for x in ep) / len(ep),
                                    gradient_norm_max=max(x['gradient_norm_max'] for x in ep))
    return out


def analyse(runs, **kw):
    ta._FITS.clear(); data = load(runs, **kw)
    if all(data['draws'].get(d) is None for d in fp.DRAWS):
        prims = {k: dict(label='UNAVAILABLE', reason='NO_COMPLETED_DRAW') for k in fp.FAMILY}
        return dict(status='UNAVAILABLE', terminals=data['terminals'], primaries=prims, readings=[REGIME, f'Every primary is UNAVAILABLE: no draw completed.', DISCLOSURE]), [], []
    per = points(data); prims = primaries(data, per); rerun = prims.pop('_saturation_rerun'); gate = not_overfit(data); lo = losses(data)
    e0_gap = {str(w): lo[f'{w}|E0']['validation'] - lo[f'{w}|E0']['train'] for w in fp.WIDTHS} if lo else None
    avail = [d for d in fp.DRAWS if data['draws'][d] is not None]
    fits = [dict(draw=d, width=w, epoch=e, lr=data['learning_rate'], **ta.fit(data['draws'][d], w, e)) for d in avail for w in fp.WIDTHS for e in fp.READOUTS]
    rows = []
    for d in avail:
        for e in fp.READOUTS:
            p = per[d][e]['p']; row = dict(draw=d, epoch=e, fall=slope(p, fp.FALL_WIDTHS), rise=slope(p, fp.RISE_WIDTHS))
            row.update({f'p_{w}': v for w, v in zip(fp.WIDTHS, p)}); row.update({f'gap_{w}': v for w, v in zip(fp.WIDTHS, per[d][e]['gap'])})
            rows.append(row)
    bound = dict(upper=sum(bool(f.get('upper')) for f in fits), lower=sum(bool(f.get('lower')) for f in fits), undefined=sum(f['p'] is None for f in fits))
    result = dict(status='COMPLETE' if len(avail) == len(fp.DRAWS) else 'PARTIAL_UNAVAILABLE_DRAWS', terminals=data['terminals'], draws_available=avail, learning_rate=data['learning_rate'],
                  widths=list(fp.WIDTHS), readouts=list(fp.READOUTS), decision={k: prims[k]['label'] for k in fp.FAMILY}, readings=readings(prims, gate, e0_gap),
                  primaries=prims, saturation_rerun=rerun, not_overfit=gate, e0_gap=e0_gap, predictions=fp.PREDICTIONS, power_stated_in_advance=fp.POWER,
                  fit_bounds=bound, shift=shift(per), by_readout=by_readout(per), losses=lo,
                  note='Only M, FALL and RISE, under Holm, are pre-registered primaries; NOT_OVERFIT is the pre-registered manipulation check; every other section is secondary or descriptive.')
    return result, rows, fits


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit('usage: fewepoch_analysis.py <RUN_B1_DIR> <RUN_B2_DIR> <NEW_OUT_DIR>')
    b1, b2, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=False, exist_ok=False)
    subject = fw.sha((HERE / 'SOURCE_SUBJECT.json').read_bytes()) if (HERE / 'SOURCE_SUBJECT.json').exists() else None
    result, rows, fits = analyse((b1, b2), subject=subject)
    (out / 'ANALYSIS.json').write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    write_csv(out / 'POINTS.csv', rows); write_csv(out / 'FITS.csv', fits)
    print(json.dumps(dict(status=result['status'], decision=result.get('decision'), not_overfit=(result.get('not_overfit') or {}).get('gates')), indent=1))
