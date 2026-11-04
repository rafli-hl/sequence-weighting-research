"""Frozen analysis of the natural-text one-rate ladder extension (stdlib only). Runs after the run; never during it.

  python -I -B onerate_analysis.py <RUN_DIR> <NEW_OUT_DIR>      -> ANALYSIS.json, POINTS.csv, FITS.csv

Every rule is fixed before any outcome (PROTOCOL.md). The ladder is 64-768 (or 64-512 under the start-up memory
fallback) at one learning rate, 3e-5: 64, 96, 512 and 768 from this run; 128-384 from revision 05's Run B, read through
its pinned inventory. Gains are signed per-sequence training-loss reductions from E0 (64-384: Run B's E0; 512, 768: this
run's); p* is vendor/core.exponent on [0, 8] (text_analysis.fit, a byte copy); undefined fits stay undefined; the ten
draws are the only inference unit (df 9). The three primaries (owner decision 20261030-01, item 5), on E4-E32:
- turn-down: per point the OLS slope of p* on log2 width over 384, 512, 768 (384, 512 under the 512 top);
- dip at one rate: per point the OLS slope over 64, 96, 128;
- memorization: per point the Spearman rank correlation across the ladder's widths between p* and the train-validation
  gap (validation minus training NLL at that epoch); never pooled across epochs.
Each draw averages its defined points; a df-9 t interval of the ten draw means gives the label (below 0 / above 0 /
otherwise). Revision 05's eligibility and saturation rules apply to each primary on the fits it uses.
Revision 02 (owner ruling 20261030-03): attempt 1 is never analysed; load() refuses its folder, its TERMINAL.json and
its subject before reading anything else.
"""
import csv, json, math, statistics, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(1, str(HERE / 'vendor'))
import text_plan as plan
import text_analysis as ta
import onerate_plan as op
import onerate_worker as ow

EPS = ta.EPS
EPOCHS = op.PRIMARY_EPOCHS
KINDS = ('turn', 'dip', 'memo')
UNREADABLE = ('UNAVAILABLE', 'UNDEFINED', 'SATURATED', 'SATURATION_SENSITIVE')
NEVER_ANALYSED = 'Attempt 1 of the one-rate run is never analysed (owner ruling 20261030-03); analyse only the revision 02 run'


# ------------------------------------------------------------------ per-point statistics
def ranks(xs):
    """Average ranks (ties share the mean of their positions), 1-based."""
    order = sorted(range(len(xs)), key=xs.__getitem__); r = [0.0] * len(xs); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(xs, ys):
    """Spearman rank correlation (Pearson on average ranks); None if either has no rank variance."""
    rx, ry = ranks(xs), ranks(ys); mx, my = math.fsum(rx) / len(rx), math.fsum(ry) / len(ry)
    sxx = math.fsum((a - mx) ** 2 for a in rx); syy = math.fsum((b - my) ** 2 for b in ry)
    if sxx <= 0 or syy <= 0: return None
    return math.fsum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


def used_widths(kind, top):
    return op.TURN_WIDTHS[top] if kind == 'turn' else op.DIP_WIDTHS if kind == 'dip' else op.LADDER[top]


def statistic(kind, p, gap, top):
    """One point's statistic on the ladder-ordered fits p (None where undefined) and gaps; None if undefined."""
    ladder = op.LADDER[top]; ks = [ladder.index(w) for w in used_widths(kind, top)]; ps = [p[k] for k in ks]
    if any(v is None for v in ps): return None
    if kind == 'memo': return spearman(ps, [gap[k] for k in ks])
    return ta.ols_slope([math.log2(ladder[k]) for k in ks], ps)


def label(kind, t):
    below, above, other = op.LABELS[kind]
    if t['interval'][1] < -EPS: return below
    if t['interval'][0] > EPS: return above
    return other


