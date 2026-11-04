"""Frozen analysis of the late-turn confirmation (stdlib only). Runs after the run; never during it.

  python -I -B lateturn_analysis.py <RUN_DIR> <NEW_OUT_DIR>      -> ANALYSIS.json, POINTS.csv, FITS.csv

Every rule is fixed before any outcome (PROTOCOL.md; owner decisions 20261031-02). Four fresh draws f01-f04, widths 256,
384, 512 and 768, all trained in the run at 3e-5. Gains are signed per-sequence training-loss reductions from each width's
own E0; p* is vendor/core.exponent on [0, 8] (text_analysis.fit, a byte copy); undefined fits stay undefined; the four
draws are the only inference unit (df 3, t = 3.182446305). The primaries, each from one point per draw:
- P1: the OLS slope of p* on log2 width over 384, 512, 768 at E32;
- P3: the peak shift S = L(E8) - L(E32) in doublings, with L the location of revision 05's sealed
  text_analysis.peak_location on the study ladder (argmax, ties to the smaller width; an interior argmax refined by the
  vertex of the three-point parabola in log2 width, clamped to its bracket; an argmax at either end recorded at that rung).
  The reading states the censoring from the counts (review 1, finding 1): S is a conservative lower bound only if no E8
  peak is at 256 and no E32 peak is at 768, and only if each censored curve continues beyond its ladder end in the
  direction it leaves it (at E8, still rising at 768; at E32, still falling with width at 256); otherwise S is not a
  lower bound for those draws, and so neither is the four-draw S (confirmation of review 1, new finding 1);
- P2: the P1 statistic at E24.
Labels from the df-3 two-sided 95% t interval of the four draw values (below 0 / above 0 / otherwise). Read in the fixed
sequence P1 -> P3 -> P2: a later primary is read as confirmed only if every earlier one gave its predicted label.
Saturation (revision 05's rule for single-point primaries): a draw is flagged if any fit its statistic uses is >= 7.999;
its fits are then refitted at bound 32 (S32, always required then); an unresolved refit (>= 31.999) or an undefined
refitted statistic makes the primary SATURATED, a changed S32 label SATURATION_SENSITIVE. A missing draw makes a primary
UNAVAILABLE and an undefined statistic UNDEFINED; there is no replacement draw. If the four draw values are equal (sd at
most 1e-9, the interval tolerance), the interval is that value and the label follows its sign; the primary is flagged degenerate and the reading says so
(review 1, finding 4).
Only the real run is analysed: load() refuses a FIXTURE approval and any run folder other than the plan's, unless a test
passes allow_fixture=True (review 1, finding 7).
"""
import csv, json, math, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import text_plan as plan
import text_analysis as ta
import lateturn_plan as lp
import lateturn_worker as lw

EPS = ta.EPS
XS = [math.log2(w) for w in lp.WIDTHS]
TURN_IDX = [lp.WIDTHS.index(w) for w in lp.TURN_WIDTHS]
UNREADABLE = ('UNAVAILABLE', 'UNDEFINED', 'SATURATED', 'SATURATION_SENSITIVE')
REGIME = ("The late-epoch pattern is tested at E24 and E32, long after the best validation loss of 384-768, which was at E4 on the seen "
          "draws d01-d10: a heavily overfit regime, unlike Jane Street's 3-epoch setting. A confirmation supports the pattern in this regime only.")
TEXT_CHECK = (f"{len(lp.TEXT_CHECK_V02['train_articles_in_fresh_groups'])} training articles in f01-f04 were used in September by the public-text check (Pythia-70M fine-tuning, work/runs/text-check-v02). "
              "The confirmation's models are trained from scratch with the study's own tokenizer and never see that check's model or outputs.")
DEGENERATE = 'All four draw values are equal to within 1e-9 (sd <= 1e-9), so the interval is that single value and the label follows its sign.'


# ------------------------------------------------------------------ per-draw statistics
def turn(p):
    ps = [p[k] for k in TURN_IDX]
    return None if any(v is None for v in ps) else ta.ols_slope([XS[k] for k in TURN_IDX], ps)


