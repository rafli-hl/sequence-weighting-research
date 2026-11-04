"""Natural-text ladder worker (Linux/CUDA). Disabled unless run from one of its one-use activations; framework is lazy.

Activation A (Run A): outcome-blind benchmark, frozen cap formula, then the tuning stage t00 (each width pre-trained
once with uniform weights, then three weighted adaptations, one per learning rate in the grid).
Activation B (Run B): benchmark, cap formula, then the ten analysis stages d01..d10, each width adapted once with the
learning rate frozen from Run A (LR_SELECTION.json). If Run A's outcome-blind forecast puts ten draws over the 6-hour
limit, the pre-registered split runs B1 (d01..d05) and B2 (d06..d10) instead, with identical science. If Run A forecast
that ten draws fit but Run B's own start-up benchmark puts them over the limit while five fit, Run B stops before any
training with status FALLBACK_TO_SPLIT and the same split applies (owner rule of 28 Oct 2026, revision 03).
Revision 05 (owner ruling of 28 Oct 2026; second and final attempt): identical science; Run A and its selection are reused
from revision 04; Run B (and B1/B2 after a start-up fallback) use new -02 folders. The Windows owner script checks the
GPU with nvidia-smi before start (PRESTART) and, at this worker's request, before every draw; the worker waits for its
verdict outside the draw's work cap and stops with GpuBusyError if the GPU stayed busy for the whole 30-minute window.
Budget, Guard and Output are the ladder worker's classes.
Native fixtures import this module and inject test doubles; they never reach the real framework.
"""
import hashlib, io, json, math, os, shutil, statistics, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_data
import text_registry

ROOT = Path('/mnt/d/sequence-weighting-research') if os.name == 'posix' else Path(r'D:\sequence-weighting-research')
SOURCE = ROOT / 'work/natural-text-ladder-source-20261028-02'
CORPUS = ROOT / 'work/runs/natural-text-corpus-20261028-01'
# Revision 05: Run A and its activation are revision 04's (reused); Run B, B1 and B2 are new -02 folders. Attempt 1
# (work/runs/natural-text-ladder-b-20261028-01, the failed revision 04 Run B) is never read.
FOLDERS = {'A': '20261028-01', 'B': '20261028-02', 'B1': '20261028-02', 'B2': '20261028-02'}
ACTIVATIONS = {m: ROOT / f'work/natural-text-ladder-activation-{m.lower()}-{v}' for m, v in FOLDERS.items()}
RUNS = {m: ROOT / f'work/runs/natural-text-ladder-{m.lower()}-{v}' for m, v in FOLDERS.items()}
BENCHMARK_WRITES = 3
LR_TAGS = {lr: f'lr{lr:.0e}' for lr in plan.LR_GRID}


