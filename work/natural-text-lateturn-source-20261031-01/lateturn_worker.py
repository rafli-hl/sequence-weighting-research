"""Late-turn confirmation: the worker (Linux/CUDA; owner decisions 20261031-02 and -03).

Disabled unless run from its one-use activation; the framework is imported lazily. Derived from the one-rate worker
(work/natural-text-onerate-source-20261030-02/onerate_worker.py, revision 02), with revision 05's sealed classes and code
paths unchanged (byte copies): text_worker.Budget, Guard, Output, Context (pretrain, adapt), benchmark, gpu_gate and
prestart. Changes from the one-rate worker:
- no Run B: the four fresh draws f01-f04 of the drawn late-turn registry, every width (256, 384, 512, 768) pre-trained
  and adapted here at 3e-5;
- admission re-derives the fresh partition (lateturn_data, sealed before any seed existed) from the corpus manifest, the
  seen registry's partition value and the late-turn registry, checks it against its pin and checks, by article, that the
  four groups are disjoint from each other and from t00 and d01-d10; the builder's cross-split check (FRESH_CHECK.json:
  every validation and test article by title and text) is bound and must read zero overlaps;
- start-up benchmark on 256, 384, 512 and 768, each width with its own peaks: every width must be within 2.25 GiB, or the
  run stops before any training (STOPPED_AT_STARTUP; no fallback, because every primary needs 768);
- per draw, each width is pre-trained, adapted once, and its model state then hashed and deleted before the next width
  (owner decisions 20261031-02, item 6), so at most one state exists at a time.
Unchanged: before every draw the owner script's check covers the GPU and AC power (power_gate.ps1); a stop whose last
check was off AC power raises PowerGateError; TERMINAL.json records which draw folders exist (the counting rule, owner
decisions 20261031-02, item 7). Any failure after the start-up benchmark ends the run FAILED; there is no retry, resume or
replacement. On any failure the worker observes, the active draw's model state (and any benchmark state left) is hashed,
deleted and recorded in TERMINAL.json. TERMINAL.json is written through the output ledger or, if that write fails, directly
as a last resort (review 1, finding 8); a worker killed from outside leaves at most one state and no TERMINAL.json.
Review 1 (subject d3d7d63a): disjoint() also maps every sequence to its group's articles, and admission requires every
overlap count of the builder's fresh check to be zero (finding 6).
"""
import gc, hashlib, json, math, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_data
import text_worker as worker
import lateturn_data
import lateturn_registry
import lateturn_plan as lp

ROOT = worker.ROOT
ACTIVATION = ROOT / lp.ACTIVATION
RUN = ROOT / lp.RUN
CORPUS = worker.CORPUS
PINS = dict(registry_sha256=lp.REGISTRY['registry_sha256'], exclusions_sha256=lp.REGISTRY['exclusions_sha256'], draw_sha256=lp.REGISTRY['draw_sha256'],
            corpus_manifest_sha256=lp.CORPUS_MANIFEST_SHA256, seen_registry_sha256=lp.SEEN['registry_sha256'], seen_partition_sha256=lp.SEEN['partition_sha256'],
            fresh_partition_sha256=lp.FRESH_PARTITION_SHA256)


class PowerGateError(RuntimeError):
    """The Windows owner script's last check before a draw, at the end of its 30-minute window, found the laptop off AC
    power: on battery, or with the power status unreadable."""


def draw_gate(out, here, stage, budget, probe, clock):
    """Revision 05's gate (text_worker.gpu_gate, unchanged). A BUSY_TIMEOUT whose last check is off AC power (ON_BATTERY
    or POWER_UNVERIFIED) is a power stop (PowerGateError), whose message counts the checks on battery and those with the
    power status unreadable. Otherwise it is GpuBusyError as before; when earlier checks were off AC, its message carries
    the same counts. (The one-rate worker's draw_gate, unchanged.)"""
    try: return worker.gpu_gate(out, here, stage, budget, probe=probe, clock=clock)
    except worker.GpuBusyError as e:
        checks = json.loads((out.root / worker.GATE_DIR / f'{stage}.json').read_bytes())['checks']
        battery = sum(c.get('verdict') == 'ON_BATTERY' for c in checks); unreadable = sum(c.get('verdict') == 'POWER_UNVERIFIED' for c in checks)
        counts = f'of {len(checks)} checks, {battery} on battery and {unreadable} with the power status unreadable (Windows power status)'
        if checks and checks[-1].get('verdict') in lp.POWER_VERDICTS:
            raise PowerGateError(f"Not on AC power at the end of the 30-minute window before {stage} (last check {checks[-1]['verdict']}; {counts}); stopped before {stage}") from e
        if battery or unreadable: raise worker.GpuBusyError(f'{e} (last check {checks[-1].get("verdict")}; {counts})') from e
        raise