# ------------------------------------------------------------------ one primary with eligibility and the saturation rule
def primary(kind, per, top, refit=None):
    """per[d]: the draw's points (dict(epoch, p, gap), ladder order), or None if its stage did not complete. refit(d, e)
    returns the point's fits at search bound 32 and whether any used refit is unresolved (fit >= 31.999). Revision 05's
    rules: UNAVAILABLE if any draw is missing, UNDEFINED if any draw is ineligible; S1 flags a point if every fit it uses
    is defined and any is >= 7.999, whether or not its statistic is defined; S32 is then required (a refitted statistic
    that is still undefined makes it not computable); SD (flagged points dropped; >= 3 points per draw, >= 3 draws) is
    required if more than 25% of the 70 nominal points are flagged or any refit is unresolved; SATURATED,
    SATURATION_SENSITIVE, else the label."""
    nominal = len(plan.DRAWS) * len(EPOCHS); ladder = op.LADDER[top]; ks = [ladder.index(w) for w in used_widths(kind, top)]
    missing = [d for d in plan.DRAWS if per.get(d) is None]
    if missing: return dict(label='UNAVAILABLE', missing=missing)
    vals = {d: {pt['epoch']: statistic(kind, pt['p'], pt['gap'], top) for pt in per[d] if pt['epoch'] in EPOCHS} for d in plan.DRAWS}
    defined = {d: [e for e in EPOCHS if vals[d].get(e) is not None] for d in plan.DRAWS}
    ineligible = [d for d in plan.DRAWS if not ta.eligible(defined[d])]
    counts = dict(nominal_points=nominal, defined_points=sum(len(v) for v in defined.values()))
    if ineligible: return dict(label='UNDEFINED', ineligible={d: defined[d] for d in ineligible}, counts=counts)
    mean = lambda xs: math.fsum(xs) / len(xs)
    draw = {d: mean([vals[d][e] for e in defined[d]]) for d in plan.DRAWS}
    t = ta.tint([draw[d] for d in plan.DRAWS]); base = label(kind, t)
    by_point = {d: {pt['epoch']: pt for pt in per[d]} for d in plan.DRAWS}
    # S1 flags a point from its fits, whether or not its statistic is defined: a memorization point whose fits are all at
    # the bound is constant across widths (no Spearman) and is flagged, not silently dropped (review 1, finding 2).
    fitted = lambda pt: all(pt['p'][k] is not None for k in ks)
    flagged = [(d, e) for d in plan.DRAWS for e in EPOCHS if e in by_point[d] and fitted(by_point[d][e]) and any(by_point[d][e]['p'][k] >= plan.P_UPPER for k in ks)]
    counts.update(flagged_points=len(flagged))
    sens = {}
    if flagged:
        refits = {(d, e): refit(d, e) for d, e in flagged}
        unresolved = sum(any(r['p'][k] >= ta.S32_UPPER - 0.001 for k in ks) for r in refits.values())
        v32 = {d: {e: (statistic(kind, refits[(d, e)]['p'], by_point[d][e]['gap'], top) if (d, e) in refits else vals[d][e])
                   for e in EPOCHS if e in defined[d] or (d, e) in refits} for d in plan.DRAWS}
        if any(v is None for x in v32.values() for v in x.values()): sens['S32'] = dict(required=True, computable=False, reason='UNDEFINED_REFIT_STATISTIC')
        else:
            t32 = ta.tint([mean(list(v32[d].values())) for d in plan.DRAWS]); sens['S32'] = dict(required=True, computable=True, label=label(kind, t32), interval=t32)
        sd_required = 4 * len(flagged) > nominal or unresolved > 0
        keep = {d: [vals[d][e] for e in defined[d] if (d, e) not in refits] for d in plan.DRAWS}
        sd_draws = [d for d in plan.DRAWS if len(keep[d]) >= ta.SD_MIN_POINTS]
        if len(sd_draws) >= ta.SD_MIN_CORPORA:
            tsd = ta.tint([mean(keep[d]) for d in sd_draws]); sens['SD'] = dict(required=sd_required, computable=True, label=label(kind, tsd), interval=tsd, draws_dropped=[d for d in plan.DRAWS if d not in sd_draws])
        else: sens['SD'] = dict(required=sd_required, computable=False, draws_kept=len(sd_draws))
        sens['unresolved_refits'] = unresolved
    required = [s for s in sens.values() if isinstance(s, dict) and s.get('required')]
    final = 'SATURATED' if any(not s['computable'] for s in required) else 'SATURATION_SENSITIVE' if any(s['label'] != base for s in required) else base
    return dict(label=final, primary_label=base, interval=t, draw_means=draw, point_values={d: {f'E{e}': vals[d][e] for e in EPOCHS} for d in plan.DRAWS},
                widths=list(used_widths(kind, top)), counts=counts, sensitivities=sens or dict(S32=dict(required=False, reason='NO_FLAGGED_POINTS'), SD=dict(required=False, reason='NO_FLAGGED_POINTS')))


