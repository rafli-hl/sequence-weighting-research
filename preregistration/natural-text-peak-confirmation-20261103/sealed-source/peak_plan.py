"""Frozen plan of the peak confirmation (owner decisions 20261103-03 and -04). Pure constants.

Six fresh WikiText-103 draws c01-c06 in two runs, C1 (c01-c03) and C2 (c04-c06), with the few-epoch recipe. Per draw and at E3:
- primary, at 3e-4: INTERIOR_PEAK if the lower limits of the df 5 intervals of D1 = p*(512) - p*(384) and D2 = p*(512) - p*(768)
  are both above 0;
- control, read only if the primary passes: D4 = p*(512) - p*(768), both at 1e-4;
- pre-registered secondary: D3 = p*(512 at 3e-4) - p*(768 at 1e-4), with the gap caveat stated in advance.
No new rate is chosen: 3e-4 is the few-epoch study's selected rate and 1e-4 is 768's lowest validation NLL on t00, both by
validation NLL only. The shared recipe, readouts and limits come from fewepoch_plan.py, a byte copy.
Importing this module cannot read data, import a framework or launch anything.
"""
import fewepoch_plan as fp
import peak_data as pd

EXECUTION_ENABLED = False

# Paths (relative to the project root).
SOURCE = 'work/natural-text-peak-source-20261103-01'
CORPUS = fp.CORPUS
ACTIVATIONS = dict(C1='work/natural-text-peak-activation-c1-20261103-01', C2='work/natural-text-peak-activation-c2-20261103-01')
RUNS = dict(C1='work/runs/natural-text-peak-c1-20261103-01', C2='work/runs/natural-text-peak-c2-20261103-01')

# The owner-run seed draw of 3 Nov 2026 (OWNER-20261103-PEAK-SEEDS-01) and its partition.
REGISTRY_SOURCE_SUBJECT = 'a58795a462a53289eeb1afbbde612558ae63063aa9c2a3968ff3d4e2dccf0b34'
REGISTRY = dict(directory='reports/natural-text-peak-seed-registry-20261103-01',
                policy_sha256='c102baf77b2a49802697b56dca5a300ad8d4d357401ca24c1897188f07bd79ac',
                registry_sha256='0e8b05285a6ad98a32a2041f0907e423c9c8d85fa6408e6a90be9acfb8c326dd',
                exclusions_sha256='7571f8144bb2eea7a6549848e423a38a615dacb37102d8b9753c6163db4c6ba1',
                draw_sha256='90a0c0aa45b448df88019fd0de34dcc1933d6fe165e2dc90c2d3e0a8200729ba', approval_id='OWNER-20261103-PEAK-SEEDS-01')
PARTITION_SHA256 = '3ba24bff0c38612d7d1751505edf8c5e02e9a98e46ff24165195c1199571ab85'

# Groups and runs.
GROUPS = pd.GROUPS
RUN_STAGES = dict(C1=GROUPS[:3], C2=GROUPS[3:])
N_TRAIN = pd.N_TRAIN

# The rates: where they come from, and the arms. A width's arms share its E0, tokens, weights and batch order.
RATE_HIGH, RATE_LOW = 3e-4, 1e-4
RATE_SOURCE = dict(file='work/runs/natural-text-fewepoch-a-20261101-01/LR_SELECTION.json', sha256='fa760ba0d693518ba1b98a40f366899ebec3a013ff03863284a3ac2c32b5ad01')
WIDTHS = (384, 512, 768)
BENCH_WIDTHS = WIDTHS                         # the start-up benchmark, 768 last
ARMS = {768: (RATE_HIGH, RATE_LOW), 512: (RATE_HIGH, RATE_LOW), 384: (RATE_HIGH,)}      # per draw: widest first, each width's state hashed and deleted after its arms
TAG_HIGH, TAG_LOW = fp.rate_tag(RATE_HIGH), fp.rate_tag(RATE_LOW)

# The contrasts: statistic = p*(first) - p*(second), each (width, rate tag).
CONTRASTS = dict(D1=((512, TAG_HIGH), (384, TAG_HIGH)), D2=((512, TAG_HIGH), (768, TAG_HIGH)), D4=((512, TAG_LOW), (768, TAG_LOW)), D3=((512, TAG_HIGH), (768, TAG_LOW)))
PRIMARY_CONTRASTS = ('D1', 'D2')
CONTROL_CONTRAST = 'D4'
SECONDARY_CONTRAST = 'D3'
UNREADABLE = ('UNAVAILABLE', 'UNDEFINED', 'SATURATED', 'SATURATION_SENSITIVE')    # in this order of precedence

# Labels.
PRIMARY_LABELS = ('INTERIOR_PEAK', 'NOT_CONFIRMED')
CONTROL_LABELS = ('PEAK_AT_BOTH_RATES', 'RATE_DEPENDENT', 'FALL_NOT_DETECTED_AT_1E-4', 'NOT_READ')

# NOT_OVERFIT gates, per arm (width, rate tag).
GATE_ARMS = dict(primary=((384, TAG_HIGH), (512, TAG_HIGH), (768, TAG_HIGH)), control=((512, TAG_LOW), (768, TAG_LOW)))

# t00 figures quoted in the gap caveat, stated in advance (Run A's records; checked by the tests).
T00_GAP = dict(w512_high=0.5676, w768_low=0.5382, w512_low=0.4422, w768_high=0.5751)

# Power stated in advance (reports/natural-text-peak-confirmation-draft-20261103-01/CONFIRMATION_PLANNING.json, six draws): the probability
# of INTERIOR_PEAK at the effects seen in d01-d10 and at half of them, each also with the sd at its upper 95% limit.
POWER = dict(seen='>0.999', half='0.941', seen_sd_upper='0.989', half_sd_upper='0.588')
