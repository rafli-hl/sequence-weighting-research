"""Few-epoch, data-rich width ladder: the worker (Linux/CUDA; owner decisions 20261101-01 and -02).

Disabled unless run from one of its one-use activations; the framework is imported lazily. Derived from the late-turn worker
(work/natural-text-lateturn-source-20261031-01/lateturn_worker.py), with revision 05's sealed classes and code paths unchanged
(byte copies): text_worker.Budget, Guard, Output, Context (pretrain, load_adaptation_model, adaptation_step, evaluate,
save_state), benchmark, gpu_gate and prestart. Modes (from the activation's AUTHORIZATION.json):
- A (Run A, the tuning draw t00 at N = 16,384): every width pre-trained once (its E0 per-sequence losses are written, as by
  every stage), then adapted for 3 epochs at each rate of 3e-5, 1e-4, 3e-4, 1e-3 and 3e-3, widest first, each width's state
  hashed and deleted after its adaptations; the adaptations record only training and validation NLL (validation at every
  readout, training at E3), no per-sequence adaptation array and no p*. A nonfinite update or evaluation in an adaptation
  records that (width, rate) as DIVERGED and Run A continues; a diverged rate is ineligible (review 1, finding 6). The common
  rate is then selected by validation NLL only (select_rate, from the written records) and written to LR_SELECTION.json;
- A2N (Run A at 2N = 32,768; D5): only after a Run A whose selection found no eligible rate, bound to that Run A;
- B1 (d01-d05) and B2 (d06-d10): per draw, every width pre-trained and adapted once at the selected rate with readouts at
  E0.25, E0.5, E1, E2 and E3 (training and validation per-sequence losses at each), widest first, each width's state hashed
  and deleted after its adaptation. B1 is admitted on Run A's terminal and selection; B2 also on B1's COMPLETE terminal.
Unchanged from the late-turn worker: admission re-derives the registry and the partition and checks disjointness; the
start-up benchmark runs every width one at a time and stops the run before any training if a width exceeds 2.25 GiB (no
fallback); the cap is revision 05's formula on this run's exact counts, with one 30-minute gate wait reserved; before every
stage the owner script's check covers the GPU and AC power; per-width state deletion; the counting rule (any stage folder
makes the run counted); TERMINAL.json through the ledger, or directly as a last resort with terminal_outside_ledger.
"""
import gc, hashlib, json, math, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_worker as worker
import wt103_corpus
import fewepoch_data as fd
import fewepoch_registry as fr
import fewepoch_plan as fp

ROOT = worker.ROOT
ACTIVATIONS = {m: ROOT / p for m, p in fp.ACTIVATIONS.items()}
RUNS = {m: ROOT / p for m, p in fp.RUNS.items()}
CORPUS = ROOT / fp.CORPUS
PINS = dict(registry_sha256=fp.REGISTRY['registry_sha256'], exclusions_sha256=fp.REGISTRY['exclusions_sha256'], draw_sha256=fp.REGISTRY['draw_sha256'],
            corpus_manifest_sha256=fp.CORPUS_MANIFEST_SHA256, partition_sha256=fp.PARTITION_SHA256)
BINDING_KEYS = ('approval_id', 'approval_record_sha256', 'registry_sha256', 'exclusions_sha256', 'draw_sha256', 'partition_sha256', 'corpus_manifest_sha256',
                'lr_selection_sha256', 'run_a_terminal_sha256', 'run_b1_terminal_sha256')
sha, encoded = worker.sha, worker.encoded


class PowerGateError(RuntimeError):
    """The Windows owner script's last check before a stage, at the end of its 30-minute window, found the laptop off AC
    power: on battery, or with the power status unreadable."""


def draw_gate(out, here, stage, budget, probe, clock):
    """The late-turn worker's draw_gate, unchanged: revision 05's gate, with a stop whose last check is off AC power raised
    as PowerGateError (with the counts of checks on battery and with the power status unreadable)."""
    try: return worker.gpu_gate(out, here, stage, budget, probe=probe, clock=clock)
    except worker.GpuBusyError as e:
        checks = json.loads((out.root / worker.GATE_DIR / f'{stage}.json').read_bytes())['checks']
        battery = sum(c.get('verdict') == 'ON_BATTERY' for c in checks); unreadable = sum(c.get('verdict') == 'POWER_UNVERIFIED' for c in checks)
        counts = f'of {len(checks)} checks, {battery} on battery and {unreadable} with the power status unreadable (Windows power status)'
        if checks and checks[-1].get('verdict') in fp.POWER_VERDICTS:
            raise PowerGateError(f"Not on AC power at the end of the 30-minute window before {stage} (last check {checks[-1]['verdict']}; {counts}); stopped before {stage}") from e
        if battery or unreadable: raise worker.GpuBusyError(f'{e} (last check {checks[-1].get("verdict")}; {counts})') from e
        raise


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def mode_of(here):
    m = json.loads((Path(here) / 'AUTHORIZATION.json').read_bytes()).get('mode')
    if m not in fp.RUN_STAGES: raise PermissionError('DISABLED: no few-epoch study approval')
    return m