def reading(labels):
    """The pre-registered reading of the three labels (PROTOCOL.md section 7)."""
    if any(v in UNREADABLE for v in labels.values()): return dict(joint=None, note='At least one primary is UNAVAILABLE, UNDEFINED, SATURATED or SATURATION_SENSITIVE; each label is read on its own.')
    memo = all(labels[k] == op.PREDICTIONS['memorization'][k] for k in KINDS)
    js = labels['turn'] == op.PREDICTIONS['jane_street']['turn']
    return dict(joint='MEMORIZATION_PREDICTIONS_MET' if memo else 'JANE_STREET_TURN_DOWN' if js else 'NEITHER_PATTERN_COMPLETE',
                memorization_predictions_met={k: labels[k] == op.PREDICTIONS['memorization'][k] for k in KINDS}, jane_street_prediction_met=js)


# ------------------------------------------------------------------ loading
def sha(b): return ow.sha(b)


def _arrays(raw_fn, rec, n):
    raw = raw_fn(rec['arrays']['path'])
    if len(raw) != rec['arrays']['bytes'] or sha(raw) != rec['arrays']['sha256']: raise ValueError('Array binding differs: ' + rec['arrays']['path'])
    if rec['layout']['block_epochs'] != list(plan.READOUTS) or rec['layout']['train_rows'] != n or rec['layout']['validation_rows'] != plan.N_VALIDATION: raise ValueError('Record layout differs: ' + rec['arrays']['path'])
    return raw


def _e0(raw_fn, binding, n):
    raw = raw_fn(binding['path'])
    if len(raw) != binding['bytes'] or sha(raw) != binding['sha256'] or len(raw) != 4 * (n + plan.N_VALIDATION): raise ValueError('E0 binding differs: ' + binding['path'])
    a = array('f'); a.frombytes(raw); return a


