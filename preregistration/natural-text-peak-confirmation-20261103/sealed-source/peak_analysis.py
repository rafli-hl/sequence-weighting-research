"""Frozen analysis of the peak confirmation (stdlib only). Runs after Runs C1 and C2; never during them.

  python -I -B peak_analysis.py <RUN_C1_DIR> <RUN_C2_DIR> <NEW_OUT_DIR>      -> ANALYSIS.json, POINTS.csv, FITS.csv

Every rule is fixed before any outcome (PROTOCOL.md; owner decisions 20261103-03 and -04). Gains are signed per-sequence
training-loss reductions from each width's own E0; p* is vendor/core.exponent on [0, 8] (text_analysis.fit, a byte copy);
undefined fits stay undefined; the six draws are the only inference unit (df 5). The gap at a readout is the validation NLL
minus the training NLL of that readout (the worker's record).
- Primary, at 3e-4 at E3: INTERIOR_PEAK if the lower limits of the 95% intervals of D1 = p*(512) - p*(384) and
  D2 = p*(512) - p*(768) are both above 0; otherwise NOT_CONFIRMED. Both must pass, so no multiplicity adjustment.
- Control, read only if the primary is INTERIOR_PEAK, at 1e-4 at E3: D4 = p*(512) - p*(768). Lower limit above 0:
  PEAK_AT_BOTH_RATES. Upper limit below 0: RATE_DEPENDENT. Otherwise FALL_NOT_DETECTED_AT_1E-4.
- Pre-registered secondary at E3: D3 = p*(512 at 3e-4) - p*(768 at 1e-4), with the gap caveat stated in advance.
A missing draw makes a contrast UNAVAILABLE and an undefined statistic UNDEFINED. Saturation (the few-epoch rule): a draw is
flagged if a fit its contrast uses is >= 7.999, and its fits are refitted at bound 32; an unresolved refit makes the contrast
SATURATED, and a side that differs at bound 32 makes it SATURATION_SENSITIVE. A primary with an unreadable contrast takes that
status and is not read. NOT_OVERFIT is per arm, from the df 5 interval of validation NLL at E3 minus E2; if it fails for an arm
a reading uses, the label stands and the reading is prefixed. No remedy exists.
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
import fewepoch_analysis as fa
import peak_plan as pk
import peak_worker as pw

EPS = ta.EPS
FINAL = fp.FINAL
DRAWS = pk.GROUPS
XS = {w: math.log2(w) for w in pk.WIDTHS}
ARM_LIST = tuple((w, fp.rate_tag(r)) for w in sorted(pk.ARMS) for r in pk.ARMS[w])


# ------------------------------------------------------------------ loading
def load(runs, pins=pw.PINS, subject=None, allow_fixture=False):
    """Runs C1 and C2 (COMPLETE, FAILED or STOPPED_AT_STARTUP). Per draw and rate tag: its widths' E0 arrays, records and
    arrays, or None if the draw's stage did not complete. Unless allow_fixture (tests only), a FIXTURE approval and any run
    folder other than the plan's are refused."""
    c1, c2 = (Path(r) for r in runs); terms = {}
    for mode, r in (('C1', c1), ('C2', c2)):
        raw = (r / 'TERMINAL.json').read_bytes(); t = json.loads(raw)
        if t.get('kind') != 'peak' or t.get('mode') != mode: raise ValueError(f'Not a peak Run {mode}: {r}')
        if not allow_fixture and (str((t.get('bindings') or {}).get('approval_id', '')).upper().startswith('FIXTURE') or r.resolve() != pw.RUNS[mode].resolve()):
            raise ValueError('Only the real peak runs are analysed: a FIXTURE approval or another run folder is refused')
        if subject is not None and t.get('subject') != subject: raise ValueError('Run subject differs from this analysis source')
        if t.get('status') not in ('COMPLETE', 'FAILED', 'STOPPED_AT_STARTUP'): raise ValueError(f'Run {mode} ended {t.get("status")}')
        bd = t.get('bindings') or {}
        if any(bd.get(k) != pins[k] for k in ('registry_sha256', 'partition_sha256', 'corpus_manifest_sha256', 'fewepoch_registry_sha256')):
            raise ValueError(f'Run {mode} was not bound to the pinned registry, partition and corpus')
        terms[mode] = (t, raw)
    if terms['C2'][0]['bindings'].get('run_c1_terminal_sha256') != pw.sha(terms['C1'][1]): raise ValueError('Run C2 was not admitted on this Run C1')
    draws = {}; want_arms = {str(w): list(r) for w, r in pk.ARMS.items()}
    for mode, r in (('C1', c1), ('C2', c2)):
        for d in pk.RUN_STAGES[mode]:
            rp = r / f'{d}-RECEIPT.json'
            if not rp.exists() or json.loads(rp.read_bytes()).get('status') != 'COMPLETE': draws[d] = None; continue
            inp = json.loads((r / d / 'INPUTS.json').read_bytes()); pre = json.loads((r / d / 'PRETRAINED.json').read_bytes()); n = inp['n_train']
            if inp['arms'] != want_arms or inp['widths'] != sorted(pk.WIDTHS) or n != pk.N_TRAIN and not allow_fixture or inp['readouts'] != list(fp.READOUTS): raise ValueError('Draw inputs differ from the plan: ' + d)
            e0s = {}
            for w in pk.WIDTHS:
                b = pre[str(w)]['E0_arrays']; e0raw = (r / b['path']).read_bytes()
                if len(e0raw) != b['bytes'] or pw.sha(e0raw) != b['sha256'] or len(e0raw) != 4 * (n + plan.N_VALIDATION): raise ValueError('E0 binding differs: ' + b['path'])
                e0 = array('f'); e0.frombytes(e0raw); e0s[w] = e0
            per_tag = {}
            for w, tag in ARM_LIST:
                rec = json.loads((r / d / f'w{w}' / tag / 'record.json').read_bytes()); arr = (r / rec['arrays']['path']).read_bytes(); lr = next(x for x in pk.ARMS[w] if fp.rate_tag(x) == tag)
                if len(arr) != rec['arrays']['bytes'] or pw.sha(arr) != rec['arrays']['sha256']: raise ValueError('Array binding differs: ' + rec['arrays']['path'])
                if rec['layout']['block_epochs'] != list(fp.READOUTS) or rec['layout']['train_rows'] != n or rec['layout']['validation_rows'] != plan.N_VALIDATION or rec['lr'] != lr or rec['width'] != w or rec['tag'] != tag:
                    raise ValueError('Record layout differs: ' + rec['arrays']['path'])
                per_tag.setdefault(tag, dict(weights=inp['weights'], n=n, widths={}))['widths'][w] = dict(e0=e0s[w], raw=arr, record=rec)
            draws[d] = per_tag
    return dict(draws=draws, terminals={m: dict(status=terms[m][0]['status'], sha256=pw.sha(terms[m][1])) for m in terms})


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
            per[d][(w, tag)] = {e: dict(p=ta.fit(arm, w, e)['p'], gap=gap_of(t, e), validation=readout(t, e, 'validation_loss'), train=readout(t, e, 'train_loss')) for e in fp.READOUTS}
    return per


