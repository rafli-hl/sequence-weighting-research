# Natural-text ladder seed-registry policy (frozen before any draw)

Frozen 28 October 2026; revision 02 after review 1 (the revision-01 text is preserved in `reports/natural-text-ladder-preparation-20261028-01/review-01-subject-b14f56b3-superseded/SEED_REGISTRY_POLICY_r01.md`). No draw has happened. The draw is a single owner-approved native step, `text_registry.py draw <this directory> <CORPUS_MANIFEST.json>`, run from `work/natural-text-ladder-source-20261028-01`. It refuses if this file is missing, the corpus manifest does not exist, a claim already exists or a draw already exists. The procedure is the capacity-shift follow-up's (`reports/capacity-shift-followup-seed-registry-20261027-01/SEED_REGISTRY_POLICY.md`), with the natural-text roles.

## Roles (46 values)

1. **`partition_seed`**: the article partition of the WikiText-2 training split into t00 and d01–d10 (`text_data.partition`).
2. **For each group t00, d01, …, d10**, in this order:
   - `init_seed`: Torch model initialization, shared by all widths of the group;
   - `weight_seed`: log-uniform 0.01–10 weights via `random.Random(1000 + seed)`;
   - `pretrain_order_seed`: the 4 uniform pre-training epoch orders, `999 + seed + epoch`;
   - `adapt_order_seed`: the 32 weighted adaptation epoch orders, `999 + seed + epoch`.
3. **`benchmark_seed`**: the outcome-blind timing and memory benchmark only, never science.

## Exclusions (every value already used)

The exclusion set E is the union of:
- the previous exclusion list `reports/v0128-fresh-seed-registry-20261021-01/EXPOSED_SEED_ROLES.json` (3,388 values);
- the frozen confirmation registry `ADMITTED_SEEDS.json` (base and namespace values) and its fixed schedules 150101 and 150201;
- the exclusion lists and every role value of the capacity-ladder registry (`reports/capacity-ladder-seed-registry-20261026-01`) and the capacity-shift follow-up registry (`reports/capacity-shift-followup-seed-registry-20261027-01`);
- a fresh conservative census, at draw time, of every non-negative integer below 2^32 found under a JSON key containing `seed`, `stream`, `schedule` or `corpus`, in any saved project JSON file. Virtual environments, wheels, `.git` and `.idea` are excluded from the census. This covers every earlier run's stage inputs.

Census coverage, the hashes of the earlier lists and unreadable files are recorded in `EXCLUSIONS.json`. Distinct values do not prove statistical independence.

## Draw and acceptance

1. Require the frozen corpus manifest (written by `prepare_corpus.py` after the tokenizer is trained twice and frozen). Create `DRAW_CLAIM.json` exclusively, recording the manifest SHA-256. Compute E and save `EXCLUSIONS.json`.
2. Make one OS entropy request (`os.urandom(1024)`), save it as hex in `DRAW.json` before interpretation, and decode 256 little-endian uint32 candidates.
3. Accept a candidate in order iff it is more than 2,048 away from every value in E and from every earlier acceptance. The streams derive `1000 + seed` and `999 + seed + epoch` (at most +1,031), so derived streams stay disjoint. The first 46 acceptances fill the role order above.
4. If fewer than 46 are accepted, write `REGISTRY_STOPPED.json` and stop. There is no redraw and no replacement.

The registry is a pure function of `DRAW.json` and `EXCLUSIONS.json`, and records the corpus manifest SHA-256 (registry schema 2). The activation builders and the worker re-derive it, check that the manifest they use has that hash, and refuse any difference. The article partition is then a pure function of `partition_seed` and the frozen corpus manifest. Because the draw requires the manifest, the tokenizer is necessarily trained and frozen before any seed exists. The partition is bound into each activation and re-derived by the worker.