BINDING_KEYS = ('approval_id', 'approval_record_sha256', 'registry_sha256', 'exclusions_sha256', 'draw_sha256', 'partition_sha256', 'corpus_manifest_sha256',
                'seen_registry_sha256', 'fresh_check_sha256')
sha, encoded = worker.sha, worker.encoded


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def fresh_partition(manifest, seen_registry, registry):
    """The fresh partition and the seen one, re-derived (lateturn_data, sealed before any seed existed)."""
    seen = lateturn_data.seen_partition(manifest, seen_registry['partition_seed'])
    return lateturn_data.fresh_partition(manifest, lateturn_data.used_articles(seen), registry['partition_seed']), seen


def disjoint(partition, seen, manifest):
    """By article: the four groups are disjoint from each other and from every article of t00 and d01-d10, and each holds
    exactly N distinct sequences, every one inside its own group's articles (mapped through the manifest's training
    article offsets; review 1, finding 6). Raises PermissionError."""
    used = lateturn_data.used_articles(seen); arts = [a for g in lp.DRAWS for a in partition['groups'][g]['articles']]
    if sorted(partition['groups']) != sorted(lp.DRAWS): raise PermissionError('Fresh partition groups differ from f01-f04')
    if len(arts) != len(set(arts)): raise PermissionError('Fresh groups share an article')
    if set(arts) & used: raise PermissionError('A fresh group uses an article of t00 or d01-d10')
    offsets = {a['index']: (a['first'], a['sequences']) for a in manifest['splits']['train']['articles']}
    for g in lp.DRAWS:
        seqs = partition['groups'][g]['sequences']
        if len(seqs) != partition['n'] or len(set(seqs)) != len(seqs): raise PermissionError('Fresh group size: ' + g)
        own = {offsets[a][0] + k for a in partition['groups'][g]['articles'] for k in range(offsets[a][1])}
        if not set(seqs) <= own: raise PermissionError('A fresh sequence lies outside its group\'s articles: ' + g)
    return dict(fresh_articles=len(arts), used_articles=len(used), n=partition['n'])


def authorization(here=ACTIVATION, corpus_dir=CORPUS, pins=PINS):
    """The one-use activation: enabled, mode LATETURN, a real approval at the real path, the sealed source unchanged, the
    approval record, the drawn late-turn registry (re-derived from its own bytes), the corpus manifest, tokenizer, the seen
    registry, the fresh partition re-derived and disjoint from the seen draws, and the builder's cross-split check."""
    a = json.loads((here / 'AUTHORIZATION.json').read_bytes())
    if a.get('enabled') is not True or a.get('execution_ready') is not True or a.get('mode') != 'LATETURN' or a.get('one_use') is not True or not a.get('approval_id'):
        raise PermissionError('DISABLED: no late-turn confirmation approval')
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
    got = (sha(reg_raw), sha(ex_raw), sha(draw_raw))
    if got != (a.get('registry_sha256'), a.get('exclusions_sha256'), a.get('draw_sha256')) or got != (pins['registry_sha256'], pins['exclusions_sha256'], pins['draw_sha256']):
        raise PermissionError('Registry binding')
    try: registry = lateturn_registry.validate(json.loads(reg_raw), ex_raw, draw_raw)
    except ValueError as e: raise PermissionError('Registry does not re-derive from its draw: ' + str(e))
    man_raw = (corpus_dir / 'CORPUS_MANIFEST.json').read_bytes()
    if len({sha(man_raw), a.get('corpus_manifest_sha256'), registry['corpus_manifest_sha256'], pins['corpus_manifest_sha256']}) != 1: raise PermissionError('Corpus manifest binding')
    manifest = json.loads(man_raw)
    try: text_data.validate_manifest(manifest, subject_hashes)
    except ValueError as e: raise PermissionError('Corpus manifest differs from the pre-registration: ' + str(e))
    if sha((corpus_dir / 'tokenizer.json').read_bytes()) != manifest['tokenizer']['sha256']: raise PermissionError('Tokenizer binding')
    seen_raw = (here / 'SEEN_REGISTRY.json').read_bytes()
    if sha(seen_raw) != a.get('seen_registry_sha256') or sha(seen_raw) != pins['seen_registry_sha256']: raise PermissionError('Seen registry binding')
    part_raw = (here / 'PARTITION.json').read_bytes()
    if sha(part_raw) != a.get('partition_sha256') or sha(part_raw) != pins['fresh_partition_sha256']: raise PermissionError('Partition binding')
    partition, seen = fresh_partition(manifest, json.loads(seen_raw), registry)
    if sha(encoded(seen)) != pins['seen_partition_sha256']: raise PermissionError('Seen partition does not re-derive from the corpus and the seen registry')
    if json.loads(part_raw) != json.loads(encoded(partition)): raise PermissionError('Partition does not re-derive from the corpus and the registries')
    disjoint(partition, seen, manifest)
    check_raw = (here / 'FRESH_CHECK.json').read_bytes(); check = json.loads(check_raw); overlaps = check.get('overlaps') or {}
    if (sha(check_raw) != a.get('fresh_check_sha256') or check.get('status') != 'PASS' or check.get('partition_sha256') != sha(part_raw)
            or not overlaps or any(v != 0 for v in overlaps.values())): raise PermissionError('Fresh-article check binding')
    return a, registry, manifest, partition