def location(p):
    """(rung, L in log2 width, 'interior' | 'boundary') from text_analysis.peak_location on the study ladder; None if any fit
    is undefined."""
    return None if any(v is None for v in p) else ta.peak_location(p, XS)


def shift(p8, p32):
    a, b = location(p8), location(p32)
    return None if a is None or b is None else a[1] - b[1]


def value(name, ps):
    """ps: {epoch: fits in ladder order}."""
    spec = lp.PRIMARIES[name]
    return turn(ps[spec['epoch']]) if spec['kind'] == 'turn' else shift(ps[spec['epochs'][0]], ps[spec['epochs'][1]])


def epochs_of(name):
    spec = lp.PRIMARIES[name]; return (spec['epoch'],) if spec['kind'] == 'turn' else tuple(spec['epochs'])


def used_rungs(name): return TURN_IDX if lp.PRIMARIES[name]['kind'] == 'turn' else list(range(len(lp.WIDTHS)))


def label(kind, t):
    below, above, other = lp.LABELS[kind]
    if t['interval'][1] < -EPS: return below
    if t['interval'][0] > EPS: return above
    return other


def primary(name, per, refit=None):
    """per[d]: {epoch: dict(p=fits in ladder order, gap=...)}, or None if the draw's stage did not complete."""
    kind = lp.PRIMARIES[name]['kind']; eps = epochs_of(name); ks = used_rungs(name)
    missing = [d for d in lp.DRAWS if per.get(d) is None]
    if missing: return dict(label='UNAVAILABLE', missing=missing)
    vals = {d: value(name, {e: per[d][e]['p'] for e in eps}) for d in lp.DRAWS}
    undefined = [d for d in lp.DRAWS if vals[d] is None]
    if undefined: return dict(label='UNDEFINED', undefined=undefined)
    t = ta.tint([vals[d] for d in lp.DRAWS]); base = label(kind, t)
    flagged = [d for d in lp.DRAWS if any(per[d][e]['p'][k] >= plan.P_UPPER for e in eps for k in ks)]
    sens = dict(required=False, reason='NO_FLAGGED_DRAWS')
    if flagged:
        refits = {d: {e: refit(d, e)['p'] for e in eps} for d in flagged}
        unresolved = sum(any(refits[d][e][k] >= ta.S32_UPPER - 0.001 for e in eps for k in ks) for d in flagged)
        v32 = {d: (value(name, refits[d]) if d in refits else vals[d]) for d in lp.DRAWS}
        if unresolved or any(v is None for v in v32.values()): sens = dict(required=True, computable=False, unresolved_refits=unresolved, flagged=flagged)
        else:
            t32 = ta.tint([v32[d] for d in lp.DRAWS]); sens = dict(required=True, computable=True, label=label(kind, t32), interval=t32, flagged=flagged)
    final = base if not sens['required'] else 'SATURATED' if not sens['computable'] else 'SATURATION_SENSITIVE' if sens['label'] != base else base
    out = dict(label=final, primary_label=base, interval=t, degenerate=t['sd'] <= EPS, draw_values=vals, epochs=list(eps), widths=[lp.WIDTHS[k] for k in ks], S32=sens)
    if kind == 'shift':
        locs = {d: {f'E{e}': dict(zip(('rung_index', 'location_log2', 'kind'), location(per[d][e]['p']))) for e in eps} for d in lp.DRAWS}
        for v in locs.values():
            for r in v.values(): r['rung_width'] = lp.WIDTHS[r['rung_index']]
        e8, e32 = (f'E{e}' for e in eps)
        count = lambda e, w: sum(locs[d][e]['rung_width'] == w for d in lp.DRAWS)
        c = dict(e8_top=count(e8, lp.WIDTHS[-1]), e8_bottom=count(e8, lp.WIDTHS[0]), e32_top=count(e32, lp.WIDTHS[-1]), e32_bottom=count(e32, lp.WIDTHS[0]))
        c['bound'] = ('NOT_A_BOUND' if c['e8_bottom'] or c['e32_top'] else 'NOT_CENSORED' if not (c['e8_top'] or c['e32_bottom']) else 'LOWER_BOUND_IF_CURVES_CONTINUE')
        out.update(locations=locs, censoring=c)
    return out