def load(run, run_b=ow.RUN_B, run_b_inventory=ow.RUN_B_INVENTORY, pins=op.RUN_B, subject=None):
    """The run (COMPLETE, FAILED or STOPPED_AT_STARTUP) and Run B through its pinned inventory. Returns the ladder top and,
    per draw, the ladder trajectories (or None if the draw's stage did not complete) and Run B's own 64 and 96 trajectories
    at their selected rates (for the paired secondary)."""
    run = Path(run)
    if run.resolve().name == Path(op.ATTEMPT_1['run']).name: raise ValueError(NEVER_ANALYSED)
    term_raw = (run / 'TERMINAL.json').read_bytes(); term = json.loads(term_raw)
    if sha(term_raw) == op.ATTEMPT_1['terminal_sha256'] or term.get('subject') == op.ATTEMPT_1['subject']: raise ValueError(NEVER_ANALYSED)
    if term.get('kind') != 'onerate' or term.get('mode') != 'ONERATE': raise ValueError('Not a one-rate ladder run')
    if subject is not None and term.get('subject') != subject: raise ValueError('Run subject differs from this analysis source')
    if term.get('status') not in ('COMPLETE', 'FAILED', 'STOPPED_AT_STARTUP'): raise ValueError('Run ended ' + str(term.get('status')))
    b = term.get('bindings') or {}
    if (b.get('run_b_terminal_sha256'), b.get('run_b_inventory_sha256')) != (pins['terminal_sha256'], pins['inventory_sha256']): raise ValueError('Run was not bound to the pinned Run B')
    rb = ow.RunB(run_b, run_b_inventory, pins)
    bound = term.get('benchmark')
    if not bound: return dict(top=None, terminal=term, terminal_sha256=sha(term_raw), draws={d: None for d in plan.DRAWS}, rate_pairs={})
    braw = (run / 'BENCHMARK.json').read_bytes()
    if len(braw) != bound['bytes'] or sha(braw) != bound['sha256']: raise ValueError('Benchmark differs from its binding')
    bench = json.loads(braw); top, reason = ow.ladder_rule(bench['benchmark']['architectures'], bench['failure'])
    if [top, reason] != [bench['ladder']['top'], bench['ladder']['reason']] or (term.get('ladder') or {}) != dict(top=top, reason=reason): raise ValueError('Ladder top does not re-derive from the bound benchmark')
    draws, pairs = {}, {}
    for d in plan.DRAWS:
        rp = run / f'{d}-RECEIPT.json'
        if top not in (512, 768) or not rp.exists() or json.loads(rp.read_bytes()).get('status') != 'COMPLETE': draws[d] = None; continue
        b_in = rb.json(f'{d}/INPUTS.json'); b_pre = rb.json(f'{d}/PRETRAINED.json')
        inp = json.loads((run / d / 'INPUTS.json').read_bytes()); pre = json.loads((run / d / 'PRETRAINED.json').read_bytes())
        if (inp['run_b_inputs_sha256'] != sha(rb.read(f'{d}/INPUTS.json')) or not all(inp['paired_with_run_b'].values()) or inp['weights'] != b_in['weights']
                or inp['top'] != top or inp['learning_rate'] != op.LR): raise ValueError('Draw inputs are not paired with Run B: ' + d)
        n = inp['n_train']; widths = {}
        for w in op.LADDER[top]:
            if w in op.REUSED:
                rec = rb.json(f'{d}/w{w}/selected/record.json'); raw = _arrays(rb.read, rec, n); e0 = _e0(rb.read, b_pre[str(w)]['E0_arrays'], n)
            else:
                rec = json.loads((run / d / f'w{w}' / op.TAG / 'record.json').read_bytes()); raw = _arrays(lambda p: (run / p).read_bytes(), rec, n)
                if w in op.ADAPT_ONLY:
                    if pre[str(w)].get('source') != 'run_b' or pre[str(w)]['run_b_E0_arrays'] != b_pre[str(w)]['E0_arrays']: raise ValueError('E0 is not Run B\'s: ' + d)
                    e0 = _e0(rb.read, b_pre[str(w)]['E0_arrays'], n)
                else: e0 = _e0(lambda p: (run / p).read_bytes(), pre[str(w)]['E0_arrays'], n)
            if rec['width'] != w or rec['lr'] != op.LR: raise ValueError(f'Not width {w} at 3e-5: ' + d)
            widths[w] = dict(e0=e0, raw=raw, record=rec)
        draws[d] = dict(weights=inp['weights'], n=n, widths=widths)
        rates = {}
        for w in op.ADAPT_ONLY:
            rec = rb.json(f'{d}/w{w}/selected/record.json')
            if rec['lr'] != op.RUN_B['rates'][w]: raise ValueError('Run B rate differs at ' + str(w))
            rates[w] = dict(e0=draws[d]['widths'][w]['e0'], raw=_arrays(rb.read, rec, n), record=rec)
        pairs[d] = dict(weights=inp['weights'], n=n, widths=rates)
    return dict(top=top, reason=reason, terminal=term, terminal_sha256=sha(term_raw), benchmark_sha256=sha(braw), draws=draws, rate_pairs=pairs)


def gap(t, epoch):
    r = next(x for x in t['record']['readouts'] if x['epoch'] == epoch)
    return r['validation_loss'] - r['train_loss']


def points(data):
    """per[d] = the draw's points at every readout epoch: fits over the ladder (None where undefined) and gaps."""
    top = data['top']; per = {}
    for d in plan.DRAWS:
        dd = data['draws'].get(d)
        if dd is None: per[d] = None; continue
        per[d] = [dict(epoch=e, p=[ta.fit(dd, w, e)['p'] for w in op.LADDER[top]], gap=[gap(dd['widths'][w], e) for w in op.LADDER[top]]) for e in plan.READOUTS]
    return per


