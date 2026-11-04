"""Frozen plan of the natural-text one-rate ladder extension (owner decisions 20261030-01 and -02). Pure constants.

R1 extends revision 05's COMPLETE Run B on the same ten draws d01-d10, at one learning rate, 3e-5, for every width:
- 64 and 96: new weighted adaptations at 3e-5 from Run B's own E0 states, with Run B's weights, orders and seeds;
- 128, 192, 256 and 384: Run B's trajectories, which already used 3e-5 (LR_SELECTION cb059387...), reused unchanged;
- 512 and 768: new widths, pre-trained and adapted exactly as Run B's widths were, from each draw's own seeds.
The start-up memory fallback (owner decision 20261030-02): if the run's own start-up benchmark finds 768 above the
probe's 2.25 GiB limit, the ladder top is 512, decided from memory only, before any training.
Revision 02 (owner ruling 20261030-03): the final attempt, in new -02 folders, after attempt 1 failed in d06 when the
charger was unplugged; attempt 1 is never analysed. Operational changes only: a power gate and a power log in the owner
script, a clear power-stop error and a draw-folder record in the worker, and the analysis's refusal of attempt 1.
Importing this module cannot read data, import a framework or launch anything.
"""
EXECUTION_ENABLED = False
REVISION = 2

# Paths (relative to the project root; text_worker.ROOT gives the root on Linux and Windows).
ACTIVATION = 'work/natural-text-onerate-activation-20261030-02'
RUN = 'work/runs/natural-text-onerate-20261030-02'
# Attempt 1 (revision 01, FAILED in d06 on the per-draw work cap after the charger was unplugged): preserved, never analysed.
ATTEMPT_1 = dict(run='work/runs/natural-text-onerate-20261030-01', activation='work/natural-text-onerate-activation-20261030-01',
                 terminal_sha256='0b994ed9fbb59717534f5e8e84a19d7f0cd8672101c4715496b790b2aa12d90c',
                 subject='4ca9833cad1152165552a8b2a42ea8f2b003f8cab4c39a3e3ab2105d2698d672',
                 failure_report='reports/natural-text-onerate-failure-20261030-01/FAILURE_REPORT.md')
POWER_VERDICTS = ('ON_BATTERY', 'POWER_UNVERIFIED')   # a before-draw check off AC power (power_gate.ps1)
SEED_REGISTRY = 'reports/natural-text-ladder-seed-registry-20261028-01'        # REGISTRY.json, EXCLUSIONS.json, DRAW.json (Run B's)
RUN_B = dict(run='work/runs/natural-text-ladder-b-20261028-02',
             inventory='reports/natural-text-ladder-analysis-20261029-01/INVENTORY_BEFORE.json',   # every Run B file by size and sha256, taken before its analysis
             terminal_sha256='277e38c747bb2082aec4139e5e549c4e581bf1a37eae1e540db48b49afd8504c',
             inventory_sha256='36a4c2f902fb58728130be20677796b1f3abba3e117edeaf3dd78fc299fc7821',
             subject='2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d',
             registry_sha256='8ce7d597578af702aa96249c0215aed2927383629add78f6fb000a1251dbcfeb',
             exclusions_sha256='ee4fba48a1f563d997089221b1bafe645a525db5a4a8885244d462f8ae6536bd',
             draw_sha256='3c0304a89f1b610ef4d58f65002aff1741a9e1897c4a3c28c0946ff4423bd2d1',
             partition_sha256='5f9f26468fade104da6e9f20021353cde9116cbb4311aa9d2025535d0caae0a7',
             corpus_manifest_sha256='72daa1e174caa346494fb9a6cd0ded4ed192038a8918e4569a2a4ddb67a0834f',
             lr_selection_sha256='cb059387dc26f6743199f446940487d55d868700130faa68b9256eb333b2c217',
             rates={64: 3e-4, 96: 1e-4, 128: 3e-5, 192: 3e-5, 256: 3e-5, 384: 3e-5})

# Widths and the one rate (owner decision 20261030-01, items 1-3).
LR = 3e-5
TAG = 'onerate'
ADAPT_ONLY = (64, 96)                       # adapted here from Run B's E0 states
REUSED = (128, 192, 256, 384)               # Run B's trajectories at 3e-5
NEW = (512, 768)                            # pre-trained and adapted here
LADDER = {768: (64, 96, 128, 192, 256, 384, 512, 768), 512: (64, 96, 128, 192, 256, 384, 512)}
BENCH_WIDTHS = (64, 96, 512, 768)           # the start-up benchmark: every width trained here, 768 last


def new_widths(top): return tuple(w for w in NEW if w <= top)
def trained_widths(top): return tuple(sorted(new_widths(top) + ADAPT_ONLY, reverse=True))   # stage order: 768, 512, 96, 64


# GPU memory (owner decisions 20261030-01 item 2 and 20261030-02 item 2; the probe's limit).
GUARD_BYTES = 5 * 2 ** 29                    # 2.5 GiB sampled-GPU guard for the whole run
MARGIN_BYTES = 2 ** 28
FIT_LIMIT_BYTES = GUARD_BYTES - MARGIN_BYTES  # 2.25 GiB = 2,415,919,104 bytes

# Resource envelope of the one owner run (revision 05's, with the 2.5 GiB guard and 3 GiB admission free space).
LIMITS = dict(overall_seconds=21600, benchmark_seconds=900, cap_multiplier=1.25, cap_fixed_seconds=120, stage_slack_seconds=60,
              storage_bytes=2 * 2 ** 30, stage_storage_bytes=2 ** 28, stage_files=128, total_files=1000,
              admission_free_bytes=3 * 2 ** 30, reserve_free_bytes=2 * 2 ** 30,
              gpu_sampled_bytes=GUARD_BYTES, worker_peak_rss_bytes=4032 * 2 ** 20)

# Primaries (owner decision 20261030-01, item 5): epochs E4-E32, df-9 intervals over the ten draws.
PRIMARY_EPOCHS = (4, 6, 8, 12, 16, 24, 32)
TURN_WIDTHS = {768: (384, 512, 768), 512: (384, 512)}       # under the 512 top the turn-down is the two-point change 384 -> 512
DIP_WIDTHS = (64, 96, 128)
LABELS = dict(turn=('TURNS_DOWN', 'CONTINUES_RISING', 'INCONCLUSIVE'),
              dip=('DIP_PERSISTS', 'NO_DIP_AT_ONE_RATE', 'INCONCLUSIVE'),
              memo=('OPPOSES_MEMORIZATION', 'TRACKS_MEMORIZATION', 'NO_DETECTED_TRACKING'))   # (interval below 0, above 0, otherwise)
PREDICTIONS = dict(memorization=dict(turn='CONTINUES_RISING', dip='NO_DIP_AT_ONE_RATE', memo='TRACKS_MEMORIZATION'),
                   jane_street=dict(turn='TURNS_DOWN'))