# ------------------------------------------------------------------ the rate selection (Run A; validation NLL only)
def select_rate(table, widths=fp.WIDTHS):
    """table[(width, lr)] = dict(E2=validation NLL at E2, E3=validation NLL at E3) on t00, or dict(diverged=True). A rate is
    eligible if no width diverged and every width's E3 validation NLL is below its E2 value. Among the eligible rates of the
    grid, the lowest mean E3 validation NLL over the widths is selected (ties to the smaller rate). If that is the grid's top
    rate, the extension rate replaces it only if it is eligible and its mean is strictly lower (D5, once). No eligible grid
    rate: NO_ELIGIBLE_RATE. p* is never used."""
    per = {}
    for lr in fp.RUN_A_RATES:
        rows = {w: table[(w, lr)] for w in widths}; diverged = sorted(w for w, r in rows.items() if r.get('diverged'))
        per[lr] = dict(eligible=not diverged and all(r['E3'] < r['E2'] for r in rows.values()), diverged_widths=diverged,
                       mean_E3_validation=None if diverged else math.fsum(r['E3'] for r in rows.values()) / len(rows),
                       per_width={str(w): (dict(diverged=True) if r.get('diverged') else dict(E2=r['E2'], E3=r['E3'], delta=r['E3'] - r['E2'])) for w, r in rows.items()})
    view = {fp.rate_tag(lr): dict(rate=lr, **v) for lr, v in per.items()}
    base = [lr for lr in fp.LR_GRID if per[lr]['eligible']]
    rule = ('eligible: no width diverged and every width E3 < E2 (validation NLL, t00); select the lowest mean E3 validation NLL among eligible grid rates, ties to the smaller; '
            'if the grid top is selected, the extension replaces it only if eligible and strictly lower; p* never used')
    if not base: return dict(status='NO_ELIGIBLE_RATE', selected_rate=None, base_selection=None, extension_considered=False, top_edge_after_extension=False, per_rate=view, rule=rule)
    pick = min(base, key=lambda lr: (per[lr]['mean_E3_validation'], lr)); base_pick = pick; considered = pick == fp.LR_GRID[-1]
    if considered and per[fp.LR_EXTENSION]['eligible'] and per[fp.LR_EXTENSION]['mean_E3_validation'] < per[pick]['mean_E3_validation']: pick = fp.LR_EXTENSION
    return dict(status='SELECTED', selected_rate=pick, base_selection=base_pick, extension_considered=considered, top_edge_after_extension=pick == fp.LR_EXTENSION,
                per_rate=view, rule=rule)


def selection_entry(rec):
    """One Run A record: its E2 and E3 validation NLL, or diverged."""
    if rec.get('status') == 'DIVERGED': return dict(diverged=True)
    if [r['epoch'] for r in rec['readouts']] != list(fp.READOUTS): raise ValueError('Run A record readouts differ from the plan')
    v = {r['epoch']: r['validation_loss'] for r in rec['readouts']}
    return dict(E2=v[fp.PREVIOUS], E3=v[fp.FINAL])


def selection_from_records(stage_dir):
    """The rate selection from Run A's written t00 records (used by the worker and, to re-derive it, by the builder)."""
    table = {}
    for w in fp.WIDTHS:
        for lr in fp.RUN_A_RATES:
            rec = json.loads((Path(stage_dir) / f'w{w}' / fp.rate_tag(lr) / 'record.json').read_bytes())
            if rec['width'] != w or rec['lr'] != lr: raise ValueError('Run A record differs from the plan: ' + fp.rate_tag(lr))
            table[(w, lr)] = selection_entry(rec)
    return select_rate(table)


# ------------------------------------------------------------------ admission
def check_terminal(raw, mode, status, bindings, keys, subject):
    t = json.loads(raw)
    if t.get('kind') != 'fewepoch' or t.get('mode') != mode or t.get('status') != status: raise PermissionError(f'Run {mode} terminal is not {status}')
    if t.get('subject') != subject: raise PermissionError(f'Run {mode} ran under another source subject')                 # review 1, finding 7
    if any((t.get('bindings') or {}).get(k) != bindings.get(k) for k in keys): raise PermissionError(f'Run {mode} was bound to other inputs')
    return t