def censoring_text(c):
    """The pre-registered censoring sentence of P3 (PROTOCOL.md section 8; review 1, finding 1)."""
    counts = (f"A peak at a ladder end is recorded at that rung. At E8 the peak was at the top rung (768) in {c['e8_top']} and at the bottom rung (256) in "
              f"{c['e8_bottom']} of 4 draws; at E32, at the top rung in {c['e32_top']} and at the bottom rung in {c['e32_bottom']}.")
    if c['bound'] == 'NOT_CENSORED': return counts + ' No peak is at a ladder end, so S is not censored.'
    if c['bound'] == 'LOWER_BOUND_IF_CURVES_CONTINUE':
        return counts + (' S is therefore a conservative lower bound on the shift, provided each censored curve continues beyond its ladder end in the direction '
                         'it leaves it (at E8, still rising at 768; at E32, still falling with width at 256). A peak above 768 cannot be tested on the 4 GiB card.')
    return counts + (' An E8 peak at 256 or an E32 peak at 768 is censored in the direction that can overstate the shift, so S is not a lower bound '
                     'for those draws, and the four-draw S and its interval are therefore not a lower bound on the shift.')


def sequence(prims):
    """The fixed sequence P1 -> P3 -> P2 (owner decisions 20261031-02, item 4)."""
    out, open_ = {}, True
    for name in lp.SEQUENCE:
        ok = open_ and prims[name]['label'] == lp.PREDICTED[name]
        out[name] = dict(label=prims[name]['label'], predicted=lp.PREDICTED[name], read_as_confirmation=open_, confirmed=ok)
        open_ = ok
    return out


TEXT = dict(
    P1={'TURNS_DOWN': 'P1 confirmed: at E32, p* falls with width over 384-768 on the four fresh draws.',
        'CONTINUES_RISING': 'P1 not confirmed: at E32, p* rises with width over 384-768 on the fresh draws, contrary to the seen secondary.',
        'INCONCLUSIVE': 'P1 not confirmed: no fall or rise over 384-768 is detected at E32 with four draws. This is not a claim of absence.'},
    P3={'SHIFTS_TO_SMALLER_WIDTH': 'P3 confirmed: the peak location moves to a smaller width from E8 to E32.',
        'SHIFTS_TO_LARGER_WIDTH': 'P3 not confirmed: the peak location moves to a larger width from E8 to E32.',
        'NO_DETECTED_SHIFT': 'P3 not confirmed: no shift of the peak location from E8 to E32 is detected with four draws. This is not a claim of absence.'},
    P2={'TURNS_DOWN': 'P2 confirmed: at E24, p* falls with width over 384-768 on the four fresh draws.',
        'CONTINUES_RISING': 'P2 not confirmed: at E24, p* rises with width over 384-768 on the fresh draws, contrary to the seen secondary.',
        'INCONCLUSIVE': 'P2 not confirmed: no fall or rise over 384-768 is detected at E24 with four draws. This is not a claim of absence.'})


def readings(prims, seq):
    """The pre-registered reading text (PROTOCOL.md section 8)."""
    out = [REGIME]
    for name in lp.SEQUENCE:
        lab = prims[name]['label']; pw = lp.POWER[name]
        power = f"Power stated in advance (four draws, 95%): {pw['observed']} at the seen effect, {pw['conservative']} conservative, {pw['halved']} halved."
        if lab in UNREADABLE: text = f'{name} is {lab}: it is not read, and no later primary of the sequence is read as a confirmation.'
        else:
            text = TEXT[name][lab]
            if not seq[name]['read_as_confirmation']: text = f'{name} ({lab}) is reported but not read as a confirmation, because an earlier primary of the fixed sequence was not confirmed.'
            if lab in ('INCONCLUSIVE', 'NO_DETECTED_SHIFT'):
                text += ('' if seq[name]['read_as_confirmation'] else ' Not detected with four draws; this is not a claim of absence.') + ' ' + power     # review 1, finding 3
            if prims[name].get('degenerate'): text += ' ' + DEGENERATE
        if name == 'P3' and 'censoring' in prims[name]: text += ' ' + censoring_text(prims[name]['censoring'])
        out.append(text)
    out.append(TEXT_CHECK)
    return out