# ------------------------------------------------------------------ start-up benchmark (no fallback)
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
    (reset before it), all inside the 900 s benchmark budget. Stops at the first failing width. (The one-rate worker's
    startup_benchmark on this study's widths.)"""
    t, g = ctx.torch, ctx.guard; start = clock(); results, overheads, failure = {}, None, None; saved = plan.WIDTHS
    g.budget = worker.Budget(min(budget.deadline, start + plan.LIMITS['benchmark_seconds']), clock)
    try:
        for w in lp.BENCH_WIDTHS:
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


def startup_rule(results, failure, limit=lp.FIT_LIMIT_BYTES):
    """Every width's peak sampled device memory must be within 2.25 GiB (inclusive) and every width must complete; there
    is no fallback. Returns ('GO' | 'STOP', reason)."""
    for w in lp.BENCH_WIDTHS:
        if str(w) not in results: return 'STOP', f"FAILED_{(failure or {}).get('kind', 'INCOMPLETE')}_AT_{w}"
        pk = ((results[str(w)] or {}).get('peaks') or {}).get('device_used_sampled')
        if pk is None: return 'STOP', f'PEAK_MISSING_AT_{w}'
        if pk > limit: return 'STOP', f'PEAK_{w}_OVER_LIMIT'
    if failure is not None: return 'STOP', f"FAILED_{failure.get('kind')}_AT_{failure.get('width')}"
    return 'GO', 'ALL_WIDTHS_WITHIN_LIMIT'


def study_counts(n_train, n_pool):
    """Exact per-draw counts of this run's stage (compare text_worker.stage_counts): every width pre-trained and adapted."""
    W = len(lp.WIDTHS)
    files = 3 + 4 * W                     # INPUTS, PRETRAINED, STATES_DELETED; per width the E0 state, E0 arrays, arrays and record
    return dict(trajectories=W, new_widths=W, files=files, dirs=2 * W, full_guards=2 + 3 * W,
                epoch_guards=W * plan.PRETRAIN['epochs'] + W * plan.ADAPT['epochs'] + files,
                pre_updates=plan.updates(n_pool, plan.PRETRAIN['epochs']), adapt_updates=plan.updates(n_train, plan.ADAPT['epochs']),
                e0_eval_batches=plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION),
                readout_eval_batches=len(plan.READOUTS) * (plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION)),
                e0_bytes=4 * (n_train + plan.N_VALIDATION), array_bytes=4 * len(plan.READOUTS) * (n_train + plan.N_VALIDATION))