# ------------------------------------------------------------------ contrasts and labels
def side(t):
    if t['interval'][0] > EPS: return 'ABOVE'
    if t['interval'][1] < -EPS: return 'BELOW'
    return 'SPANS'


def contrast_values(per, name, e=FINAL, draws=DRAWS):
    a, b = pk.CONTRASTS[name]; out = {}
    for d in draws:
        x, y = per[d][a][e]['p'], per[d][b][e]['p']; out[d] = None if x is None or y is None else x - y
    return out


def contrast(data, per, name):
    """One contrast at E3: its values, df 5 interval, unadjusted p and side, under the missing-data and saturation rules."""
    missing = [d for d in DRAWS if per[d] is None]
    if missing: return dict(status='UNAVAILABLE', missing=missing)
    vals = contrast_values(per, name); undefined = [d for d in DRAWS if vals[d] is None]
    if undefined: return dict(status='UNDEFINED', undefined=undefined, values=vals)
    t = fa.test([vals[d] for d in DRAWS]); s = side(t); out = dict(status=s, side=s, values=vals, interval=t); arms = pk.CONTRASTS[name]
    flagged = [d for d in DRAWS if any(per[d][arm][FINAL]['p'] >= plan.P_UPPER for arm in arms)]; out['flagged'] = flagged
    if not flagged: out['S32'] = dict(required=False, reason='NO_FLAGGED_DRAWS'); return out
    v32, unresolved = dict(vals), 0
    for d in flagged:
        ps = []
        for w, tag in arms:
            arm = data['draws'][d][tag]; r = ta.exponent_upper(arm['weights'], ta.gains(arm, w, FINAL), ta.S32_UPPER); ps.append(r['p']); unresolved += r['p'] is None or r['p'] >= ta.S32_UPPER - 0.001
        v32[d] = None if any(p is None for p in ps) else ps[0] - ps[1]
    computable = not unresolved and all(v is not None for v in v32.values())
    out['S32'] = dict(required=True, computable=computable, unresolved_refits=unresolved)
    if not computable: out['status'] = 'SATURATED'; return out
    t32 = fa.test([v32[d] for d in DRAWS]); s32 = side(t32); out['S32'].update(interval=t32, side=s32)
    if s32 != s: out['status'] = 'SATURATION_SENSITIVE'
    return out


