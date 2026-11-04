"""Capacity-shift follow-up worker (Linux/CUDA). Disabled unless run from its one-use activation; framework is lazy.

Derived from work/capacity-ladder-source-20261026-01/ladder_worker.py: twelve corpus stages, a 40-epoch adaptation
horizon with an in-run check that epochs 1-30 use the ladder's 30-epoch order schedule, and no landmark states.
Modes: `run` (benchmark, frozen cap formula, then twelve corpus stages) is the only runtime entry.
Native fixtures import this module and inject test doubles; they never reach the real framework.
"""
import hashlib, json, math, os, shutil, statistics, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ladder_plan as plan
import ladder_registry

ROOT = Path('/mnt/d/sequence-weighting-research') if os.name == 'posix' else Path(r'D:\sequence-weighting-research')
SOURCE = ROOT / 'work/capacity-shift-followup-source-20261027-01'
ACTIVATION = ROOT / 'work/capacity-shift-followup-activation-20261027-01'
RUN = ROOT / 'work/runs/capacity-shift-followup-20261027-01'
TYPES = ('shared', 'group', 'instance')
BENCHMARK_ARM = 'H'   # the costliest objective graph (two extra masked sums); timing only
BENCHMARK_WRITES = 3  # state writes per architecture in the benchmark; the median is used (one drvfs stall cannot set the cap)


