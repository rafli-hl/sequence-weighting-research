# Proposal (not built): a natural-text capacity ladder

Status, 28 October 2026: **proposal only.** Nothing has been built, downloaded, tokenized or run. Every time and memory figure below is planning arithmetic from `natural_text_budget.py` → `NATURAL_TEXT_BUDGET.json`, anchored on measured costs from the follow-up run's own benchmark. None of them is a measurement of this design.

## 1. Question

Do Jane Street's finding (1) (p* rises then falls with model size) and finding (2) (more epochs move the peak to smaller models) appear when small Transformers are trained **from scratch on natural text** with log-uniform per-sequence weights?

All of the project's evidence so far is synthetic, including the pre-registered MOVES_SMALLER result (`REPORT.md` in this directory). This design would test whether the pattern survives the move to real text. It still would not test large-scale behaviour.

## 2. Design sketch (to be frozen in a versioned protocol before any outcome)

- **Corpus. Option A (recommended): WikiText-2 raw, already in the project.**
  - Location: `work/text-assets/`, Hugging Face revision b08601e0…, pinned and hash-verified on 28 Sep 2026, licence CC-BY-SA-3.0. No download is needed.
  - Size: 2,051,910 words in 36,718 rows (about 629 articles). That is an estimated 2.36–2.77 M tokens with a 4,096-token BPE (assumed 1.15–1.35 tokens per word).
  - The training rows are already extracted as JSON, so no parquet reader is needed.
- **Option B: a TinyStories subset**, as the owner suggested.
  - Simpler language suits tiny models, and there would be room for more and larger draws.
  - It needs an owner-approved, pinned download and a licence check first.
- **Option C: WikiText-103**, from the same pinned repository and under the same licence.
  - It is about a 315 MB download and gives roughly 40 times more text.
- **Tokenizer.** A 4,096-token BPE trained once on the training split with the locked `tokenizers` 0.21.4 in WSL, frozen before any outcome. The local Pythia tokenizer (50,304 tokens) would make the output layer dominate the small models: 6 × 50,304 × w FLOPs per token, against 288 w² in the non-embedding layers.
- **Sequences and draws (the replication unit).**
  - Sequences are 128 tokens, chunked within articles.
  - Each draw is a disjoint set of **whole articles** giving N = 1,536 training sequences (196,608 tokens).
  - An estimated 12–14 such draws fit in WikiText-2 train; **10** are proposed, leaving a margin.
  - All draws share 512 validation sequences from the validation split.
  - A separate tuning draw is used only for learning-rate selection.
- **Weights.** Log-uniform 0.01–10 per sequence, mean-normalized, drawn per draw from its own seed (as in `engine.weights`).
- **Models.**
  - Depth-4 decoder Transformers of the project's architecture family, in a new versioned `model.py` that takes the vocabulary size (the current file fixes `VOCAB = 84`), with 4 heads.
  - Widths 64, 96, 128, 192, 256 and 384 (six rungs), plus 512 if the memory decision in section 3 allows it.
  - Trained from scratch, with one initialization seed per draw shared by all widths.
- **Arms.**
  - **R** (weighted sequence loss) is primary.
  - A uniform-weight **U** run is an optional loss reference; p* is undefined for U.
  - S_batch and H do not carry over, because natural text has no shared, group or instance labels. The mechanism decomposition of the synthetic studies is therefore not available here.
- **Recipe.**
  - AdamW with a constant learning rate, weight decay 0.1, clip 1 and batch 32.
  - 32 epochs, with per-sequence training losses and validation at E1, E2, E4, E8, E16 and E32.
  - The learning rate is chosen once, by validation NLL on the tuning draw only and never by p*, with a documented tie rule.
  - Clip fractions are recorded. In the synthetic follow-up nearly every update was clipped, so the clip threshold should be part of the frozen recipe, not an afterthought.
- **Gains and estimator.**
  - Signed per-sequence training gains run from the initialization checkpoint to each readout.
  - The estimator is the unchanged `core.exponent`, bounded at 8, with the follow-up's S1/S32/SD saturation rule.
  - Initial losses are close to log V for every sequence, so these gains measure how much of each sequence was learned.
  - Alternative, to be decided before freezing: a brief uniform pre-training on held-out text, then weighted training, which mirrors the synthetic E0 design.
