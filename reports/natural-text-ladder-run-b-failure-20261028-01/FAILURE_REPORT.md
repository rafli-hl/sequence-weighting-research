# Run B failure: natural-text capacity ladder

**Date:** 28 Oct 2026.

**Status: FAILED in draw d02** with `TimeoutError: Original deadline exhausted`, which is the per-draw work cap. Run B ran under Approval 2 and Amendment 01 (adc19ccc…), on subject 90e3f3ef….

**Records:**
- Run B terminal: `work/runs/natural-text-ladder-b-20261028-01/TERMINAL.json`, ab01d898c6a2888c2a9672346b7990ca99057c51030a62005282257fb90506e4.
- Owner exit receipt: FAILED, exit code 1, 1,958.9 s, no retry.
- The timing table below comes from `TIMING.json` (f47ce902…), produced by `timing_table.py`.

Everything is preserved: 71 files and 457.5 MB in the run directory, plus the activation. Nothing was rerun, moved or deleted.

## What happened (measured)

- **Run B's own benchmark** projected 708.7 s per draw. The frozen cap is ceil(1.25 × 708.7 + 120) = **1,006 s per draw**.
- **d01 completed** in 671.9 s, within the projection.
- **d02 used its 1,006 s** before its last trajectory finished. That was width 384, which had run 252 s; d01's width-384 adaptation took 225.5 s. The worker stopped at the cap, as designed. Its elapsed time was 1,777.9 s.
- **The slowdown was uniform across widths** (adaptation seconds from file write times):

| Width | Run A, mean of 3 | Run B d01 | Run B d02 | d02 / d01 |
|---|---|---|---|---|
| 64 | 65.2 | 63.4 | 104.2 | 1.64 |
| 96 | 69.4 | 65.9 | 114.6 | 1.74 |
| 128 | 72.9 | 70.7 | 125.9 | 1.78 |
| 192 | 94.5 | 90.9 | 160.3 | 1.76 |
| 256 | 114.0 | 124.3 | 192.8 | 1.55 |
| 384 | 178.4 | 225.5 | unfinished after 252 s | — |

  d02's uniform pre-training was also slower: 13.5–49.5 s per width, against 9.8–28.5 s in d01.
- **Run A did not slow down.** It ran the same widths for 31 minutes (21:07–21:38) at a steady speed.
- **One change was identified.** Windows reports that a GPU game process (`VALORANT-Win64-Shipping.exe`, with its `vgtray.exe` tray) started at **22:20:36**. That was during d01's width-256 adaptation, the first trajectory that ran slower than Run A. After the run, with no worker running, `nvidia-smi` showed the game on the GPU, 2,396 MiB used and 34% utilization.

  The timing coincides, but the records cannot prove the cause; no other change was found.
- **The GPU memory guard did not register the game.** The sampled-GPU reading (total − free from `cudaMemGetInfo` inside WSL) peaked at 1,597,820,108 bytes. That is the same value as Run A and d01, and it never rose in d02, although width 384 ran while the game was open.

  So the guard did not see the game's GPU memory. How much memory the game used during the run is not recorded. The requirement that the GPU be otherwise idle (PROTOCOL §9) is therefore an operating condition that no guard checks.

## Consequence (pre-registered)

Run B failed after its start-up check, other than through the fallback. Under PROTOCOL §9 and the owner's confirmation of 28 Oct 2026 (`natural-text-ladder-owner-decisions-20261028-01`), **both primaries are UNAVAILABLE**.

Approval 2 was one-use with no retries: "A start-up fallback or any failure stops the work until a new approval." The start-up fallback did not apply, because the start-up check found the ten-draw run feasible.

## Outcome-blind status

- d01 (complete) and d02 (five of six trajectories) have saved per-sequence arrays.
- **None has been read; no p\* or loss has been computed from Run B, and no analysis has been run.** `timing_table.py` reads only file times and the operational fields of TERMINAL.json, BENCHMARK.json and the receipts.
- `text_analysis.load` accepts a FAILED run and would analyse d01. That would reveal d01's p\* points while adding nothing to the primaries, which are already UNAVAILABLE.
- The ten draws therefore remain unseen for every outcome. The owner decides whether to keep them that way.
