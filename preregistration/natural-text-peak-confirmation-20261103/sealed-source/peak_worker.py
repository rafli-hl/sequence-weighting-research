"""Peak confirmation: the worker (Linux/CUDA; owner decisions 20261103-03 and -04).

Disabled unless run from one of its one-use activations; the framework is imported lazily. Derived from the few-epoch worker
(fewepoch_worker.py, a byte copy here), whose classes and functions it uses unchanged where it can: Context (pretrain,
adapt_readouts), inputs, remove_states, draw_gate, classify; and text_worker's Budget, Guard, Output, benchmark, prestart.
What is new is the layout. Modes (from the activation's AUTHORIZATION.json): C1 (c01-c03) and C2 (c04-c06). Per draw, each
width is pre-trained once and adapted at each of its arms (pk.ARMS: 768 and 512 at 3e-4 and 1e-4, 384 at 3e-4), widest first,
from the one E0, with training and validation per-sequence losses at E0.25, E0.5, E1, E2 and E3; the width's state is hashed
and deleted after its arms. C2 is admitted only on C1's COMPLETE terminal under the same source subject and inputs.
Unchanged from the few-epoch worker: admission re-derives the registry and the partition and checks disjointness; the start-up
benchmark runs every width one at a time and stops the run before any training if a width exceeds 2.25 GiB; the cap is the same
formula on this run's exact counts, with one 30-minute gate wait reserved; a run over the 6-hour formula stops before any
training; before every stage the owner script's check covers the GPU and AC power; the counting rule (any stage folder makes
the run counted); TERMINAL.json through the ledger, or directly as a last resort with terminal_outside_ledger.
"""
import gc, json, math, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_worker as worker
import wt103_corpus
import fewepoch_plan as fp
import fewepoch_worker as fw
import peak_data as pd
import peak_registry as pr
import peak_plan as pk

ROOT = worker.ROOT
ACTIVATIONS = {m: ROOT / p for m, p in pk.ACTIVATIONS.items()}
RUNS = {m: ROOT / p for m, p in pk.RUNS.items()}
CORPUS = ROOT / pk.CORPUS
PINS = dict(registry_sha256=pk.REGISTRY['registry_sha256'], exclusions_sha256=pk.REGISTRY['exclusions_sha256'], draw_sha256=pk.REGISTRY['draw_sha256'],
            corpus_manifest_sha256=fp.CORPUS_MANIFEST_SHA256, partition_sha256=pk.PARTITION_SHA256, fewepoch_registry_sha256=fp.REGISTRY['registry_sha256'], fewepoch_partition_sha256=fp.PARTITION_SHA256)
BINDING_KEYS = ('approval_id', 'approval_record_sha256', 'registry_sha256', 'exclusions_sha256', 'draw_sha256', 'partition_sha256', 'corpus_manifest_sha256', 'fewepoch_registry_sha256', 'run_c1_terminal_sha256')
sha, encoded = worker.sha, worker.encoded


def mode_of(here):
    m = json.loads((Path(here) / 'AUTHORIZATION.json').read_bytes()).get('mode')
    if m not in pk.RUN_STAGES: raise PermissionError('DISABLED: no peak confirmation approval')
    return m


# ------------------------------------------------------------------ admission
def check_c1_terminal(raw, bindings, keys, subject):
    t = json.loads(raw)
    if t.get('kind') != 'peak' or t.get('mode') != 'C1' or t.get('status') != 'COMPLETE': raise PermissionError('Run C1 terminal is not COMPLETE')
    if t.get('subject') != subject: raise PermissionError('Run C1 ran under another source subject')
    if any((t.get('bindings') or {}).get(k) != bindings.get(k) for k in keys): raise PermissionError('Run C1 was bound to other inputs')
    return t


