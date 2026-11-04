"""Natural-text one-rate ladder extension: the worker (Linux/CUDA; owner decisions 20261030-01 and -02).

Disabled unless run from its one-use activation; the framework is imported lazily. It runs on the same ten draws as
revision 05's COMPLETE Run B (onerate_plan.py), with revision 05's sealed classes and code paths unchanged (byte copies):
text_worker.Budget, Guard, Output, Context (pretrain, adapt), benchmark, gpu_gate and prestart.
1. Admission (review 1, findings 1 and 5): the real framework runs only when this file is the activation's copy and the
   activation is the bound one; the sealed source, the registry, corpus and partition re-derived as in revision 05; and Run
   B: its TERMINAL.json and its inventory pinned by sha256, and every Run B file that this run or its analysis reads
   checked against that inventory before the run folder exists (RunB.verify).
2. Start-up benchmark: text_worker.benchmark, one width at a time (64, 96, 512, 768), each width with its own peaks,
   under the 2.5 GiB guard and the 900 s benchmark budget. The start-up memory fallback (owner decision 20261030-02) sets
   the ladder top from the peak sampled device memory only (ladder_rule): 768 if its peak is within 2.25 GiB; 512 if 768
   is above it, stops on the guard, or stops on CUDA out of memory with its peak above it; otherwise the run stops before
   any training (STOPPED_AT_STARTUP), as it does if 64, 96 or 512 fails or is above the limit. The benchmark's model
   states are hashed and deleted. Revision 05's cap formula, applied to this run's per-stage counts (study_cap), must fit
   ten draws within 6 h, or the run stops before any training.
3. Per draw (after the owner script's Windows GPU check): the draw's inputs re-derived and checked equal to Run B's
   (seeds, sequence indices, tensor hashes and weights); 768 and 512 pre-trained and adapted at 3e-5; 96 and 64 adapted
   at 3e-5 from Run B's E0 states (copied after their hash checks; the sealed reload checks every tensor hash). Every model
   state written in the draw is then hashed and deleted (owner decision 20261030-01, item 4).
Revision 02 (owner ruling 20261030-03; the final attempt): before every draw the owner script's check covers the GPU and
AC power (power_gate.ps1); a stop whose last check was off AC power raises PowerGateError (review of revision 02,
finding 1), and TERMINAL.json records which draw folders exist (the ruling's counting test).
Any failure after the start-up benchmark ends the run FAILED; there is no retry, resume or replacement. On any failure
the worker observes (an exception inside it), the active draw's model states (and any benchmark state left) are hashed
and deleted, and recorded in TERMINAL.json (review 1, finding 3). A worker killed from outside (a WSL shutdown, the Linux
OOM killer, a host reboot) leaves the active draw's states and no TERMINAL.json; the owner's report lists them, and they
are deleted only on the owner's instruction. Deleted benchmark states are released from the output ledger (finding 4).
"""
import gc, hashlib, json, math, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_data
import text_registry
import text_worker as worker
import onerate_plan as op

ROOT = worker.ROOT
ACTIVATION = ROOT / op.ACTIVATION
RUN = ROOT / op.RUN
RUN_B = ROOT / op.RUN_B['run']
RUN_B_INVENTORY = ROOT / op.RUN_B['inventory']
CORPUS = worker.CORPUS
class PowerGateError(RuntimeError):
    """The Windows owner script's last check before a draw, at the end of its 30-minute window, found the laptop off AC
    power: on battery, or with the power status unreadable (revision 02)."""