def authorization(here, corpus_dir=CORPUS, pins=PINS):
    """The one-use activation: enabled, a mode with its real path and a real approval, the sealed source unchanged, the
    approval record, the registry (re-derived from its own bytes), the WikiText-103 corpus manifest (sealed rules, the
    acquisition subject), the tokenizer, the partition (re-derived) and its disjointness; for B1 and B2 Run A's terminal and
    selection, and for B2 Run B1's COMPLETE terminal; for A2N Run A's terminal with NO_ELIGIBLE_RATE."""
    here = Path(here); a = json.loads((here / 'AUTHORIZATION.json').read_bytes()); mode = a.get('mode')
    if a.get('enabled') is not True or a.get('execution_ready') is not True or mode not in fp.RUN_STAGES or a.get('one_use') is not True or not a.get('approval_id'):
        raise PermissionError('DISABLED: no few-epoch study approval')
    if here.resolve() == ACTIVATIONS[mode].resolve() and (a.get('fixture') is not False or str(a['approval_id']).upper().startswith('FIXTURE')): raise PermissionError('Real activation needs a real approval')
    if any(v is None for v in pins.values()): raise PermissionError('The corpus, registry and partition pins are not set (PENDING)')
    raw = (here / 'SOURCE_SUBJECT.json').read_bytes()
    if sha(raw) != a.get('source_subject_sha256'): raise PermissionError('Source subject differs from the authorization')
    if sha((here / 'APPROVAL_RECORD.json').read_bytes()) != a.get('approval_record_sha256'): raise PermissionError('Approval record binding')
    subject_hashes = {}
    for row in json.loads(raw)['files']:
        b = (here / row['path']).read_bytes()
        if len(b) != row['bytes'] or sha(b) != row['sha256']: raise PermissionError('Changed source ' + row['path'])
        subject_hashes[row['path']] = row['sha256']
    reg_raw, ex_raw, draw_raw = ((here / n).read_bytes() for n in ('REGISTRY.json', 'EXCLUSIONS.json', 'DRAW.json'))
    got = (sha(reg_raw), sha(ex_raw), sha(draw_raw))
    if got != (a.get('registry_sha256'), a.get('exclusions_sha256'), a.get('draw_sha256')) or got != (pins['registry_sha256'], pins['exclusions_sha256'], pins['draw_sha256']):
        raise PermissionError('Registry binding')
    try: registry = fr.validate(json.loads(reg_raw), ex_raw, draw_raw, pins['corpus_manifest_sha256'])
    except ValueError as e: raise PermissionError('Registry does not re-derive from its draw: ' + str(e))
    man_raw = (Path(corpus_dir) / 'CORPUS_MANIFEST.json').read_bytes()
    if len({sha(man_raw), a.get('corpus_manifest_sha256'), registry['corpus_manifest_sha256'], pins['corpus_manifest_sha256']}) != 1: raise PermissionError('Corpus manifest binding')
    manifest = json.loads(man_raw)
    try: wt103_corpus.validate_manifest(manifest, subject_hashes)
    except (ValueError, KeyError) as e: raise PermissionError('Corpus manifest differs from the pre-registration: ' + str(e))
    if manifest.get('source_subject_sha256') != fp.ACQUISITION_SUBJECT or manifest.get('fixture') is not False and here.resolve() == ACTIVATIONS[mode].resolve():
        raise PermissionError('Corpus was not made by the approved acquisition')
    if sha((Path(corpus_dir) / 'tokenizer.json').read_bytes()) != manifest['tokenizer']['sha256']: raise PermissionError('Tokenizer binding')
    part_raw = (here / 'PARTITION.json').read_bytes()
    if sha(part_raw) != a.get('partition_sha256') or sha(part_raw) != pins['partition_sha256']: raise PermissionError('Partition binding')
    partition = fd.partition(manifest, registry['partition_seed'])
    if json.loads(part_raw) != json.loads(encoded(partition)): raise PermissionError('Partition does not re-derive from the corpus and the registry')
    fd.disjoint(partition, manifest)
    extra = dict(n=fp.N_TRAIN if mode == 'A' else fp.N_FALLBACK if mode == 'A2N' else None)
    ours = dict(registry_sha256=a['registry_sha256'], partition_sha256=a['partition_sha256'], corpus_manifest_sha256=a['corpus_manifest_sha256'])
    if mode != 'A':
        t_raw = (here / 'RUN_A_TERMINAL.json').read_bytes()
        if sha(t_raw) != a.get('run_a_terminal_sha256'): raise PermissionError('Run A terminal binding')
        ta_ = check_terminal(t_raw, 'A', 'COMPLETE', ours, tuple(ours), a['source_subject_sha256'])
        if mode == 'A2N':
            if ta_.get('selection_status') != 'NO_ELIGIBLE_RATE': raise PermissionError('Run A2N needs a Run A without an eligible rate')
        else:
            s_raw = (here / 'LR_SELECTION.json').read_bytes(); s = json.loads(s_raw)
            if sha(s_raw) != a.get('lr_selection_sha256') or sha(s_raw) != (ta_.get('lr_selection') or {}).get('sha256'): raise PermissionError('Rate selection binding')
            if s.get('status') != 'SELECTED' or s.get('selected_rate') not in fp.RUN_A_RATES or s.get('n_train') != fp.N_TRAIN: raise PermissionError('Rate selection is not usable by B1/B2 in this revision')
            extra.update(n=fp.N_TRAIN, lr=s['selected_rate'], selection=s)
            if mode == 'B2':
                b_raw = (here / 'RUN_B1_TERMINAL.json').read_bytes()
                if sha(b_raw) != a.get('run_b1_terminal_sha256'): raise PermissionError('Run B1 terminal binding')
                check_terminal(b_raw, 'B1', 'COMPLETE', dict(ours, lr_selection_sha256=a['lr_selection_sha256'], run_a_terminal_sha256=a['run_a_terminal_sha256']),
                               tuple(ours) + ('lr_selection_sha256', 'run_a_terminal_sha256'), a['source_subject_sha256'])
    return a, registry, manifest, partition, extra


