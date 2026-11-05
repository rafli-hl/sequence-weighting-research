# Seed registry policy: matched-progress confirmation (N7) on fresh WikiText-103 draws

**Frozen:** 4 Nov 2026, before any seed of this study is drawn. The registry tool (`matched_registry.py` in `work/natural-text-matched-source-20261104-01`) pins this file's SHA-256 and refuses a draw if it differs.

**Roles (26 values):**
- `partition_seed`;
- for each of the six fresh groups m01–m06: `init_seed`, `weight_seed`, `pretrain_order_seed`, `adapt_order_seed`;
- `benchmark_seed` (the start-up benchmark of every run).

No tuning group: no new rate is chosen.

**Mechanics (the peak registry's, unchanged except as stated):**
- one exclusive claim, then a single draw of 1,024 bytes of operating-system entropy, read as 256 little-endian uint32 candidates;
- deterministic ordered acceptance: a candidate is accepted if it is more than 2,048 away from every excluded value and from every value already accepted, until 26 are accepted; fewer than 26 stops the registry, with no redraw;
- the registry re-derives exactly from its own draw and exclusion bytes (`validate`).

**Which seeds are excluded:** every earlier registry's values and exclusion list (the v0128 lists, the capacity ladder, S, the natural-text ladder used by N1 and N3 and by their first attempts, N4, N5 and N6), and a census of saved JSON records.

**Changed from the peak registry, by the owner's rule of 4 Nov 2026:** the census never enters a folder whose path holds `work/runs`: the project's own, or a copy of that path at any depth. The earlier registries' saved exclusion lists already hold what earlier censuses found there, and the first attempts of N1 and N3 used the seeds of their registries.

**Bindings:**
- the draw requires the WikiText-103 corpus manifest, which must equal the few-epoch study's pin and validate under the sealed corpus rules;
- it requires the few-epoch and peak registries and partitions, which must equal their pins;
- it requires an owner approval id (OWNER-YYYYMMDD-..., never FIXTURE);
- the claim and the registry record the approval id and the hash of every registry-source file.

**Which articles are fresh** (`matched_data.fresh_pool`, sealed with this policy). Start from the eligible training articles, those the corpus manifest does not exclude:
1. **Assigned articles are out:** every article the few-epoch partition assigned to t00 or d01–d10, and every article the peak partition assigned to c01–c06, including the ones behind unused sequences. They are re-derived with the sealed `fewepoch_data.partition` and `peak_data.partition`.
2. **Text duplicates of assigned articles are out:** every remaining article whose full text (`text_sha256` in the manifest) equals that of an assigned article.
3. **Repeats inside the pool are out:** every copy of any text that occurs more than once among what remains, so no two fresh groups can share a full text.

N1, N3, N4 and the first attempts of N1 and N3 drew WikiText-2 articles, and the corpus manifest excludes every article equal by title or text to a WikiText-2 article. S is synthetic. So none of them can contribute an article.

**Partition rule** (`matched_data.partition`, sealed with this policy):
- the fresh articles are sorted by index, then shuffled with `random.Random(partition_seed)`;
- they are assigned whole, in that order, to m01, ..., m06, each group until it holds at least 16,384 sequences;
- each group uses its first 16,384 sequences in assignment order.

The rule depends only on per-article sequence counts, text hashes and the three partition seeds, so it is outcome-blind.

**Written by the draw:** `DRAW_CLAIM.json`, `EXCLUSIONS.json`, `DRAW.json`, `PARTITION.json` and `REGISTRY.json`, which records the partition's hash. The partition is written here so that it can be checked without opening `work/runs/`.

**What this does not remove:** exact token sequences and 64-token runs that recur outside identical full texts, and articles that share a title with an assigned article but not its text. The validation set, the pre-training pool and the tokenizer stay those of the earlier natural-text studies.