def draw_gate(out, here, stage, budget, probe, clock):
    """Revision 05's gate (text_worker.gpu_gate, unchanged). A BUSY_TIMEOUT whose last check is off AC power (ON_BATTERY
    or POWER_UNVERIFIED) is a power stop (PowerGateError), whose message counts the checks on battery and those with the
    power status unreadable. Otherwise it is GpuBusyError as before; when earlier checks were off AC, its message carries
    the same counts (confirmation of the revision 02 review, N1)."""
    try: return worker.gpu_gate(out, here, stage, budget, probe=probe, clock=clock)
    except worker.GpuBusyError as e:
        checks = json.loads((out.root / worker.GATE_DIR / f'{stage}.json').read_bytes())['checks']
        battery = sum(c.get('verdict') == 'ON_BATTERY' for c in checks); unreadable = sum(c.get('verdict') == 'POWER_UNVERIFIED' for c in checks)
        counts = f'of {len(checks)} checks, {battery} on battery and {unreadable} with the power status unreadable (Windows power status)'
        if checks and checks[-1].get('verdict') in op.POWER_VERDICTS:
            raise PowerGateError(f"Not on AC power at the end of the 30-minute window before {stage} (last check {checks[-1]['verdict']}; {counts}); stopped before {stage}") from e
        if battery or unreadable: raise worker.GpuBusyError(f'{e} (last check {checks[-1].get("verdict")}; {counts})') from e
        raise


BINDING_KEYS = ('approval_id', 'approval_record_sha256', 'registry_sha256', 'exclusions_sha256', 'draw_sha256', 'partition_sha256', 'corpus_manifest_sha256',
                'run_b_terminal_sha256', 'run_b_inventory_sha256')
sha, encoded = worker.sha, worker.encoded


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


class RunB:
    """Revision 05's COMPLETE Run B, read-only. Every file used must equal its row in the pinned inventory."""
    def __init__(self, root=RUN_B, inventory=RUN_B_INVENTORY, pins=op.RUN_B):
        raw = Path(inventory).read_bytes()
        if sha(raw) != pins['inventory_sha256']: raise PermissionError('Run B inventory differs from its pin')
        self.root, self.files = Path(root), json.loads(raw)['run']['files']
        term_raw = self.read('TERMINAL.json')
        if sha(term_raw) != pins['terminal_sha256']: raise PermissionError('Run B terminal differs from its pin')
        t = json.loads(term_raw)
        if (t.get('status') != 'COMPLETE' or t.get('mode') != 'B' or t.get('subject') != pins['subject']
                or [s['stage'] for s in t.get('stages', [])] != list(plan.DRAWS) or any(s['status'] != 'COMPLETE' for s in t['stages'])): raise PermissionError('Run B is not the COMPLETE revision 05 run')
        b = t.get('bindings') or {}
        if any(b.get(k) != pins[k] for k in ('registry_sha256', 'partition_sha256', 'corpus_manifest_sha256', 'lr_selection_sha256')): raise PermissionError('Run B bindings differ from the pins')
        self.terminal, self.terminal_sha256, self.inventory_sha256 = t, sha(term_raw), sha(raw)

    def read(self, rel):
        row = self.files.get(rel)
        if row is None: raise PermissionError('Not in the Run B inventory: ' + rel)
        b = (self.root / rel).read_bytes()
        if len(b) != row[0] or sha(b) != row[1]: raise PermissionError('Run B file differs from its inventory: ' + rel)
        return b

    def json(self, rel): return json.loads(self.read(rel))

    def verify(self):
        """Every Run B file that this run or its analysis reads, checked against the inventory, and Run B's rate per
        width (review 1, finding 5): per draw INPUTS.json, PRETRAINED.json, every width's record, arrays and E0 arrays,
        and the E0 states of 64 and 96. Raises PermissionError."""
        n = size = 0
        for d in plan.DRAWS:
            pre = self.json(f'{d}/PRETRAINED.json'); rels = [f'{d}/INPUTS.json', f'{d}/PRETRAINED.json']
            for w in plan.WIDTHS:
                rec = self.json(f'{d}/w{w}/selected/record.json')
                if rec.get('width') != w or rec.get('lr') != op.RUN_B['rates'][w]: raise PermissionError(f'Run B record differs from its rate: {d} width {w}')
                rels += [f'{d}/w{w}/selected/record.json', rec['arrays']['path'], pre[str(w)]['E0_arrays']['path']]
            rels += [pre[str(w)]['state']['path'] for w in op.ADAPT_ONLY]
            for rel in rels: size += len(self.read(rel)); n += 1
        self.verified = dict(files=n, bytes=size)
        return self.verified