def worst(statuses):
    return next((s for s in pk.UNREADABLE if s in statuses), None)


def decide(contrasts):
    """The primary from D1 and D2; the control from D4, read only if the primary is INTERIOR_PEAK."""
    prim = [contrasts[k]['status'] for k in pk.PRIMARY_CONTRASTS]; bad = worst(prim)
    primary = bad if bad else 'INTERIOR_PEAK' if all(s == 'ABOVE' for s in prim) else 'NOT_CONFIRMED'
    if primary != 'INTERIOR_PEAK': return primary, 'NOT_READ'
    s = contrasts[pk.CONTROL_CONTRAST]['status']
    return primary, (s if s in pk.UNREADABLE else dict(ABOVE='PEAK_AT_BOTH_RATES', BELOW='RATE_DEPENDENT', SPANS='FALL_NOT_DETECTED_AT_1E-4')[s])


def not_overfit(data):
    if any(data['draws'].get(d) is None for d in DRAWS): return dict(status='UNAVAILABLE')
    out = {}
    for w, tag in ARM_LIST:
        dv = [readout(data['draws'][d][tag]['widths'][w], FINAL, 'validation_loss') - readout(data['draws'][d][tag]['widths'][w], fp.PREVIOUS, 'validation_loss') for d in DRAWS]
        t = ta.tint(dv); out[f'{w}|{tag}'] = dict(interval=t, label='NOT_OVERFIT' if t['interval'][1] < -EPS else 'OVERFIT' if t['interval'][0] > EPS else 'PLATEAU')
    gates = {k: all(out[f'{w}|{tag}']['label'] == 'NOT_OVERFIT' for w, tag in v) for k, v in pk.GATE_ARMS.items()}
    return dict(status='COMPUTED', arms=out, all_arms=all(v['label'] == 'NOT_OVERFIT' for v in out.values()), gates=gates, failing={k: [f'{w} at {tag}' for w, tag in v if out[f'{w}|{tag}']['label'] != 'NOT_OVERFIT'] for k, v in pk.GATE_ARMS.items()})


# ------------------------------------------------------------------ readings (PROTOCOL.md section 7)
SCOPE = ('The few-epoch question is read only where the arms a reading uses were still improving their validation loss from E2 to E3 (NOT_OVERFIT). The models are small (depth 4, at most 34.7 M parameters) and this is one corpus family at one recipe. '
         'No reading claims a mechanism or a scaling law.')
