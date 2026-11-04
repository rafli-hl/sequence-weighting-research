# Owner ruling on failures before d01: natural-text capacity ladder, revision 05

**Date:** 29 Oct 2026. The owner made this ruling while Run B was in progress and before any outcome existed.

**Applies to:**
- source subject 2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d (revision 05, the second and final attempt);
- activation B, approval id OWNER-20261029-TEXT-B-02 (approval record sha256 b351b65f16ac4ad4dd6fd572e6b74433823f3144c1f338500e03e9b18ebeb9fb);
- the earlier record of the same day, `reports/natural-text-ladder-owner-decisions-20261029-01/OWNER_DECISIONS.md` (sha256 7225fec3241ecf7d4bfe3b550e8c0699307caeb242d725a4fd873e2d98f8f6b3).

That earlier record is left unchanged. This ruling settles the cases that its section "Cases the approval text leaves open" left to the owner. No sealed file is changed. To write this record, the assistant opened nothing in the run folder, nor any progress log or GPU check record.

## Owner ruling (verbatim)

> Ruling, made while Run B is in progress and before any outcome exists: any failure before d01 begins counts as producing no data and is not the failed attempt, whatever the cause, including a crash during start-up or the start-up benchmark, no valid GPU verdict before d01, and the window being closed before d01. The test, checked without opening any outcome: no draw folder (d01 or later) exists in the run folder, and TERMINAL.json shows no completed stages. If any draw folder exists, the run counts as the final attempt and a failure closes the ladder as UNAVAILABLE. A start-up fallback stays under its own rule. A new attempt after a covered stop needs new versioned source, the scoped review and a new approval, with the science unchanged. Record this in the owner decisions file with its hash.

## Decisions

1. **Any failure before d01 begins is not the failed attempt, whatever its cause.** Such a failure produces no draw data. This widens the rule of the earlier record, which covered only a GPU not-idle stop before d01.
2. **The test**, checked without opening any outcome:
   - no draw folder (`d01` to `d10`) exists in the run folder;
   - `TERMINAL.json` shows no completed stages.
3. **If any draw folder exists, the run is the final attempt.** A failure then closes the natural-text ladder as UNAVAILABLE, and the failed run is not analysed.
4. **A start-up fallback stays under its own rule.** It stops the work until a new approval.
5. **A new attempt after a covered stop needs:**
   - new versioned source;
   - the scoped review;
   - a new approval.

   The science stays unchanged.

## How the test reads on the sealed worker (from source, not from any run)

The facts below come from `text_worker.py` of subject 2ac27fe7….

**When a draw folder appears.** The worker makes a draw folder (`d01` to `d10`, at the top of the run folder) only after that draw's GPU gate returns IDLE: the gate at line 569, then `ctx.stage`, which calls `Output.begin_stage`. The run folder holds other entries before d01 begins, and none of them is a draw folder:
- the `benchmark/` folder;
- the `cache/` folder;
- the `gpu-checks/` folder, which holds files such as `d01-REQUEST.json`;
- `BENCHMARK.json`.

**When a stage counts as completed.** A stage is listed as completed in `TERMINAL.json` only after its folder exists and its `<stage>-RECEIPT.json` is written. So a completed stage always has a draw folder.

**One reading point, not a ruling.** If the worker were killed before it could write `TERMINAL.json` (for example by closing the window), the second condition could not be read as worded. In that case, the assistant would report what exists and leave the reading to the owner, rather than apply the rule itself.
