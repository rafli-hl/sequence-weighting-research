"""Frozen plan of the matched-progress confirmation, N7 (owner instruction of 4 Nov 2026). Pure constants.

Six fresh WikiText-103 draws m01-m06 in two runs, M1 (m01-m03) and M2 (m04-m06), with the few-epoch recipe, 3.5 epochs and dense readouts.
Per draw, the target is 512's value at E3; 768's p* is read along its own readouts E2-E3.5 by linear interpolation at that value.
A fixed sequence of six statistics, each read as a confirmation only while every earlier one is confirmed (the order: owner decision 20261104-02):
- P1, the primary, at 1e-4: D4m_train = p*(512, E3) - p*(768, matched on the training NLL);
- S1, at 1e-4: D4m matched on the gap;
- S3, at 1e-4: the fixed-update D4 at E3, expected negative, which replicates N6's RATE_DEPENDENT;
- S4 and S5, at 3e-4: D2m_train, matched on the training NLL, and the fixed-update D2 at E3;
- S2, at 1e-4, last: D4m matched on the validation NLL.
No rate is chosen: 3e-4 is the few-epoch study's selected rate and 1e-4 is 768's lowest validation NLL on t00, both by validation NLL
only. The shared recipe and limits come from fewepoch_plan.py, a byte copy.
The registry and partition pins are PENDING (None) until the owner-run seed draw; the worker and the builder refuse real mode until a
pin-only revision sets them. Importing this module cannot read data, import a framework or launch anything.
"""
import fewepoch_plan as fp
import matched_data as md

EXECUTION_ENABLED = False

# Paths (relative to the project root).
SOURCE = 'work/natural-text-matched-source-20261104-01'
CORPUS = fp.CORPUS
ACTIVATIONS = dict(M1='work/natural-text-matched-activation-m1-20261104-01', M2='work/natural-text-matched-activation-m2-20261104-01')
RUNS = dict(M1='work/runs/natural-text-matched-m1-20261104-01', M2='work/runs/natural-text-matched-m2-20261104-01')

# The owner-run seed draw and its partition: PENDING until they exist.
REGISTRY = dict(directory='reports/natural-text-matched-seed-registry-20261104-01',
                policy_sha256='323b5ae492243b9f9b34fd7a3e2bf516b4d96572aa497d065ae89ca8a1921080',
                registry_sha256='bee578826fbdb5e66fbb36d577e45929af756e05b12b62d6cd141b4b5da7ea64',
                exclusions_sha256='a90573e7eb6e4ead368c189899939e6ec1202d1f091746db17535f5c49522236',
                draw_sha256='ae25d9af79865f81bf639842fdc32637acc1280520a1ee56a3fbc3ab58daf1cf',
                approval_id='OWNER-20261104-MATCHED-SEEDS-01')
PARTITION_SHA256 = 'b7eb3d3ba200b86046c6d731d2f0200ff657b6c2aaeebd43423cd4aec530e33b'


def pins_set():
    return all(v is not None for v in (REGISTRY['registry_sha256'], REGISTRY['exclusions_sha256'], REGISTRY['draw_sha256'], REGISTRY['approval_id'], PARTITION_SHA256))


# The two earlier registries whose articles are out (their pins; the registries live in reports/).
PEAK_REGISTRY = dict(directory='reports/natural-text-peak-seed-registry-20261103-01', registry_sha256='0e8b05285a6ad98a32a2041f0907e423c9c8d85fa6408e6a90be9acfb8c326dd')
PEAK_PARTITION_SHA256 = md.PEAK_PARTITION_SHA256

# Groups and runs.
GROUPS = md.GROUPS
RUN_STAGES = dict(M1=GROUPS[:3], M2=GROUPS[3:])
N_TRAIN = md.N_TRAIN
MIN_DRAWS = 5                                 # a statistic with fewer available draws is UNAVAILABLE
MIN_M1_DRAWS_FOR_M2 = 2                       # a FAILED Run M1 admits Run M2 with at least this many completed draws, counted from operational records (owner decision 20261104-02)

