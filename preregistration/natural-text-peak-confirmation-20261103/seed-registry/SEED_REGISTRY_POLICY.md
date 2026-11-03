# Seed registry policy: peak confirmation on fresh WikiText-103 draws

**Frozen:** 3 Nov 2026, before any seed of this study is drawn. The registry tool (`peak_registry.py` in `work/natural-text-peak-registry-source-20261103-01`) pins this file's SHA-256 and refuses a draw if it differs. Owner decision: `reports/natural-text-ladder-owner-decisions-20261103-03/OWNER_DECISIONS.md`.

**Roles (26 values):**
- `partition_seed`;
- for each of the six fresh groups c01–c06: `init_seed`, `weight_seed`, `pretrain_order_seed`, `adapt_order_seed`;
- `benchmark_seed` (the start-up benchmark of every run).

No tuning group: no new rate is chosen.

**Mechanics (the few-epoch registry's, unchanged):**
- one exclusive claim, then a single draw of 1,024 bytes of operating-system entropy, read as 256 little-endian uint32 candidates;
- deterministic ordered acceptance: a candidate is accepted if it is more than 2,048 away from every excluded value and from every value already accepted, until 26 are accepted; fewer than 26 stops the registry, with no redraw;
- the exclusions are every earlier registry's values and exclusion list (the v0128 lists, the capacity ladder, the capacity-shift follow-up, the natural-text ladder, the late-turn confirmation, the few-epoch study) and a census of every saved JSON record of the project;
- the registry re-derives exactly from its own draw and exclusion bytes (`validate`).

**Bindings:**
- the draw requires the WikiText-103 corpus manifest, which must equal the few-epoch study's pin and validate under the sealed corpus rules;
- it requires the few-epoch registry and partition, which must equal the few-epoch study's pins;
- it requires an owner approval id (OWNER-YYYYMMDD-..., never FIXTURE);
- the claim and the registry record the approval id and the hash of every registry-source file.

**Which articles are fresh** (`peak_data.fresh_pool`, sealed with this policy). Start from the eligible training articles, those the corpus manifest does not exclude:
1. **Assigned articles are out:** every article the few-epoch partition assigned to t00 or d01–d10, including the ones behind their unused second halves. They are re-derived with the sealed `fewepoch_data.partition`.
2. **Text duplicates of assigned articles are out:** every remaining article whose full text (`text_sha256` in the manifest) equals that of an assigned article.
3. **Repeats inside the pool are out:** every copy of any text that occurs more than once among what remains, so no two fresh groups can share a full text.

**Partition rule** (`peak_data.partition`, sealed with this policy):
- the fresh articles are sorted by index, then shuffled with `random.Random(partition_seed)`;
- they are assigned whole, in that order, to c01, ..., c06, each group until it holds at least 16,384 sequences;
- each group uses its first 16,384 sequences in assignment order.

The rule depends only on per-article sequence counts, text hashes and the two partition seeds, so it is outcome-blind.

**What this does not remove, and is measured and disclosed instead:** exact token sequences and 64-token runs that recur outside identical full texts. The validation set, the pre-training pool and the tokenizer stay those of the earlier natural-text studies.
