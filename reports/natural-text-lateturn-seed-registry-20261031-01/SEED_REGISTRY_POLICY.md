# Late-turn confirmation seed-registry policy (frozen before any draw)

**Frozen 31 October 2026**, before any seed of the confirmation exists (owner decisions 20261031-02). No draw has happened.

**The draw** is a single owner-approved native step, run with Windows Python 3.12:

`lateturn_registry.py draw <this directory> <CORPUS_MANIFEST.json> --approval-id <owner id>`

The tool is in `work/natural-text-lateturn-registry-source-20261031-01/`.

**It refuses, before writing anything, if:**
- this file is missing, or its SHA-256 differs from the one pinned in the tool;
- the corpus manifest is not the frozen one (SHA-256 72daa1e174caa346494fb9a6cd0ded4ed192038a8918e4569a2a4ddb67a0834f), or does not validate against the sealed corpus code;
- the approval id does not start with `OWNER-`, or starts with `FIXTURE`;
- a claim or a draw already exists.

**The procedure** is the natural-text ladder registry's (`reports/natural-text-ladder-seed-registry-20261028-01/SEED_REGISTRY_POLICY.md`), with the confirmation's roles and one more exclusion source.

## Roles (18 values)

1. **`partition_seed`**: the partition of the unused WikiText-2 training articles into the fresh groups f01–f04 (rule below).
2. **For each group f01, f02, f03, f04**, in this order, with the same use as in the natural-text ladder:
   - `init_seed`: Torch model initialization, shared by all widths of the group;
   - `weight_seed`: log-uniform 0.01–10 weights via `random.Random(1000 + seed)`;
   - `pretrain_order_seed`: the 4 uniform pre-training epoch orders, `999 + seed + epoch`;
   - `adapt_order_seed`: the 32 weighted adaptation epoch orders, `999 + seed + epoch`.
3. **`benchmark_seed`**: the outcome-blind timing and memory benchmark only, never science.

## Exclusions (every value already used)

The exclusion set E is the union of:
- **everything the natural-text ladder registry excluded,** from the same sources:
  - the previous exposed list `reports/v0128-fresh-seed-registry-20261021-01/EXPOSED_SEED_ROLES.json`;
  - the frozen confirmation registry `ADMITTED_SEEDS.json` (base and namespace values) and its fixed schedules;
  - the capacity-ladder and capacity-shift follow-up registries, with their exclusion lists;
- **the natural-text ladder registry** (`reports/natural-text-ladder-seed-registry-20261028-01`): its exclusion list and all 46 of its role values;
- **a fresh conservative census at draw time:** every non-negative integer below 2^32 found under a JSON key containing `seed`, `stream`, `schedule` or `corpus`, in any saved project JSON file. Virtual environments, wheels, `.git` and `.idea` are excluded. This covers every earlier run, including revision 05's Run B and the one-rate run.

Census coverage, the hashes of the earlier lists and any unreadable files are recorded in `EXCLUSIONS.json`. Distinct values do not prove statistical independence.

## Draw and acceptance

1. **Claim.** Check the approval id, this policy's pin and the corpus manifest. Then create `DRAW_CLAIM.json` exclusively, recording:
   - the policy SHA-256;
   - the manifest SHA-256;
   - the approval id;
   - the SHA-256 of every file of the registry source.

   Compute E and save `EXCLUSIONS.json`.
2. **Entropy.** Make one OS entropy request (`os.urandom(1024)`) and save it as hex in `DRAW.json` before it is interpreted. Decode it into 256 little-endian uint32 candidates.
3. **Acceptance.**
   - A candidate is accepted, in order, iff it is more than 2,048 away from every value in E and from every earlier acceptance.
   - The streams derive `1000 + seed` and `999 + seed + epoch` (at most +1,031), so derived streams stay disjoint.
   - The first 18 acceptances fill the role order above.
4. **Too few acceptances.** If fewer than 18 are accepted, write `REGISTRY_STOPPED.json` and stop. There is no redraw and no replacement.

**The registry** is a pure function of `DRAW.json` and `EXCLUSIONS.json`. It records the corpus manifest SHA-256, the policy SHA-256 and the approval id. The study's builder and worker re-derive it and refuse any difference.

## The fresh partition (frozen now; applied by the study source)

**Implementation:** `lateturn_data.fresh_partition`, sealed with the registry tool before any seed exists. The study source uses a byte copy of it.

**The rule:**
1. **Used articles.** Re-derive the seen partition (t00 and d01–d10) with the sealed `text_data.partition`, from the natural-text ladder registry's `partition_seed` and the frozen corpus manifest. It must equal the seen partition (`PARTITION.json` 5f9f2646…). Every article in it is used.
2. **Unused articles.** The other training articles (157 articles, 6,263 sequences) are sorted by index and shuffled with `random.Random(partition_seed)`, using this registry's `partition_seed`.
3. **Assignment.** In that order, assign whole articles to f01, then f02, f03 and f04, until each holds at least N sequences. Each group uses its first N sequences in assignment order. Articles left after f04 are unused.
4. **N** is 1,536. If four groups cannot be filled, N is the largest multiple of 16 (at least 512) that fills them: the step-down rule of the seen partition (owner decisions 20261031-02, item 1).

The partition depends only on per-article sequence counts and the two partition seeds, so it is outcome-blind.

**Planning figure:** four groups fill at N = 1,536 in 73.1% of random article orders, and at N = 1,504 in 98.9% (`reports/natural-text-onerate-confirmation-draft-20261031-01/CONFIRMATION_PLANNING.json`).
