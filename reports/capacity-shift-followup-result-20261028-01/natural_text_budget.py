"""Planning arithmetic for a proposed natural-text capacity ladder (stdlib; reads saved files only; runs nothing).

  python -I -B natural_text_budget.py      -> NATURAL_TEXT_BUDGET.json

Anchors (measured, saved):
- the follow-up run's own outcome-blind benchmark (work/runs/capacity-shift-followup-20261027-01/BENCHMARK.json):
  seconds per update for depth-4 widths 32-384 at batch 32 x 40 tokens, giving an effective training FLOP rate;
- the size of the locally stored WikiText-2 raw training split (work/text-assets/train-rows.json).
Everything else is a stated assumption: training FLOPs per token = 6 x non-embedding params + 6 x V x width
(output layer) + 12 x layers x T x width (attention), evaluation = one third of that per token, and FP32 activation
memory from the standard per-layer estimate (34 s b h + 5 a s^2 b, in 2-byte units, doubled for FP32).
"""
import json, math, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
bench = json.loads((ROOT / 'work/runs/capacity-shift-followup-20261027-01/BENCHMARK.json').read_bytes())['benchmark']
P = lambda w, l: l * (12 * w * w + 13 * w) + (2 * 84 + 40 + 2) * w
measured = {k: dict(seconds_per_update=v['seconds_per_update'], effective_TFLOPs=6 * P(*map(int, k.split('/'))) * 32 * 40 / v['seconds_per_update'] / 1e12,
                    device_used_sampled_GB=v['peaks']['device_used_sampled'] / 1e9) for k, v in bench['architectures'].items()}
floor = min(v['seconds_per_update'] for v in measured.values())           # per-update overhead floor (small models)
rate = measured['384/4']['effective_TFLOPs']                                # largest measured rung
rows = json.loads((ROOT / 'work/text-assets/train-rows.json').read_bytes()); rows = rows if isinstance(rows, list) else rows['rows']
texts = [r['text'] if isinstance(r, dict) and 'text' in r else r.get('row', {}).get('text', '') if isinstance(r, dict) else r for r in rows]
words = sum(len(t.split()) for t in texts); chars = sum(len(t) for t in texts)
articles = sum(1 for t in texts if t.strip().startswith('= ') and not t.strip().startswith('= ='))

L, H, T, B, V = 4, 4, 128, 32, 4096            # depth, heads, sequence length, batch, BPE vocabulary (trained locally; assumption)
N_TRAIN, N_VAL, EPOCHS, READOUTS = 1536, 512, 32, (1, 2, 4, 8, 16, 32)
WIDTHS = (64, 96, 128, 192, 256, 384, 512, 768)
def params(w): return dict(non_embedding=L * (12 * w * w + 13 * w), embedding=V * w + T * w, output=V * w)
def train_flops_per_token(w): return 6 * L * 12 * w * w + 6 * V * w + 12 * L * T * w
def memory_GB(w, batch=B):
    p = sum(params(w).values()); state = 16 * p                                     # FP32 weights, grads, two Adam moments
    act = L * 2 * (34 * T * batch * w + 5 * H * T * T * batch) * 2                    # FP32: twice the 2-byte estimate
    logits = 3 * batch * T * V * 4                                                    # logits, softmax and grad
    return (state + act + logits) / 1e9
tokens_epoch = N_TRAIN * T; updates = EPOCHS * N_TRAIN // B
per_width = {}
for w in WIDTHS:
    f = train_flops_per_token(w); train = EPOCHS * tokens_epoch * f; evals = len(READOUTS) * (N_TRAIN + N_VAL) * T * f / 3
    sc = {name: (train + evals) / (r * 1e12) + updates * floor for name, r in (('optimistic_2x', 2 * rate), ('planning', rate), ('pessimistic_half', rate / 2))}
    per_width[w] = dict(params=params(w), train_flops_per_token=f, total_flops=train + evals, seconds=sc, memory_GB_batch32=memory_GB(w), memory_GB_batch16=memory_GB(w, 16))
def total(ws, draws, arms=1): return {k: draws * arms * sum(per_width[w]['seconds'][k] for w in ws) / 3600 for k in ('optimistic_2x', 'planning', 'pessimistic_half')}
tokens_low, tokens_high = 1.15 * words, 1.35 * words                                 # assumed BPE tokens per word for a 4,096 vocabulary
value = dict(status='PLANNING_ARITHMETIC_NOT_A_MEASUREMENT', anchors=dict(measured_benchmark=measured, per_update_floor_seconds=floor, planning_TFLOPs=rate,
             note='Measured at batch 32 x 40 tokens, FP32 (TF32 off); larger token batches are expected to be more efficient but that is unmeasured.'),
             wikitext2_train=dict(rows=len(texts), chars=chars, words=words, articles_approx=articles, tokens_estimate=[tokens_low, tokens_high],
                                  disjoint_draws_at_N=dict({str(n): [math.floor(tokens_low / (n * T)), math.floor(tokens_high / (n * T))] for n in (1024, 1536, 2048)})),
             design=dict(layers=L, heads=H, seq_len=T, batch=B, vocab=V, n_train=N_TRAIN, n_validation=N_VAL, epochs=EPOCHS, readouts=READOUTS, updates_per_trajectory=updates),
             per_width=per_width,
             totals_hours=dict(R_only_7_widths_64_512_10_draws=total(WIDTHS[:7], 10), R_and_U_7_widths_10_draws=total(WIDTHS[:7], 10, 2),
                               R_only_8_widths_64_768_10_draws=total(WIDTHS, 10), R_only_6_widths_64_384_10_draws=total(WIDTHS[:6], 10)),
             memory_note='The 2 GiB sampled-device guard counts whole-device use; the follow-up measured about 0.9 GB already in use with the smallest model loaded.',
             disk_note='Per-sequence loss arrays and records only (no model states beyond E0): well under 1 GiB.')
(HERE / 'NATURAL_TEXT_BUDGET.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(floor=floor, rate=rate, words=words, articles=articles, tokens=[round(tokens_low), round(tokens_high)], draws=value['wikitext2_train']['disjoint_draws_at_N'],
                      memory={w: [round(v['memory_GB_batch32'], 2), round(v['memory_GB_batch16'], 2)] for w, v in per_width.items()},
                      minutes_planning={w: round(v['seconds']['planning'] / 60, 1) for w, v in per_width.items()}, totals=value['totals_hours']), indent=1))