# ------------------------------------------------------------------ start-up benchmark (no fallback; the late-turn rule on eight widths)
def classify(error):
    text = f'{type(error).__name__}: {error}'
    if 'Sampled GPU limit' in text: return 'GUARD'
    if type(error).__name__ == 'OutOfMemoryError' or 'out of memory' in text.lower(): return 'OOM'
    if 'Worker peak RSS limit' in text: return 'RSS'
    if isinstance(error, TimeoutError): return 'TIMEOUT'
    return 'OTHER'


def startup_benchmark(ctx, seed, pool, budget, clock):
    """text_worker.benchmark (sealed, unchanged) one width at a time in BENCH_WIDTHS order, each width with its own peaks
    (reset before it), all inside the 900 s benchmark budget. Stops at the first failing width."""
    t, g = ctx.torch, ctx.guard; start = clock(); results, overheads, failure = {}, None, None; saved = plan.WIDTHS
    g.budget = worker.Budget(min(budget.deadline, start + fp.LIMITS['benchmark_seconds']), clock)
    try:
        for w in fp.BENCH_WIDTHS:
            plan.WIDTHS = (w,); g.peaks = {}
            reset = getattr(t.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            t0 = clock()
            try: r = worker.benchmark(ctx, seed, fp.LIMITS['benchmark_seconds'], pool, clock)
            except Exception as e:
                failure = dict(width=w, kind=classify(e), type=type(e).__name__, message=str(e)[:400], peaks=dict(g.peaks), seconds=clock() - t0); break
            results[str(w)] = dict(r['architectures'][str(w)], seconds=clock() - t0); overheads = r['overheads']
    finally:
        plan.WIDTHS = saved; g.budget = budget; gc.collect()
        empty = getattr(t.cuda, 'empty_cache', None)
        if empty is not None: empty()
    return results, overheads, failure


def startup_rule(results, failure, limit=fp.FIT_LIMIT_BYTES):
    for w in fp.BENCH_WIDTHS:
        if str(w) not in results: return 'STOP', f"FAILED_{(failure or {}).get('kind', 'INCOMPLETE')}_AT_{w}"
        pk = ((results[str(w)] or {}).get('peaks') or {}).get('device_used_sampled')
        if pk is None: return 'STOP', f'PEAK_MISSING_AT_{w}'
        if pk > limit: return 'STOP', f'PEAK_{w}_OVER_LIMIT'
    if failure is not None: return 'STOP', f"FAILED_{failure.get('kind')}_AT_{failure.get('width')}"
    return 'GO', 'ALL_WIDTHS_WITHIN_LIMIT'


def study_counts(mode, n_train, n_pool):
    """Exact per-stage counts. Tuning (A, A2N): five adaptations per width, validation at every readout and training at E3,
    a record and no arrays per adaptation. Study (B1, B2): one adaptation per width, training and validation at every
    readout, arrays and a record."""
    W = len(fp.WIDTHS); tuning = mode in fp.TUNING_MODES; k = len(fp.RUN_A_RATES) if tuning else 1; R = len(fp.READOUTS)
    files = 3 + W * (2 + k * (1 if tuning else 2))
    readout_eval = (R * plan.eval_batches(plan.N_VALIDATION) + plan.eval_batches(n_train)) if tuning else R * (plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION))
    return dict(trajectories=W * k, adaptations_per_width=k, files=files, dirs=W + W * k, full_guards=2 + W + 2 * W * k,
                epoch_guards=W * plan.PRETRAIN['epochs'] + W * k * fp.EPOCHS + files,
                pre_updates=plan.updates(n_pool, plan.PRETRAIN['epochs']), adapt_updates=plan.updates(n_train, fp.EPOCHS),
                e0_eval_batches=plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION), readout_eval_batches=readout_eval,
                e0_bytes=4 * (n_train + plan.N_VALIDATION), array_bytes=0 if tuning else 4 * R * (n_train + plan.N_VALIDATION), arrays=not tuning)