def refitter(data):
    def refit(d, e):
        dd = data['draws'][d]
        fits = [ta.exponent_upper(dd['weights'], ta.gains(dd, w, e), ta.S32_UPPER) for w in op.LADDER[data['top']]]
        return dict(p=[f['p'] for f in fits])
    return refit


# ------------------------------------------------------------------ secondaries (non-gating)
def by_epoch(per, top):
    """Per readout epoch: the ten-draw panel p* curve over the ladder and its argmax, and the three statistics' df-9
    intervals at that epoch alone (descriptive). UNAVAILABLE if a draw is missing; UNDEFINED if any fit is undefined."""
    out = {}
    for e in plan.READOUTS:
        if any(per[d] is None for d in plan.DRAWS): out[f'E{e}'] = dict(label='UNAVAILABLE'); continue
        pts = {d: next(p for p in per[d] if p['epoch'] == e) for d in plan.DRAWS}
        if any(v is None for p in pts.values() for v in p['p']): out[f'E{e}'] = dict(label='UNDEFINED', undefined_fits=sum(v is None for p in pts.values() for v in p['p'])); continue
        curve = [math.fsum(pts[d]['p'][k] for d in plan.DRAWS) / len(plan.DRAWS) for k in range(len(op.LADDER[top]))]
        gaps = [math.fsum(pts[d]['gap'][k] for d in plan.DRAWS) / len(plan.DRAWS) for k in range(len(op.LADDER[top]))]
        row = dict(curve=curve, gap=gaps, argmax_width=op.LADDER[top][max(range(len(curve)), key=lambda k: (curve[k], -k))])
        for kind in KINDS:
            v = [statistic(kind, pts[d]['p'], pts[d]['gap'], top) for d in plan.DRAWS]
            row[kind] = dict(interval=ta.tint(v), label=label(kind, ta.tint(v))) if all(x is not None for x in v) else dict(undefined=True)
        out[f'E{e}'] = row
    return out


def rate_pairs(data):
    """64 and 96: per draw, the mean over E4-E32 of p*(3e-5) minus p*(Run B's selected rate), and the same for the gap and
    the validation NLL at E32; df-9 intervals (descriptive; Run B's rates were 3e-4 at 64 and 1e-4 at 96)."""
    if any(data['draws'].get(d) is None for d in plan.DRAWS): return dict(label='UNAVAILABLE')
    out = {}
    for w in op.ADAPT_ONLY:
        dp, dg, dv = [], [], []
        for d in plan.DRAWS:
            new, old = data['draws'][d], data['rate_pairs'][d]
            diffs = [ta.fit(new, w, e)['p'] - ta.fit(old, w, e)['p'] for e in EPOCHS if ta.fit(new, w, e)['p'] is not None and ta.fit(old, w, e)['p'] is not None]
            if not diffs: return dict(label='UNDEFINED', width=w, draw=d)
            dp.append(math.fsum(diffs) / len(diffs)); dg.append(gap(new['widths'][w], 32) - gap(old['widths'][w], 32))
            dv.append(next(x['validation_loss'] for x in new['widths'][w]['record']['readouts'] if x['epoch'] == 32) - next(x['validation_loss'] for x in old['widths'][w]['record']['readouts'] if x['epoch'] == 32))
        out[str(w)] = dict(run_b_rate=op.RUN_B['rates'][w], p_star_difference=ta.tint(dp), gap_E32_difference=ta.tint(dg), validation_nll_E32_difference=ta.tint(dv))
    return out


def losses(data):
    out = {}
    avail = [data['draws'][d] for d in plan.DRAWS if data['draws'].get(d) is not None]
    if not avail: return out
    for w in op.LADDER[data['top']]:
        for e in plan.READOUTS:
            rows = [next(r for r in dd['widths'][w]['record']['readouts'] if r['epoch'] == e) for dd in avail]
            tr = math.fsum(r['train_loss'] for r in rows) / len(rows); va = math.fsum(r['validation_loss'] for r in rows) / len(rows)
            out[f'{w}|E{e}'] = dict(train=tr, validation=va, gap=va - tr, n=len(rows))
        e0 = [dd['widths'][w]['e0'] for dd in avail]; n = avail[0]['n']
        out[f'{w}|E0'] = dict(train=math.fsum(math.fsum(a[:n]) / n for a in e0) / len(e0), validation=math.fsum(math.fsum(a[n:]) / (len(a) - n) for a in e0) / len(e0))
        ep = [x for dd in avail for x in dd['widths'][w]['record']['epochs']]
        out[f'{w}|clipping'] = dict(clip_fraction_mean=math.fsum(x['clip_fraction'] for x in ep) / len(ep), gradient_norm_mean=math.fsum(x['gradient_norm_mean'] for x in ep) / len(ep),
                                    gradient_norm_max=max(x['gradient_norm_max'] for x in ep), source='run B' if w in op.REUSED else 'this run')
    return out