def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(x): return (json.dumps(x, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


# ------------------------------------------------------------------ pure pieces (native-testable)
def objective(arm, sequence_loss, token_loss, kinds, w):
    """Per-batch objective with component coefficients (shared, group, instance) from plan.COEFFICIENTS.

    R and U are the original v0128 graph (sequence_loss*w).mean() (U has w=1); S_batch and H replace the
    instance (and for H also the shared) coefficient by the actual loss-device FP32 batch mean of w.
    """
    if arm in ('R', 'U'): return (sequence_loss * w).mean()
    mu = w.mean()
    instance = (token_loss * (kinds == 2)).sum(1) / 12.0
    if arm == 'S_batch': return (sequence_loss * w + (mu - w) * instance).mean()
    if arm == 'H':
        shared = (token_loss * (kinds == 0)).sum(1) / 12.0
        return (sequence_loss * w + (mu - w) * (shared + instance)).mean()
    raise ValueError('Unknown arm ' + repr(arm))


class Landmarks:
    """First-crossing group-progress landmarks P = 1 - L_train,group(t) / L_train,group(E0).

    Tracks plan.ALL_LANDMARKS; only plan.LANDMARKS add a validation evaluation (no states are saved in the
    follow-up; the supplementary 0.02/0.05 landmarks use the training arrays already saved at every check)."""
    def __init__(self, e0_group_loss, targets=plan.ALL_LANDMARKS):
        if not (isinstance(e0_group_loss, float) and math.isfinite(e0_group_loss)): raise ValueError('E0 group loss')
        self.base = e0_group_loss; self.previous = (0, 0.0); self.max_P = 0.0
        self.state = {q: dict(target=q, status='PENDING' if e0_group_loss > 0 else 'UNDEFINED_E0') for q in targets}

    def update(self, update, group_loss):
        if self.base <= 0: return None, []
        P = 1.0 - group_loss / self.base; crossed = []
        if not math.isfinite(P): raise FloatingPointError('Nonfinite progress')
        self.max_P = max(self.max_P, P)
        for q, s in self.state.items():
            if s['status'] == 'PENDING' and P >= q:
                prev_update, prev_P = self.previous
                s.update(status='CROSSED', update=update, P=P, overshoot=P - q, previous_update=prev_update, previous_P=prev_P,
                         crossed_at_first_check=prev_update == 0, coarse=(P - q) > plan.COARSE_OVERSHOOT)
                crossed.append(q)
        self.previous = (update, P)
        return P, crossed

    def finish(self):
        for s in self.state.values():
            if s['status'] == 'PENDING': s.update(status='MISSED', max_P=self.max_P)
        return {str(q): dict(s) for q, s in self.state.items()}


ARRAY_BYTES = (len(plan.CHECK_UPDATES) * plan.ADAPT['train_rows'] + (len(plan.FIXED_EPOCHS) + len(plan.LANDMARKS)) * plan.ADAPT['validation_rows']) * 7 * 4
RECORD_BYTES = plan.RECORD_BYTES              # generous bound for one record.json
STAGE_FILES = 2 + (1 + len(plan.CONDITIONS)) * len(plan.ARCHS) + 2 * len(plan.trajectories())   # INPUTS, PRETRAINED; state + E0 per arch; arrays + record
STAGE_DIRS = len(plan.ARCHS) + len(plan.trajectories())
STAGE_FULL_GUARDS = 2 + len(plan.ARCHS) + 2 * len(plan.trajectories())
STAGE_EPOCH_GUARDS = (len(plan.ARCHS) * plan.PRETRAIN['epochs'] + len(plan.trajectories()) * plan.ADAPT['epochs']) + STAGE_FILES


def write_model(arch):
    """Least-squares fixed + per-byte write cost over the architectures' median state writes (both clamped >= 0)."""
    xs = [float(v['state_bytes']) for v in arch.values()]; ys = [float(v['seconds_per_state_write']) for v in arch.values()]
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    sxx = math.fsum((x - mx) ** 2 for x in xs); sxy = math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = max(0.0, sxy / sxx) if sxx > 0 else 0.0; a = my - b * mx
    if a < 0: a, b = 0.0, math.fsum(x * y for x, y in zip(xs, ys)) / math.fsum(x * x for x in xs)
    return a, b


def stage_cap(benchmark):
    """Frozen cap formula from the outcome-blind benchmark. The benchmark times the real step, evaluation, state
    write/readback, state reload and guard code paths, so every per-call cost here is measured, not assumed."""
    arch, o = benchmark['architectures'], benchmark['overheads']
    total = 30.0 + o['seconds_data_generation']
    fixed_write, per_byte = write_model(arch)
    pre_updates = plan.PRETRAIN['epochs'] * plan.PRETRAIN['rows'] // plan.PRETRAIN['batch']
    for (w, l) in plan.ARCHS:
        b = arch[f'{w}/{l}']
        n = sum(1 for t in plan.trajectories() if (t[2], t[3]) == (w, l))
        evals = n * (len(plan.CHECK_UPDATES) * 16 + (len(plan.FIXED_EPOCHS) + len(plan.LANDMARKS)) * 8) + len(plan.CONDITIONS) * 24 + 72
        total += pre_updates * b['seconds_per_pretraining_update'] + n * plan.TOTAL_UPDATES * b['seconds_per_update'] + evals * b['seconds_per_eval_batch']
        total += b['seconds_per_state_write'] + n * b['seconds_per_state_reload']        # the pretrained state; no landmark states
        total += len(plan.CONDITIONS) * (fixed_write + per_byte * 768 * 7 * 4) + n * (2 * fixed_write + per_byte * (ARRAY_BYTES + RECORD_BYTES))
    total += STAGE_FULL_GUARDS * (o['seconds_per_full_guard'] + (STAGE_FILES + STAGE_DIRS + o['cache_entries']) * o['seconds_per_inventory_entry'])
    total += STAGE_EPOCH_GUARDS * o['seconds_per_epoch_guard']
    work = math.ceil(1.5 * total + 120)
    L = plan.LIMITS
    k = len(plan.CORPORA)
    feasible = work <= L['stage_work_seconds'] and k * (work + 300) + L['benchmark_seconds'] <= L['overall_seconds']
    return dict(projected_stage_seconds=total, stage_work_cap_seconds=min(work, L['stage_work_seconds']), feasible=feasible,
                formula=f"ceil(1.5*projected+120) <= {L['stage_work_seconds']} s; {k}*(cap+300)+{L['benchmark_seconds']} <= {L['overall_seconds']} s",
                trajectories_per_stage=len(plan.trajectories()), stage_files=STAGE_FILES, full_guards=STAGE_FULL_GUARDS, epoch_guards=STAGE_EPOCH_GUARDS,
                write_model=dict(fixed_seconds=fixed_write, seconds_per_byte=per_byte))


# ------------------------------------------------------------------ guards and output accounting
class Budget:
    def __init__(self, deadline, clock=time.monotonic): self.deadline = float(deadline); self.clock = clock
    def remaining(self): return self.deadline - self.clock()
    def check(self):
        if self.remaining() <= 0: raise TimeoutError('Original deadline exhausted')


class Guard:
    """Same cadence principle as the confirmation amendment.

    tick(): every update and forward pass (deadline, worker peak RSS, sampled GPU).
    epoch(): every epoch boundary and before every write (deadline, 2 GiB disk reserve); Output adds the exact
             prewrite quota from its own write ledger.
    full(): trajectory and stage boundaries: epoch() plus a real inventory of the active stage and cache trees.
    """
    def __init__(self, budget, out, cuda=None, rss=None):
        self.budget = budget; self.out = out; self.cuda = cuda; self.peaks = {}; self.calls = dict(tick=0, full=0, epoch=0)
        self.rss = rss or (lambda: __import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss * 1024)
    def tick(self):
        self.budget.check(); self.calls['tick'] += 1
        r = self.rss(); self.peaks['worker_peak_rss'] = max(self.peaks.get('worker_peak_rss', 0), r)
        if r > plan.LIMITS['worker_peak_rss_bytes']: raise RuntimeError('Worker peak RSS limit')
        if self.cuda is not None:
            free, total = self.cuda.mem_get_info()
            for k, v in (('cuda_allocated', self.cuda.max_memory_allocated()), ('cuda_reserved', self.cuda.max_memory_reserved()), ('device_used_sampled', total - free)):
                self.peaks[k] = max(self.peaks.get(k, 0), int(v))
                if v > plan.LIMITS['gpu_sampled_bytes']: raise RuntimeError('Sampled GPU limit')
    def epoch(self):
        self.budget.check(); self.calls['epoch'] += 1
        if shutil.disk_usage(self.out.root).free < plan.LIMITS['reserve_free_bytes']: raise RuntimeError('D reserve')
    def full(self):
        self.epoch(); self.calls['full'] += 1; self.out.check_inventory()


class Output:
    """One-use output tree: prewrite quota from an exact write ledger, atomic rename, and real inventories of
    the active stage and cache trees at boundaries (closed stages are carried as their measured totals)."""
    def __init__(self, root, stage_bytes, stage_files, total_bytes, total_files):
        self.root = Path(root); self.caps = (stage_bytes, stage_files, total_bytes, total_files)
        self.stage = None; self.stage_bytes = self.stage_files = 0; self.guard = None
        self.closed = [0, 0]; self.top_bytes = self.top_files = 0; self.cache = (0, 0)
    def begin_stage(self, name):
        if self.stage is not None: raise RuntimeError('A stage is already open')
        self.stage = name; d = self.root / name
        if d.exists(): raise FileExistsError('Stage directory exists; no resume')
        d.mkdir(); self.stage_bytes = self.stage_files = 0
    def close_stage(self):
        """Move the measured stage tree into the closed totals and reset the stage ledger (no double count)."""
        if self.stage is None: return
        s, f = self.inventory(self.root / self.stage); self.closed[0] += s; self.closed[1] += f
        self.stage = None; self.stage_bytes = self.stage_files = 0
    def live_total(self):
        stage = self.inventory(self.root / self.stage) if self.stage is not None else (0, 0)
        cache = self.inventory(self.root / 'cache') if (self.root / 'cache').exists() else (0, 0)
        return stage, cache, (self.closed[0] + stage[0] + cache[0] + self.top_bytes, self.closed[1] + stage[1] + cache[1] + self.top_files)
    def inventory(self, root=None):
        size = files = 0
        for dirpath, dirnames, filenames in os.walk(root or self.root):
            for name in dirnames + filenames:
                p = Path(dirpath) / name; s = p.lstat()
                if os.path.islink(p) or getattr(s, 'st_file_attributes', 0) & 1024: raise RuntimeError('Link/reparse in output')
            for name in filenames:
                p = Path(dirpath) / name
                if not p.is_file(): raise RuntimeError('Nonregular output')
                size += p.stat().st_size; files += 1
        return size, files
    def check_inventory(self):
        (s, f), cache, (size, files) = self.live_total()
        if s > self.caps[0] or f > self.caps[1]: raise RuntimeError('Stage output quota exceeded')
        if size > self.caps[2] or files > self.caps[3]: raise RuntimeError('Total output quota exceeded')
        self.stage_bytes, self.stage_files = s, f; self.cache = cache  # resynchronize the ledger with the measured trees
        return size, files
    def ledger_total(self):
        return (self.closed[0] + self.stage_bytes + self.top_bytes + self.cache[0], self.closed[1] + self.stage_files + self.top_files + self.cache[1])
    def write(self, relative, data):
        data = bytes(data)
        parts = relative.split('/')
        if any(p in ('', '.', '..') for p in parts) or ':' in relative or relative.startswith('/'): raise ValueError('Unsafe output name')
        if self.guard is not None: self.guard.epoch()
        target = self.root.joinpath(*parts)
        if target.exists(): raise FileExistsError('Immutable output: ' + relative)
        in_stage = self.stage is not None and parts[0] == self.stage
        if in_stage and (self.stage_bytes + len(data) > self.caps[0] or self.stage_files + 1 > self.caps[1]): raise RuntimeError('Prewrite stage quota')
        size, files = self.ledger_total()
        if size + len(data) > self.caps[2] or files + 1 > self.caps[3]: raise RuntimeError('Prewrite total quota')
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.part')
        with temp.open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(temp, target)
        if in_stage: self.stage_bytes += len(data); self.stage_files += 1
        else: self.top_bytes += len(data); self.top_files += 1
        return dict(path=relative, bytes=len(data), sha256=sha(data))
    def json(self, relative, value): return self.write(relative, encoded(value))


# ------------------------------------------------------------------ framework-dependent pieces
class Context:
    def __init__(self, torch, engine, Model, guard, out):
        self.torch, self.engine, self.Model, self.guard, self.out = torch, engine, Model, guard, out
        self.counts = dict(models=0, updates=0, eval_batches=0, pretrained_states=0)

    def floats(self, arrays):
        """Concatenate loss (n), component_loss (n x 3), component_accuracy (n x 3) as little-endian float32."""
        parts = [arrays['loss'], arrays['component_loss'], arrays['component_accuracy']]
        return b''.join(x.detach().cpu().contiguous().numpy().astype('<f4').tobytes() for x in parts)

    def evaluate(self, model, data):
        t = self.torch; cpu = t.get_rng_state().clone(); gpu = t.cuda.get_rng_state(0).clone(); mode = model.training
        try:
            with t.random.fork_rng(devices=[0]):
                metrics, arrays = self.engine.evaluate(model, data)
        finally: model.train(mode)
        if not t.equal(cpu, t.get_rng_state()) or not t.equal(gpu, t.cuda.get_rng_state(0)): raise RuntimeError('Evaluation changed RNG')
        self.counts['eval_batches'] += (len(data[0]) + 31) // 32
        return metrics, arrays

    def save_state(self, relative, model):
        import io
        state = self.engine.cpu_state(model)
        if not all(bool(self.torch.isfinite(v).all()) for v in state.values()): raise FloatingPointError('Nonfinite state')
        buffer = io.BytesIO(); self.torch.save(state, buffer); payload = buffer.getvalue()
        binding = self.out.write(relative, payload)
        if (self.out.root / relative).read_bytes() != payload: raise RuntimeError('State readback differs')
        return binding

    def pretraining_step(self, model, optimizer, pre, ids):
        t = self.torch; self.guard.tick(); tokens, kinds = [x[ids].cuda() for x in pre['train']]
        loss = self.engine.pretraining_objective(model(tokens[:, :-1]), tokens, kinds)
        optimizer.zero_grad(set_to_none=True); loss.backward()
        norm = t.nn.utils.clip_grad_norm_(model.parameters(), plan.PRETRAIN['clip'])
        if not t.isfinite(loss) or not t.isfinite(norm): raise FloatingPointError('Nonfinite U update')
        optimizer.step()

    def adaptation_step(self, model, optimizer, arm, data, weights, ids):
        t = self.torch; self.guard.tick(); tokens, kinds = (x[ids].cuda() for x in data['train'])
        sequence_loss, token_loss, _ = self.engine.losses(model, tokens, kinds)
        loss = objective(arm, sequence_loss, token_loss, kinds, weights[ids].cuda())
        optimizer.zero_grad(set_to_none=True); loss.backward()
        norm = t.nn.utils.clip_grad_norm_(model.parameters(), plan.ADAPT['clip'])
        if not t.isfinite(loss) or not t.isfinite(norm): raise FloatingPointError('Nonfinite adaptation update')
        optimizer.step(); return float(norm)

    def load_adaptation_model(self, arch, state_path, state_hashes, init_seed):
        """Reload an E0 state exactly as every trajectory does: bytes from disk, tensor-hash check, fresh model,
        strict load, the per-forward guard hook and a fresh AdamW."""
        import io
        t = self.torch; w, l = arch; g = self.guard
        state = t.load(io.BytesIO((self.out.root / state_path).read_bytes()), map_location='cpu', weights_only=True)
        if {k: self.engine.tensor_hash(v) for k, v in state.items()} != state_hashes: raise RuntimeError('E0 state hash')
        t.manual_seed(init_seed); t.cuda.manual_seed_all(init_seed)
        model = self.Model(w, l, plan.SEQ_LEN).cuda(); model.load_state_dict(state, strict=True); self.counts['models'] += 1
        model.register_forward_pre_hook(lambda m, args: g.tick())
        optimizer = t.optim.AdamW(model.parameters(), lr=plan.ADAPT['lr'], weight_decay=plan.ADAPT['weight_decay'])
        if optimizer.state: raise RuntimeError('Optimizer must start empty')
        return model, optimizer

    def pretrain(self, stage, arch, seeds, pre, adapt, orders2048):
        t = self.torch; w, l = arch; g = self.guard
        g.full(); t.manual_seed(seeds['init_seed']); t.cuda.manual_seed_all(seeds['init_seed'])
        model = self.Model(w, l, plan.SEQ_LEN).cuda(); self.counts['models'] += 1
        if sum(p.numel() for p in model.parameters()) != plan.parameters(w, l): raise RuntimeError('Parameter count')
        optimizer = t.optim.AdamW(model.parameters(), lr=plan.PRETRAIN['lr'], weight_decay=plan.PRETRAIN['weight_decay'])
        for epoch in range(1, plan.PRETRAIN['epochs'] + 1):
            g.epoch(); model.train()
            for ids in orders2048[epoch - 1].split(plan.PRETRAIN['batch']):
                self.pretraining_step(model, optimizer, pre, ids); self.counts['updates'] += 1
        if not all(int(s['step'].item()) == 256 for s in optimizer.state.values()): raise RuntimeError('U optimizer steps')
        model.register_forward_pre_hook(lambda m, args: g.tick())   # evaluation forwards are ticked too (hooks are not in the state)
        u_metrics = {s: self.evaluate(model, pre[s])[0] for s in ('train', 'validation')}
        name = f'{stage}/{w}x{l}'
        state = self.save_state(name + '/pretrained.pt', model); self.counts['pretrained_states'] += 1
        e0 = {}
        for c in plan.CONDITIONS:
            blocks = {}
            for split in ('train', 'validation'):
                m, a = self.evaluate(model, adapt[c][split]); blocks[split] = dict(metrics=m, bytes=self.floats(a))
            raw = blocks['train']['bytes'] + blocks['validation']['bytes']
            e0[c] = dict(arrays=self.out.write(f'{name}/E0-{c}.f32', raw), metrics={s: blocks[s]['metrics'] for s in blocks},
                         group_train_loss=float(blocks['train']['metrics']['group']['loss']))
        result = dict(arch=f'{w}/{l}', parameters=plan.parameters(w, l), state=state, U_metrics=u_metrics, E0=e0,
                      state_tensor_hashes={k: self.engine.tensor_hash(v) for k, v in model.state_dict().items()})
        del optimizer, model; t.cuda.empty_cache()
        return result

    def adapt(self, stage, arch, condition, arm, pre_result, seeds, data, weights, orders):
        t = self.torch; w, l = arch; g = self.guard; name = f'{stage}/{w}x{l}/{condition}-{arm}'
        g.full()
        model, optimizer = self.load_adaptation_model(arch, pre_result['state']['path'], pre_result['state_tensor_hashes'], seeds['init_seed'])
        landmarks = Landmarks(pre_result['E0'][condition]['group_train_loss'])
        checks = set(plan.CHECK_UPDATES); fixed = {16 * e for e in plan.FIXED_EPOCHS}
        train_blocks, validation_blocks, records, epochs = [], [], [], []
        update = 0
        for epoch in range(1, plan.ADAPT['epochs'] + 1):
            g.epoch(); model.train(); norms = []
            for ids in orders[epoch - 1].split(plan.ADAPT['batch']):
                norms.append(self.adaptation_step(model, optimizer, arm, data, weights, ids)); update += 1; self.counts['updates'] += 1
                if update in checks:
                    metrics, arrays = self.evaluate(model, data['train'])
                    P, crossed = landmarks.update(update, float(metrics['group']['loss']))
                    main = [q for q in crossed if q in plan.LANDMARKS]
                    train_blocks.append(self.floats(arrays))
                    rec = dict(update=update, epoch_fraction=update / 16, train=metrics, progress=P, crossed=list(crossed))
                    if update in fixed or main:
                        vm, va = self.evaluate(model, data['validation']); validation_blocks.append(self.floats(va)); rec['validation'] = vm
                        rec['validation_block'] = len(validation_blocks) - 1
                    records.append(rec); model.train()
            epochs.append(dict(epoch=epoch, gradient_norm_mean=sum(norms) / len(norms), gradient_norm_max=max(norms),
                               clip_fraction=sum(n > plan.ADAPT['clip'] for n in norms) / len(norms)))
        if update != plan.TOTAL_UPDATES or any(int(s['step']) != plan.TOTAL_UPDATES for s in optimizer.state.values()): raise RuntimeError('Trajectory updates')
        arrays = self.out.write(f'{name}/arrays.f32', b''.join(train_blocks) + b''.join(validation_blocks))
        record = dict(stage=stage, arch=f'{w}/{l}', condition=condition, arm=arm, coefficients=plan.COEFFICIENTS[arm], checks=records,
                      epochs=epochs, landmarks=landmarks.finish(), arrays=arrays, layout=dict(train_rows=512, validation_rows=256,
                      per_row=7, train_blocks=len(train_blocks), validation_blocks=len(validation_blocks), order='loss, component_loss[3], component_accuracy[3]'))
        self.out.json(f'{name}/record.json', record)
        del optimizer, model; t.cuda.empty_cache(); g.full()
        return dict(path=f'{name}/record.json', landmarks=record['landmarks'])

    def stage(self, stage, seeds):
        e = self.engine; self.out.begin_stage(stage); self.guard.full()
        all_adapt, ameta = e.paired_data(seeds['adaptation_seed'])
        pre, pmeta = e.pre_data(seeds['pretraining_seed'])
        adapt = {c: {s: all_adapt[c][s] for s in ('train', 'validation')} for c in plan.CONDITIONS}; del all_adapt
        weights = dict(random=e.weights(seeds['weight_seed'], 'random'), uniform=e.weights(seeds['weight_seed'], 'uniform'))
        e.validate_weights(weights['random']); e.validate_weights(weights['uniform'], allow_constant=True)
        orders = e.orders(seeds['order_seed'], plan.ADAPT['train_rows'], plan.ADAPT['epochs'])
        orders2048 = e.orders(seeds['order_seed'], plan.PRETRAIN['rows'], plan.PRETRAIN['epochs'])
        # Epochs 1-30 must be exactly the ladder's 30-epoch schedule (constant learning rate, no scheduler), so
        # updates 1-480 follow the ladder recipe; a horizon-dependent schedule fails the stage before any training.
        if len(orders) != plan.ADAPT['epochs'] or not self.torch.equal(orders[:plan.LADDER_ADAPT_EPOCHS], e.orders(seeds['order_seed'], plan.ADAPT['train_rows'], plan.LADDER_ADAPT_EPOCHS)):
            raise RuntimeError('Adaptation order schedule depends on the horizon')
        hashes = dict(adapt={c: {s: e.tensor_hash(*adapt[c][s]) for s in adapt[c]} for c in adapt}, pre={s: e.tensor_hash(*pre[s]) for s in pre},
                      weights=e.tensor_hash(weights['random']), orders=e.tensor_hash(orders), preorders=e.tensor_hash(orders2048))
        self.out.json(f'{stage}/INPUTS.json', dict(seeds=seeds, tensor_hashes=hashes, weights=[float(x) for x in weights['random'].tolist()], adaptation_metadata={c: {k: v for k, v in ameta[c].items() if k in ('condition', 'effective_rule_count', 'tensor_sha256')} for c in ameta}))
        pretrained = {arch: self.pretrain(stage, arch, seeds, pre, adapt, orders2048) for arch in plan.ARCHS}
        self.out.json(f'{stage}/PRETRAINED.json', {f'{w}/{l}': v for (w, l), v in pretrained.items()})
        rows = []
        for (condition, arm, w, l) in plan.trajectories():
            wv = weights['uniform'] if arm == 'U' else weights['random']
            rows.append(self.adapt(stage, (w, l), condition, arm, pretrained[(w, l)], seeds, adapt[condition], wv, orders))
        if e.tensor_hash(weights['random']) != hashes['weights'] or e.tensor_hash(orders) != hashes['orders']: raise RuntimeError('Paired inputs changed')
        return rows


def benchmark(ctx, seed, limit_seconds, clock=time.monotonic):
    """Outcome-blind timing on a benchmark-only corpus through the same code paths as a stage: data generation,
    pretraining steps, state write with readback, E0 reload with hash check, adaptation steps with the per-forward
    guard hook, train and validation evaluations through the RNG-checked wrapper, and the guard calls.
    Per architecture: 16 + 32 pretraining and 16 + 32 adaptation updates (warm-up untimed). No p*, no landmarks."""
    t, e, g = ctx.torch, ctx.engine, ctx.guard; start = clock(); arch_out = {}
    def sync():
        if hasattr(t.cuda, 'synchronize'): t.cuda.synchronize()
    t0 = clock()
    pre, _ = e.pre_data(seed); adapt, _ = e.paired_data(seed); data = adapt['G16']
    w_random = e.weights(seed, 'random'); e.validate_weights(w_random)
    orders = e.orders(seed); pre_orders = e.orders(seed, plan.PRETRAIN['rows'], 1)
    data_seconds = clock() - t0
    for (w, l) in plan.ARCHS:
        if clock() - start > limit_seconds: raise TimeoutError('Benchmark limit')
        name = f'benchmark/{w}x{l}'
        g.full(); t.manual_seed(seed); t.cuda.manual_seed_all(seed); model = ctx.Model(w, l, plan.SEQ_LEN).cuda()
        opt = t.optim.AdamW(model.parameters(), lr=plan.PRETRAIN['lr'], weight_decay=plan.PRETRAIN['weight_decay'])
        batches = list(pre_orders[0].split(plan.PRETRAIN['batch']))
        for ids in batches[:16]: ctx.pretraining_step(model, opt, pre, ids)
        sync(); t0 = clock()
        for ids in batches[16:48]: ctx.pretraining_step(model, opt, pre, ids)
        sync(); per_pre = (clock() - t0) / 32
        writes = []
        for k in range(BENCHMARK_WRITES):
            t0 = clock(); state = ctx.save_state(f'{name}-w{k}.pt', model); writes.append(clock() - t0)
        per_write = statistics.median(writes)
        hashes = {k: e.tensor_hash(v) for k, v in model.state_dict().items()}
        del opt, model; t.cuda.empty_cache()
        t0 = clock(); model, opt = ctx.load_adaptation_model((w, l), state['path'], hashes, seed); sync(); per_reload = clock() - t0
        model.train()
        for ids in orders[0].split(plan.ADAPT['batch']): ctx.adaptation_step(model, opt, BENCHMARK_ARM, data, w_random, ids)
        sync(); t0 = clock()
        for ids in list(orders[1].split(plan.ADAPT['batch'])) + list(orders[2].split(plan.ADAPT['batch'])): ctx.adaptation_step(model, opt, BENCHMARK_ARM, data, w_random, ids)
        sync(); per_update = (clock() - t0) / 32
        t0 = clock()
        _, a = ctx.evaluate(model, data['train']); ctx.floats(a); _, a = ctx.evaluate(model, data['validation']); ctx.floats(a)
        sync(); per_eval = (clock() - t0) / 24
        arch_out[f'{w}/{l}'] = dict(seconds_per_pretraining_update=per_pre, seconds_per_update=per_update, seconds_per_eval_batch=per_eval,
                                    seconds_per_state_write=per_write, state_write_seconds=writes, seconds_per_state_reload=per_reload, state_bytes=state['bytes'],
                                    parameters=plan.parameters(w, l), peaks=dict(g.peaks))
        model.train(); del opt, model; t.cuda.empty_cache()
    t0 = clock()
    for _ in range(16): g.full()
    per_full = (clock() - t0) / 16
    entries = sum(len(d) + len(f) for _, d, f in os.walk(ctx.out.root / 'benchmark'))
    t0 = clock()
    for _ in range(16): ctx.out.inventory(ctx.out.root / 'benchmark')
    per_entry = (clock() - t0) / (16 * max(entries, 1))
    t0 = clock()
    for _ in range(64): g.epoch()
    per_epoch = (clock() - t0) / 64
    cache_entries = sum(len(d) + len(f) for _, d, f in os.walk(ctx.out.root / 'cache')) if (ctx.out.root / 'cache').exists() else 0
    overheads = dict(seconds_data_generation=data_seconds, seconds_per_full_guard=per_full, seconds_per_inventory_entry=per_entry,
                     seconds_per_epoch_guard=per_epoch, cache_entries=cache_entries, benchmark_seconds=clock() - start)
    return dict(architectures=arch_out, overheads=overheads, arm=BENCHMARK_ARM)


# ------------------------------------------------------------------ admission and entry
def authorization(here=HERE):
    a = json.loads((here / 'AUTHORIZATION.json').read_bytes())
    if a.get('enabled') is not True or a.get('execution_ready') is not True: raise PermissionError('DISABLED: no capacity-shift follow-up approval')
    if here != ACTIVATION or a.get('one_use') is not True or not a.get('approval_id'): raise PermissionError('Separate one-use activation required')
    raw = (here / 'SOURCE_SUBJECT.json').read_bytes()
    if sha(raw) != a.get('source_subject_sha256'): raise PermissionError('Source subject not approved')
    for row in json.loads(raw)['files']:
        b = (here / row['path']).read_bytes()
        if len(b) != row['bytes'] or sha(b) != row['sha256']: raise PermissionError('Changed source ' + row['path'])
    reg_raw, ex_raw, draw_raw = ((here / n).read_bytes() for n in ('REGISTRY.json', 'EXCLUSIONS.json', 'DRAW.json'))
    if sha(reg_raw) != a.get('registry_sha256') or sha(ex_raw) != a.get('exclusions_sha256') or sha(draw_raw) != a.get('draw_sha256'): raise PermissionError('Registry binding')
    try: registry = ladder_registry.validate(json.loads(reg_raw), ex_raw, draw_raw)
    except ValueError as e: raise PermissionError('Registry does not re-derive from its draw: ' + str(e))
    return a, registry


def run(dependencies=None, here=HERE, out_root=RUN, clock=time.monotonic):
    a, registry = authorization(here)
    start = clock(); budget = Budget(start + plan.LIMITS['overall_seconds'] - 120, clock)
    if out_root.exists(): raise FileExistsError('One-use run directory exists; no retry')
    if shutil.disk_usage(out_root.parent).free < plan.LIMITS['admission_free_bytes']: raise RuntimeError('Admission free space')
    out_root.mkdir()
    out = Output(out_root, plan.LIMITS['stage_storage_bytes'], plan.LIMITS['stage_files'], plan.LIMITS['storage_bytes'], plan.LIMITS['total_files'])
    status = dict(subject=a['source_subject_sha256'], stages=[], status='STARTED'); guard = ctx = None
    try:
        if dependencies is None:
            import framework_setup
            torch, engine, Model = framework_setup.setup(out_root / 'cache')
        else: torch, engine, Model = dependencies
        guard = Guard(budget, out, cuda=torch.cuda); out.guard = guard
        ctx = Context(torch, engine, Model, guard, out)
        bench = benchmark(ctx, registry['benchmark']['benchmark_seed'], plan.LIMITS['benchmark_seconds'], clock)
        bench_counts = dict(ctx.counts); ctx.counts = {k: 0 for k in ctx.counts}   # scientific counts exclude the benchmark
        caps = stage_cap(bench); out.json('BENCHMARK.json', dict(benchmark=bench, caps=caps, benchmark_counts=bench_counts, guard_calls=dict(guard.calls)))
        if not caps['feasible']: raise RuntimeError('Projected stage time exceeds the frozen envelope; stopping before any scientific stage')
        for row in registry['corpus_pairs']:
            stage = row['corpus_slot']; stage_start = clock()
            guard.budget = Budget(min(budget.deadline, stage_start + caps['stage_work_cap_seconds']), clock)
            rows = ctx.stage(stage, {k: v for k, v in row.items() if k != 'corpus_slot'})
            guard.budget = budget
            guard.full(); out.close_stage()
            receipt = dict(stage=stage, status='COMPLETE', trajectories=len(rows), seconds=clock() - stage_start, counts=dict(ctx.counts),
                           guard_calls=dict(guard.calls), peaks=dict(guard.peaks), closed_totals=list(out.closed), ledger_total=list(out.ledger_total()))
            out.json(f'{stage}-RECEIPT.json', receipt); status['stages'].append(receipt)
        status['status'] = 'COMPLETE'
    except BaseException as error:
        status.update(status='FAILED', error=dict(type=type(error).__name__, message=str(error)[:400]), active_stage=out.stage)
        raise
    finally:
        status.update(elapsed_seconds=clock() - start, counts=dict(ctx.counts) if ctx else {}, peaks=dict(guard.peaks) if guard else {})
        out.stage = None; out.guard = None
        try:
            size, files = out.inventory(); status['inventory'] = dict(bytes=size, files=files)
            out.json('TERMINAL.json', status)
        except BaseException as e: sys.stderr.write('Terminal publication failed: ' + repr(e)[:300] + '\n')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != 'run': raise SystemExit('usage: ladder_worker.py run')   # the follow-up keeps the ladder module names
    try: raise SystemExit(run())
    except PermissionError as e: sys.stderr.write(str(e) + '\n'); raise SystemExit(1)