def study_cap(benchmark, mode, n_train, n_pool):
    """Revision 05's cap formula on this run's exact counts: cap = ceil(1.25 x projected + 120 s); feasible iff
    stages x (cap + 60) + 900 + 1,800 (one gate wait) <= 21,600 s."""
    arch, o = benchmark['architectures'], benchmark['overheads']; c = study_counts(mode, n_train, n_pool); k = c['adaptations_per_width']
    total = 30.0 + o['seconds_data_generation']
    fixed_write, per_byte = worker.write_model(arch)
    for w in fp.WIDTHS:
        b = arch[str(w)]
        total += c['pre_updates'] * b['seconds_per_pretraining_update'] + c['e0_eval_batches'] * b['seconds_per_eval_batch'] + b['seconds_per_state_write'] + fixed_write + per_byte * c['e0_bytes']
        total += k * (b['seconds_per_state_reload'] + c['adapt_updates'] * b['seconds_per_update'] + c['readout_eval_batches'] * b['seconds_per_eval_batch']
                      + (2 if c['arrays'] else 1) * fixed_write + per_byte * (c['array_bytes'] + plan.RECORD_BYTES))
    total += c['full_guards'] * (o['seconds_per_full_guard'] + (c['files'] + c['dirs'] + o['cache_entries']) * o['seconds_per_inventory_entry'])
    total += c['epoch_guards'] * o['seconds_per_epoch_guard']
    L = fp.LIMITS; n = len(fp.RUN_STAGES[mode])
    work = math.ceil(L['cap_multiplier'] * total + L['cap_fixed_seconds'])
    max_cap = (L['overall_seconds'] - L['benchmark_seconds'] - fp.GATE_RESERVE_SECONDS) / n - L['stage_slack_seconds']
    return dict(projected_stage_seconds=total, stage_work_cap_seconds=min(work, math.floor(max_cap)), feasible=work <= max_cap, stages=n, counts=c,
                formula=f"ceil({L['cap_multiplier']}*projected+{L['cap_fixed_seconds']}) <= {math.floor(max_cap)} s; {n}*(cap+{L['stage_slack_seconds']})+{L['benchmark_seconds']}+{fp.GATE_RESERVE_SECONDS} <= {L['overall_seconds']} s",
                write_model=dict(fixed_seconds=fixed_write, seconds_per_byte=per_byte))


def remove_states(out_root, rel):
    """Every model state (and partial state write) under out_root/rel, recorded by sha256 and size, then deleted. Errors
    are recorded per file and never raised. (The late-turn worker's remove_states, unchanged.)"""
    base = Path(out_root) / rel; deleted, errors = [], []
    try: files = sorted(p for p in base.rglob('*') if p.is_file() and (p.name.endswith('.pt') or p.name.endswith('.pt.part'))) if base.exists() else []
    except Exception as e: return dict(deleted=deleted, errors=[dict(path=rel, stage='list', error=f'{type(e).__name__}: {str(e)[:200]}')])
    for p in files:
        name = p.relative_to(out_root).as_posix()
        try: entry = dict(path=name, bytes=p.stat().st_size, sha256=sha_file(p))
        except Exception as e: errors.append(dict(path=name, stage='hash', error=f'{type(e).__name__}: {str(e)[:200]}')); continue
        try: p.unlink(); deleted.append(entry)
        except Exception as e: errors.append(dict(entry, stage='delete', error=f'{type(e).__name__}: {str(e)[:200]}'))
    return dict(deleted=deleted, deleted_bytes=sum(d['bytes'] for d in deleted), errors=errors)


