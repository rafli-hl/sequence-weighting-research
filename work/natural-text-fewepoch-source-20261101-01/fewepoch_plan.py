"""Frozen plan of the few-epoch, data-rich width ladder (owner decisions 20261101-01 and -02). Pure constants.

WikiText-103 raw (acquired under the sealed acquisition source; the frozen 4,096-token natural-text tokenizer), widths
64-768, 3 epochs of weighted adaptation at one common constant rate chosen on a tuning draw t00 by validation NLL only, readouts
at E0.25, E0.5, E1, E2 and E3, ten fresh analysis draws d01-d10 in two runs B1 (d01-d05) and B2 (d06-d10). Three primaries
under Holm's step-down at family-wise 5% (two-sided; df 9):
- M: per draw, p* at 768 minus p* at 384 at matched train-validation gap (interpolated along each width's readouts E0.25-E3,
  first crossing in readout order), averaged over 101 equally spaced gap levels both widths reach;
- FALL: the OLS slope of p* on log2 width over 384, 512, 768 at E3;
- RISE: the OLS slope of p* on log2 width over 64, 96, 128, 192, 256, 384 at E3.
NOT_OVERFIT (manipulation check): per width, validation NLL at E3 minus E2 per draw; a primary is read as a few-epoch test
only if every width it uses has its df-9 interval below 0. The peak shift across readouts is a secondary.
The corpus, registry and partition pins are PENDING (None) until the acquisition and the seed draw exist; the worker, the
registry tool and the builder refuse real mode until they are set by a pin-only revision.
Importing this module cannot read data, import a framework or launch anything.
"""
EXECUTION_ENABLED = False

# Paths (relative to the project root; text_worker.ROOT gives the root on Linux and Windows).
SOURCE = 'work/natural-text-fewepoch-source-20261101-01'
CORPUS = 'work/runs/natural-text-corpus-wt103-20261101-01'
ACTIVATIONS = dict(A='work/natural-text-fewepoch-activation-a-20261101-01', A2N='work/natural-text-fewepoch-activation-a2n-20261101-01',
                   B1='work/natural-text-fewepoch-activation-b1-20261101-01', B2='work/natural-text-fewepoch-activation-b2-20261101-01')
RUNS = dict(A='work/runs/natural-text-fewepoch-a-20261101-01', A2N='work/runs/natural-text-fewepoch-a2n-20261101-01',
            B1='work/runs/natural-text-fewepoch-b1-20261101-01', B2='work/runs/natural-text-fewepoch-b2-20261101-01')

# The acquisition (A1-A3) and the pins set after it (PENDING until then).
ACQUISITION_SUBJECT = '2b8033ef98cfbd76a04858a8003d4344a904cc43a81c49dbc599c5357379adda'   # the corpus manifest must record this source subject
CORPUS_MANIFEST_SHA256 = 'be911db7a63238a205fc74c5732f78431befd61ba7d26af48202a31163df39ea'   # the WikiText-103 corpus manifest written by A3 (owner-run, 1 Nov 2026)
REGISTRY = dict(directory='reports/natural-text-fewepoch-seed-registry-20261101-01',
                policy_sha256='16eb8ba5dafc6fbbfc829fbc5fbcce3ed9ed670bc3a3c05d94b9bb689a797fc9',
                registry_sha256='75db913de7b1860cd269ce262144859334b61e8248ebad5c00b47caaa60106af', exclusions_sha256='ac8ed671f509b1c0da6fca833b772cfc1ba9846f61ffeea3d2a583dc32df8455', draw_sha256='6647f6e9cb97c94219beb666b4a567bc71948ba889faa8f674b24ee902286cf4', approval_id='OWNER-20261101-FEWEPOCH-SEEDS-01')   # the owner-run seed draw (2 Nov 2026)
PARTITION_SHA256 = 'ccba750a3201fa4e390f1e00b408256c2cbcf02894a3145d10a5fe3133bee119'   # encoded fewepoch_data.partition of the drawn registry


def pins_set():
    return all(v is not None for v in (CORPUS_MANIFEST_SHA256, REGISTRY['registry_sha256'], REGISTRY['exclusions_sha256'], REGISTRY['draw_sha256'], PARTITION_SHA256))


