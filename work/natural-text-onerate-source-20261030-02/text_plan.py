"""Frozen natural-text capacity-ladder plan (owner-approved design of 28 Oct 2026). Pure constants.

Importing this module cannot read data, import a framework or launch anything.
"""
EXECUTION_ENABLED = False

# Corpus: WikiText-2 raw, already in the project (work/text-assets/, pinned 28 Sep 2026). The rows files are the exact
# text used; their SHA-256 values are pre-registered here and verified by prepare_corpus.py before anything is read.
TEXT_ASSETS = {'train': ('work/text-assets/train-rows.json', '339320f36b834daef5db836a568b5ffa4d379ee2ea2a970e5f7bd19ac977e72f'),
               'validation': ('work/text-assets/validation-rows.json', '6219396608ccab5a58a61c291f63a8613fbea966584202ef7e9e06d0619b9464'),
               'test': ('work/text-assets/test-rows.json', '224cadbb0cb2f889e8d8a6b9fbbb6990fcb0acef61d71cc5b60e8c1c51358b55')}
ARTICLE_HEAD = r'^ = [^=].* = \n$'          # a level-1 WikiText heading row ...
HEAD_NEEDS_BLANK_ROWS = True                  # ... with an empty row directly before and after it starts an article (owner decision,
                                              # 28 Oct 2026: table and formula rows can match the pattern); rows before the first head are dropped
ARTICLE_COUNTS = dict(train=600, validation=60, test=60)   # what that rule gives on the pinned rows (checked in every corpus manifest)

# Tokenizer (pre-registered; trained once, frozen before any draw is cut). Training text: the `text` field of every row of
# train-rows.json, in file order, unmodified (36,718 rows, empty rows included).
TOKENIZER = dict(library='tokenizers', library_version='0.21.4', model='BPE', vocab_size=4096, min_frequency=2,
                 special_tokens=('<|endoftext|>',), pre_tokenizer='ByteLevel(add_prefix_space=False, use_regex=True)',
                 decoder='ByteLevel', initial_alphabet='ByteLevel.alphabet()', training_text='train-rows.json text fields, file order, unmodified')
VOCAB = 4096
CONTEXT = 128                                 # input positions; each sequence has CONTEXT + 1 tokens and CONTEXT targets
SEQ_TOKENS = CONTEXT + 1                      # articles are encoded separately and chunked into non-overlapping windows; remainders dropped

# Draws: one tuning group and ten analysis groups of whole training-split articles (the inference unit is the draw).
TUNING = 't00'
DRAWS = tuple(f'd{i:02d}' for i in range(1, 11))
GROUPS = (TUNING,) + DRAWS
# Run B layout (owner decision, 28 Oct 2026): one run of all ten draws, or, if Run A's outcome-blind timing forecast
# puts ten draws over the 6-hour limit, two sequential runs B1 (d01-d05) and B2 (d06-d10) with identical science.
RUN_STAGES = dict(A=(TUNING,), B=DRAWS, B1=DRAWS[:5], B2=DRAWS[5:])
N_TRAIN = 1536                                 # sequences per group; pre-registered fallback in text_data.partition
N_STEP, N_FLOOR = 16, 512                      # fallback: largest multiple of 16 (>= 512) that fills all eleven groups
N_VALIDATION = 512                             # from the validation split, stride-selected, shared by all groups
POOL_MAX = 2048                                # uniform pre-training pool from the test split, stride-selected, shared

# Models: depth-4 decoder Transformers, 4 heads, untied output layer (text_model.py).
WIDTHS = (64, 96, 128, 192, 256, 384)
LAYERS = 4
HEADS = 4

# Recipe.
BATCH = 16
EVAL_BATCH = 32
PRETRAIN = dict(epochs=4, lr=3e-4, weight_decay=0.1, clip=5.0)             # uniform weights; fixed, never tuned
ADAPT = dict(epochs=32, weight_decay=0.1, clip=1.0)                         # weighted (R), constant learning rate
LR_GRID = (3e-5, 1e-4, 3e-4)                                                # chosen per width on t00 by validation NLL only
READOUTS = (1, 2, 4, 6, 8, 12, 16, 24, 32)
PRIMARY_EPOCHS = (4, 6, 8, 12, 16, 24, 32)                                  # equally spaced in log2 epoch (half doublings)
# Primary B two-lines test (owner decisions of 28 Oct 2026, revisions 03 and 04; in the style of Simonsohn 2018, without
# the Robin Hood adjustment): the break is located from the data. Per draw-epoch point it is the rung nearest that point's
# own quadratic vertex (ties to the smaller width), clamped in to the nearest rung that leaves at least this many widths
# on each line (so 96, 128, 192 or 256; never discarded), and it belongs to both lines.
TWO_LINES_MIN_WIDTHS = 2
# Revision 04 (owner decision of 28 Oct 2026): INTERIOR_PEAK also needs a per-point rise and fall: for each point the
# smaller of (left slope, -right slope); a rise at some epochs cannot pair with a fall at others.
CURVATURE_ZERO_TOL = 1e-12                    # |c| at or below this is zero curvature: no finite vertex (round-off on flat curves)
VERTEX_WIDTH_LOG2_RANGE = (0.0, 16.0)                                       # vertex reported as a width only inside this range
P_UPPER, P_LOWER = 7.999, 0.001

# Resource envelope per owner run (A: probe and learning-rate choice; B: analysis draws).
LIMITS = dict(overall_seconds=21600, benchmark_seconds=900, cap_multiplier=1.25, cap_fixed_seconds=120, stage_slack_seconds=60,
              storage_bytes=2 * 2 ** 30, stage_storage_bytes=2 ** 28, stage_files=128, total_files=1000,
              admission_free_bytes=4 * 2 ** 30, reserve_free_bytes=2 * 2 ** 30,
              gpu_sampled_bytes=2 * 2 ** 30, worker_peak_rss_bytes=4032 * 2 ** 20)
RECORD_BYTES = 2 ** 18


def parameters(width, layers=LAYERS, vocab=VOCAB, length=CONTEXT):
    """Exact parameter count of text_model.Model(width, layers, length, vocab)."""
    return layers * (12 * width * width + 13 * width) + (2 * vocab + length + 2) * width


def updates(n, epochs, batch=BATCH):
    return epochs * ((n + batch - 1) // batch)


def eval_batches(n, batch=EVAL_BATCH):
    return (n + batch - 1) // batch
