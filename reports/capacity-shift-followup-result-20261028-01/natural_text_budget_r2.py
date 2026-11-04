"""Planning arithmetic for the natural-text capacity ladder, proposal revision 2 (owner decisions of 28 Oct 2026).

  python -I -B natural_text_budget_r2.py      -> NATURAL_TEXT_BUDGET_r2.json

Reads saved files only and runs nothing. Revision 1 (batch 32) is kept as natural_text_budget.py ->
NATURAL_TEXT_BUDGET.json. Changes: batch 16 at every width (the 2 GiB sampled-device guard unchanged); a fixed uniform
pre-training before weighted adaptation (E0 = a sequence-weight-invariant baseline); nine readouts; a tuning draw.
Anchors (measured): the follow-up benchmark (seconds per update, effective FLOP rate, device memory in use with the
smallest model) and the sizes of the local WikiText-2 splits. FLOP and activation-memory formulas as in revision 1.
"""
import json, math, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
bench = json.loads((ROOT / 'work/runs/capacity-shift-followup-20261027-01/BENCHMARK.json').read_bytes())['benchmark']
P = lambda w, l: l * (12 * w * w + 13 * w) + (2 * 84 + 40 + 2) * w
rate = 6 * P(384, 4) * 32 * 40 / bench['architectures']['384/4']['seconds_per_update'] / 1e12
floor = min(v['seconds_per_update'] for v in bench['architectures'].values())
baseline = min(v['peaks']['device_used_sampled'] for v in bench['architectures'].values())   # whole-device use with the 32/4 model loaded
GUARD = 2 * 2 ** 30
def words(split):
    rows = json.loads((ROOT / f'work/text-assets/{split}-rows.json').read_bytes()); rows = rows if isinstance(rows, list) else rows['rows']
    return sum(len((r['text'] if isinstance(r, dict) else r).split()) for r in rows)
W = {s: words(s) for s in ('train', 'validation', 'test')}
tok = {s: (1.15 * n, 1.35 * n) for s, n in W.items()}                    # assumed BPE tokens per word (4,096 vocabulary)

L, H, T, B, V = 4, 4, 128, 16, 4096
WIDTHS = (64, 96, 128, 192, 256, 384); OPTIONAL = (512,)
N_TRAIN, N_VAL, N_PRE = 1536, 512, 2048
PRE_EPOCHS, EPOCHS = 4, 32
READOUTS = (1, 2, 4, 6, 8, 12, 16, 24, 32); PRIMARY = (4, 6, 8, 12, 16, 24, 32)
DRAWS, TUNING_DRAWS, LR_GRID = 10, 1, 3
def params(w): return L * (12 * w * w + 13 * w) + 2 * V * w + T * w
def flops_per_token(w): return 6 * L * 12 * w * w + 6 * V * w + 12 * L * T * w
def memory_bytes(w, batch=B):
    return 16 * params(w) + L * 2 * (34 * T * batch * w + 5 * H * T * T * batch) * 2 + 3 * batch * T * V * 4
pre_updates = PRE_EPOCHS * N_PRE // B; adapt_updates = EPOCHS * N_TRAIN // B
evals = (1 + len(READOUTS)) * (N_TRAIN + N_VAL) * T                     # E0 plus nine readouts, forward only
def seconds(w, r, adaptations=1):
    f = flops_per_token(w)
    pre = (pre_updates * B * T * f) / (r * 1e12) + pre_updates * floor
    ada = (adapt_updates * B * T * f + evals * f / 3) / (r * 1e12) + adapt_updates * floor
    return pre + adaptations * ada
scen = dict(optimistic_2x=2 * rate, planning=rate, pessimistic_half=rate / 2)
per_width = {}
for w in WIDTHS + OPTIONAL:
    m = memory_bytes(w)
    per_width[w] = dict(params=params(w), memory_estimate_GB=m / 1e9, with_measured_baseline_GB=(m + baseline) / 1e9,
                        guard_margin_GB=(GUARD - m - baseline) / 1e9, within_guard=m + baseline < GUARD,
                        minutes_per_draw={k: seconds(w, r) / 60 for k, r in scen.items()})