# ------------------------------------------------------------------ adaptation with fractional readouts
class Context(worker.Context):
    def adapt_readouts(self, stage, width, lr, tag, pre_result, seeds, data, weights, orders, arrays):
        """3 epochs at a constant rate with readouts after updates round(e x N / 16), e in READOUTS. Study (arrays=True):
        training and validation per-sequence losses at every readout, written as arrays. Tuning (arrays=False): validation
        at every readout and training at E3 only; no arrays. The sealed adaptation step, evaluation and reload are used."""
        t = self.torch; g = self.guard; name = f'{stage}/w{width}/{tag}'; n = len(data['train'])
        g.full()
        model, optimizer = self.load_adaptation_model(width, pre_result['state']['path'], pre_result['state_tensor_hashes'], seeds['init_seed'], lr)
        at = {fp.readout_update(e, n, plan.BATCH): e for e in fp.READOUTS}
        blocks, readouts, epochs, update = [], [], [], 0
        try:
            for epoch in range(1, fp.EPOCHS + 1):
                g.epoch(); model.train(); norms = []
                for ids in orders[epoch - 1].split(plan.BATCH):
                    norms.append(self.adaptation_step(model, optimizer, data['train'], weights, ids)); update += 1; self.counts['updates'] += 1
                    if update in at:
                        e = at[update]; va = self.evaluate(model, data['validation'])
                        tr = self.evaluate(model, data['train']) if arrays or e == fp.FINAL else None
                        if arrays: blocks.append(self.floats(tr) + self.floats(va))
                        readouts.append(dict(epoch=e, update=update, train_loss=None if tr is None else float(tr.mean()), validation_loss=float(va.mean())))
                        model.train()
                epochs.append(dict(epoch=epoch, gradient_norm_mean=sum(norms) / len(norms), gradient_norm_max=max(norms), clip_fraction=sum(x > plan.ADAPT['clip'] for x in norms) / len(norms)))
        except FloatingPointError as error:
            if arrays: raise                                                            # a study draw fails closed
            record = dict(stage=stage, width=width, lr=lr, tag=tag, status='DIVERGED', error=str(error)[:300], update=update, readouts=readouts, epochs=epochs, n_train=n)
            self.out.json(f'{name}/record.json', record)                               # review 1, finding 6: the rate is ineligible
            del optimizer, model; t.cuda.empty_cache(); g.full()
            return dict(path=f'{name}/record.json', tag=tag, lr=lr, readouts=readouts, status='DIVERGED')
        expected = plan.updates(n, fp.EPOCHS)
        if update != expected or any(int(s['step']) != expected for s in optimizer.state.values()): raise RuntimeError('Adaptation updates')
        if [r['epoch'] for r in readouts] != list(fp.READOUTS): raise RuntimeError('Readouts')
        record = dict(stage=stage, width=width, lr=lr, tag=tag, status='COMPLETE', readouts=readouts, epochs=epochs, n_train=n)
        if arrays:
            record['arrays'] = self.out.write(f'{name}/arrays.f32', b''.join(blocks))
            record['layout'] = dict(blocks=len(blocks), block_epochs=list(fp.READOUTS), train_rows=n, validation_rows=len(data['validation']),
                                    order='per readout: train per-sequence loss, then validation per-sequence loss (little-endian float32)')
        self.out.json(f'{name}/record.json', record)
        del optimizer, model; t.cuda.empty_cache(); g.full()
        return dict(path=f'{name}/record.json', tag=tag, lr=lr, readouts=readouts, status='COMPLETE')


def inputs(ctx, d, seeds, corpus, partition, n):
    e = ctx.engine
    idx = fd.sequences(partition, d, n)
    data = dict(train=e.load_sequences(corpus['train'], idx), validation=e.load_sequences(corpus['validation'], corpus['validation_indices']))
    pool = e.load_sequences(corpus['test'], corpus['pool_indices'])
    weights = e.weights(seeds['weight_seed'], n); orders = e.orders(seeds['adapt_order_seed'], n, fp.EPOCHS)
    pool_orders = e.orders(seeds['pretrain_order_seed'], len(pool), plan.PRETRAIN['epochs'])
    hashes = dict(train=e.tensor_hash(data['train']), validation=e.tensor_hash(data['validation']), pool=e.tensor_hash(pool),
                  weights=e.tensor_hash(weights), orders=e.tensor_hash(orders), pool_orders=e.tensor_hash(pool_orders))
    return idx, data, pool, weights, orders, pool_orders, hashes