# Groups and runs.
TUNING = 't00'
DRAWS = tuple(f'd{i:02d}' for i in range(1, 11))
GROUPS = (TUNING,) + DRAWS
RUN_STAGES = dict(A=(TUNING,), A2N=(TUNING,), B1=DRAWS[:5], B2=DRAWS[5:])
TUNING_MODES = ('A', 'A2N')

# Data per draw (D1): N sequences of 129 tokens; each group is filled with whole articles to N_FILL, so that the Run A
# fallback at 2N needs no new partition.
N_TRAIN = 16384
N_FALLBACK = 2 * N_TRAIN                     # Run A2N only (D5); a B layout at 2N needs a later revision
N_FILL = 2 * N_TRAIN

# Models and the recipe (revision 05's, except the epochs, readouts and rate).
WIDTHS = (64, 96, 128, 192, 256, 384, 512, 768)
STAGE_ORDER = tuple(reversed(WIDTHS))         # per draw: widest first; each width's state hashed and deleted after its training
BENCH_WIDTHS = WIDTHS                         # the start-up benchmark, 768 last
EPOCHS = 3
READOUTS = (0.25, 0.5, 1, 2, 3)               # in epochs; a readout follows update round(e x N / 16)
FINAL, PREVIOUS = 3, 2
LR_GRID = (3e-5, 1e-4, 3e-4, 1e-3)            # D4
LR_EXTENSION = 3e-3                           # D5: considered only if the grid's top rate is selected
RUN_A_RATES = LR_GRID + (LR_EXTENSION,)
SELECTED_TAG = 'selected'
POWER_VERDICTS = ('ON_BATTERY', 'POWER_UNVERIFIED')


def rate_tag(lr): return f'lr{lr:.0e}'


def readout_update(epoch, n, batch=16):
    """The update after which readout `epoch` is taken (N must be a multiple of 64 so that quarter epochs are whole)."""
    if n % (4 * batch): raise ValueError('N must be a multiple of 64')
    return int(round(epoch * n / batch))


# GPU memory: the late-turn run's guard and start-up limit (no fallback: two primaries need 768).
GUARD_BYTES = 5 * 2 ** 29
FIT_LIMIT_BYTES = GUARD_BYTES - 2 ** 28

# Resource envelope of each owner run (the late-turn limits) and the reserve for one full 30-minute gate wait.
LIMITS = dict(overall_seconds=21600, benchmark_seconds=900, cap_multiplier=1.25, cap_fixed_seconds=120, stage_slack_seconds=60,
              storage_bytes=2 * 2 ** 30, stage_storage_bytes=2 ** 28, stage_files=128, total_files=1000,
              admission_free_bytes=3 * 2 ** 30, reserve_free_bytes=2 * 2 ** 30,
              gpu_sampled_bytes=GUARD_BYTES, worker_peak_rss_bytes=4032 * 2 ** 20)
GATE_RESERVE_SECONDS = 1800

# Primaries (owner decisions 20261101-02): Holm over the family at two-sided 5%.
FAMILY = ('M', 'FALL', 'RISE')
ALPHA = 0.05
M_WIDTHS = (384, 768)
M_LEVELS = 101
FALL_WIDTHS = (384, 512, 768)
RISE_WIDTHS = (64, 96, 128, 192, 256, 384)
GATE_WIDTHS = dict(M=M_WIDTHS, FALL=FALL_WIDTHS, RISE=RISE_WIDTHS)
LABELS = dict(M=('CAPACITY_BEYOND_MEMORIZATION', 'CAPACITY_ABOVE_MEMORIZATION', 'NOT_DETECTED'),         # (rejected below 0, rejected above 0, not rejected)
              FALL=('TURNS_DOWN', 'CONTINUES_RISING', 'INCONCLUSIVE'),
              RISE=('FALLS', 'RISES', 'INCONCLUSIVE'))
PREDICTIONS = dict(memorization_only=dict(M='NOT_DETECTED', FALL='CONTINUES_RISING or INCONCLUSIVE', RISE='RISES'),
                   jane_street=dict(M='not fixed by the pattern', FALL='TURNS_DOWN', RISE='RISES'))
# Power stated in advance (reports/natural-text-fewepoch-preparation-20261101-01/FEWEPOCH_PLANNING_r2.json, Holm over the
# three primaries, ten draws): the probability of rejecting in the direction of the seen effect, at the seen effect and at half.
POWER = dict(M=dict(seen='>0.999', half='0.953'), FALL=dict(seen='0.999', half='0.714'), RISE=dict(seen='>0.999', half='>0.999'))