def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(x): return (json.dumps(x, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


# ------------------------------------------------------------------ per-stage counts and the frozen cap formula
def adaptations(mode): return len(plan.LR_GRID) if mode == 'A' else 1
def stages(mode): return len(plan.RUN_STAGES[mode])


def stage_counts(mode, n_train, n_pool):
    W, k = len(plan.WIDTHS), adaptations(mode); trajectories = W * k
    files = 2 + 2 * W + 2 * trajectories                     # INPUTS, PRETRAINED; E0 state and E0 arrays per width; arrays and record per adaptation
    return dict(trajectories=trajectories, files=files, dirs=W + trajectories, full_guards=2 + W + 2 * trajectories,
                epoch_guards=W * plan.PRETRAIN['epochs'] + trajectories * plan.ADAPT['epochs'] + files,
                pre_updates=plan.updates(n_pool, plan.PRETRAIN['epochs']), adapt_updates=plan.updates(n_train, plan.ADAPT['epochs']),
                e0_eval_batches=plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION),
                readout_eval_batches=len(plan.READOUTS) * (plan.eval_batches(n_train) + plan.eval_batches(plan.N_VALIDATION)),
                e0_bytes=4 * (n_train + plan.N_VALIDATION), array_bytes=4 * len(plan.READOUTS) * (n_train + plan.N_VALIDATION))


def write_model(arch):
    """Least-squares fixed + per-byte write cost over the architectures' median state writes (both clamped >= 0)."""
    xs = [float(v['state_bytes']) for v in arch.values()]; ys = [float(v['seconds_per_state_write']) for v in arch.values()]
    mx, my = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
    sxx = math.fsum((x - mx) ** 2 for x in xs); sxy = math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = max(0.0, sxy / sxx) if sxx > 0 else 0.0; a = my - b * mx
    if a < 0: a, b = 0.0, math.fsum(x * y for x, y in zip(xs, ys)) / math.fsum(x * x for x in xs)
    return a, b


def stage_cap(benchmark, mode, n_train, n_pool):
    """Projected stage time from the outcome-blind benchmark (every measured per-call cost times its exact per-stage
    count); cap = ceil(1.25 x projected + 120 s); feasible iff stages x (cap + 60) + 900 <= 21,600 s."""
    arch, o = benchmark['architectures'], benchmark['overheads']; c = stage_counts(mode, n_train, n_pool); k = adaptations(mode)
    total = 30.0 + o['seconds_data_generation']
    fixed_write, per_byte = write_model(arch)
    for w in plan.WIDTHS:
        b = arch[str(w)]
        total += c['pre_updates'] * b['seconds_per_pretraining_update'] + k * c['adapt_updates'] * b['seconds_per_update']
        total += (c['e0_eval_batches'] + k * c['readout_eval_batches']) * b['seconds_per_eval_batch']
        total += b['seconds_per_state_write'] + k * b['seconds_per_state_reload']
        total += (fixed_write + per_byte * c['e0_bytes']) + k * (2 * fixed_write + per_byte * (c['array_bytes'] + plan.RECORD_BYTES))
    total += c['full_guards'] * (o['seconds_per_full_guard'] + (c['files'] + c['dirs'] + o['cache_entries']) * o['seconds_per_inventory_entry'])
    total += c['epoch_guards'] * o['seconds_per_epoch_guard']
    L = plan.LIMITS; n = stages(mode)
    work = math.ceil(L['cap_multiplier'] * total + L['cap_fixed_seconds'])
    max_cap = (L['overall_seconds'] - L['benchmark_seconds']) / n - L['stage_slack_seconds']
    return dict(projected_stage_seconds=total, stage_work_cap_seconds=min(work, math.floor(max_cap)), feasible=work <= max_cap, stages=n, counts=c,
                formula=f"ceil({L['cap_multiplier']}*projected+{L['cap_fixed_seconds']}) <= {math.floor(max_cap)} s; {n}*(cap+{L['stage_slack_seconds']})+{L['benchmark_seconds']} <= {L['overall_seconds']} s",
                write_model=dict(fixed_seconds=fixed_write, seconds_per_byte=per_byte))


# ------------------------------------------------------------------ guards and output accounting (ladder worker classes)
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

    @staticmethod
    def floats(tensor): return tensor.detach().cpu().contiguous().numpy().astype('<f4').tobytes()

    def evaluate(self, model, tokens):
        t = self.torch; cpu = t.get_rng_state().clone(); gpu = t.cuda.get_rng_state(0).clone(); mode = model.training
        try:
            with t.random.fork_rng(devices=[0]):
                out = self.engine.evaluate(model, tokens)
        finally: model.train(mode)
        if not t.equal(cpu, t.get_rng_state()) or not t.equal(gpu, t.cuda.get_rng_state(0)): raise RuntimeError('Evaluation changed RNG')
        if not bool(t.isfinite(out).all()): raise FloatingPointError('Nonfinite evaluation loss')
        self.counts['eval_batches'] += plan.eval_batches(len(tokens))
        return out

    def save_state(self, relative, model):
        state = self.engine.cpu_state(model)
        if not all(bool(self.torch.isfinite(v).all()) for v in state.values()): raise FloatingPointError('Nonfinite state')
        buffer = io.BytesIO(); self.torch.save(state, buffer); payload = buffer.getvalue()
        binding = self.out.write(relative, payload)
        if (self.out.root / relative).read_bytes() != payload: raise RuntimeError('State readback differs')
        return binding

    def pretraining_step(self, model, optimizer, pool, ids):
        t = self.torch; self.guard.tick()
        loss = self.engine.losses(model, pool[ids].cuda()).mean()
        optimizer.zero_grad(set_to_none=True); loss.backward()
        norm = t.nn.utils.clip_grad_norm_(model.parameters(), plan.PRETRAIN['clip'])
        if not t.isfinite(loss) or not t.isfinite(norm): raise FloatingPointError('Nonfinite pre-training update')
        optimizer.step(); return float(norm)

    def adaptation_step(self, model, optimizer, train, weights, ids):
        t = self.torch; self.guard.tick()
        loss = (self.engine.losses(model, train[ids].cuda()) * weights[ids].cuda()).mean()
        optimizer.zero_grad(set_to_none=True); loss.backward()
        norm = t.nn.utils.clip_grad_norm_(model.parameters(), plan.ADAPT['clip'])
        if not t.isfinite(loss) or not t.isfinite(norm): raise FloatingPointError('Nonfinite adaptation update')
        optimizer.step(); return float(norm)

    def load_adaptation_model(self, width, state_path, state_hashes, init_seed, lr):
        """Reload an E0 state exactly as every adaptation does: bytes from disk, tensor-hash check, fresh model, strict
        load, the per-forward guard hook and a fresh constant-learning-rate AdamW."""
        t = self.torch; g = self.guard
        state = t.load(io.BytesIO((self.out.root / state_path).read_bytes()), map_location='cpu', weights_only=True)
        if {k: self.engine.tensor_hash(v) for k, v in state.items()} != state_hashes: raise RuntimeError('E0 state hash')
        t.manual_seed(init_seed); t.cuda.manual_seed_all(init_seed)
        model = self.Model(width, plan.LAYERS, plan.CONTEXT, plan.VOCAB).cuda(); model.load_state_dict(state, strict=True); self.counts['models'] += 1
        model.register_forward_pre_hook(lambda m, args: g.tick())
        optimizer = t.optim.AdamW(model.parameters(), lr=lr, weight_decay=plan.ADAPT['weight_decay'])
        if optimizer.state: raise RuntimeError('Optimizer must start empty')
        return model, optimizer

    def pretrain(self, stage, width, seeds, pool, data, pool_orders):
        """Uniform-weight pre-training on the shared pool (fixed length), then E0 per-sequence losses on the group's
        training and validation sequences. E0 is the sequence-weight-invariant baseline of every gain."""
        t = self.torch; g = self.guard
        g.full(); t.manual_seed(seeds['init_seed']); t.cuda.manual_seed_all(seeds['init_seed'])
        model = self.Model(width, plan.LAYERS, plan.CONTEXT, plan.VOCAB).cuda(); self.counts['models'] += 1
        if sum(p.numel() for p in model.parameters()) != plan.parameters(width): raise RuntimeError('Parameter count')
        optimizer = t.optim.AdamW(model.parameters(), lr=plan.PRETRAIN['lr'], weight_decay=plan.PRETRAIN['weight_decay'])
        norms = []
        for epoch in range(1, plan.PRETRAIN['epochs'] + 1):
            g.epoch(); model.train()
            for ids in pool_orders[epoch - 1].split(plan.BATCH):
                norms.append(self.pretraining_step(model, optimizer, pool, ids)); self.counts['updates'] += 1
        expected = plan.updates(len(pool), plan.PRETRAIN['epochs'])
        if not all(int(s['step'].item()) == expected for s in optimizer.state.values()): raise RuntimeError('Pre-training optimizer steps')
        model.register_forward_pre_hook(lambda m, args: g.tick())
        e0 = {s: self.evaluate(model, data[s]) for s in ('train', 'validation')}
        name = f'{stage}/w{width}'
        state = self.save_state(name + '/E0.pt', model); self.counts['pretrained_states'] += 1
        arrays = self.out.write(name + '/E0.f32', self.floats(e0['train']) + self.floats(e0['validation']))
        result = dict(width=width, parameters=plan.parameters(width), state=state, E0_arrays=arrays, pretraining_updates=expected,
                      E0_train_loss=float(e0['train'].mean()), E0_validation_loss=float(e0['validation'].mean()),
                      pretraining_clip_fraction=sum(n > plan.PRETRAIN['clip'] for n in norms) / len(norms),
                      state_tensor_hashes={k: self.engine.tensor_hash(v) for k, v in model.state_dict().items()})
        del optimizer, model; t.cuda.empty_cache()
        return result

    def adapt(self, stage, width, lr, tag, pre_result, seeds, data, weights, orders):
        t = self.torch; g = self.guard; name = f'{stage}/w{width}/{tag}'
        g.full()
        model, optimizer = self.load_adaptation_model(width, pre_result['state']['path'], pre_result['state_tensor_hashes'], seeds['init_seed'], lr)
        blocks, readouts, epochs, update = [], [], [], 0
        for epoch in range(1, plan.ADAPT['epochs'] + 1):
            g.epoch(); model.train(); norms = []
            for ids in orders[epoch - 1].split(plan.BATCH):
                norms.append(self.adaptation_step(model, optimizer, data['train'], weights, ids)); update += 1; self.counts['updates'] += 1
            epochs.append(dict(epoch=epoch, gradient_norm_mean=sum(norms) / len(norms), gradient_norm_max=max(norms),
                               clip_fraction=sum(n > plan.ADAPT['clip'] for n in norms) / len(norms)))
            if epoch in plan.READOUTS:
                tr, va = self.evaluate(model, data['train']), self.evaluate(model, data['validation'])
                blocks.append(self.floats(tr) + self.floats(va))
                readouts.append(dict(epoch=epoch, update=update, train_loss=float(tr.mean()), validation_loss=float(va.mean())))
                model.train()
        expected = plan.updates(len(data['train']), plan.ADAPT['epochs'])
        if update != expected or any(int(s['step']) != expected for s in optimizer.state.values()): raise RuntimeError('Adaptation updates')
        arrays = self.out.write(f'{name}/arrays.f32', b''.join(blocks))
        record = dict(stage=stage, width=width, lr=lr, tag=tag, readouts=readouts, epochs=epochs, arrays=arrays,
                      layout=dict(blocks=len(blocks), block_epochs=list(plan.READOUTS), train_rows=len(data['train']), validation_rows=len(data['validation']),
                                  order='per readout: train per-sequence loss, then validation per-sequence loss (little-endian float32)'))
        self.out.json(f'{name}/record.json', record)
        del optimizer, model; t.cuda.empty_cache(); g.full()
        return dict(path=f'{name}/record.json', tag=tag, lr=lr)

    def stage(self, stage, seeds, lrs, corpus, groups):
        """One group: its training sequences (partition), the shared validation and pool sequences, its weights and
        orders; every width pre-trained once, then adapted at each learning rate in `lrs[width]`."""
        e = self.engine; self.out.begin_stage(stage); self.guard.full()
        idx = groups[stage]['sequences']
        data = dict(train=e.load_sequences(corpus['train'], idx), validation=e.load_sequences(corpus['validation'], corpus['validation_indices']))
        pool = e.load_sequences(corpus['test'], corpus['pool_indices'])
        n = len(idx)
        weights = e.weights(seeds['weight_seed'], n)
        orders = e.orders(seeds['adapt_order_seed'], n, plan.ADAPT['epochs'])
        pool_orders = e.orders(seeds['pretrain_order_seed'], len(pool), plan.PRETRAIN['epochs'])
        hashes = dict(train=e.tensor_hash(data['train']), validation=e.tensor_hash(data['validation']), pool=e.tensor_hash(pool),
                      weights=e.tensor_hash(weights), orders=e.tensor_hash(orders), pool_orders=e.tensor_hash(pool_orders))
        self.out.json(f'{stage}/INPUTS.json', dict(seeds=seeds, n_train=n, sequence_indices_sha256=sha(json.dumps(idx).encode()), tensor_hashes=hashes,
                                                   weights=[float(x) for x in weights.tolist()], learning_rates={str(w): [lr for _, lr in v] for w, v in lrs.items()}))
        pretrained = {w: self.pretrain(stage, w, seeds, pool, data, pool_orders) for w in plan.WIDTHS}
        self.out.json(f'{stage}/PRETRAINED.json', {str(w): v for w, v in pretrained.items()})
        rows = [self.adapt(stage, w, lr, tag, pretrained[w], seeds, data, weights, orders) for w in plan.WIDTHS for tag, lr in lrs[w]]
        if e.tensor_hash(weights) != hashes['weights'] or e.tensor_hash(orders) != hashes['orders']: raise RuntimeError('Paired inputs changed')
        return rows


def benchmark(ctx, seed, limit_seconds, pool, clock=time.monotonic):
    """Outcome-blind timing and memory probe on the shared pre-training pool through the same code paths as a stage:
    per width 16 untimed + 32 timed pre-training steps, three state writes with readback (median), the E0 reload with
    its hash check, 16 untimed + 32 timed weighted adaptation steps with the per-forward guard hook, and one
    evaluation of the pool; then the full-guard, inventory-per-entry and epoch-guard costs. Every step passes the
    sampled-GPU guard, so a width that would exceed 2 GiB stops the run here, before any science. No fits."""
    t, e, g = ctx.torch, ctx.engine, ctx.guard; start = clock(); arch_out = {}
    def sync():
        if hasattr(t.cuda, 'synchronize'): t.cuda.synchronize()
    t0 = clock()
    w_bench = e.weights(seed, len(pool)); pool_orders = e.orders(seed, len(pool), 1)
    data_seconds = clock() - t0
    batches = list(pool_orders[0].split(plan.BATCH))
    if len(batches) < 48: raise RuntimeError('Pool too small for the benchmark')
    for w in plan.WIDTHS:
        if clock() - start > limit_seconds: raise TimeoutError('Benchmark limit')
        name = f'benchmark/w{w}'
        g.full(); t.manual_seed(seed); t.cuda.manual_seed_all(seed); model = ctx.Model(w, plan.LAYERS, plan.CONTEXT, plan.VOCAB).cuda()
        opt = t.optim.AdamW(model.parameters(), lr=plan.PRETRAIN['lr'], weight_decay=plan.PRETRAIN['weight_decay'])
        for ids in batches[:16]: ctx.pretraining_step(model, opt, pool, ids)
        sync(); t0 = clock()
        for ids in batches[16:48]: ctx.pretraining_step(model, opt, pool, ids)
        sync(); per_pre = (clock() - t0) / 32
        writes = []
        for k in range(BENCHMARK_WRITES):
            t0 = clock(); state = ctx.save_state(f'{name}-w{k}.pt', model); writes.append(clock() - t0)
        hashes = {k: e.tensor_hash(v) for k, v in model.state_dict().items()}
        del opt, model; t.cuda.empty_cache()
        t0 = clock(); model, opt = ctx.load_adaptation_model(w, state['path'], hashes, seed, plan.LR_GRID[1]); sync(); per_reload = clock() - t0
        model.train()
        for ids in batches[:16]: ctx.adaptation_step(model, opt, pool, w_bench, ids)
        sync(); t0 = clock()
        for ids in batches[16:48]: ctx.adaptation_step(model, opt, pool, w_bench, ids)
        sync(); per_update = (clock() - t0) / 32
        t0 = clock(); ctx.evaluate(model, pool); sync(); per_eval = (clock() - t0) / plan.eval_batches(len(pool))
        arch_out[str(w)] = dict(seconds_per_pretraining_update=per_pre, seconds_per_update=per_update, seconds_per_eval_batch=per_eval,
                                seconds_per_state_write=statistics.median(writes), state_write_seconds=writes, seconds_per_state_reload=per_reload,
                                state_bytes=state['bytes'], parameters=plan.parameters(w), peaks=dict(g.peaks))
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
    return dict(architectures=arch_out, overheads=overheads)


# ------------------------------------------------------------------ Windows-side GPU checks (revision 05)
GATE_DIR = 'gpu-checks'                 # requests and records in the run folder; the owner script's verdicts in the activation
GATE_RESPONSE_WAIT_SECONDS = 2400       # the owner script's 30-minute busy window plus a margin; then fail closed
GATE_POLL_SECONDS = 1.0
GATE_VERDICTS = ('IDLE', 'BUSY_TIMEOUT')


class GpuBusyError(RuntimeError):
    """The Windows owner script found the GPU busy (nvidia-smi) for its whole 30-minute window before a draw."""


def gate_response(raw, stage):
    """A Windows GPU check verdict (PRESTART, or before a draw): its stage, a final verdict, and every check behind it,
    of which only the last may read IDLE, and only when the verdict is IDLE."""
    r = json.loads(raw); checks = r.get('checks')
    if r.get('schema') != 1 or r.get('stage') != stage or r.get('verdict') not in GATE_VERDICTS or not isinstance(checks, list) or not checks:
        raise RuntimeError('Malformed Windows GPU check verdict for ' + stage)
    if (checks[-1].get('verdict') == 'IDLE') != (r['verdict'] == 'IDLE') or any(c.get('verdict') == 'IDLE' for c in checks[:-1]):
        raise RuntimeError('Inconsistent Windows GPU check verdict for ' + stage)
    return r


def prestart(here):
    """The owner script's pre-start check (made before its claim) must exist and read IDLE. Returns it and any refused
    pre-start checks as (name, bytes), to be recorded in the run folder."""
    d = here / GATE_DIR; path = d / 'PRESTART.json'
    if not path.exists(): raise PermissionError('No Windows pre-start GPU check')
    raw = path.read_bytes()
    try: r = gate_response(raw, 'PRESTART')
    except (RuntimeError, ValueError) as e: raise PermissionError(str(e))
    if r['verdict'] != 'IDLE': raise PermissionError('Windows pre-start GPU check is not IDLE')
    return [('PRESTART.json', raw)] + [(p.name, p.read_bytes()) for p in sorted(d.glob('PRESTART-REFUSED-*.json'))]


def gpu_gate(out, here, stage, budget, probe=None, clock=time.monotonic, sleep=time.sleep, wait=None):
    """Before a draw: request the owner script's nvidia-smi check (run folder) and wait for its verdict (activation
    folder), polling with the overall deadline checked. The verdict, with every check behind it, is recorded in the run
    folder. The wait lies outside the draw's work cap. BUSY_TIMEOUT stops the run before the draw (GpuBusyError)."""
    wait = GATE_RESPONSE_WAIT_SECONDS if wait is None else wait
    request = dict(schema=1, stage=stage, overall_remaining_seconds=budget.remaining())
    if probe is not None:
        try: request['wsl_device_used_bytes'] = int(probe())
        except Exception as e: request['wsl_device_used_error'] = type(e).__name__
    out.json(f'{GATE_DIR}/{stage}-REQUEST.json', request)
    path = here / GATE_DIR / f'{stage}-RESPONSE.json'; start = clock()
    while not path.exists():
        budget.check()
        if clock() - start > wait: raise TimeoutError('No Windows GPU check verdict before ' + stage)
        sleep(GATE_POLL_SECONDS)
    raw = path.read_bytes(); r = gate_response(raw, stage)
    out.write(f'{GATE_DIR}/{stage}.json', raw)
    if r['verdict'] != 'IDLE':
        seen = {c.get('verdict') for c in r['checks']}
        state = 'busy' if seen == {'BUSY'} else 'unverifiable (every Windows nvidia-smi check failed)' if seen == {'UNVERIFIED'} else 'busy or unverifiable'
        raise GpuBusyError(f'GPU {state} for the whole 30-minute window before {stage} (Windows nvidia-smi); stopped before {stage}')
    return r


# ------------------------------------------------------------------ admission and entry
def load_corpus(manifest, corpus_dir):
    out = {}
    for split in ('train', 'validation', 'test'):
        m = manifest['splits'][split]; raw = (corpus_dir / m['file']).read_bytes()
        if len(raw) != m['bytes'] or sha(raw) != m['sha256']: raise PermissionError('Corpus file differs from its manifest: ' + split)
        out[split] = raw
    out['validation_indices'] = text_data.validation_indices(manifest); out['pool_indices'] = text_data.pool_indices(manifest)
    return out


RUN_B_PLANS = {'B': ('B',), 'B1+B2': ('B1', 'B2'), 'UNAVAILABLE': ()}
# Authorization bindings copied into TERMINAL.json, so the analysis can check that B2 was admitted on this B1 (revision 04).
BINDING_KEYS = ('approval_id', 'approval_record_sha256', 'registry_sha256', 'corpus_manifest_sha256', 'partition_sha256', 'lr_selection_sha256',
                'run_a_terminal_sha256', 'run_b1_terminal_sha256', 'run_b_fallback_terminal_sha256')


def check_fallback(run_b, subject):
    """Run B's start-up fallback (owner rule of 28 Oct 2026, revision 03): Run B stopped before any stage because its
    own benchmark, under the frozen cap formula, put ten draws over 6 h while five fit. Re-derived from the benchmark
    bound in its TERMINAL.json. Returns the SHA-256 of that TERMINAL.json; raises ValueError otherwise."""
    run_b = Path(run_b)
    if not (run_b / 'TERMINAL.json').exists(): raise ValueError('Run B has no terminal record')
    term_raw = (run_b / 'TERMINAL.json').read_bytes(); term = json.loads(term_raw)
    if term.get('status') != 'FALLBACK_TO_SPLIT' or term.get('mode') != 'B' or term.get('subject') != subject or term.get('stages') != []: raise ValueError('Run B did not end in the pre-registered start-up fallback')
    bench_raw = (run_b / 'BENCHMARK.json').read_bytes(); bound = term.get('benchmark') or {}
    if len(bench_raw) != bound.get('bytes') or sha(bench_raw) != bound.get('sha256'): raise ValueError('Run B benchmark differs from its binding')
    b = json.loads(bench_raw)
    if (stage_cap(b['benchmark'], 'B', b['partition_n'], b['pool_n'])['feasible'] or not stage_cap(b['benchmark'], 'B1', b['partition_n'], b['pool_n'])['feasible']
            or b['caps']['feasible'] is not False or b['run_b_forecast']['B1']['feasible'] is not True): raise ValueError('Run B benchmark does not support the fallback')
    if any((run_b / d).exists() for d in plan.DRAWS): raise ValueError('Run B has a draw directory')
    return sha(term_raw)


def validate_selection(selection, run_a_terminal_sha256, mode=None, run_b_fallback=False):
    """The frozen selection: SELECTED, bound to Run A's TERMINAL.json, one grid rate per width, and a Run B plan that
    permits `mode`: B for one run; B1 and B2 for the pre-registered split, planned from Run A's forecast or, under plan
    B, after Run B's verified start-up fallback (run_b_fallback); none if UNAVAILABLE."""
    if selection.get('status') != 'SELECTED' or selection.get('run_a_terminal_sha256') != run_a_terminal_sha256: raise ValueError('Learning-rate selection status or Run A binding')
    lrs = selection.get('learning_rates', {})
    if sorted(lrs) != sorted(str(w) for w in plan.WIDTHS) or any(v not in plan.LR_GRID for v in lrs.values()): raise ValueError('Learning-rate selection values')
    plan_b = selection.get('run_b_plan', {}).get('plan')
    allowed = RUN_B_PLANS.get(plan_b, ()) + (('B1', 'B2') if plan_b == 'B' and run_b_fallback else ())
    if plan_b not in RUN_B_PLANS or (mode is not None and mode not in allowed): raise ValueError(f'Run B plan {plan_b} does not permit mode {mode}')
    return {w: float(lrs[str(w)]) for w in plan.WIDTHS}


def authorization(here=HERE, corpus_dir=None, runs=None):
    corpus_dir = corpus_dir or CORPUS; runs = runs or RUNS
    a = json.loads((here / 'AUTHORIZATION.json').read_bytes())
    if a.get('enabled') is not True or a.get('execution_ready') is not True: raise PermissionError('DISABLED: no natural-text ladder approval')
    mode = a.get('mode')
    if mode not in ACTIVATIONS or here != ACTIVATIONS[mode] or a.get('one_use') is not True or not a.get('approval_id'): raise PermissionError('Separate one-use activation required')
    raw = (here / 'SOURCE_SUBJECT.json').read_bytes()
    if sha(raw) != a.get('source_subject_sha256'): raise PermissionError('Source subject not approved')
    if sha((here / 'APPROVAL_RECORD.json').read_bytes()) != a.get('approval_record_sha256'): raise PermissionError('Approval record binding')
    subject_hashes = {}
    for row in json.loads(raw)['files']:
        b = (here / row['path']).read_bytes()
        if len(b) != row['bytes'] or sha(b) != row['sha256']: raise PermissionError('Changed source ' + row['path'])
        subject_hashes[row['path']] = row['sha256']
    reg_raw, ex_raw, draw_raw = ((here / n).read_bytes() for n in ('REGISTRY.json', 'EXCLUSIONS.json', 'DRAW.json'))
    if sha(reg_raw) != a.get('registry_sha256') or sha(ex_raw) != a.get('exclusions_sha256') or sha(draw_raw) != a.get('draw_sha256'): raise PermissionError('Registry binding')
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
    selection = None
    if mode != 'A':
        sel_raw = (here / 'LR_SELECTION.json').read_bytes()
        if sha(sel_raw) != a.get('lr_selection_sha256'): raise PermissionError('Learning-rate selection binding')
        term_a = (runs['A'] / 'TERMINAL.json').read_bytes()
        if sha(term_a) != a.get('run_a_terminal_sha256'): raise PermissionError('Run A terminal differs from the bound one')
        fallback = False
        if mode in ('B1', 'B2') and json.loads(sel_raw).get('run_b_plan', {}).get('plan') == 'B':
            try: fb = check_fallback(runs['B'], a['source_subject_sha256'])
            except ValueError as e: raise PermissionError(str(e))
            if fb != a.get('run_b_fallback_terminal_sha256'): raise PermissionError('Run B fallback terminal differs from the bound one')
            fallback = True
        try: selection = validate_selection(json.loads(sel_raw), sha(term_a), mode, fallback)
        except ValueError as e: raise PermissionError(str(e))
        if mode == 'B2':
            t1_raw = (runs['B1'] / 'TERMINAL.json').read_bytes(); t1 = json.loads(t1_raw)
            if sha(t1_raw) != a.get('run_b1_terminal_sha256') or t1.get('status') != 'COMPLETE' or t1.get('mode') != 'B1': raise PermissionError('Run B2 requires the bound, COMPLETE Run B1')
    return a, registry, manifest, partition, selection


def run(dependencies=None, here=HERE, out_root=None, clock=time.monotonic, corpus_dir=None):
    corpus_dir = corpus_dir or CORPUS
    a, registry, manifest, partition, selection = authorization(here, corpus_dir)
    mode = a['mode']; out_root = out_root or RUNS[mode]
    start = clock(); budget = Budget(start + plan.LIMITS['overall_seconds'] - 120, clock)
    if out_root.exists(): raise FileExistsError('One-use run directory exists; no retry')
    if shutil.disk_usage(out_root.parent).free < plan.LIMITS['admission_free_bytes']: raise RuntimeError('Admission free space')
    prestart_records = prestart(here)            # revision 05: refused before the run folder exists
    out_root.mkdir()
    out = Output(out_root, plan.LIMITS['stage_storage_bytes'], plan.LIMITS['stage_files'], plan.LIMITS['storage_bytes'], plan.LIMITS['total_files'])
    status = dict(subject=a['source_subject_sha256'], mode=mode, stages=[], status='STARTED', bindings={k: a[k] for k in BINDING_KEYS if k in a}); guard = ctx = None
    try:
        for name, raw in prestart_records: out.write(f'{GATE_DIR}/{name}', raw)
        if dependencies is None:
            import text_framework_setup
            torch, engine, Model = text_framework_setup.setup(out_root / 'cache')
        else: torch, engine, Model = dependencies
        guard = Guard(budget, out, cuda=torch.cuda); out.guard = guard
        ctx = Context(torch, engine, Model, guard, out)
        corpus = load_corpus(manifest, corpus_dir)
        pool = engine.load_sequences(corpus['test'], corpus['pool_indices'])
        bench = benchmark(ctx, registry['benchmark']['benchmark_seed'], plan.LIMITS['benchmark_seconds'], pool, clock)
        bench_counts = dict(ctx.counts); ctx.counts = {k: 0 for k in ctx.counts}   # scientific counts exclude the benchmark
        caps = stage_cap(bench, mode, partition['n'], len(pool))
        # Outcome-blind forecasts (owner rules of 28 Oct 2026): Run A forecasts one ten-draw Run B and a five-draw split run
        # (select_lr.py turns them into the frozen Run B plan); Run B forecasts the five-draw run for its start-up fallback.
        forecast = ({m: stage_cap(bench, m, partition['n'], len(pool)) for m in ('B', 'B1')} if mode == 'A' else
                    {'B1': stage_cap(bench, 'B1', partition['n'], len(pool))} if mode == 'B' else None)
        status['benchmark'] = out.json('BENCHMARK.json', dict(benchmark=bench, caps=caps, run_b_forecast=forecast, benchmark_counts=bench_counts, guard_calls=dict(guard.calls),
                                                              partition_n=partition['n'], pool_n=len(pool)))
        if not caps['feasible']:
            if mode == 'B' and forecast['B1']['feasible']:
                # Start-up fallback (revision 03): ten draws do not fit in 6 h by Run B's own benchmark but five do. Stop here,
                # before any training; the draws go to the pre-registered split runs B1 and B2 (new activations).
                status.update(status='FALLBACK_TO_SPLIT', fallback=dict(rule='Run B infeasible and a five-draw run feasible by the frozen cap formula on this benchmark',
                                                                        B=caps['formula'], B1=forecast['B1']['formula']))
                return 0
            raise RuntimeError('Projected stage time exceeds the frozen envelope; stopping before any scientific stage')
        seeds = {row['group']: {k: v for k, v in row.items() if k != 'group'} for row in registry['groups']}
        plan_stages = list(plan.RUN_STAGES[mode])
        lrs = ({w: [(LR_TAGS[lr], lr) for lr in plan.LR_GRID] for w in plan.WIDTHS} if mode == 'A' else {w: [('selected', selection[w])] for w in plan.WIDTHS})
        device_used = lambda: (lambda free, total: total - free)(*torch.cuda.mem_get_info())
        for stage in plan_stages:
            gpu_gate(out, here, stage, budget, probe=device_used, clock=clock)      # revision 05: outside the work cap
            stage_start = clock()
            guard.budget = Budget(min(budget.deadline, stage_start + caps['stage_work_cap_seconds']), clock)
            rows = ctx.stage(stage, seeds[stage], lrs, corpus, partition['groups'])
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
    if len(sys.argv) != 2 or sys.argv[1] != 'run': raise SystemExit('usage: text_worker.py run')
    try: raise SystemExit(run())
    except PermissionError as e: sys.stderr.write(str(e) + '\n'); raise SystemExit(1)