PEAK = 'At 3e-4 at E3, p* at 512 is above p* at 384 and at 768 on fresh draws (INTERIOR_PEAK). This is an ordering of three rungs; it does not place the peak between rungs.'
PRIMARY_TEXT = dict(INTERIOR_PEAK=PEAK, NOT_CONFIRMED='No peak confirmed: at 3e-4 at E3, the lower limits of 512 - 384 and 512 - 768 are not both above 0 (NOT_CONFIRMED). This is not a claim of absence. The peak is not confirmed, and the earlier pattern stays descriptive.')
CONTROL_TEXT = {'PEAK_AT_BOTH_RATES': "Peak at both rates (PEAK_AT_BOTH_RATES): 512 also stays above 768 at 1e-4. The fall from 512 to 768 is not explained by 768's rate, at the two rates tested. 384 was not trained at 1e-4, so the rise to 512 is measured at 3e-4 only.",
                'RATE_DEPENDENT': 'Peak at 3e-4 only (RATE_DEPENDENT): at 1e-4, 768 is above 512, so the fall seen at 3e-4 is rate-dependent, at the two rates tested.',
                'FALL_NOT_DETECTED_AT_1E-4': 'Peak at 3e-4 (FALL_NOT_DETECTED_AT_1E-4): fall from 512 to 768 at 1e-4 not detected; not a claim of absence; not read as rate-dependent.'}
PREMISE = "Premise of the control: on these draws validation NLL at 768 is not detectably lower at 1e-4 than at 3e-4, so 1e-4 is not shown to be 768's better rate here."
GAP_CAVEAT = (f"D3, a pre-registered secondary: p* at 512 at 3e-4 minus p* at 768 at 1e-4, at E3. It is not a test of the rate account, because it compares two rates. Stated in advance: on t00 the gap at 512 at 3e-4 ({pk.T00_GAP['w512_high']}) is above the gap at 768 at 1e-4 ({pk.T00_GAP['w768_low']}), "
              'so if p* simply tracked the gap, D3 would be above 0 with no turn at 768.')
DISCLOSURE = ('Data: never-assigned WikiText-103 training articles, with text duplicates of assigned articles and repeats inside the pool removed; new seeds; no new tuning. The validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies. '
              'The hypothesis was formed after seeing d01-d10, and the idea for the control also came after seeing p*; the rate 1e-4 comes from validation NLL on t00 only.')


def power_line():
    p = pk.POWER
    return f"Power stated in advance (six draws; from effects seen in d01-d10): {p['seen']} at the seen effects, {p['half']} at half of them; with the sd at its upper 95% limit, {p['seen_sd_upper']} and {p['half_sd_upper']}."


def readings(primary, control, gate, premise_failed=False):
    out = [SCOPE]
    def prefix(label, *keys):
        failing = [x for k in keys for x in gate['failing'][k]] if gate.get('status') == 'COMPUTED' else []
        return f"{label} is not read as a few-epoch test: {', '.join(failing)} not still improving from E2 to E3 (NOT_OVERFIT failed). " if failing else ''
    if primary in pk.UNREADABLE: out.append(f'The primary is {primary}: it is not read.')
    else:
        text = PRIMARY_TEXT[primary]
        if primary == 'NOT_CONFIRMED': text += ' ' + power_line()
        out.append(prefix(primary, 'primary') + text)
    if control == 'NOT_READ': out.append('The control (512 against 768, both at 1e-4) is read only if the primary is INTERIOR_PEAK: it is not read.')
    elif control in pk.UNREADABLE: out.append(f'The control is {control}: it is not read.')
    else: out.append(prefix(control, 'primary', 'control') + CONTROL_TEXT[control])      # the control is read only if the primary is
    if premise_failed and control not in ('NOT_READ',) + pk.UNREADABLE: out.append(PREMISE)
    out.append(GAP_CAVEAT); out.append(DISCLOSURE)
    return out