# ------------------------------------------------------------------ loading
def sha(b): return lw.sha(b)


def _arrays(path, rec, n):
    raw = Path(path).read_bytes()
    if len(raw) != rec['arrays']['bytes'] or sha(raw) != rec['arrays']['sha256']: raise ValueError('Array binding differs: ' + rec['arrays']['path'])
    if rec['layout']['block_epochs'] != list(plan.READOUTS) or rec['layout']['train_rows'] != n or rec['layout']['validation_rows'] != plan.N_VALIDATION: raise ValueError('Record layout differs: ' + rec['arrays']['path'])
    return raw


def _e0(path, binding, n):
    raw = Path(path).read_bytes()
    if len(raw) != binding['bytes'] or sha(raw) != binding['sha256'] or len(raw) != 4 * (n + plan.N_VALIDATION): raise ValueError('E0 binding differs: ' + binding['path'])
    a = array('f'); a.frombytes(raw); return a


def load(run, pins=lw.PINS, subject=None, allow_fixture=False):
    """The run (COMPLETE, FAILED or STOPPED_AT_STARTUP). Returns the start-up decision and, per draw, the four trajectories
    (or None if the draw's stage did not complete). Unless allow_fixture (tests only), a FIXTURE approval and any run folder
    other than the plan's are refused."""
    run = Path(run)
    term_raw = (run / 'TERMINAL.json').read_bytes(); term = json.loads(term_raw)
    if term.get('kind') != 'lateturn' or term.get('mode') != 'LATETURN': raise ValueError('Not a late-turn confirmation run')
    if not allow_fixture and (str((term.get('bindings') or {}).get('approval_id', '')).upper().startswith('FIXTURE') or run.resolve() != lw.RUN.resolve()):
        raise ValueError('Only the real late-turn run is analysed: a FIXTURE approval or another run folder is refused')
    if subject is not None and term.get('subject') != subject: raise ValueError('Run subject differs from this analysis source')
    if term.get('status') not in ('COMPLETE', 'FAILED', 'STOPPED_AT_STARTUP'): raise ValueError('Run ended ' + str(term.get('status')))
    b = term.get('bindings') or {}
    if (b.get('registry_sha256'), b.get('partition_sha256'), b.get('corpus_manifest_sha256')) != (pins['registry_sha256'], pins['fresh_partition_sha256'], pins['corpus_manifest_sha256']):
        raise ValueError('Run was not bound to the pinned registry, partition and corpus')
    bound = term.get('benchmark')
    if not bound: return dict(decision=None, terminal=term, terminal_sha256=sha(term_raw), draws={d: None for d in lp.DRAWS})
    braw = (run / 'BENCHMARK.json').read_bytes()
    if len(braw) != bound['bytes'] or sha(braw) != bound['sha256']: raise ValueError('Benchmark differs from its binding')
    bench = json.loads(braw); decision, reason = lw.startup_rule(bench['benchmark']['architectures'], bench['failure'])
    if [decision, reason] != [bench['startup']['decision'], bench['startup']['reason']] or (term.get('startup') or {}) != dict(decision=decision, reason=reason):
        raise ValueError('Start-up decision does not re-derive from the bound benchmark')
    draws = {}
    for d in lp.DRAWS:
        rp = run / f'{d}-RECEIPT.json'
        if decision != 'GO' or not rp.exists() or json.loads(rp.read_bytes()).get('status') != 'COMPLETE': draws[d] = None; continue
        inp = json.loads((run / d / 'INPUTS.json').read_bytes()); pre = json.loads((run / d / 'PRETRAINED.json').read_bytes())
        if inp['learning_rate'] != lp.LR or inp['widths'] != list(lp.WIDTHS): raise ValueError('Draw inputs differ from the plan: ' + d)
        n = inp['n_train']; widths = {}
        for w in lp.WIDTHS:
            rec = json.loads((run / d / f'w{w}' / lp.TAG / 'record.json').read_bytes())
            if rec['width'] != w or rec['lr'] != lp.LR: raise ValueError(f'Not width {w} at 3e-5: ' + d)
            widths[w] = dict(e0=_e0(run / pre[str(w)]['E0_arrays']['path'], pre[str(w)]['E0_arrays'], n), raw=_arrays(run / rec['arrays']['path'], rec, n), record=rec)
        draws[d] = dict(weights=inp['weights'], n=n, widths=widths)
    return dict(decision=decision, reason=reason, terminal=term, terminal_sha256=sha(term_raw), benchmark_sha256=sha(braw), draws=draws)