def stage(ctx, mode, d, seeds, corpus, partition, n, lr=None):
    """One stage: t00 (tuning) or one analysis draw. Widest first: pre-training, the adaptations, then the width's model state
    hashed and deleted before the next width."""
    e, out, g = ctx.engine, ctx.out, ctx.guard; tuning = mode in fp.TUNING_MODES
    out.begin_stage(d); g.full()
    idx, data, pool, weights, orders, pool_orders, hashes = inputs(ctx, d, seeds, corpus, partition, n)
    out.json(f'{d}/INPUTS.json', dict(seeds=seeds, n_train=n, sequence_indices_sha256=sha(json.dumps(idx).encode()), articles=partition['groups'][d]['articles'], tensor_hashes=hashes,
                                      weights=[float(x) for x in weights.tolist()], rates=list(fp.RUN_A_RATES) if tuning else [lr], widths=list(fp.WIDTHS), readouts=list(fp.READOUTS)))
    pretrained, rows, per_width = {}, [], {}
    for w in fp.STAGE_ORDER:
        pretrained[w] = ctx.pretrain(d, w, seeds, pool, data, pool_orders)
        for r in (fp.RUN_A_RATES if tuning else (lr,)):
            res = ctx.adapt_readouts(d, w, r, fp.rate_tag(r) if tuning else fp.SELECTED_TAG, pretrained[w], seeds, data, weights, orders, arrays=not tuning)
            rows.append(dict(width=w, lr=r, readouts=res['readouts'], status=res['status']))
        per_width[str(w)] = remove_states(out.root, f'{d}/w{w}')
    out.json(f'{d}/PRETRAINED.json', {str(w): v for w, v in pretrained.items()})
    if e.tensor_hash(weights) != hashes['weights'] or e.tensor_hash(orders) != hashes['orders']: raise RuntimeError('Paired inputs changed')
    states = dict(per_width=per_width, deleted=[x for v in per_width.values() for x in v['deleted']], errors=[x for v in per_width.values() for x in v['errors']])
    states['deleted_bytes'] = sum(x['bytes'] for x in states['deleted'])
    out.json(f'{d}/STATES_DELETED.json', states)
    return rows, states