- **Primary (to be frozen).** Per draw, the OLS slope of the peak location on log2(epoch) over E4–E32, with a t interval (df = draws − 1), the same labels and suffixes as the follow-up, and the same undefined rules.
- **Secondaries.** Per-epoch peak-shape labels, train and validation NLL with the memorization gap, clipping, and fit quality J(p*) and J(0).

## 3. Feasibility on the RTX 3050 Laptop GPU (4,095.5 MiB)

**Anchors measured in the follow-up benchmark** (FP32, TF32 off, batch 32 × 40 tokens):
- about 1.19 TFLOP/s effective at 384/4;
- a per-update floor of 15.5 ms for the smallest models.

The design's 4,096-token batches are expected to run at least as efficiently, but that is unmeasured. The planning scenarios therefore use the measured rate, with ×2 and ×½ bounds.

| Width (depth 4) | Planning minutes per trajectory (32 epochs) | FP32 memory estimate, batch 32 | Batch 16 |
|---:|---:|---:|---:|
| 64 | 0.7 | 0.52 GB | 0.27 GB |
| 128 | 1.2 | 0.68 GB | 0.36 GB |
| 256 | 2.9 | 1.02 GB | 0.55 GB |
| 384 | 5.6 | 1.39 GB | 0.78 GB |
| 512 | 9.1 | 1.78 GB | 1.02 GB |
| 768 | 18.8 | 2.64 GB | 1.60 GB |

**Time for 10 draws, R only** (planning, with the 2×-faster and 2×-slower bounds):

| Rungs | Planning | Range |
|---|---:|---:|
| Six rungs, 64–384 | 2.2 h | 1.3–4.0 h |
| Seven rungs, 64–512 | 3.7 h | 2.1–7.0 h |
| Seven rungs with the U reference | 7.5 h | — |
| Eight rungs, 64–768 | 6.9 h | — |

The six-rung design fits one owner run of the existing ≤ 6 h envelope at the planning rate.

**Memory is the binding constraint.**
- The project's sampled-device guard is 2 GiB of whole-device use, and the follow-up measured about 0.9 GB already in use with the smallest model loaded.
- At batch 32, 384/4 would need about 2.3 GB in total and 512/4 about 2.7 GB. Both are within the 4 GiB card but above the guard.
- Options, an owner decision before freezing:
  - batch 16;
  - sequence length 64;
  - a higher, explicitly approved guard (for example 3.5 GiB);
  - stopping at 384/4.

768/4 is not recommended.

**Disk.** Per-sequence loss arrays and records only, well under 1 GiB; no model states beyond initialization. D: had 6.19 GiB free on 28 Oct.

**Software.** No new packages are needed for Option A: the WSL lock already has torch 2.7.0+cu126, tokenizers 0.21.4 and transformers 4.51.3.

## 4. Steps before any run (each needs owner approval)

1. Choose the corpus option, tokenizer, gain baseline (initialization or a brief uniform pre-training) and memory option.
2. Write and freeze the versioned protocol, the draw and seed registry, and the analysis. The analysis can reuse `shift_analysis` logic with a new plan.
3. Run an outcome-blind benchmark probe on the tuning draw: throughput and peak memory per width at T = 128. No p*.
4. Tune the learning rate on the tuning draw by validation NLL only.
5. Native fixtures, then an independent review, then one owner run with no retry.

## 5. What it could and could not show

- **It could show** whether the synthetic pattern survives on natural text: an interior p* peak across widths, and a peak that moves to smaller widths with more epochs. The test would use fresh draws and pre-registered rules.
- **It could not show:**
  - a mechanism, because there are no component labels;
  - large-model or scaling behaviour, because the widest rung has about 10 M (384/4) to 17 M (512/4) parameters;
  - independence beyond disjoint article sets drawn from one encyclopaedia corpus.
- **It shares the follow-up's other limits:**
  - progress confounding at fixed epochs;
  - one constant-learning-rate trajectory read at several epochs;
  - possible saturation near p = 8.