# ------------------------------------------------------------------ secondaries (non-gating; no multiplicity adjustment)
def paired(per, a, b, key, e=FINAL):
    """Interval over the draws of (key at arm a) - (key at arm b); None if a value is missing."""
    vals = [per[d][a][e][key] - per[d][b][e][key] if per[d][a][e][key] is not None and per[d][b][e][key] is not None else None for d in DRAWS]
    return None if any(v is None for v in vals) else dict(values=dict(zip(DRAWS, vals)), interval=ta.tint(vals))


def rate_effects(per):
    """Per width with two arms, 1e-4 minus 3e-4 at E3: p*, validation NLL, training NLL and the gap."""
    out = {}
    for w in (512, 768):
        lo, hi = (w, pk.TAG_LOW), (w, pk.TAG_HIGH)
        out[str(w)] = {k: paired(per, lo, hi, k) for k in ('p', 'validation', 'train', 'gap')}
    return out


def by_readout(per):
    out = {}
    for e in fp.READOUTS:
        row = dict(contrasts={})
        for name in pk.CONTRASTS:
            vals = contrast_values(per, name, e); row['contrasts'][name] = None if any(v is None for v in vals.values()) else dict(values=vals, interval=ta.tint(list(vals.values())))
        row['panel'] = {f'{w}|{tag}': {k: (None if any(per[d][(w, tag)][e][k] is None for d in DRAWS) else math.fsum(per[d][(w, tag)][e][k] for d in DRAWS) / len(DRAWS)) for k in ('p', 'gap', 'validation', 'train')} for w, tag in ARM_LIST}
        high = {d: {w: per[d][(w, pk.TAG_HIGH)][e]['p'] for w in pk.WIDTHS} for d in DRAWS}
        if not any(v is None for x in high.values() for v in x.values()):
            row['per_draw_argmax_at_3e-4'] = {d: max(pk.WIDTHS, key=lambda w: (high[d][w], -w)) for d in DRAWS}
            slopes = [ta.ols_slope([XS[w] for w in pk.WIDTHS], [high[d][w] for w in pk.WIDTHS]) for d in DRAWS]; row['fall_at_3e-4'] = dict(values=dict(zip(DRAWS, slopes)), interval=ta.tint(slopes))
        out[f'E{e}'] = row
    return out


def matched_gap(per):
    """M on these draws (few-epoch definition, at 3e-4): p* at 768 minus at 384 at matched gap. A secondary here, with its confound."""
    vals, details = {}, {}
    for d in DRAWS:
        a, b = per[d][(384, pk.TAG_HIGH)], per[d][(768, pk.TAG_HIGH)]; p3 = [a[e]['p'] for e in fp.READOUTS]; p7 = [b[e]['p'] for e in fp.READOUTS]
        if any(v is None for v in p3 + p7): vals[d] = None; details[d] = dict(reason='UNDEFINED_FIT'); continue
        m = fa.matched([a[e]['gap'] for e in fp.READOUTS], p3, [b[e]['gap'] for e in fp.READOUTS], p7); vals[d] = m['value']; details[d] = m
    undefined = [d for d in DRAWS if vals[d] is None]
    return dict(status='UNDEFINED', undefined=undefined, details=details) if undefined else dict(status='COMPUTED', values=vals, details=details, interval=ta.tint(list(vals.values())), note='At matched gap the larger width has had fewer epochs, so a nonzero M is also what p* gives if it depends on training progress rather than on the gap.')


