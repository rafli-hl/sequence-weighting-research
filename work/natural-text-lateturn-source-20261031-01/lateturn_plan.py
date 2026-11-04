"""Frozen plan of the late-turn confirmation (owner decisions 20261031-02 and -03). Pure constants.

A fresh-draw confirmation of the one-rate study's late-epoch turn-down (its sealed by-epoch secondaries, seen on d01-d10):
four fresh WikiText-2 groups f01-f04 (the drawn late-turn registry; the partition frozen in lateturn_data before any seed
existed), widths 256, 384, 512 and 768, every width pre-trained and adapted in this run at one learning rate, 3e-5, with
the natural-text recipe unchanged. Each width's model state is hashed and deleted after its training (item 6). There is no
start-up memory fallback: every primary needs 768, so the run stops before any training if a width does not fit.
Primaries, read in a fixed sequence P1 -> P3 -> P2, each at two-sided 95% (df 3):
- P1: the OLS slope of p* on log2 width over 384, 512, 768 at E32;
- P3: the shift of the peak location from E8 to E32, L(E8) - L(E32) in doublings, L from revision 05's sealed
  text_analysis.peak_location on the study ladder (a peak at a ladder end is recorded at that rung; S is a lower bound
  only under the censoring condition of PROTOCOL.md section 6);
- P2: the P1 statistic at E24.
Importing this module cannot read data, import a framework or launch anything.
"""
EXECUTION_ENABLED = False

# Paths (relative to the project root; text_worker.ROOT gives the root on Linux and Windows).
ACTIVATION = 'work/natural-text-lateturn-activation-20261031-01'
RUN = 'work/runs/natural-text-lateturn-20261031-01'

# The drawn late-turn registry (OWNER-20261031-LATETURN-SEEDS-01) and its fresh partition.
REGISTRY = dict(directory='reports/natural-text-lateturn-seed-registry-20261031-01',
                registry_sha256='b9b6a8821613a1f2de610404145aaff56279a7967c130d0c215cdcf5beb0b9ff',
                exclusions_sha256='f6cd90b6bf40190c355ece776100db4ce85bf2feffe04d9c416cda47041fd76b',
                draw_sha256='f0e7298a6193aeee95b83fae32e9446043e5de170563721eae0ebac63faf058f',
                policy_sha256='1050451f48c9a0bcb9b6a7e2f8203b98b424e8d3bad9a4f61d7eadc07f7b0dab',
                registry_source_subject='49398ed5123b7ca241d76810088f75085c50320ce61afce2becc4360f133ae69',
                approval_id='OWNER-20261031-LATETURN-SEEDS-01')
SEEN = dict(registry='reports/natural-text-ladder-seed-registry-20261028-01/REGISTRY.json',          # t00, d01-d10: the used articles
            registry_sha256='8ce7d597578af702aa96249c0215aed2927383629add78f6fb000a1251dbcfeb',
            partition_sha256='5f9f26468fade104da6e9f20021353cde9116cbb4311aa9d2025535d0caae0a7')
CORPUS_MANIFEST_SHA256 = '72daa1e174caa346494fb9a6cd0ded4ed192038a8918e4569a2a4ddb67a0834f'
FRESH_PARTITION_SHA256 = 'f25cfb6d79913fa4c73eca123c022b532540c8fe0d2788c5c197e18881cf1c0f'   # encoded lateturn_data.fresh_partition (N = 1,536)
# The September public-text check (work/runs/text-check-v02) fine-tuned Pythia-70M on paragraphs of these 10 training
# articles, all in f01-f04 (disclosed; owner decisions 20261031-03, item 3: the owner has not yet chosen between keeping the
# frozen rule, option a, and excluding these articles, option b; this source proceeds under option a). The builder refuses
# unless the selection file has this hash and gives exactly these articles (review 1, finding 5).
TEXT_CHECK_V02 = dict(selection='work/runs/text-check-v02/selected-rows.json', selection_sha256='418b04e99fd44bba70b5898be5b42b8008df82cbb12a82cdcda42f02642cb5bd',
                      train_articles_in_fresh_groups=(0, 1, 6, 7, 10, 15, 21, 26, 27, 29))

# Draws, widths and the one rate.
DRAWS = ('f01', 'f02', 'f03', 'f04')
WIDTHS = (256, 384, 512, 768)
STAGE_ORDER = (768, 512, 384, 256)            # per draw: pre-train, adapt, then hash and delete the state, widest first
BENCH_WIDTHS = (256, 384, 512, 768)           # the start-up benchmark, 768 last
LR = 3e-5
TAG = 'lateturn'
POWER_VERDICTS = ('ON_BATTERY', 'POWER_UNVERIFIED')   # a before-draw check off AC power (power_gate.ps1)

# GPU memory (the one-rate study's guard and the probe's limit).
GUARD_BYTES = 5 * 2 ** 29                     # 2.5 GiB sampled-GPU guard for the whole run
MARGIN_BYTES = 2 ** 28
FIT_LIMIT_BYTES = GUARD_BYTES - MARGIN_BYTES  # 2.25 GiB = 2,415,919,104 bytes

# Resource envelope of the one owner run (the one-rate run's).
LIMITS = dict(overall_seconds=21600, benchmark_seconds=900, cap_multiplier=1.25, cap_fixed_seconds=120, stage_slack_seconds=60,
              storage_bytes=2 * 2 ** 30, stage_storage_bytes=2 ** 28, stage_files=128, total_files=1000,
              admission_free_bytes=3 * 2 ** 30, reserve_free_bytes=2 * 2 ** 30,
              gpu_sampled_bytes=GUARD_BYTES, worker_peak_rss_bytes=4032 * 2 ** 20)

# Primaries (owner decisions 20261031-02, items 3-5): one point per draw, df-3 intervals over the four draws.
TURN_WIDTHS = (384, 512, 768)
PRIMARIES = dict(P1=dict(kind='turn', epoch=32), P3=dict(kind='shift', epochs=(8, 32)), P2=dict(kind='turn', epoch=24))
SEQUENCE = ('P1', 'P3', 'P2')                 # fixed order; a later primary is read as confirmed only if every earlier one was
LABELS = dict(turn=('TURNS_DOWN', 'CONTINUES_RISING', 'INCONCLUSIVE'),
              shift=('SHIFTS_TO_LARGER_WIDTH', 'SHIFTS_TO_SMALLER_WIDTH', 'NO_DETECTED_SHIFT'))     # (interval below 0, above 0, otherwise)
PREDICTED = dict(P1='TURNS_DOWN', P3='SHIFTS_TO_SMALLER_WIDTH', P2='TURNS_DOWN')
# Power stated in advance (reports/natural-text-onerate-confirmation-draft-20261031-01/CONFIRMATION_PLANNING.json; four
# draws, two-sided 95%): the probability of the predicted label at the seen effect, and under the conservative and the
# halved effect.
POWER = dict(P1=dict(observed='>0.9999', conservative='>0.9999', halved='>0.9999'),
             P3=dict(observed='>0.9999', conservative='>0.9999', halved='>0.9999'),
             P2=dict(observed='0.678', conservative='0.157', halved='0.247'))