def authorization(here=ACTIVATION, corpus_dir=CORPUS, run_b=RUN_B, run_b_inventory=RUN_B_INVENTORY, run_b_pins=op.RUN_B):
    """The one-use activation: enabled, mode ONERATE, a real approval at the real path, the sealed source unchanged, the
    approval record, the registry, corpus manifest, tokenizer and partition re-derived as in revision 05, and Run B."""
    a = json.loads((here / 'AUTHORIZATION.json').read_bytes())
    if a.get('enabled') is not True or a.get('execution_ready') is not True or a.get('mode') != 'ONERATE' or a.get('one_use') is not True or not a.get('approval_id'):
        raise PermissionError('DISABLED: no one-rate ladder approval')
    if Path(here).resolve() == ACTIVATION.resolve() and (a.get('fixture') is not False or str(a['approval_id']).upper().startswith('FIXTURE')): raise PermissionError('Real activation needs a real approval')
    raw = (here / 'SOURCE_SUBJECT.json').read_bytes()
    if sha(raw) != a.get('source_subject_sha256'): raise PermissionError('Source subject differs from the authorization')
    if sha((here / 'APPROVAL_RECORD.json').read_bytes()) != a.get('approval_record_sha256'): raise PermissionError('Approval record binding')
    subject_hashes = {}
    for row in json.loads(raw)['files']:
        b = (here / row['path']).read_bytes()
        if len(b) != row['bytes'] or sha(b) != row['sha256']: raise PermissionError('Changed source ' + row['path'])
        subject_hashes[row['path']] = row['sha256']
    reg_raw, ex_raw, draw_raw = ((here / n).read_bytes() for n in ('REGISTRY.json', 'EXCLUSIONS.json', 'DRAW.json'))
    if (sha(reg_raw), sha(ex_raw), sha(draw_raw)) != (a.get('registry_sha256'), a.get('exclusions_sha256'), a.get('draw_sha256')): raise PermissionError('Registry binding')
    try: registry = text_registry.validate(json.loads(reg_raw), ex_raw, draw_raw)
    except ValueError as e: raise PermissionError('Registry does not re-derive from its draw: ' + str(e))
    man_raw = (corpus_dir / 'CORPUS_MANIFEST.json').read_bytes()
    if sha(man_raw) != a.get('corpus_manifest_sha256') or sha(man_raw) != registry['corpus_manifest_sha256']: raise PermissionError('Corpus manifest binding')
    manifest = json.loads(man_raw)
    try: text_data.validate_manifest(manifest, subject_hashes)
    except ValueError as e: raise PermissionError('Corpus manifest differs from the pre-registration: ' + str(e))
    if sha((corpus_dir / 'tokenizer.json').read_bytes()) != manifest['tokenizer']['sha256']: raise PermissionError('Tokenizer binding')
    part_raw = (here / 'PARTITION.json').read_bytes()
    if sha(part_raw) != a.get('partition_sha256'): raise PermissionError('Partition binding')
    partition = json.loads(part_raw)
    if partition != json.loads(encoded(text_data.partition(manifest, registry['partition_seed']))): raise PermissionError('Partition does not re-derive from the corpus and the registry')
    if any(a.get(k) != run_b_pins[k] for k in ('registry_sha256', 'exclusions_sha256', 'draw_sha256', 'partition_sha256', 'corpus_manifest_sha256')): raise PermissionError('Not Run B draws')
    rb = RunB(run_b, run_b_inventory, run_b_pins)
    if (a.get('run_b_terminal_sha256'), a.get('run_b_inventory_sha256')) != (rb.terminal_sha256, rb.inventory_sha256): raise PermissionError('Run B binding')
    rb.verify()
    return a, registry, manifest, partition, rb