def gap(t, epoch):
    r = next(x for x in t['record']['readouts'] if x['epoch'] == epoch)
    return r['validation_loss'] - r['train_loss']


def points(data):
    """per[d][epoch] = fits over the ladder (None where undefined) and gaps, at every readout epoch."""
    per = {}
    for d in lp.DRAWS:
        dd = data['draws'].get(d)
        per[d] = None if dd is None else {e: dict(p=[ta.fit(dd, w, e)['p'] for w in lp.WIDTHS], gap=[gap(dd['widths'][w], e) for w in lp.WIDTHS]) for e in plan.READOUTS}
    return per


def refitter(data):
    def refit(d, e):
        dd = data['draws'][d]
        return dict(p=[ta.exponent_upper(dd['weights'], ta.gains(dd, w, e), ta.S32_UPPER)['p'] for w in lp.WIDTHS])
    return refit


# ------------------------------------------------------------------ secondaries (non-gating)
def by_epoch(per):
    """Per readout epoch: the four-draw panel p* curve and gap, the panel and per-draw argmax, the turn statistic (df-3
    interval) and the peak location L (descriptive)."""
    out = {}
    for e in plan.READOUTS:
        if any(per[d] is None for d in lp.DRAWS): out[f'E{e}'] = dict(label='UNAVAILABLE'); continue
        pts = {d: per[d][e] for d in lp.DRAWS}
        if any(v is None for p in pts.values() for v in p['p']): out[f'E{e}'] = dict(label='UNDEFINED'); continue
        curve = [math.fsum(pts[d]['p'][k] for d in lp.DRAWS) / len(lp.DRAWS) for k in range(len(lp.WIDTHS))]
        gaps = [math.fsum(pts[d]['gap'][k] for d in lp.DRAWS) / len(lp.DRAWS) for k in range(len(lp.WIDTHS))]
        argmax = lambda c: lp.WIDTHS[max(range(len(c)), key=lambda k: (c[k], -k))]
        tv = [turn(pts[d]['p']) for d in lp.DRAWS]; locs = {d: location(pts[d]['p'])[1] for d in lp.DRAWS}
        out[f'E{e}'] = dict(curve=curve, gap=gaps, argmax_width=argmax(curve), per_draw_argmax={d: argmax(pts[d]['p']) for d in lp.DRAWS},
                            turn=dict(interval=ta.tint(tv), label=label('turn', ta.tint(tv))), location_log2=locs, location_mean_log2=math.fsum(locs.values()) / len(locs))
    return out


def averaged_turn(per):
    """The one-rate study's turn-down statistic (mean over E4-E32 of the 384-768 slope per draw), for comparison only."""
    if any(per[d] is None for d in lp.DRAWS): return dict(label='UNAVAILABLE')
    vals = []
    for d in lp.DRAWS:
        v = [turn(per[d][e]['p']) for e in plan.PRIMARY_EPOCHS]
        if any(x is None for x in v): return dict(label='UNDEFINED', draw=d)
        vals.append(math.fsum(v) / len(v))
    t = ta.tint(vals); return dict(interval=t, label=label('turn', t), note='Descriptive: the seen study\'s epoch-averaged turn-down on the fresh draws; not a primary.')


