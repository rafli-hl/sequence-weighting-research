# Owner approval of the late-turn confirmation run, and the instructions after its result

**Date:** 31 Oct 2026. **Applies to:** the late-turn confirmation, with source subject 9286f324f9dfb49bdf2b6956c7ea76112c2a24214bdec12e931ea646f543f5ba, pinned builder 3d2efd0e4a305eff5d587367c3b26b986bec1000708e08c73544f33f00025714 and drawn registry b9b6a8821613a1f2de610404145aaff56279a7967c130d0c215cdcf5beb0b9ff (`reports/natural-text-lateturn-preparation-20261031-01/REPORT.md`).

## Owner message at approval (verbatim)

> Approved with your suggested text: option a, and the limitation accepted. The P3 conditional lower-bound correction is accepted. Checklist done. Running steps 1 and 2 now, step 3 only after COMPLETE. Please do not touch D: until I report back.

## Approval text for OWNER-20261031-LATETURN-01 (verbatim)

The builder recorded this text in `work/natural-text-lateturn-activation-20261031-01/APPROVAL_RECORD.json` (`user_text`; record sha256 c07acd01a3056ffaf38860985e36f43a54df6370d17c77e888c7da90e740fbef).

> I approve OWNER-20261031-LATETURN-01 for the late-turn confirmation, with source subject 9286f324f9dfb49bdf2b6956c7ea76112c2a24214bdec12e931ea646f543f5ba and pinned builder 3d2efd0e4a305eff5d587367c3b26b986bec1000708e08c73544f33f00025714, on the drawn registry b9b6a8821613a1f2de610404145aaff56279a7967c130d0c215cdcf5beb0b9ff. I choose option a: keep the frozen partition with the 10 text-check articles disclosed. I accept the documented limitation that the terminal_outside_ledger flag is recorded in TERMINAL.json only. Build the activation once, run LATETURN_OWNER_RUN.ps1 once, and run the sealed analysis once only after a COMPLETE terminal. No retries. A run that creates any draw folder is the only attempt of this study; a refusal or a stop before any draw folder exists claims nothing and is not counted. A FAILED or STOPPED_AT_STARTUP run is not retried and is not analysed without my decision.

## Owner report and instructions after the result (verbatim)

> Late-turn confirmation COMPLETE: P1 TURNS_DOWN (confirmed), P3 SHIFTS_TO_SMALLER_WIDTH (confirmed), P2 INCONCLUSIVE (not confirmed, low power stated in advance). Output below.
> 1. Record the result, quoting the labels and the sealed readings exactly, including the overfit-regime wording, the conditional lower bound for P3 and the text-check disclosure. Check TERMINAL.json for terminal_outside_ledger and state the result.
> 2. Update NEXT_EXPERIMENT, INDEX, HANDOFF and RESEARCH_GOAL. Then write one evidence-chain summary across the four natural-text studies (ladder, one-rate extension, late-turn confirmation) plus the synthetic follow-up, separating pre-registered confirmations, pre-registered nulls, and exploratory observations. No claim beyond the evidence.
> 3. Do not start the paper yet; stop after the summary.

**Note.** The output mentioned ("Output below") was not included in the message. The result is read from disk.

## Decisions as recorded

1. **Option (a).** The frozen partition is kept, and the 10 training articles used by the September text check are disclosed. Option (b), excluding them, is closed for this study.
2. **The documented limitation is accepted.** The `terminal_outside_ledger` flag is recorded in TERMINAL.json only. For this run, the flag is absent (`reports/natural-text-lateturn-result-20261031-01/RESULT.md`, section 1).
3. **The P3 wording is accepted.** S is a conservative lower bound on the shift only under the censoring condition of PROTOCOL.md section 6 (review 1, finding 1).
4. **Execution, by the owner only:**
   - the activation was built at 14:24:05 (+07:00) on 31 Oct (`APPROVAL_RECORD.json`, `created_local`);
   - the run ended COMPLETE (TERMINAL.json d61250a2…; owner receipt 48e38a09…);
   - the sealed analysis was run after the COMPLETE terminal, into `reports/natural-text-lateturn-analysis-20261031-01`.

   The assistant ran none of these steps and made no tool call on D: between the approval and the owner's report.
5. **Next, as instructed:**
   1. the result report;
   2. the updates to NEXT_EXPERIMENT.md, INDEX.md, HANDOFF.md and RESEARCH_GOAL.md;
   3. one evidence-chain summary across the natural-text studies and the synthetic follow-up;
   4. a stop. No paper work starts.