# ------------------------------------------------------------------ start-up benchmark and the memory fallback
def classify(error):
    """Why a benchmark width stopped: the sampled-GPU guard, CUDA out of memory, the worker RSS limit, a timeout or other."""
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
    g.budget = worker.Budget(min(budget.deadline, start + plan.LIMITS['benchmark_seconds']), clock)
    try:
        for w in op.BENCH_WIDTHS:
            plan.WIDTHS = (w,); g.peaks = {}
            reset = getattr(t.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            t0 = clock()
            try: r = worker.benchmark(ctx, seed, plan.LIMITS['benchmark_seconds'], pool, clock)
            except Exception as e:
                failure = dict(width=w, kind=classify(e), type=type(e).__name__, message=str(e)[:400], peaks=dict(g.peaks), seconds=clock() - t0); break
            results[str(w)] = dict(r['architectures'][str(w)], seconds=clock() - t0); overheads = r['overheads']
    finally:
        plan.WIDTHS = saved; g.budget = budget; gc.collect()
        empty = getattr(t.cuda, 'empty_cache', None)
        if empty is not None: empty()
    return results, overheads, failure


def ladder_rule(results, failure, limit=op.FIT_LIMIT_BYTES):
    """The start-up memory fallback (owner decision 20261030-02), from each width's peak sampled device memory only.
    Returns (768 | 512 | 'STOP', reason)."""
    pk = lambda w: ((results.get(str(w)) or {}).get('peaks') or {}).get('device_used_sampled')
    for w in op.BENCH_WIDTHS[:-1]:
        if str(w) not in results: return 'STOP', f"FAILED_{(failure or {}).get('kind', 'INCOMPLETE')}_AT_{w}"
        if pk(w) is None: return 'STOP', f'PEAK_MISSING_AT_{w}'
        if pk(w) > limit: return 'STOP', f'PEAK_{w}_OVER_LIMIT'
    if failure is None:
        if pk(768) is None: return 'STOP', 'PEAK_MISSING_AT_768'
        return (768, 'PEAK_768_WITHIN_LIMIT') if pk(768) <= limit else (512, 'PEAK_768_OVER_LIMIT')
    at = (failure.get('peaks') or {}).get('device_used_sampled')
    if failure.get('width') == 768 and failure.get('kind') == 'GUARD': return 512, 'STOPPED_GUARD_AT_768'
    if failure.get('width') == 768 and failure.get('kind') == 'OOM' and at is not None and at > limit: return 512, 'STOPPED_OOM_AT_768'
    return 'STOP', f"FAILED_{failure.get('kind')}_AT_{failure.get('width')}"


def study_counts(top, n_train, n_pool):
    """Exact per-draw counts of this run's stage (compare text_worker.stage_counts)."""
    new, T, C = op.new_widths(top), len(op.trained_widths(top)), len(op.ADAPT_ONLY)
    files = 3 + 2 * len(new) + C + 2 * T      # INPUTS, PRETRAINED, STATES_DELETED; E0 state and arrays per new width; the E0 copy per adapt-only width; arrays and record per trajectory
    return dict(trajectories=T, new_widths=len(new), copies=C, files=files, dirs=2 * T, full_guards=2 + len(new) + 2 * T,
                epoch_guards=len(new) * plan.PRETRAIN['epochs'] + T * plan.ADAPT['epochs'] + files,
                pre_updates=plan.updates(n_pool, plan.PRETRAIN['epochs']), adapt_updates=plan.updates(n_train, plan.ADAPT['epochs']),
                e0_eval_batches=plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION),
                readout_eval_batches=len(plan.READOUTS) * (plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION)),
                e0_bytes=4 * (n_train + plan.N_VALIDATION), array_bytes=4 * len(plan.READOUTS) * (n_train + plan.N_VALIDATION))