# ------------------------------------------------------------------ entry
def run(dependencies=None, here=None, out_root=None, clock=time.monotonic, corpus_dir=CORPUS, pins=PINS):
    here = Path(here) if here is not None else HERE
    mode = mode_of(here)
    if dependencies is None and not (HERE.resolve() == here.resolve() == ACTIVATIONS[mode].resolve()):
        raise PermissionError('The worker runs only from its one-use activation')          # the code that runs is the hash-checked copy
    out_root = Path(out_root) if out_root is not None else RUNS[mode]
    a, registry, manifest, partition, extra = authorization(here, corpus_dir, pins)
    if a.get('fixture') is not False and dependencies is None: raise PermissionError('A fixture activation runs only with injected test doubles')
    L = fp.LIMITS; start = clock(); budget = worker.Budget(start + L['overall_seconds'] - 120, clock)
    if out_root.exists(): raise FileExistsError('One-use run directory exists; no retry')
    if shutil.disk_usage(out_root.parent).free < L['admission_free_bytes']: raise RuntimeError('Admission free space')
    prestart_records = worker.prestart(here)
    out_root.mkdir()
    out = worker.Output(out_root, L['stage_storage_bytes'], L['stage_files'], L['storage_bytes'], L['total_files'])
    status = dict(kind='fewepoch', subject=a['source_subject_sha256'], mode=mode, status='STARTED', stages=[], bindings={k: a[k] for k in BINDING_KEYS if k in a},
                  n_train=extra['n'], learning_rate=extra.get('lr'))
    saved_limits = plan.LIMITS; guard = ctx = None; run_peaks = {}; code = 1; stages = fp.RUN_STAGES[mode]
    try:
        plan.LIMITS = dict(L)
        for name, raw in prestart_records: out.write(f'{worker.GATE_DIR}/{name}', raw)
        if dependencies is None:
            import text_framework_setup
            torch, engine, Model = text_framework_setup.setup(out_root / 'cache')
        else: torch, engine, Model = dependencies
        guard = worker.Guard(budget, out, cuda=torch.cuda); out.guard = guard
        ctx = Context(torch, engine, Model, guard, out)
        corpus = worker.load_corpus(manifest, corpus_dir)
        pool = engine.load_sequences(corpus['test'], corpus['pool_indices'])
        results, overheads, failure = startup_benchmark(ctx, registry['benchmark']['benchmark_seed'], pool, budget, clock)
        bench_states = remove_states(out_root, 'benchmark')
        counted = [x for x in bench_states['deleted'] if x['path'].endswith('.pt')]
        out.top_bytes -= sum(x['bytes'] for x in counted); out.top_files -= len(counted)
        bench_states['ledger_released'] = dict(bytes=sum(x['bytes'] for x in counted), files=len(counted))
        decision, reason = startup_rule(results, failure)
        bench_counts = dict(ctx.counts); ctx.counts = {k: 0 for k in ctx.counts}
        bench = dict(architectures=results, overheads=overheads)
        caps = study_cap(bench, mode, extra['n'], len(pool)) if decision == 'GO' else None
        status['startup'] = dict(decision=decision, reason=reason)
        status['benchmark'] = out.json('BENCHMARK.json', dict(benchmark=bench, failure=failure, startup=dict(decision=decision, reason=reason, fit_limit_bytes=fp.FIT_LIMIT_BYTES, guard_bytes=fp.GUARD_BYTES),
                                                              caps=caps, states=bench_states, benchmark_counts=bench_counts, guard_calls=dict(guard.calls), n_train=extra['n'], pool_n=len(pool)))
        if decision == 'STOP' or not caps['feasible']:
            status.update(status='STOPPED_AT_STARTUP', stop_reason=reason if decision == 'STOP' else 'STAGES_OVER_6_H'); return 1
        seeds = {row['group']: {k: v for k, v in row.items() if k != 'group'} for row in registry['groups']}
        device_used = lambda: (lambda free, total: total - free)(*torch.cuda.mem_get_info())
        for d in stages:
            draw_gate(out, here, d, budget, device_used, clock)
            stage_start = clock(); guard.peaks = {}
            reset = getattr(torch.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            guard.budget = worker.Budget(min(budget.deadline, stage_start + caps['stage_work_cap_seconds']), clock)
            rows, states = stage(ctx, mode, d, seeds[d], corpus, partition, extra['n'], extra.get('lr'))
            guard.budget = budget
            guard.full(); out.close_stage()
            for k, v in guard.peaks.items(): run_peaks[k] = max(run_peaks.get(k, 0), v)
            receipt = dict(stage=d, status='COMPLETE', trajectories=len(rows), seconds=clock() - stage_start, counts=dict(ctx.counts), guard_calls=dict(guard.calls),
                           peaks=dict(guard.peaks), states_deleted=len(states['deleted']), state_deletion_errors=len(states['errors']), closed_totals=list(out.closed), ledger_total=list(out.ledger_total()))
            out.json(f'{d}-RECEIPT.json', receipt); status['stages'].append(receipt)
        if mode in fp.TUNING_MODES:
            selection = dict(selection_from_records(out_root / fp.TUNING), n_train=extra['n'], mode=mode, group=fp.TUNING)
            status['lr_selection'] = out.json('LR_SELECTION.json', selection); status['selection_status'] = selection['status']; status['selected_rate'] = selection['selected_rate']
        status['status'] = 'COMPLETE'; code = 0
    except BaseException as error:
        status.update(status='FAILED', error=dict(type=type(error).__name__, message=str(error)[:400]), active_stage=out.stage)
        status['states_on_failure'] = {rel: remove_states(out_root, rel) for rel in ('benchmark', out.stage) if rel is not None}
        raise
    finally:
        plan.LIMITS = saved_limits
        if guard is not None:
            for k, v in guard.peaks.items(): run_peaks[k] = max(run_peaks.get(k, 0), v)
        status.update(elapsed_seconds=clock() - start, counts=dict(ctx.counts) if ctx else {}, peaks=run_peaks)
        out.stage = None; out.guard = None
        try:
            try:
                status['stage_folders'] = sorted(d for d in stages if (out_root / d).is_dir())
                status['counted_as_attempt'] = bool(status['stage_folders'])
            except Exception as e: status['stage_folders_error'] = f'{type(e).__name__}: {str(e)[:200]}'
            size, files = out.inventory(); status['inventory'] = dict(bytes=size, files=files)
            out.json('TERMINAL.json', status)
        except BaseException as e:
            sys.stderr.write('Terminal publication failed: ' + repr(e)[:300] + '\n')
            try:
                status['terminal_outside_ledger'] = f'{type(e).__name__}: {str(e)[:200]}'
                with open(out_root / 'TERMINAL.json', 'xb') as f: f.write(encoded(status))
            except BaseException as e2: sys.stderr.write('Terminal last-resort write failed: ' + repr(e2)[:300] + '\n')
    return code


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'run': raise SystemExit('usage: fewepoch_worker.py run')
    try: raise SystemExit(run())
    except PermissionError as e: sys.stderr.write(str(e) + '\n'); raise SystemExit(1)