# The rates and the arms. A width's arms share its E0, tokens, weights and batch order.
RATE_HIGH, RATE_LOW = 3e-4, 1e-4
RATE_SOURCE = dict(file='reports/natural-text-peak-analysis-approval-20261103-01/pinned-records/LR_SELECTION.json', sha256='fa760ba0d693518ba1b98a40f366899ebec3a013ff03863284a3ac2c32b5ad01')
WIDTHS = (512, 768)
BENCH_WIDTHS = WIDTHS                         # the start-up benchmark, 768 last
ARMS = {768: (RATE_HIGH, RATE_LOW), 512: (RATE_HIGH, RATE_LOW)}      # per draw: widest first, each width's state hashed and deleted after its arms
TAG_HIGH, TAG_LOW = fp.rate_tag(RATE_HIGH), fp.rate_tag(RATE_LOW)

# Readouts, in epochs; a readout follows update round(e x N / 16). E0 is each width's pre-trained state, shared by its arms.
READOUTS = (0.25, 0.5, 1, 2, 2.25, 2.5, 2.75, 3, 3.25, 3.5)
LAST_READOUT = 3.5
ORDER_EPOCHS = 4                              # batch orders are drawn per epoch; the fourth is used up to E3.5
FINAL, PREVIOUS = fp.FINAL, fp.PREVIOUS       # E3 and E2
MATCH_PATH = (2, 2.25, 2.5, 2.75, 3, 3.25, 3.5)

# The statistics, in their fixed sequence. first and second are (width, rate tag). matched: first at E3, second read along MATCH_PATH at
# first's value of key. fixed: both at E3. expected: the side of 0 that confirms.
STATISTICS = dict(
    P1=dict(kind='matched', key='train', first=(512, TAG_LOW), second=(768, TAG_LOW), expected='ABOVE'),
    S1=dict(kind='matched', key='gap', first=(512, TAG_LOW), second=(768, TAG_LOW), expected='ABOVE'),
    S3=dict(kind='fixed', key=None, first=(512, TAG_LOW), second=(768, TAG_LOW), expected='BELOW'),
    S4=dict(kind='matched', key='train', first=(512, TAG_HIGH), second=(768, TAG_HIGH), expected='ABOVE'),
    S5=dict(kind='fixed', key=None, first=(512, TAG_HIGH), second=(768, TAG_HIGH), expected='ABOVE'),
    S2=dict(kind='matched', key='validation', first=(512, TAG_LOW), second=(768, TAG_LOW), expected='ABOVE'))
SEQUENCE = ('P1', 'S1', 'S3', 'S4', 'S5', 'S2')
PRIMARY = 'P1'
UNREADABLE = ('UNAVAILABLE', 'SATURATED', 'SATURATION_SENSITIVE')      # in this order of precedence

# Labels.
PRIMARY_LABELS = dict(ABOVE='REVERSAL_CONFIRMED', BELOW='NOT_REVERSED', SPANS='INCONCLUSIVE')
SECONDARY_LABELS = ('CONFIRMED', 'CONTRARY', 'INCONCLUSIVE')
NOT_READ = 'NOT_READ'                         # a step the fixed sequence does not reach, whatever its interval; the side stays in its status

# NOT_OVERFIT gates, per arm (width, rate tag). Not gating a label: a failing arm prefixes a reading.
GATE_ARMS = dict(rate_low=((512, TAG_LOW), (768, TAG_LOW)), rate_high=((512, TAG_HIGH), (768, TAG_HIGH)))

# Power stated in advance (reports/natural-text-matched-preparation-20261104-01/MATCHED_PLANNING.json): the probability that P1 reads REVERSAL_CONFIRMED.
POWER = dict(sd='0.0025', six_seen='>0.999', six_half='0.999', six_half_sd_upper='0.703', five_seen='>0.999', five_half='0.990', five_half_sd_upper='0.576')
