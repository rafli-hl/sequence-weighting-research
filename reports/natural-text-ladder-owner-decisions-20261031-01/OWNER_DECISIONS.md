# Owner approval of revision 02 and the owner's instructions after its result

**Date:** 30–31 Oct 2026. The approval was given before the revision 02 run existed. The instructions after the result were given after the run and its sealed analysis had both ended COMPLETE.

**Applies to:**
- the one-rate ladder extension, revision 02, the final attempt (owner ruling 20261030-03), source subject 52ad878309ddfa6a5e1e5a501ad91f9dc6d5285194ca6165dd0c74d7db363730 and pinned builder 99606db0f6855d11dc8bcd5e1c930eedc08144feeded344022c55bd4e5b97ff2;
- its activation `work/natural-text-onerate-activation-20261030-02/`, its run `work/runs/natural-text-onerate-20261030-02/` and its analysis `reports/natural-text-onerate-analysis-20261030-02/`.

## 1. The approval (verbatim)

> Approved with your suggested text. Checklist done: charger in, lid open, Turbo mode, sleep off, updates paused, IntelliJ and GPU apps closed. Running steps 1 and 2 now, step 3 only after COMPLETE. Please do not touch D: until I report back.

**The approval text** is the one the assistant suggested. The builder recorded it in `APPROVAL_RECORD.json` as `user_text`, with approval id OWNER-20261030-ONERATE-02 and the creation time 2026-10-31 00:02:33:

> I approve OWNER-20261030-ONERATE-02 for revision 02 of the one-rate ladder extension, the final attempt under ruling 20261030-03, with source subject 52ad878309ddfa6a5e1e5a501ad91f9dc6d5285194ca6165dd0c74d7db363730 and pinned builder 99606db0f6855d11dc8bcd5e1c930eedc08144feeded344022c55bd4e5b97ff2. Build the activation once, run ONERATE_OWNER_RUN.ps1 once, and run the sealed analysis once only after a COMPLETE terminal. No retries. The power gate and the power log are part of the run. A run that creates any draw folder counts as the final attempt, and a refusal before any draw folder exists claims nothing and is not counted. C1 is accepted as a documented limitation. Attempt 1 is never analysed for outcomes. A FAILED or STOPPED_AT_STARTUP run is not retried and is not analysed without my decision.

**Who ran what.** The owner ran the build, the run and the analysis. The assistant ran nothing and did not access D: until the owner reported back.

## 2. The owner's instructions after the result (verbatim)

> Run COMPLETE and analysis COMPLETE: turn_down CONTINUES_RISING, dip NO_DIP_AT_ONE_RATE, memorization TRACKS_MEMORIZATION, joint MEMORIZATION_PREDICTIONS_MET. Output below.
> 1. Record the result as planned, quoting the three pre-registered labels and the joint reading exactly.
> 2. In the same report, give equal prominence to the sealed by-epoch secondaries, labelled as secondary and not pre-registered as primaries: the turn-down is TURNS_DOWN at E24 (-0.023) and E32 (-0.175), 10/10 draws each; the argmax width moves 768 (E4-E16) to 512 (E24) to 384 (E32); at E32 the gap keeps rising with width while p* falls. State plainly that the epoch-averaged primaries dilute this late-epoch pattern, and that the joint label MEMORIZATION_PREDICTIONS_MET is accurate for the averages but must not be summarised alone. Verify every number from ANALYSIS.json.
> 3. Draft, do not build, a small confirmatory study on the fresh unused draws: primaries for the turn-down over 384-768 at E24 and E32 separately, and for the shift of the peak location from E8 to E32. Include power from the observed effect sizes, time and disk. Stop for my decision.

**Note.** The console output mentioned ("Output below") was not included in the message. Every number was therefore read from the saved records.

## 3. Decisions as recorded

1. **The run and the analysis are accepted as COMPLETE.** The result is recorded in `reports/natural-text-onerate-result-20261031-01/RESULT.md`, with the three labels and the joint reading quoted exactly.
2. **Equal prominence.** The by-epoch secondaries get the same prominence in that report, each labelled secondary and not pre-registered as a primary. Every number is checked against `ANALYSIS.json` by `verify_result.py`, which writes `RESULT_CHECK.json`.
3. **The confirmatory study is a draft only:** `reports/natural-text-onerate-confirmation-draft-20261031-01/PROPOSAL_DRAFT.md`. It has no source, seed draw, fixture, review, activation or run. The next step is the owner's decision.