def authorization(here, corpus_dir=CORPUS, pins=PINS):
    """The one-use activation: enabled, a mode with its real path and a real approval, the sealed source unchanged, the
    approval record, the registry (re-derived from its own bytes), the WikiText-103 corpus manifest (sealed rules, the
    acquisition subject), the tokenizer, the few-epoch registry, the partition (re-derived) and its disjointness; for C2 Run
    C1's COMPLETE terminal."""
    here = Path(here); a = json.loads((here / 'AUTHORIZATION.json').read_bytes()); mode = a.get('mode')
    if a.get('enabled') is not True or a.get('execution_ready') is not True or mode not in pk.RUN_STAGES or a.get('one_use') is not True or not a.get('approval_id'):
        raise PermissionError('DISABLED: no peak confirmation approval')
    if here.resolve() == ACTIVATIONS[mode].resolve() and (a.get('fixture') is not False or str(a['approval_id']).upper().startswith('FIXTURE')): raise PermissionError('Real activation needs a real approval')
    if any(v is None for v in pins.values()): raise PermissionError('A pin is not set (PENDING)')
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
    try: registry = pr.validate(json.loads(reg_raw), ex_raw, draw_raw, pins['corpus_manifest_sha256'])
    except ValueError as e: raise PermissionError('Registry does not re-derive from its draw: ' + str(e))
    man_raw = (Path(corpus_dir) / 'CORPUS_MANIFEST.json').read_bytes()
    if len({sha(man_raw), a.get('corpus_manifest_sha256'), registry['corpus_manifest_sha256'], pins['corpus_manifest_sha256']}) != 1: raise PermissionError('Corpus manifest binding')
    manifest = json.loads(man_raw)
    try: wt103_corpus.validate_manifest(manifest, subject_hashes)
    except (ValueError, KeyError) as e: raise PermissionError('Corpus manifest differs from the pre-registration: ' + str(e))
    if manifest.get('source_subject_sha256') != fp.ACQUISITION_SUBJECT or manifest.get('fixture') is not False: raise PermissionError('Corpus was not made by the approved acquisition')
    if sha((Path(corpus_dir) / 'tokenizer.json').read_bytes()) != manifest['tokenizer']['sha256']: raise PermissionError('Tokenizer binding')
    few_raw = (here / 'FEWEPOCH_REGISTRY.json').read_bytes()
    if sha(few_raw) != a.get('fewepoch_registry_sha256') or sha(few_raw) != pins['fewepoch_registry_sha256']: raise PermissionError('Few-epoch registry binding')
    part_raw = (here / 'PARTITION.json').read_bytes()
    if sha(part_raw) != a.get('partition_sha256') or sha(part_raw) != pins['partition_sha256']: raise PermissionError('Partition binding')
    try: assigned = pd.assigned_articles(manifest, json.loads(few_raw)['partition_seed'], pins['fewepoch_partition_sha256'])
    except ValueError as e: raise PermissionError('Few-epoch partition: ' + str(e))
    partition = pd.partition(manifest, assigned, registry['partition_seed'])
    if json.loads(part_raw) != json.loads(encoded(partition)): raise PermissionError('Partition does not re-derive from the corpus and the registry')
    pd.disjoint(partition, manifest, assigned)
    if mode == 'C2':
        ours = dict(registry_sha256=a['registry_sha256'], partition_sha256=a['partition_sha256'], corpus_manifest_sha256=a['corpus_manifest_sha256'])
        t_raw = (here / 'RUN_C1_TERMINAL.json').read_bytes()
        if sha(t_raw) != a.get('run_c1_terminal_sha256'): raise PermissionError('Run C1 terminal binding')
        check_c1_terminal(t_raw, ours, tuple(ours), a['source_subject_sha256'])
    return a, registry, manifest, partition