def study_cap(benchmark, n_train, n_pool):
    """Revision 05's cap formula (text_worker.stage_cap: every measured per-call cost times its exact per-stage count;
    cap = ceil(1.25 x projected + 120 s); feasible iff draws x (cap + 60) + 900 <= 21,600 s) on this run's stage: every
    width pre-trained (with its E0 state and arrays) and adapted once. Hashing and deleting each state is not a measured
    cost; the 1.25 multiplier covers it."""
    arch, o = benchmark['architectures'], benchmark['overheads']; c = study_counts(n_train, n_pool)
    total = 30.0 + o['seconds_data_generation']
    fixed_write, per_byte = worker.write_model(arch)
    for w in lp.WIDTHS:
        b = arch[str(w)]
        total += c['pre_updates'] * b['seconds_per_pretraining_update'] + c['e0_eval_batches'] * b['seconds_per_eval_batch'] + b['seconds_per_state_write'] + fixed_write + per_byte * c['e0_bytes']
        total += b['seconds_per_state_reload'] + c['adapt_updates'] * b['seconds_per_update'] + c['readout_eval_batches'] * b['seconds_per_eval_batch']
        total += 2 * fixed_write + per_byte * (c['array_bytes'] + plan.RECORD_BYTES)
    total += c['full_guards'] * (o['seconds_per_full_guard'] + (c['files'] + c['dirs'] + o['cache_entries']) * o['seconds_per_inventory_entry'])
    total += c['epoch_guards'] * o['seconds_per_epoch_guard']
    L = plan.LIMITS; n = len(lp.DRAWS)
    work = math.ceil(L['cap_multiplier'] * total + L['cap_fixed_seconds'])
    max_cap = (L['overall_seconds'] - L['benchmark_seconds']) / n - L['stage_slack_seconds']
    return dict(projected_stage_seconds=total, stage_work_cap_seconds=min(work, math.floor(max_cap)), feasible=work <= max_cap, stages=n, counts=c,
                formula=f"ceil({L['cap_multiplier']}*projected+{L['cap_fixed_seconds']}) <= {math.floor(max_cap)} s; {n}*(cap+{L['stage_slack_seconds']})+{L['benchmark_seconds']} <= {L['overall_seconds']} s",
                write_model=dict(fixed_seconds=fixed_write, seconds_per_byte=per_byte))


def remove_states(out_root, rel):
    """Every model state (and partial state write) under out_root/rel, recorded by sha256 and size, then deleted. Errors
    are recorded per file and never raised. (The one-rate worker's remove_states, unchanged.)"""
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
def stage(ctx, d, seeds, corpus, groups):
    """One fresh draw: its inputs; then per width, widest first, pre-training, one adaptation at 3e-5, and the width's
    model state hashed and deleted before the next width (owner decisions 20261031-02, item 6)."""
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
    out.json(f'{d}/INPUTS.json', dict(seeds=seeds, n_train=n, sequence_indices_sha256=sha(json.dumps(idx).encode()), articles=groups[d]['articles'], tensor_hashes=hashes,
                                      weights=[float(x) for x in weights.tolist()], learning_rate=lp.LR, widths=list(lp.WIDTHS)))
    pretrained, rows, per_width = {}, [], {}
    for w in lp.STAGE_ORDER:
        pretrained[w] = ctx.pretrain(d, w, seeds, pool, data, pool_orders)
        rows.append(ctx.adapt(d, w, lp.LR, lp.TAG, pretrained[w], seeds, data, weights, orders))
        per_width[str(w)] = remove_states(out.root, f'{d}/w{w}')
    out.json(f'{d}/PRETRAINED.json', {str(w): v for w, v in pretrained.items()})
    if e.tensor_hash(weights) != hashes['weights'] or e.tensor_hash(orders) != hashes['orders']: raise RuntimeError('Paired inputs changed')
    states = dict(per_width=per_width, deleted=[x for v in per_width.values() for x in v['deleted']], errors=[x for v in per_width.values() for x in v['errors']])
    states['deleted_bytes'] = sum(x['bytes'] for x in states['deleted'])
    out.json(f'{d}/STATES_DELETED.json', states)
    return rows, states


