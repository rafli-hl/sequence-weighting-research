# Conditional external-text check

Execute only if the synthetic confirmation gate in PROTOCOL_STAGE1.md passes.
This protocol is written before text results are observed.

- Model: EleutherAI/pythia-70m, final pretrained checkpoint; resolve and record
  an immutable repository commit and weight-file SHA256. Full fine-tuning,
  float32, no LoRA or quantization, local RTX 3050 only.
- Data: Salesforce/wikitext, wikitext-2-raw-v1. Deterministically take the first
  512 train, 128 validation, and 128 test paragraphs containing at least 129
  tokenizer tokens; retain only the first 129 tokens. Save source row indices,
  token arrays, content hashes and dataset revision. Exclude exact duplicate
  selected token sequences across splits. This is a selected paragraph subset,
  not standard WikiText benchmark perplexity. Pretraining overlap is unknown.
- Objective: mean full next-token NLL across 128 targets per sequence, followed
  by a fixed scalar sequence weight. Same log-uniform weights [0.01,10],
  corpus mean normalization, and p* estimator as the synthetic study.
- Pair random and uniform weights, seed 42, identical pretrained checkpoint
  and example order; three epochs, AdamW lr 0.00003, weight decay 0.1,
  gradient clipping 1, effective batch 32 (microbatch 4, accumulation 8).
  Accumulate losses divided by the number of microbatches before clipping once
  per optimizer step. All model parameters are trained.
- Evaluate train and validation before adaptation and after each epoch.
  Test is computed once at fixed epoch 3. No tuning from text test results.
  Gains are relative to the pretrained checkpoint on the same training rows.
- Save per-sequence losses, weights, p*, signed/negative gains, clip frequency,
  checkpoint, timings and allocated/reserved GPU memory. Refuse CPU fallback.
- A single model and seed validate execution of the measurement on text; they
  cannot validate a capacity curve, prove the mechanism, or establish an effect
  on downstream benchmark performance. The learning rate is fixed in advance,
  not claimed to optimize validation performance.

Sources:
- https://huggingface.co/EleutherAI/pythia-70m
- https://huggingface.co/datasets/Salesforce/wikitext
- https://huggingface.co/docs/dataset-viewer/en/rows