# ------------------------------------------------------------------ start-up benchmark (no fallback; the few-epoch rule on this ladder)
def startup_benchmark(ctx, seed, pool, budget, clock):
    """text_worker.benchmark (sealed, unchanged) one width at a time in BENCH_WIDTHS order, each width with its own peaks
    (reset before it), all inside the 900 s benchmark budget. Stops at the first failing width."""
    t, g = ctx.torch, ctx.guard; start = clock(); results, overheads, failure = {}, None, None; saved = plan.WIDTHS
    g.budget = worker.Budget(min(budget.deadline, start + fp.LIMITS['benchmark_seconds']), clock)
    try:
        for w in pk.BENCH_WIDTHS:
            plan.WIDTHS = (w,); g.peaks = {}
            reset = getattr(t.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            t0 = clock()
            try: r = worker.benchmark(ctx, seed, fp.LIMITS['benchmark_seconds'], pool, clock)
            except Exception as e:
                failure = dict(width=w, kind=fw.classify(e), type=type(e).__name__, message=str(e)[:400], peaks=dict(g.peaks), seconds=clock() - t0); break
            results[str(w)] = dict(r['architectures'][str(w)], seconds=clock() - t0); overheads = r['overheads']
    finally:
        plan.WIDTHS = saved; g.budget = budget; gc.collect()
        empty = getattr(t.cuda, 'empty_cache', None)
        if empty is not None: empty()
    return results, overheads, failure


def startup_rule(results, failure, limit=fp.FIT_LIMIT_BYTES):
    for w in pk.BENCH_WIDTHS:
        if str(w) not in results: return 'STOP', f"FAILED_{(failure or {}).get('kind', 'INCOMPLETE')}_AT_{w}"
        pk_ = ((results[str(w)] or {}).get('peaks') or {}).get('device_used_sampled')
        if pk_ is None: return 'STOP', f'PEAK_MISSING_AT_{w}'
        if pk_ > limit: return 'STOP', f'PEAK_{w}_OVER_LIMIT'
    if failure is not None: return 'STOP', f"FAILED_{failure.get('kind')}_AT_{failure.get('width')}"
    return 'GO', 'ALL_WIDTHS_WITHIN_LIMIT'


def study_counts(n_train, n_pool, arms=None):
    """Exact per-stage counts of a layout {width: rates}: training and validation at every readout, arrays and a record per arm.
    On the few-epoch ladder with one rate per width they equal fewepoch_worker.study_counts for a B run."""
    arms = pk.ARMS if arms is None else arms; W = len(arms); A = sum(len(r) for r in arms.values()); R = len(fp.READOUTS); files = 3 + W * 2 + A * 2
    return dict(trajectories=A, adaptations_per_width={str(w): len(r) for w, r in arms.items()}, files=files, dirs=W + A, full_guards=2 + W + 2 * A, epoch_guards=W * plan.PRETRAIN['epochs'] + A * fp.EPOCHS + files,
                pre_updates=plan.updates(n_pool, plan.PRETRAIN['epochs']), adapt_updates=plan.updates(n_train, fp.EPOCHS), e0_eval_batches=plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION),
                readout_eval_batches=R * (plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION)), e0_bytes=4 * (n_train + plan.N_VALIDATION), array_bytes=4 * R * (n_train + plan.N_VALIDATION), arrays=True)


def study_cap(benchmark, mode, n_train, n_pool, arms=None):
    """The few-epoch cap formula on this layout's exact counts: cap = ceil(1.25 x projected + 120 s); feasible iff
    stages x (cap + 60) + 900 + 1,800 (one gate wait) <= 21,600 s."""
    arms = pk.ARMS if arms is None else arms; arch, o = benchmark['architectures'], benchmark['overheads']; c = study_counts(n_train, n_pool, arms)
    total = 30.0 + o['seconds_data_generation']
    fixed_write, per_byte = worker.write_model(arch)
    for w, rates in arms.items():
        b = arch[str(w)]
        total += c['pre_updates'] * b['seconds_per_pretraining_update'] + c['e0_eval_batches'] * b['seconds_per_eval_batch'] + b['seconds_per_state_write'] + fixed_write + per_byte * c['e0_bytes']
        total += len(rates) * (b['seconds_per_state_reload'] + c['adapt_updates'] * b['seconds_per_update'] + c['readout_eval_batches'] * b['seconds_per_eval_batch'] + 2 * fixed_write + per_byte * (c['array_bytes'] + plan.RECORD_BYTES))
    total += c['full_guards'] * (o['seconds_per_full_guard'] + (c['files'] + c['dirs'] + o['cache_entries']) * o['seconds_per_inventory_entry'])
    total += c['epoch_guards'] * o['seconds_per_epoch_guard']
    L = fp.LIMITS; n = len(pk.RUN_STAGES[mode])
    work = math.ceil(L['cap_multiplier'] * total + L['cap_fixed_seconds'])
    max_cap = (L['overall_seconds'] - L['benchmark_seconds'] - fp.GATE_RESERVE_SECONDS) / n - L['stage_slack_seconds']
    return dict(projected_stage_seconds=total, stage_work_cap_seconds=min(work, math.floor(max_cap)), feasible=work <= max_cap, stages=n, counts=c,
                formula=f"ceil({L['cap_multiplier']}*projected+{L['cap_fixed_seconds']}) <= {math.floor(max_cap)} s; {n}*(cap+{L['stage_slack_seconds']})+{L['benchmark_seconds']}+{fp.GATE_RESERVE_SECONDS} <= {L['overall_seconds']} s",
                write_model=dict(fixed_seconds=fixed_write, seconds_per_byte=per_byte))