def study_cap(benchmark, top, n_train, n_pool):
    """Revision 05's cap formula (text_worker.stage_cap: every measured per-call cost times its exact per-stage count;
    cap = ceil(1.25 x projected + 120 s); feasible iff 10 x (cap + 60) + 900 <= 21,600 s) on this run's stage: pre-training
    and E0 only for the new widths, the E0 copy for 64 and 96, one adaptation per trained width."""
    arch, o = benchmark['architectures'], benchmark['overheads']; c = study_counts(top, n_train, n_pool)
    total = 30.0 + o['seconds_data_generation']
    fixed_write, per_byte = worker.write_model(arch)
    for w in op.new_widths(top):
        b = arch[str(w)]
        total += c['pre_updates'] * b['seconds_per_pretraining_update'] + c['e0_eval_batches'] * b['seconds_per_eval_batch'] + b['seconds_per_state_write'] + fixed_write + per_byte * c['e0_bytes']
    for w in op.ADAPT_ONLY: total += fixed_write + per_byte * arch[str(w)]['state_bytes']
    for w in op.trained_widths(top):
        b = arch[str(w)]
        total += b['seconds_per_state_reload'] + c['adapt_updates'] * b['seconds_per_update'] + c['readout_eval_batches'] * b['seconds_per_eval_batch']
        total += 2 * fixed_write + per_byte * (c['array_bytes'] + plan.RECORD_BYTES)
    total += c['full_guards'] * (o['seconds_per_full_guard'] + (c['files'] + c['dirs'] + o['cache_entries']) * o['seconds_per_inventory_entry'])
    total += c['epoch_guards'] * o['seconds_per_epoch_guard']
    L = plan.LIMITS; n = len(plan.DRAWS)
    work = math.ceil(L['cap_multiplier'] * total + L['cap_fixed_seconds'])
    max_cap = (L['overall_seconds'] - L['benchmark_seconds']) / n - L['stage_slack_seconds']
    return dict(projected_stage_seconds=total, stage_work_cap_seconds=min(work, math.floor(max_cap)), feasible=work <= max_cap, stages=n, top=top, counts=c,
                formula=f"ceil({L['cap_multiplier']}*projected+{L['cap_fixed_seconds']}) <= {math.floor(max_cap)} s; {n}*(cap+{L['stage_slack_seconds']})+{L['benchmark_seconds']} <= {L['overall_seconds']} s",
                write_model=dict(fixed_seconds=fixed_write, seconds_per_byte=per_byte))


def remove_states(out_root, rel):
    """Every model state (and partial state write) under out_root/rel, recorded by sha256 and size, then deleted. Errors
    are recorded per file and never raised."""
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


# ------------------------------------------------------------------ one draw
def stage(ctx, d, seeds, corpus, groups, rb, top):
    """One draw: inputs re-derived and checked equal to Run B's; the new widths pre-trained; 96 and 64 from Run B's E0;
    every trained width adapted once at 3e-5; then every model state of the draw hashed and deleted."""
    e, out, g = ctx.engine, ctx.out, ctx.guard
    out.begin_stage(d); g.full()
    idx = groups[d]['sequences']
    data = dict(train=e.load_sequences(corpus['train'], idx), validation=e.load_sequences(corpus['validation'], corpus['validation_indices']))
    pool = e.load_sequences(corpus['test'], corpus['pool_indices'])
    n = len(idx)
    weights = e.weights(seeds['weight_seed'], n)
    orders = e.orders(seeds['adapt_order_seed'], n, plan.ADAPT['epochs'])
    pool_orders = e.orders(seeds['pretrain_order_seed'], len(pool), plan.PRETRAIN['epochs'])
    hashes = dict(train=e.tensor_hash(data['train']), validation=e.tensor_hash(data['validation']), pool=e.tensor_hash(pool),
                  weights=e.tensor_hash(weights), orders=e.tensor_hash(orders), pool_orders=e.tensor_hash(pool_orders))
    b_raw = rb.read(f'{d}/INPUTS.json'); b_in = json.loads(b_raw); listed = [float(x) for x in weights.tolist()]
    paired = dict(seeds=b_in['seeds'] == seeds, n_train=b_in['n_train'] == n, sequence_indices=b_in['sequence_indices_sha256'] == sha(json.dumps(idx).encode()),
                  tensor_hashes=b_in['tensor_hashes'] == hashes, weights=b_in['weights'] == listed)
    if not all(paired.values()): raise RuntimeError('Draw inputs differ from Run B: ' + ', '.join(k for k, v in paired.items() if not v))
    out.json(f'{d}/INPUTS.json', dict(seeds=seeds, n_train=n, sequence_indices_sha256=sha(json.dumps(idx).encode()), tensor_hashes=hashes, weights=listed,
                                      learning_rate=op.LR, top=top, run_b_inputs_sha256=sha(b_raw), paired_with_run_b=paired))
    b_pre = rb.json(f'{d}/PRETRAINED.json'); pretrained = {}
    for w in sorted(op.new_widths(top), reverse=True): pretrained[w] = ctx.pretrain(d, w, seeds, pool, data, pool_orders)
    for w in sorted(op.ADAPT_ONLY, reverse=True):
        bp = b_pre[str(w)]; raw = rb.read(bp['state']['path'])
        if len(raw) != bp['state']['bytes'] or sha(raw) != bp['state']['sha256']: raise RuntimeError('Run B E0 state differs from its record: ' + bp['state']['path'])
        pretrained[w] = dict(width=w, source='run_b', state=out.write(f'{d}/w{w}/E0.pt', raw), run_b_state=bp['state'], run_b_E0_arrays=bp['E0_arrays'],
                             state_tensor_hashes=bp['state_tensor_hashes'], E0_train_loss=bp['E0_train_loss'], E0_validation_loss=bp['E0_validation_loss'])
    out.json(f'{d}/PRETRAINED.json', {str(w): v for w, v in pretrained.items()})
    rows = [ctx.adapt(d, w, op.LR, op.TAG, pretrained[w], seeds, data, weights, orders) for w in op.trained_widths(top)]
    if e.tensor_hash(weights) != hashes['weights'] or e.tensor_hash(orders) != hashes['orders']: raise RuntimeError('Paired inputs changed')
    states = remove_states(out.root, d)
    out.json(f'{d}/STATES_DELETED.json', states)
    return rows, states