# ------------------------------------------------------------------ entry
def run(dependencies=None, here=ACTIVATION, out_root=RUN, clock=time.monotonic, corpus_dir=CORPUS, pins=PINS):
    if dependencies is None and not (HERE.resolve() == Path(here).resolve() == ACTIVATION.resolve()):
        raise PermissionError('The worker runs only from its one-use activation')          # the code that runs is the hash-checked copy
    a, registry, manifest, partition = authorization(here, corpus_dir, pins)
    if a.get('fixture') is not False and dependencies is None: raise PermissionError('A fixture activation runs only with injected test doubles')
    L = lp.LIMITS; start = clock(); budget = worker.Budget(start + L['overall_seconds'] - 120, clock)
    if out_root.exists(): raise FileExistsError('One-use run directory exists; no retry')
    if shutil.disk_usage(out_root.parent).free < L['admission_free_bytes']: raise RuntimeError('Admission free space')
    prestart_records = worker.prestart(here)                    # the owner script's Windows IDLE check, made before its claim
    out_root.mkdir()
    out = worker.Output(out_root, L['stage_storage_bytes'], L['stage_files'], L['storage_bytes'], L['total_files'])
    status = dict(kind='lateturn', subject=a['source_subject_sha256'], mode='LATETURN', status='STARTED', stages=[], bindings={k: a[k] for k in BINDING_KEYS if k in a})
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
        decision, reason = startup_rule(results, failure)
        bench_counts = dict(ctx.counts); ctx.counts = {k: 0 for k in ctx.counts}         # scientific counts exclude the benchmark
        bench = dict(architectures=results, overheads=overheads)
        caps = study_cap(bench, partition['n'], len(pool)) if decision == 'GO' else None
        status['startup'] = dict(decision=decision, reason=reason)
        status['benchmark'] = out.json('BENCHMARK.json', dict(benchmark=bench, failure=failure, startup=dict(decision=decision, reason=reason, fit_limit_bytes=lp.FIT_LIMIT_BYTES, guard_bytes=lp.GUARD_BYTES),
                                                              caps=caps, states=bench_states, benchmark_counts=bench_counts, guard_calls=dict(guard.calls), partition_n=partition['n'], pool_n=len(pool)))
        if decision == 'STOP' or not caps['feasible']:
            status.update(status='STOPPED_AT_STARTUP', stop_reason=reason if decision == 'STOP' else 'FOUR_DRAWS_OVER_6_H'); return 1
        seeds = {row['group']: {k: v for k, v in row.items() if k != 'group'} for row in registry['groups']}
        device_used = lambda: (lambda free, total: total - free)(*torch.cuda.mem_get_info())
        for d in lp.DRAWS:
            draw_gate(out, here, d, budget, device_used, clock)                                 # GPU and AC power; outside the draw's work cap
            stage_start = clock(); guard.peaks = {}
            reset = getattr(torch.cuda, 'reset_peak_memory_stats', None)
            if reset is not None: reset()
            guard.budget = worker.Budget(min(budget.deadline, stage_start + caps['stage_work_cap_seconds']), clock)
            rows, states = stage(ctx, d, seeds[d], corpus, partition['groups'])
            guard.budget = budget
            guard.full(); out.close_stage()
            for k, v in guard.peaks.items(): run_peaks[k] = max(run_peaks.get(k, 0), v)
            receipt = dict(stage=d, status='COMPLETE', trajectories=len(rows), seconds=clock() - stage_start, counts=dict(ctx.counts), guard_calls=dict(guard.calls),
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
            try:                                                                                      # the counting rule: any draw folder makes this run the
                status['draw_folders'] = sorted(d for d in lp.DRAWS if (out_root / d).is_dir())       # study's only attempt; a scan error is recorded and
                status['counted_as_final_attempt'] = bool(status['draw_folders'])                     # never blocks the terminal
            except Exception as e: status['draw_folders_error'] = f'{type(e).__name__}: {str(e)[:200]}'
            size, files = out.inventory(); status['inventory'] = dict(bytes=size, files=files)
            out.json('TERMINAL.json', status)
        except BaseException as e:
            sys.stderr.write('Terminal publication failed: ' + repr(e)[:300] + '\n')
            try:                                                      # last resort, outside the output ledger and its quotas (review 1, finding 8)
                status['terminal_outside_ledger'] = f'{type(e).__name__}: {str(e)[:200]}'
                with open(out_root / 'TERMINAL.json', 'xb') as f: f.write(encoded(status))
            except BaseException as e2: sys.stderr.write('Terminal last-resort write failed: ' + repr(e2)[:300] + '\n')
    return code


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'run': raise SystemExit('usage: lateturn_worker.py run')
    try: raise SystemExit(run())
    except PermissionError as e: sys.stderr.write(str(e) + '\n'); raise SystemExit(1)
