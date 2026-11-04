"""Frozen capacity-shift follow-up plan (fresh-corpus test of the G16 peak shift under R). Pure constants.

Derived from work/capacity-ladder-source-20261026-01/ladder_plan.py. Changes: G16 only, arms R and S_batch, the
eight depth-4 rungs (no bridge, no H), 40 adaptation epochs, validation also at E15/E25/E40, twelve corpora, no
landmark states, and a resource envelope resized for this workload.
Importing this module cannot generate data, import a framework or launch anything.
"""
EXECUTION_ENABLED = False

# Architectures: the ladder's eight widths at fixed depth 4 (approximately log-spaced, x1.5 / x1.33 alternating).
LADDER = ((32, 4), (48, 4), (64, 4), (96, 4), (128, 4), (192, 4), (256, 4), (384, 4))
BRIDGE = ()
ARCHS = LADDER + BRIDGE
HEADS = 4
SEQ_LEN = 40
CONDITIONS = ('G16',)
ARMS = ('R', 'S_batch')                      # all architectures
H_ARCHS = ()                                 # no H trajectories; H stays defined for the timing benchmark only
H_CONDITIONS = ()
COEFFICIENTS = {'R': ('w', 'w', 'w'), 'S_batch': ('w', 'w', 'mu'), 'H': ('mu', 'w', 'mu'), 'U': (1, 1, 1)}  # shared/group/instance

# Recipe: the v0128 / confirmation / ladder recipe, except the adaptation horizon (30 -> 40 epochs).
PRETRAIN = dict(rows=2048, validation_rows=256, epochs=4, batch=32, lr=3e-4, weight_decay=0.1, clip=5.0)
ADAPT = dict(train_rows=512, validation_rows=256, batch=32, lr=1e-4, weight_decay=0.1, clip=1.0, epochs=40)
LADDER_ADAPT_EPOCHS = 30                                           # horizon of the completed ladder (identity check)
UPDATES_PER_EPOCH = ADAPT['train_rows'] // ADAPT['batch']          # 16
TOTAL_UPDATES = UPDATES_PER_EPOCH * ADAPT['epochs']                # 640
FIXED_EPOCHS = (1, 3, 5, 10, 15, 20, 25, 30, 40)                   # validation readouts
PRIMARY_EPOCHS = (15, 20, 25, 30, 40)                              # primary slope epochs
CHECK_UPDATES = tuple(range(4, 3 * UPDATES_PER_EPOCH + 1, 4)) + tuple(UPDATES_PER_EPOCH * e for e in range(4, ADAPT['epochs'] + 1))
LANDMARKS = (0.10, 0.50, 0.90)                                     # group-progress targets (validation saved; no states)
SUPPLEMENTARY_LANDMARKS = (0.02, 0.05)                             # train arrays only
ALL_LANDMARKS = tuple(sorted(SUPPLEMENTARY_LANDMARKS + LANDMARKS))
SAVE_LANDMARK_STATES = False
COARSE_OVERSHOOT = 0.05                                            # flag, never a reason to drop
P_UPPER = 7.999; P_LOWER = 0.001                                   # inherited estimator boundary conventions

CORPORA = tuple(f'c{i:02d}' for i in range(1, 13))
SEED_ROLES = ('adaptation_seed', 'pretraining_seed', 'weight_seed', 'order_seed', 'init_seed')
BENCHMARK_ROLE = 'benchmark_seed'
RECORD_BYTES = 2 ** 18                                             # generous bound for one record.json (ladder: 28 KB measured)

# Resource envelope (owner-checked before admission; worker-enforced during work).
# stage_work_seconds = (overall - benchmark) / 12 - 300, so the per-stage cap and the overall feasibility rule coincide.
LIMITS = dict(stage_work_seconds=1425, overall_seconds=21600, benchmark_seconds=900,
              storage_bytes=3 * 2 ** 30, stage_storage_bytes=2 ** 28, stage_files=128, total_files=1000,
              admission_free_bytes=5 * 2 ** 30, reserve_free_bytes=2 * 2 ** 30,
              gpu_sampled_bytes=2 * 2 ** 30, worker_peak_rss_bytes=4032 * 2 ** 20)


def parameters(width, layers, vocab=84, length=SEQ_LEN):
    """Exact parameter count of vendor/model.py Model(width, layers, length)."""
    return layers * (12 * width * width + 13 * width) + (2 * vocab + length + 2) * width


def trajectories():
    rows = [(c, a, w, l) for c in CONDITIONS for a in ARMS for (w, l) in ARCHS]
    rows += [(c, 'H', w, l) for c in H_CONDITIONS for (w, l) in H_ARCHS]
    return tuple(rows)


def counts():
    per_corpus = len(trajectories())
    t = per_corpus * len(CORPORA)
    checks = len(CHECK_UPDATES)
    return dict(architectures=len(ARCHS), trajectories_per_corpus=per_corpus, trajectories=t,
                pretraining_models=len(ARCHS) * len(CORPORA),
                pretraining_updates=len(ARCHS) * len(CORPORA) * PRETRAIN['epochs'] * PRETRAIN['rows'] // PRETRAIN['batch'],
                adaptation_updates=t * TOTAL_UPDATES, checks_per_trajectory=checks,
                train_check_batches=t * checks * ADAPT['train_rows'] // ADAPT['batch'],
                fixed_validation_batches=t * len(FIXED_EPOCHS) * ADAPT['validation_rows'] // ADAPT['batch'],
                max_landmark_validation_batches=t * len(LANDMARKS) * ADAPT['validation_rows'] // ADAPT['batch'],
                E0_batches=len(ARCHS) * len(CORPORA) * len(CONDITIONS) * (ADAPT['train_rows'] + ADAPT['validation_rows']) // ADAPT['batch'],
                pretraining_final_eval_batches=len(ARCHS) * len(CORPORA) * (PRETRAIN['rows'] + PRETRAIN['validation_rows']) // PRETRAIN['batch'])


def storage_estimate():
    state = {a: 4 * parameters(*a) for a in ARCHS}
    landmark = sum(4 * parameters(w, l) * len(LANDMARKS) for (c, a, w, l) in trajectories()) * len(CORPORA) if SAVE_LANDMARK_STATES else 0
    pretrained = sum(state.values()) * len(CORPORA)
    per_check = ADAPT['train_rows'] * 7 * 4
    arrays = len(trajectories()) * len(CORPORA) * (len(CHECK_UPDATES) * per_check + (len(FIXED_EPOCHS) + len(LANDMARKS)) * ADAPT['validation_rows'] * 7 * 4)
    E0 = len(ARCHS) * len(CORPORA) * len(CONDITIONS) * (ADAPT['train_rows'] + ADAPT['validation_rows']) * 7 * 4
    records = len(trajectories()) * len(CORPORA) * RECORD_BYTES
    benchmark = 3 * sum(state.values())   # three benchmark state writes per architecture (median timing)
    return dict(landmark_states=landmark, pretrained_states=pretrained, arrays=arrays, E0_arrays=E0, records_bound=records, benchmark_states=benchmark,
                total=landmark + pretrained + arrays + E0 + records + benchmark, per_stage=(landmark + pretrained + arrays + E0 + records) / len(CORPORA),
                state_bytes_by_arch={f'{w}/{l}': b for (w, l), b in state.items()})
