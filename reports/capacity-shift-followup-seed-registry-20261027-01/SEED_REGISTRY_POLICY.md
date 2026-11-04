# Capacity-shift follow-up seed-registry policy (frozen before any draw)

Frozen 27 October 2026. No draw has happened. The draw is a single owner-approved native step, `ladder_registry.py draw <this directory>`, run from `work/capacity-shift-followup-source-20261027-01`. It refuses if this file is missing, a claim already exists or a draw already exists. The procedure is the capacity ladder's (`reports/capacity-ladder-seed-registry-20261026-01/SEED_REGISTRY_POLICY.md`), with twelve corpus slots, 256 candidates and the ladder registry added to the exclusions.

## Roles

For each of twelve corpus slots c01–c12: `adaptation_seed` (adaptation corpus via `engine.paired_data`; only G16 is trained), `pretraining_seed` (U pretraining corpus via `engine.pre_data`), `weight_seed` (log-uniform 0.01–10 weights via `engine.weights`), `order_seed` (40-epoch adaptation order and 4-epoch pretraining order via `engine.orders`), `init_seed` (Torch model initialization). One more role, `benchmark_seed`, is used only by the outcome-blind timing benchmark and never for science. That makes 61 values.

## Exclusions (every value already used)

The exclusion set E is the union of:

1. the previous exclusion list `reports/v0128-fresh-seed-registry-20261021-01/EXPOSED_SEED_ROLES.json` (3,388 values; SHA-256 6c8aa6277d54d1b11254b03741baddd3f40ba4ace903f14485fe084c6d742263);
2. every base and namespace value of the frozen confirmation registry (`reports/v0128-fresh-seed-registry-20261021-01/ADMITTED_SEEDS.json`, SHA-256 820d2443…) and its fixed schedules 150101/150201;
3. every value of the capacity-ladder exclusion list (`reports/capacity-ladder-seed-registry-20261026-01/EXCLUSIONS.json`) and every role value of the drawn capacity-ladder registry (`REGISTRY.json` in the same directory: 25 corpus roles and the benchmark seed);
4. a fresh conservative census, at draw time, of every non-negative integer below 2^32 appearing under a JSON key containing `seed`, `stream`, `schedule` or `corpus` in any saved project JSON file (excluding virtual environments, wheels, `.git` and `.idea`). This deliberately over-excludes and also covers the confirmation's and the ladder's run records.

Census coverage, the hashes of the files in items 1–3 and unreadable files are recorded in `EXCLUSIONS.json`. Values that are deleted, undocumented or only in binary records cannot be established. Distinct values do not prove statistical independence.

## Draw and acceptance

1. Create `DRAW_CLAIM.json` exclusively (it fails if the file exists, so a crashed or concurrent draw cannot be repeated), then compute E and save `EXCLUSIONS.json`.
2. Make one OS entropy request (`os.urandom(1024)`), saved as hex in `DRAW.json` before interpretation, and decode 256 little-endian uint32 candidates.
3. Examine the candidates in order. Accept a candidate iff it is more than 2,048 away from every value in E and from every previously accepted value. The engine derives `seed+77`, `1000+seed` and `999+seed+epoch` (at most +1,039 with 40 epochs), so this keeps all derived streams disjoint. The first 61 acceptances fill the role order above (c01 roles in the listed order, then c02, …, c12, then the benchmark seed).
4. If fewer than 61 are accepted, write `REGISTRY_STOPPED.json` and stop. There is no redraw and no replacement.

The candidate count was raised from the ladder's 64 to 256 because 61 acceptances are needed; with about 4,000 excluded values (3,954 at the ladder draw) each blocking a window of 4,097, under 0.5% of candidates are expected to be rejected. This ordered acceptance is fixed before the draw and depends on no outcome, so it is not a candidate search. The registry (`REGISTRY.json`, status FROZEN_DRAWN) binds the policy, exclusion and draw hashes. It is a pure function of `DRAW.json` and `EXCLUSIONS.json`: the activation builder and the worker both re-derive it from those bytes and refuse any difference in role values or acceptance decisions before any generation. The activation binds all three hashes.

## Use

Each corpus is generated once, by the run, from its own five roles. All architectures and arms of a corpus share its data, weights, orders and initialization seed, so they are paired. No corpus is replaced if a stage fails; its rows become UNAVAILABLE.