# ------------------------------------------------------------------ one stage
def inputs(ctx, d, seeds, corpus, partition, n):
    """fewepoch_worker.inputs (sealed, unchanged) on this partition."""
    return fw.inputs(ctx, d, seeds, corpus, dict(n_fill=partition['n'], groups=partition['groups']), n)


def stage(ctx, d, seeds, corpus, partition, n, arms=None):
    """One draw. Widest first: pre-training, the width's arms from its one E0, then the width's model state hashed and deleted
    before the next width. A nonfinite update fails closed (the sealed adapt_readouts with arrays)."""
    arms = pk.ARMS if arms is None else arms; e, out, g = ctx.engine, ctx.out, ctx.guard
    out.begin_stage(d); g.full()
    idx, data, pool, weights, orders, pool_orders, hashes = inputs(ctx, d, seeds, corpus, partition, n)
    order = sorted(arms, reverse=True)
    out.json(f'{d}/INPUTS.json', dict(seeds=seeds, n_train=n, sequence_indices_sha256=sha(json.dumps(idx).encode()), articles=partition['groups'][d]['articles'], tensor_hashes=hashes,
                                      weights=[float(x) for x in weights.tolist()], arms={str(w): list(arms[w]) for w in order}, widths=sorted(arms), readouts=list(fp.READOUTS)))
    pretrained, rows, per_width = {}, [], {}
    for w in order:
        pretrained[w] = ctx.pretrain(d, w, seeds, pool, data, pool_orders)
        for r in arms[w]:
            res = ctx.adapt_readouts(d, w, r, fp.rate_tag(r), pretrained[w], seeds, data, weights, orders, arrays=True)
            rows.append(dict(width=w, lr=r, readouts=res['readouts'], status=res['status']))
        per_width[str(w)] = fw.remove_states(out.root, f'{d}/w{w}')
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
    a, registry, manifest, partition = authorization(here, corpus_dir, pins)
    if a.get('fixture') is not False and dependencies is None: raise PermissionError('A fixture activation runs only with injected test doubles')
    L = fp.LIMITS; start = clock(); budget = worker.Budget(start + L['overall_seconds'] - 120, clock); n = partition['n']
    if out_root.exists(): raise FileExistsError('One-use run directory exists; no retry')
    if shutil.disk_usage(out_root.parent).free < L['admission_free_bytes']: raise RuntimeError('Admission free space')
    prestart_records = worker.prestart(here)
    out_root.mkdir()
    out = worker.Output(out_root, L['stage_storage_bytes'], L['stage_files'], L['storage_bytes'], L['total_files'])
    status = dict(kind='peak', subject=a['source_subject_sha256'], mode=mode, status='STARTED', stages=[], bindings={k: a[k] for k in BINDING_KEYS if k in a}, n_train=n, arms={str(w): list(r) for w, r in pk.ARMS.items()})
    saved_limits = plan.LIMITS; guard = ctx = None; run_peaks = {}; code = 1; stages = pk.RUN_STAGES[mode]
    try:
        plan.LIMITS = dict(L)
        for name, raw in prestart_records: out.write(f'{worker.GATE_DIR}/{name}', raw)
        if dependencies is None:
            import text_framework_setup
            torch, engine, Model = text_framework_setup.setup(out_root / 'cache')
        else: torch, engine, Model = dependencies
        guard = worker.Guard(budget, out, cuda=torch.cuda); out.guard = guard
        ctx = fw.Context(torch, engine, Model, guard, out)
        corpus = worker.load_corpus(manifest, corpus_dir)
        pool = engine.load_sequences(corpus['test'], corpus['pool_indices'])
        results, overheads, failure = startup_benchmark(ctx, registry['benchmark']['benchmark_seed'], pool, budget, clock)
        bench_states = fw.remove_states(out_root, 'benchmark')
        counted = [x for x in bench_states['deleted'] if x['path'].endswith('.pt')]
        out.top_bytes -= sum(x['bytes'] for x in counted); out.top_files -= len(counted)
        bench_states['ledger_released'] = dict(bytes=sum(x['bytes'] for x in counted), files=len(counted))
        decision, reason = startup_rule(results, failure)
        bench_counts = dict(ctx.counts); ctx.counts = {k: 0 for k in ctx.counts}
        bench = dict(architectures=results, overheads=overheads)
        caps = study_cap(bench, mode, n, len(pool)) if decision == 'GO' else None
        status['startup'] = dict(decision=decision, reason=reason)
        status['benchmark'] = out.json('BENCHMARK.json', dict(benchmark=bench, failure=failure, startup=dict(decision=decision, reason=reason, fit_limit_bytes=fp.FIT_LIMIT_BYTES, guard_bytes=fp.GUARD_BYTES),
                                                              caps=caps, states=bench_states, benchmark_counts=bench_counts, guard_calls=dict(guard.calls), n_train=n, pool_n=len(pool)))
        if decision == 'STOP' or not caps['feasible']:
            status.update(status='STOPPED_AT_STARTUP', stop_reason=reason if decision == 'STOP' else 'STAGES_OVER_6_H'); return 1
        seeds = {row['group']: {k: v for k, v in row.items() if k != 'group'} for row in registry['groups']}
        device_used = lambda: (lambda free, total: total - free)(*torch.cuda.mem_get_info())
        for d in stages:
            fw.draw_gate(out, here, d, budget, device_used, clock)
            stage_start = clock(); guard.peaks = {}
            reset = getattr(torch.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            guard.budget = worker.Budget(min(budget.deadline, stage_start + caps['stage_work_cap_seconds']), clock)
            rows, states = stage(ctx, d, seeds[d], corpus, partition, n)
            guard.budget = budget
            guard.full(); out.close_stage()
            for k, v in guard.peaks.items(): run_peaks[k] = max(run_peaks.get(k, 0), v)
            receipt = dict(stage=d, status='COMPLETE', trajectories=len(rows), seconds=clock() - stage_start, counts=dict(ctx.counts), guard_calls=dict(guard.calls),
                           peaks=dict(guard.peaks), states_deleted=len(states['deleted']), state_deletion_errors=len(states['errors']), closed_totals=list(out.closed), ledger_total=list(out.ledger_total()))
            out.json(f'{d}-RECEIPT.json', receipt); status['stages'].append(receipt)
        status['status'] = 'COMPLETE'; code = 0
    except BaseException as error:
        status.update(status='FAILED', error=dict(type=type(error).__name__, message=str(error)[:400]), active_stage=out.stage)
        status['states_on_failure'] = {rel: fw.remove_states(out_root, rel) for rel in ('benchmark', out.stage) if rel is not None}
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
    if len(sys.argv) != 2 or sys.argv[1] != 'run': raise SystemExit('usage: peak_worker.py run')
    try: raise SystemExit(run())
    except PermissionError as e: sys.stderr.write(str(e) + '\n'); raise SystemExit(1)