def losses(data):
    out = {}
    avail = [data['draws'][d] for d in lp.DRAWS if data['draws'].get(d) is not None]
    if not avail: return out
    for w in lp.WIDTHS:
        for e in plan.READOUTS:
            rows = [next(r for r in dd['widths'][w]['record']['readouts'] if r['epoch'] == e) for dd in avail]
            tr = math.fsum(r['train_loss'] for r in rows) / len(rows); va = math.fsum(r['validation_loss'] for r in rows) / len(rows)
            out[f'{w}|E{e}'] = dict(train=tr, validation=va, gap=va - tr, n=len(rows))
        e0 = [dd['widths'][w]['e0'] for dd in avail]; n = avail[0]['n']
        out[f'{w}|E0'] = dict(train=math.fsum(math.fsum(a[:n]) / n for a in e0) / len(e0), validation=math.fsum(math.fsum(a[n:]) / (len(a) - n) for a in e0) / len(e0))
        series = [(0, out[f'{w}|E0']['validation'])] + [(e, out[f'{w}|E{e}']['validation']) for e in plan.READOUTS]
        out[f'{w}|validation_minimum'] = dict(zip(('epoch', 'validation'), min(series, key=lambda x: (x[1], x[0]))))
        ep = [x for dd in avail for x in dd['widths'][w]['record']['epochs']]
        out[f'{w}|clipping'] = dict(clip_fraction_mean=math.fsum(x['clip_fraction'] for x in ep) / len(ep), gradient_norm_mean=math.fsum(x['gradient_norm_mean'] for x in ep) / len(ep),
                                    gradient_norm_max=max(x['gradient_norm_max'] for x in ep))
    return out


def analyse(run, **kw):
    ta._FITS.clear(); data = load(run, **kw)
    if data['decision'] != 'GO' or all(data['draws'].get(d) is None for d in lp.DRAWS):
        prim = {k: dict(label='UNAVAILABLE', reason='NO_COMPLETED_DRAW') for k in lp.SEQUENCE}; seq = sequence(prim)
        return dict(status='UNAVAILABLE', run_status=data['terminal']['status'], startup=data['terminal'].get('startup'), primaries=prim, sequence=seq, readings=readings(prim, seq)), [], []
    per = points(data); refit = refitter(data)
    prim = {k: primary(k, per, refit) for k in lp.SEQUENCE}; seq = sequence(prim)
    avail = [d for d in lp.DRAWS if data['draws'][d] is not None]
    fits = [dict(draw=d, width=w, epoch=e, lr=lp.LR, **ta.fit(data['draws'][d], w, e)) for d in avail for w in lp.WIDTHS for e in plan.READOUTS]
    rows = [dict(draw=d, epoch=e, **{f'p_{w}': v for w, v in zip(lp.WIDTHS, per[d][e]['p'])}, **{f'gap_{w}': v for w, v in zip(lp.WIDTHS, per[d][e]['gap'])},
                 turn=turn(per[d][e]['p']), location_log2=(location(per[d][e]['p']) or (None, None))[1]) for d in avail for e in plan.READOUTS]
    bound = dict(upper=sum(bool(f.get('upper')) for f in fits), lower=sum(bool(f.get('lower')) for f in fits), undefined=sum(f['p'] is None for f in fits))
    result = dict(status='COMPLETE' if len(avail) == len(lp.DRAWS) else 'PARTIAL_UNAVAILABLE_DRAWS', run_status=data['terminal']['status'], draws_available=avail,
                  run_terminal_sha256=data['terminal_sha256'], run_benchmark_sha256=data['benchmark_sha256'], startup=dict(decision=data['decision'], reason=data['reason']),
                  widths=list(lp.WIDTHS), decision={k: prim[k]['label'] for k in lp.SEQUENCE}, sequence=seq, readings=readings(prim, seq), primaries=prim,
                  fit_bounds=bound, by_epoch=by_epoch(per), epoch_averaged_turn=averaged_turn(per), losses=losses(data),
                  note='Only the three primaries P1, P3 and P2, read in that fixed sequence, are pre-registered; every other section is secondary or descriptive.')
    return result, rows, fits


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit('usage: lateturn_analysis.py <RUN_DIR> <NEW_OUT_DIR>')
    run, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=False, exist_ok=False)
    subject = lw.sha((HERE / 'SOURCE_SUBJECT.json').read_bytes()) if (HERE / 'SOURCE_SUBJECT.json').exists() else None
    result, rows, fits = analyse(run, subject=subject)
    (out / 'ANALYSIS.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_csv(out / 'POINTS.csv', rows); write_csv(out / 'FITS.csv', fits)
    print(json.dumps(dict(status=result['status'], startup=result.get('startup'), decision=result.get('decision'), sequence=result['sequence']), indent=1))
