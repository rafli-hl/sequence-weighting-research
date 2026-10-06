"""Stage 11 v0.12 prospective configuration; no outcome-dependent choices."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPS = [(64, 2), (128, 3), (256, 4)]
PARAMETERS = {64: 113408, 128: 621696, 256: 3212800}
CONDITIONS = ['G16', 'G1']
ARMS = ['random', 'uniform']
EPOCHS = [1, 3, 5, 10, 20, 30]
GRID = [dict(lr=lr, wd=.1, clip=1.) for lr in [1e-5, 3e-5, 1e-4]]
F_INDEX = 2
TUNE = [(88111, 140101, 98101), (88321, 140201, 98102)]
CONFIRM = [(d, s, p) for d, p in [(88547, 98201), (88771, 98202),
    (88993, 98203), (89203, 98204), (89431, 98205)] for s in [150101, 150201]]
TRAIN_SECONDS = 5400
PREP_SECONDS = 300
AUDIT_SECONDS = 1800
REPORT_SECONDS = 1800
NEW_STORAGE_BYTES = 4 * 2**30
FREE_START_BYTES = 6 * 2**30
FREE_RESERVE_BYTES = 2 * 2**30
MAX_EPOCHS = 30
BATCH = 32