def hours(ws):
    return {k: (DRAWS * sum(seconds(w, r) for w in ws) + TUNING_DRAWS * sum(seconds(w, r, LR_GRID) for w in ws)) / 3600 for k, r in scen.items()}
storage = DRAWS * sum(4 * params(w) for w in WIDTHS) + (DRAWS + TUNING_DRAWS * LR_GRID) * len(WIDTHS) * ((1 + len(READOUTS)) * (N_TRAIN + N_VAL) * 4 + 2 ** 16)
need = (DRAWS + TUNING_DRAWS) * N_TRAIN * T
value = dict(status='PLANNING_ARITHMETIC_NOT_A_MEASUREMENT', revision=2,
             anchors=dict(planning_TFLOPs=rate, per_update_floor_seconds=floor, device_in_use_with_smallest_model_GB=baseline / 1e9, guard_GB=GUARD / 1e9,
                          note='Measured at batch 32 x 40 tokens, FP32 (TF32 off). Batch 16 x 128 = 2,048 tokens per update; the per-update floor is assumed unchanged.'),
             data=dict(words=W, tokens_estimate=tok,
                       train_tokens_needed=need, train_groups_possible=[math.floor(t / (N_TRAIN * T)) for t in tok['train']], groups_needed=DRAWS + TUNING_DRAWS,
                       pretraining_pool='test split', pretraining_tokens_needed=N_PRE * T, pretraining_fits=tok['test'][0] >= N_PRE * T,
                       validation_pool='validation split', validation_tokens_needed=N_VAL * T, validation_fits=tok['validation'][0] >= N_VAL * T),
             design=dict(layers=L, heads=H, seq_len=T, batch=B, vocab=V, widths=WIDTHS, optional_widths=OPTIONAL, n_train=N_TRAIN, n_validation=N_VAL,
                         n_pretraining=N_PRE, pretraining_epochs=PRE_EPOCHS, pretraining_updates=pre_updates, epochs=EPOCHS, adaptation_updates=adapt_updates,
                         readouts=READOUTS, primary_epochs=PRIMARY, draws=DRAWS, tuning_draws=TUNING_DRAWS, lr_grid=LR_GRID),
             per_width=per_width,
             totals_hours=dict(six_widths_64_384=hours(WIDTHS), seven_widths_with_512=hours(WIDTHS + OPTIONAL),
                               run_A_tuning_only_six_widths={k: TUNING_DRAWS * sum(seconds(w, r, LR_GRID) for w in WIDTHS) / 3600 for k, r in scen.items()},
                               run_B_analysis_only_six_widths={k: DRAWS * sum(seconds(w, r) for w in WIDTHS) / 3600 for k, r in scen.items()}),
             storage_GiB=storage / 2 ** 30, storage_note='E0 states for every draw and width, plus per-sequence loss arrays and record bounds; no other states.')
(HERE / 'NATURAL_TEXT_BUDGET_r2.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(rate=round(rate, 3), floor=floor, baseline_GB=round(baseline / 1e9, 3), groups=value['data']['train_groups_possible'],
                      pre_fits=value['data']['pretraining_fits'], val_fits=value['data']['validation_fits'],
                      mem={w: (round(v['with_measured_baseline_GB'], 2), round(v['guard_margin_GB'], 2), v['within_guard']) for w, v in per_width.items()},
                      minutes={w: round(v['minutes_per_draw']['planning'], 1) for w, v in per_width.items()},
                      totals={k: {x: round(y, 2) for x, y in v.items()} for k, v in value['totals_hours'].items()}, storage_GiB=round(value['storage_GiB'], 2)), indent=1))
