# Owner decisions on Approval 2, revision 05: natural-text capacity ladder

**Date:** 29 Oct 2026.

**Applies to:**
- source subject 2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d (revision 05, the second and final attempt);
- builder 4933e9714c6f0440954798894aee530578e738b8b91f4b274046c2add1a1b498;
- Amendment 01, sha256 adc19ccce9b02d959fb94a938b2e4371e09dc98e8be4f527014a6e1a8a789f22, unchanged;
- the approval record of activation B, `work/natural-text-ladder-activation-b-20261028-02/APPROVAL_RECORD.json`:
  - sha256 b351b65f16ac4ad4dd6fd572e6b74433823f3144c1f338500e03e9b18ebeb9fb;
  - 8,921 bytes, written 29 Oct 2026 at 10:46 local time;
  - approval id OWNER-20261029-TEXT-B-02.

No sealed or earlier file is changed. To get the approval text, the assistant read only `APPROVAL_RECORD.json` in the activation folder. It opened no run output, progress log or GPU check record.

## Owner message (verbatim)

> Approved, with no analysis of a failed run. I added one sentence: a GPU not-idle stop before any draw starts training produces no data, so it does not count as the failed attempt and a new approval may follow. Please record that rule. Running now.

## Approval text (verbatim, the `user_text` field of the approval record)

> I approve natural-text ladder Approval 2 for revision 05, the second and final attempt, under subject 2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d and builder 4933e9714c6f0440954798894aee530578e738b8b91f4b274046c2add1a1b498, with Amendment 01 sha256 adc19ccce9b02d959fb94a938b2e4371e09dc98e8be4f527014a6e1a8a789f22 applying unchanged to this subject: activation B and the single Run B, each once, with no retries. A pre-start GPU refusal claims nothing and the run command may then be repeated. A GPU not-idle stop before any draw starts training produces no data and is not counted as the failed attempt; a new approval may then follow. A start-up fallback stops the work until a new approval. If the run fails for any reason after training has started the natural-text ladder closes as UNAVAILABLE and the failed run is not analysed.

**How it differs from the text suggested in the approval request:**
- **Added sentence:** "A GPU not-idle stop before any draw starts training produces no data and is not counted as the failed attempt; a new approval may then follow."
- **Last sentence:** it now reads "If the run fails for any reason after training has started …". The suggested text read "If the run fails for any reason …".

## Decisions

1. **Approval 2 for revision 05 is granted.** The owner runs the build of activation B and the single Run B, each once, with no retries. The assistant runs neither.
2. **A failed revision 05 run is not analysed.** This settles the question that PROTOCOL.md §12 left to the owner. The analysis of a completed Run B still needs its own approval.
3. **New rule: a GPU not-idle stop before any draw starts training is not the failed attempt.**
   - Such a stop produces no draw data. It does not close the ladder, and a new approval may follow.
   - It narrows the owner ruling of 28 Oct ("If revision 05's run fails for any reason, the natural-text ladder closes as UNAVAILABLE") for this case only.
   - A pre-start refusal was already not counted: it claims nothing, and the same command may be run again.

## How the rule applies to the sealed worker (read from source, not from any run)

**The order of Run B.** `text_worker.py` of subject 2ac27fe7… runs Run B in this order:
1. the pre-start check;
2. the run folder;
3. the outcome-blind start-up benchmark, which trains throwaway models on the pool, not on a draw;
4. the cap formula and the fallback check;
5. for each draw, the GPU gate (line 569), then the draw itself (line 570).

**Covered: a not-idle stop at the gate before d01.** The gate's verdict is BUSY_TIMEOUT, and the worker raises GpuBusyError ending "stopped before d01". The stop shows in these records, none of which is an outcome:
- `TERMINAL.json` shows status FAILED, error type GpuBusyError and an empty stage list;
- no d01 directory exists;
- the owner receipt shows stop_reason GPU_NOT_IDLE_30_MIN.

**Not covered: a not-idle stop before d02 to d10.** By then d01 has trained, so the run has failed after training started. The ladder closes as UNAVAILABLE and the run is not analysed.

**A new attempt needs new source.** The worker refuses a run folder that already exists ("One-use run directory exists; no retry"), and revision 05 fixes the run folder at -02. A new attempt after a covered stop therefore needs:
- new versioned source with new folders;
- fixture tests;
- the scoped review;
- a new approval.

The draws, seeds, learning rates, Amendment 01 and the cap formula would stay unchanged.

## Cases the approval text leaves open (for an owner ruling; not decided here)

Some failures before d01 starts training are not a GPU not-idle stop. Examples:
- an error during start-up or during the start-up benchmark, which trains benchmark models but not a draw;
- no valid verdict from the owner script before d01: the TimeoutError "No Windows GPU check verdict before d01", or a malformed verdict;
- the owner window being closed before d01 starts.

The added sentence covers only a GPU not-idle stop. The last sentence closes the ladder only for a failure "after training has started". So the text does not say whether these failures count as the failed attempt. Like a covered stop, they produce no draw data.

**The assistant's recommendation (not a decision):** apply the owner's reason, "produces no data", to every failure before d01 starts training. The test would be mechanical: `TERMINAL.json` shows an empty stage list and no draw directory exists.
