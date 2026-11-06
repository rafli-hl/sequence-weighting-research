# Owner decisions after N7's result: the assistant check, the re-assessment, the epoch boundary and the package for PR #6

**Date:** 6 Nov 2026, local time (+07:00). **Applies to:** `reports/natural-text-matched-result-20261105-01/RESULT.md`.

## First owner message (verbatim)

> 1. The recomputation was the assistant's, run from the chat on the laptop; its record is reports/natural-text-matched-assistant-recompute-20261106-01/ (recompute.py b1e822ee…, RECOMPUTE.json 24a51292…). It reads POINTS.csv only; it matches the sealed P1, S1, S3, S4 and S5, and it adds a post-hoc epoch-boundary bound: with 768 read at the higher p* of its bracket in every draw, P1 is +0.00702 [+0.00216, +0.01189], 5/6 positive. File it beside the report as an assistant check, not a sealed result, and note that it cannot reach p*, losses, E0 or clipping.
> 2. Update RESEARCH_GOAL.md: the claims table and the 4 Nov section get N7's status in your scoped wording; add a dated re-assessment, 73/100 (owner), with categories alignment 6/10, implementation 14/20, controlled experiments 17/20, evidence 15/20, mechanism 7/15, reproducibility 10/10, plan 5/5 (check they sum to 74 or adjust controlled experiments to 16 so the total is 73), reason: the strongest post-hoc claim is now a publicly pre-registered, confirmed result, narrowed as in RESULT.md.
> 3. The epoch-boundary question is not pursued; record it as a limitation and future work (readouts inside E2.0–E2.25), citing the bound above.
> 4. Then prepare the GitHub package for PR #6: RESULT.md, RESULT_VERIFICATION.json, the analysis outputs, the run verifications and receipts that contain no personal paths, the input check, the note files, the assistant recompute, and the root README line. List every file with its SHA-256. Do not commit.

## As recorded, from the first message

1. **The recomputation.** It was made by the assistant in the chat on the owner's laptop, and not by the session that ran the frozen layout and the verifier. Its files are dated 2026-11-05T18:28:06Z. `reports/natural-text-ladder-owner-decisions-20261105-03/OWNER_DECISIONS.md` says that no saved record was found. That was true when it was written, because the record was saved about 20 minutes later. That file is bound into `RESULT.md` by its hash, so it is not edited, and this record is the correction.
2. **The sum.** The seven categories as given sum to 74 (6 + 14 + 17 + 15 + 7 + 10 + 5). By the owner's instruction for that case, controlled experiments is recorded as 16/20, so the total is 73/100.
3. **The epoch boundary** is not pursued. It is a limitation and future work, and nothing is authorized.
4. **The package** is prepared and not committed.

**Authorized by this message:** the filing of the check, `RESEARCH_GOAL.md`, the record of the limitation, and the preparation of the package. **Not authorized:** a commit, a push, a pull request by the assistant, any run, or opening anything under `work/runs/`.

## Second owner message (verbatim)

> Answers:
> 1. Publish RESULT.md redacted (the default), with the swap recorded in PUBLICATION_TRANSFORMATIONS.json.
> 2. Yes: add make_results_report.py, verify_results_report.py, check_run_inputs.py, decision records 20261105-03 and 20261106-01, and Run M1's status result. Apply the same <LOCAL_USER_HOME> redaction to any of them that contain the home path, and record each in PUBLICATION_TRANSFORMATIONS.json.
> 3. Do not add NATURAL_TEXT_STUDIES.md, PUBLICATION_NOTES.md or DATA_AVAILABILITY.md; they live on main, and the assistant will update them when building PR #6.
> 4. No independent read; the assistant will check the package.
> 5. Your reproducibility flag is accepted: change the re-assessment in RESEARCH_GOAL.md to 72/100 with reproducibility 9/10 (alignment 6, implementation 14, controlled experiments 16, evidence 15, mechanism 7, reproducibility 9, plan 5), reason for the 9: no recomputation of p* or the losses from the run files.
> Rebuild the package, and report its full file list with SHA-256 and every redaction. The assistant will publish from its own Linux clone, so the autocrlf steps aren't needed. Do not commit.

## As recorded, from the second message

1. **`RESULT.md` is published redacted,** with the swap recorded in `PUBLICATION_TRANSFORMATIONS.json`.
2. **Added to the package:** the frozen layout, the verifier, the input check's script, the decision records 20261105-03 and 20261106-01 (this file), and Run M1's status result. The builder redacts any file that holds the home path. None of these six does, so `RESULT.md` remains the only redaction.
3. **Not added:** `NATURAL_TEXT_STUDIES.md`, `PUBLICATION_NOTES.md` and `DATA_AVAILABILITY.md`. The assistant that builds PR #6 updates them on `main`.
4. **No independent read.**
5. **The re-assessment is 72/100,** with reproducibility at 9/10 because nothing recomputed p\* or the losses from the run files: 6 + 14 + 16 + 15 + 7 + 9 + 5 = 72.
6. **PR #6 is published from the other assistant's Linux clone,** so the Windows steps are dropped from the package.

**Authorized by this message:** the rebuild of the package and the change to `RESEARCH_GOAL.md`. **Not authorized:** a commit, a push, a pull request by the assistant, any run, or opening anything under `work/runs/`.