def analyse(run, **kw):
    ta._FITS.clear(); data = load(run, **kw); top = data['top']
    if top is None or all(data['draws'].get(d) is None for d in plan.DRAWS):
        prim = {k: dict(label='UNAVAILABLE', reason='NO_COMPLETED_DRAW') for k in KINDS}
        return dict(status='UNAVAILABLE', run_status=data['terminal']['status'], ladder=dict(top=top, reason=data.get('reason')), primaries=prim, reading=reading({k: 'UNAVAILABLE' for k in KINDS})), [], []
    per = points(data); refit = refitter(data)
    prim = {k: primary(k, per, top, refit) for k in KINDS}
    labels = {k: prim[k]['label'] for k in KINDS}
    avail = [d for d in plan.DRAWS if data['draws'][d] is not None]
    fits = [dict(draw=d, width=w, epoch=e, source='run B' if w in op.REUSED else 'this run', lr=op.LR, **ta.fit(data['draws'][d], w, e)) for d in avail for w in op.LADDER[top] for e in plan.READOUTS]
    fits += [dict(draw=d, width=w, epoch=e, source='run B selected rate', lr=op.RUN_B['rates'][w], **ta.fit(data['rate_pairs'][d], w, e)) for d in avail for w in op.ADAPT_ONLY for e in plan.READOUTS]
    rows = [dict(draw=d, epoch=p['epoch'], **{f'p_{w}': v for w, v in zip(op.LADDER[top], p['p'])}, **{f'gap_{w}': v for w, v in zip(op.LADDER[top], p['gap'])},
                 **{k: statistic(k, p['p'], p['gap'], top) for k in KINDS}) for d in avail for p in per[d]]
    bound = dict(upper=sum(bool(f.get('upper')) for f in fits if f['lr'] == op.LR), lower=sum(bool(f.get('lower')) for f in fits if f['lr'] == op.LR),
                 undefined=sum(f['p'] is None for f in fits if f['lr'] == op.LR))
    result = dict(status='COMPLETE' if len(avail) == len(plan.DRAWS) else 'PARTIAL_UNAVAILABLE_DRAWS', run_status=data['terminal']['status'], draws_available=avail,
                  run_terminal_sha256=data['terminal_sha256'], run_benchmark_sha256=data['benchmark_sha256'], ladder=dict(top=top, reason=data['reason'], widths=list(op.LADDER[top])),
                  decision=dict(turn_down=labels['turn'], dip_at_one_rate=labels['dip'], memorization=labels['memo']), reading=reading(labels), primaries=prim,
                  fit_bounds=bound, by_epoch=by_epoch(per, top), rate_pairs_64_96=rate_pairs(data), losses=losses(data),
                  note='Only the three decision labels are pre-registered primaries; every other section is secondary or descriptive.')
    return result, rows, fits


def write_csv(path, table):
    fields = sorted({k for r in table for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(table)


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit('usage: onerate_analysis.py <RUN_DIR> <NEW_OUT_DIR>')
    run, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=False, exist_ok=False)
    subject = ow.sha((HERE / 'SOURCE_SUBJECT.json').read_bytes()) if (HERE / 'SOURCE_SUBJECT.json').exists() else None
    result, rows, fits = analyse(run, subject=subject)
    (out / 'ANALYSIS.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_csv(out / 'POINTS.csv', rows); write_csv(out / 'FITS.csv', fits)
    print(json.dumps(dict(status=result['status'], ladder=result['ladder'], decision=result.get('decision'), reading=result['reading']), indent=1))
