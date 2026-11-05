# Owner decisions on N7, after the seed draw: second addendum

**Given on 4 Nov 2026.** `OWNER_DECISIONS.md` is bound in the seal. The first addendum, `OWNER_DECISIONS_ADDENDUM.md` (`c68095be…`), is fixed, because the public registration names it by its hash. So these later messages are recorded here. The owner's approval of the real-engine check is in `reports/natural-text-matched-engine-check-result-20261104-01/OWNER_APPROVAL.md`.

## The owner's acceptance of the seal, verbatim

> Seal 7ef133ad… accepted. The assistant verified on the laptop that SOURCE_SUBJECT.json, matched_plan.py, README.md, engine_check.py, build_matched_activation.py, PIN_DIFF.diff and OWNER_DECISIONS_ADDENDUM.md match your hashes, and that PIN_DIFF.diff changes only the five draw pins, the two README status lines and EXPECTED_SUBJECT in engine_check.py and the activation builder. The EXPECTED_SUBJECT lines are accepted as pins.
>
> Now:
> 1. Revise test_matched.py for the pinned state and run the full suite (no Torch or GPU needed). Report the result.
> 2. Prepare the real-engine check: give me its PowerShell command (with a hash loop over every file it reads or runs), its expected duration, what it reads and writes, and its exit codes. It must read no corpus file and compute no study loss, and its result report must say so.
> 3. Update NEXT_EXPERIMENT.md, HANDOFF.md, INDEX.md and REPORT-revision-02.md (or a new report beside it) to the current state: seeds drawn, seal 7ef133ad…, real-engine check next, then the scoped review, the public registration, the activation and Runs M1 and M2.
> Report every new or changed SHA-256, then STOP before the engine check. Do not commit.

## The owner's message after the real-engine check, verbatim (the console output is in `OWNER_CONSOLE_OUTPUT.txt`, beside the result)

> Engine check output below: both parts passed (inputs exit=0, smoke exit=0). Now:
> 1. Run verify_engine_check.py to write the result report, and correct the out-of-date lines in NEXT_EXPERIMENT.md, HANDOFF.md section 57, REPORT-seal-7ef133ad.md and PINNED_STATE_FILES.json (run04 passed 25/25; the check is approved and passed).
> 2. Record in the result report that real Torch counted 1 tied value in m03 where the draw's numpy disclosure counted 0 (all others equal: 3, 4, 1, 1, 1), both within the limit of 16. Do not edit DISCLOSURE_FIGURES.md.
> 3. Then run the scoped fresh-context review of everything changed since review-02 and not yet reviewed: the pin step, the guard (run_engine_check_guarded.py), test_matched.py's pinned-state changes, verify_engine_check.py, the engine-check command, and the documents. Report findings and fixes.
> 4. Then prepare the public registration package for PR #5: the sealed source (seal 7ef133ad…), the seed registry, the owner decisions 20261104-02 and the addendum, the engine-check result, and a registration README that states the design, the primary and the fixed sequence, says that no study data exists, names the addendum by SHA-256, and states the token-overlap limitation. List every file with its SHA-256.
> STOP before any activation. Do not commit.

**The laptop checks in these messages** were not made in the assistant's session that recorded this file.