# ------------------------------------------------------------------ entry
def run(dependencies=None, here=ACTIVATION, out_root=RUN, clock=time.monotonic, corpus_dir=CORPUS, run_b=RUN_B, run_b_inventory=RUN_B_INVENTORY, run_b_pins=op.RUN_B):
    if dependencies is None and not (HERE.resolve() == Path(here).resolve() == ACTIVATION.resolve()):
        raise PermissionError('The worker runs only from its one-use activation')          # the code that runs is the hash-checked copy (review 1, finding 1)
    a, registry, manifest, partition, rb = authorization(here, corpus_dir, run_b, run_b_inventory, run_b_pins)
    if a.get('fixture') is not False and dependencies is None: raise PermissionError('A fixture activation runs only with injected test doubles')
    L = op.LIMITS; start = clock(); budget = worker.Budget(start + L['overall_seconds'] - 120, clock)
    if out_root.exists(): raise FileExistsError('One-use run directory exists; no retry')
    if shutil.disk_usage(out_root.parent).free < L['admission_free_bytes']: raise RuntimeError('Admission free space')
    prestart_records = worker.prestart(here)                    # the owner script's Windows IDLE check, made before its claim
    out_root.mkdir()
    out = worker.Output(out_root, L['stage_storage_bytes'], L['stage_files'], L['storage_bytes'], L['total_files'])
    status = dict(kind='onerate', subject=a['source_subject_sha256'], mode='ONERATE', status='STARTED', stages=[], bindings={k: a[k] for k in BINDING_KEYS if k in a},
                  run_b_verified=rb.verified)
    saved_limits = plan.LIMITS; guard = ctx = None; run_peaks = {}; code = 1
    try:
        plan.LIMITS = dict(L)                                   # the run's limits, including the 2.5 GiB guard; restored below
        for name, raw in prestart_records: out.write(f'{worker.GATE_DIR}/{name}', raw)
        if dependencies is None:
            import text_framework_setup
            torch, engine, Model = text_framework_setup.setup(out_root / 'cache')
        else: torch, engine, Model = dependencies
        guard = worker.Guard(budget, out, cuda=torch.cuda); out.guard = guard
        ctx = worker.Context(torch, engine, Model, guard, out)
        corpus = worker.load_corpus(manifest, corpus_dir)
        pool = engine.load_sequences(corpus['test'], corpus['pool_indices'])
        results, overheads, failure = startup_benchmark(ctx, registry['benchmark']['benchmark_seed'], pool, budget, clock)
        bench_states = remove_states(out_root, 'benchmark')
        counted = [x for x in bench_states['deleted'] if x['path'].endswith('.pt')]          # written through the ledger; partial writes never were
        out.top_bytes -= sum(x['bytes'] for x in counted); out.top_files -= len(counted)
        bench_states['ledger_released'] = dict(bytes=sum(x['bytes'] for x in counted), files=len(counted))
        top, reason = ladder_rule(results, failure)
        bench_counts = dict(ctx.counts); ctx.counts = {k: 0 for k in ctx.counts}         # scientific counts exclude the benchmark
        bench = dict(architectures=results, overheads=overheads)
        caps = study_cap(bench, top, partition['n'], len(pool)) if top in (512, 768) else None
        status['ladder'] = dict(top=top, reason=reason)
        status['benchmark'] = out.json('BENCHMARK.json', dict(benchmark=bench, failure=failure, ladder=dict(top=top, reason=reason, fit_limit_bytes=op.FIT_LIMIT_BYTES, guard_bytes=op.GUARD_BYTES),
                                                              caps=caps, states=bench_states, benchmark_counts=bench_counts, guard_calls=dict(guard.calls), partition_n=partition['n'], pool_n=len(pool)))
        if top == 'STOP' or not caps['feasible']:
            status.update(status='STOPPED_AT_STARTUP', stop_reason=reason if top == 'STOP' else 'TEN_DRAWS_OVER_6_H'); return 1
        seeds = {row['group']: {k: v for k, v in row.items() if k != 'group'} for row in registry['groups']}
        device_used = lambda: (lambda free, total: total - free)(*torch.cuda.mem_get_info())
        for d in plan.DRAWS:
            draw_gate(out, here, d, budget, device_used, clock)                                 # GPU and AC power; outside the draw's work cap
            stage_start = clock(); guard.peaks = {}
            reset = getattr(torch.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            guard.budget = worker.Budget(min(budget.deadline, stage_start + caps['stage_work_cap_seconds']), clock)
            rows, states = stage(ctx, d, seeds[d], corpus, partition['groups'], rb, top)
            guard.budget = budget
            guard.full(); out.close_stage()
            for k, v in guard.peaks.items(): run_peaks[k] = max(run_peaks.get(k, 0), v)
            receipt = dict(stage=d, status='COMPLETE', top=top, trajectories=len(rows), seconds=clock() - stage_start, counts=dict(ctx.counts), guard_calls=dict(guard.calls),
                           peaks=dict(guard.peaks), states_deleted=len(states['deleted']), state_deletion_errors=len(states['errors']), closed_totals=list(out.closed), ledger_total=list(out.ledger_total()))
            out.json(f'{d}-RECEIPT.json', receipt); status['stages'].append(receipt)
        status['status'] = 'COMPLETE'; code = 0
    except BaseException as error:
        status.update(status='FAILED', error=dict(type=type(error).__name__, message=str(error)[:400]), active_stage=out.stage)
        status['states_on_failure'] = {rel: remove_states(out_root, rel) for rel in ('benchmark', out.stage) if rel is not None}   # never raises
        raise
    finally:
        plan.LIMITS = saved_limits
        if guard is not None:
            for k, v in guard.peaks.items(): run_peaks[k] = max(run_peaks.get(k, 0), v)
        status.update(elapsed_seconds=clock() - start, counts=dict(ctx.counts) if ctx else {}, peaks=run_peaks)
        out.stage = None; out.guard = None
        try:
            try:                                                                                      # owner ruling 20261030-03: any draw folder makes this run
                status['draw_folders'] = sorted(d for d in plan.DRAWS if (out_root / d).is_dir())     # the final attempt; a scan error is recorded and never
                status['counted_as_final_attempt'] = bool(status['draw_folders'])                     # blocks the terminal (review of revision 02, finding 4)
            except Exception as e: status['draw_folders_error'] = f'{type(e).__name__}: {str(e)[:200]}'
            size, files = out.inventory(); status['inventory'] = dict(bytes=size, files=files)
            out.json('TERMINAL.json', status)
        except BaseException as e: sys.stderr.write('Terminal publication failed: ' + repr(e)[:300] + '\n')
    return code


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'run': raise SystemExit('usage: onerate_worker.py run')
    try: raise SystemExit(run())
    except PermissionError as e: sys.stderr.write(str(e) + '\n'); raise SystemExit(1)
