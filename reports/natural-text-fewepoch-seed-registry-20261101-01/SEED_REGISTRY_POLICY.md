# Seed registry policy: few-epoch, data-rich width ladder

**Frozen:** 1 Nov 2026, before the corpus exists and before any seed of this study is drawn. The registry tool (`fewepoch_registry.py` in `work/natural-text-fewepoch-source-20261101-01`) pins this file's SHA-256 and refuses a draw if it differs.

**Roles (46 values):**
- `partition_seed`;
- for each of the eleven groups t00 (tuning) and d01–d10 (analysis): `init_seed`, `weight_seed`, `pretrain_order_seed`, `adapt_order_seed`;
- `benchmark_seed` (the start-up benchmark of every run).

**Mechanics (the late-turn registry's, unchanged):**
- one exclusive claim, then a single draw of 1,024 bytes of operating-system entropy, read as 256 little-endian uint32 candidates;
- deterministic ordered acceptance: a candidate is accepted if it is more than 2,048 away from every excluded value and from every value already accepted, until 46 are accepted; fewer than 46 stops the registry, with no redraw;
- the exclusions are every earlier registry's values and exclusion list (the v0128 lists, the capacity ladder, the capacity-shift follow-up, the natural-text ladder, the late-turn confirmation) and a census of every saved JSON record of the project;
- the registry re-derives exactly from its own draw and exclusion bytes (`validate`), at the builder and at every worker admission.

**Bindings:**
- the draw requires the WikiText-103 corpus manifest, which must equal the pin set in `fewepoch_plan.py` after the acquisition (A3) and validate under the sealed corpus rules;
- it requires an owner approval id (OWNER-YYYYMMDD-..., never FIXTURE);
- the claim and the registry record the approval id and the hash of every registry-source file.

**Partition rule** (`fewepoch_data.partition`, sealed with this policy):
- the eligible training articles (not excluded by the corpus manifest) are sorted, then shuffled with `random.Random(partition_seed)`;
- they are assigned whole, in that order, to t00, d01, ..., d10, each group until it holds at least 32,768 sequences;
- each group uses its first N sequences in assignment order: N = 16,384, or 32,768 only after the pre-registered Run A fallback at 2N.

The rule depends only on per-article sequence counts and the partition seed, so it is outcome-blind.