def losses(data):
    out = {}; avail = [data['draws'][d] for d in DRAWS if data['draws'].get(d) is not None]
    if not avail: return out
    for w, tag in ARM_LIST:
        ts = [dd[tag]['widths'][w] for dd in avail]; ep = [x for t in ts for x in t['record']['epochs']]; key = f'{w}|{tag}'
        out[key] = {f'E{e}': dict(train=math.fsum(readout(t, e, 'train_loss') for t in ts) / len(ts), validation=math.fsum(readout(t, e, 'validation_loss') for t in ts) / len(ts)) for e in fp.READOUTS}
        out[key]['clipping'] = dict(clip_fraction_mean=math.fsum(x['clip_fraction'] for x in ep) / len(ep), gradient_norm_mean=math.fsum(x['gradient_norm_mean'] for x in ep) / len(ep), gradient_norm_max=max(x['gradient_norm_max'] for x in ep))
    for w in pk.WIDTHS:
        e0 = [dd[pk.TAG_HIGH]['widths'][w]['e0'] for dd in avail]; n = avail[0][pk.TAG_HIGH]['n']
        out[f'{w}|E0'] = dict(train=math.fsum(math.fsum(a[:n]) / n for a in e0) / len(e0), validation=math.fsum(math.fsum(a[n:]) / (len(a) - n) for a in e0) / len(e0))
    return out


def analyse(runs, **kw):
    ta._FITS.clear(); data = load(runs, **kw); avail = [d for d in DRAWS if data['draws'].get(d) is not None]
    if not avail:
        return dict(status='UNAVAILABLE', terminals=data['terminals'], decision=dict(primary='UNAVAILABLE', control='NOT_READ'), readings=[SCOPE, 'The primary is UNAVAILABLE: no draw completed.', DISCLOSURE]), [], []
    full = {d: (data['draws'][d] if d in avail else None) for d in DRAWS}; per = points(dict(data, draws=full)); gate = not_overfit(data)
    contrasts = {name: contrast(data, per, name) for name in pk.CONTRASTS}; primary, control = decide(contrasts); fits, rows = [], []
    for d in avail:
        for w, tag in ARM_LIST:
            arm = data['draws'][d][tag]
            for e in fp.READOUTS:
                fits.append(dict(draw=d, width=w, tag=tag, epoch=e, **ta.fit(arm, w, e))); v = per[d][(w, tag)][e]; rows.append(dict(draw=d, width=w, tag=tag, epoch=e, p=v['p'], gap=v['gap'], validation=v['validation'], train=v['train']))
    bound = dict(upper=sum(bool(f.get('upper')) for f in fits), lower=sum(bool(f.get('lower')) for f in fits), undefined=sum(f['p'] is None for f in fits))
    complete = len(avail) == len(DRAWS); effects = rate_effects(per) if complete else None
    premise_failed = complete and effects['768']['validation']['interval']['interval'][1] >= -EPS
    result = dict(status='COMPLETE' if complete else 'PARTIAL_UNAVAILABLE_DRAWS', terminals=data['terminals'], draws_available=avail, arms={str(w): list(r) for w, r in pk.ARMS.items()}, readouts=list(fp.READOUTS), decision=dict(primary=primary, control=control), readings=readings(primary, control, gate, premise_failed),
                  contrasts=contrasts, not_overfit=gate, gap_caveat_stated_in_advance=dict(pk.T00_GAP), power_stated_in_advance=dict(pk.POWER), fit_bounds=bound, losses=losses(data),
                  note='The primary and the control are pre-registered; D3 is a pre-registered secondary; NOT_OVERFIT is the pre-registered manipulation check; every other section is secondary or descriptive, with no multiplicity adjustment.')
    if complete: result.update(rate_effects=effects, by_readout=by_readout(per), matched_gap=matched_gap(per))
    return result, rows, fits


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit('usage: peak_analysis.py <RUN_C1_DIR> <RUN_C2_DIR> <NEW_OUT_DIR>')
    c1, c2, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    subject = pw.sha((HERE / 'SOURCE_SUBJECT.json').read_bytes()) if (HERE / 'SOURCE_SUBJECT.json').exists() else None
    result, rows, fits = analyse((c1, c2), subject=subject)
    out.mkdir(parents=False, exist_ok=False)
    (out / 'ANALYSIS.json').write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    write_csv(out / 'POINTS.csv', rows); write_csv(out / 'FITS.csv', fits)
    print(json.dumps(dict(status=result['status'], decision=result.get('decision'), not_overfit=(result.get('not_overfit') or {}).get('gates')), indent=1))
