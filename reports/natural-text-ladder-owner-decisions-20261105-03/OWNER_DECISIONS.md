# Owner approval and report of the sealed analysis, and the instruction for the results report

**Date:** 6 Nov 2026, local time (+07:00). The analysis ran on 5 Nov by UTC. This folder's name is the one the request's commands fixed. **Applies to:** `reports/natural-text-matched-analysis-approval-20261105-01/REPORT.md`.

## First owner message (verbatim)

> I approve OWNER-20261105-MATCHED-ANALYSIS-01: the sealed matched-progress analysis of Runs M1 and M2, run once by me with no retry, with matched_analysis.py 2108f0b287a0b355d20b3d6faedec6bd93d6ad1074f3f5da629b69e14e6ddf9c under source subject 7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56, registered at merge commit f3a2571029f4a0b4d0dc2ee974338e13996e11d8, bound to Run M1 terminal 1392187d518d55ce9463fd7c687d258a791e7e1780d68e4be46b11de1337e65d and Run M2 terminal 6ac3614815ce884dffbfb1b093188fb72699a636a24fbd9c7070b6b4fe8c3737, with its output only in reports/natural-text-matched-analysis-20261105-01, followed by my input check, and by the results report from make_results_report.py db330602333ad0c2058c60be0c071948d763e698881dd29376f40dd57d7837dd, checked by verify_results_report.py 00e013dcfd197401df529c379dd9741be6696143c8bf87b0f472bf23070b97d9.

The owner sent these same words a second time, in a message that was interrupted, just before the report below.

## Second owner message (verbatim)

> Analysis output and input check below: status COMPLETE, P1 REVERSAL_CONFIRMED, confirmed_through S5, S2 UNAVAILABLE (TARGET_OUTSIDE_PATH 3), NOT_OVERFIT both rates, records_against_arrays within limit, input check PASS 67/0. Output hashes: ANALYSIS.json a4af7bad…, FITS.csv b1cd03de…, MATCHED.csv 86ea11d7…, POINTS.csv 234434a3…. The assistant independently recomputed P1, S1, S3, S4 and S5 from POINTS.csv and matches the sealed analysis on every mean, interval and sign count.
> [paste the full output here]
>
> Now run make_results_report.py and verify_results_report.py as approved, and report the verdict, the report path and hashes. Then update NEXT_EXPERIMENT.md, HANDOFF.md, INDEX.md, and RESPONSE.md's claim 4/5 status by a NEW note file (do not edit RESPONSE.md): the matched-progress reversal is now a pre-registered, confirmed result. Do not commit.

**The placeholder is as it arrived.** `[paste the full output here]` is what the message held, so no console output of the analysis or the input check is on record. The command's receipt is kept as `ANALYSIS_EXIT_RECEIPT.json`, and the input check as `RUN_INPUTS_CHECK.json`, both in `reports/natural-text-matched-run-checks-20261104-01/`.

**The sentence on an independent recomputation is the owner's.** The assistant that writes this record did not make that recomputation: it had opened no analysis output when this record was written, apart from hashing the four files, and it stayed off D: from the approval until the owner reported back. The top level of the project root and of `reports/` shows nothing changed since the analysis except the output folder and the run-checks folder, so no saved record of that recomputation was found there. This record does not treat it as a check. The check of record is `verify_results_report.py`.

## As recorded

1. The sealed analysis was approved and run by the owner, once. The command's claim and receipt say it started at 2026-11-05T17:55:38Z and ended at 2026-11-05T17:58:43Z, 184.7 s, exit 0. The receipt's four output hashes begin with the four the owner reports, and equal the files on disk. The owner's input check wrote its record at 2026-11-05T18:00:34Z.
2. Run the frozen layout and then the verifier, as approved, and report the verdict, the report's path and the hashes.
3. Update `NEXT_EXPERIMENT.md`, `HANDOFF.md` and `INDEX.md`.
4. Record the status of claims 4 and 5 of `RESPONSE.md` in a new note file. `RESPONSE.md` itself is not edited.
5. No commit.

**Authorized by this message:** the layout, the verifier, those three documents and that new note. **Not authorized:** a commit, an edit of `RESPONSE.md`, any second run of the analysis, or opening anything under `work/runs/`.
