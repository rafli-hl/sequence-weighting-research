# Owner approval of the sealed analysis, its report, and the instruction after it

**Date:** 3 Nov 2026. **Applies to:** `reports/natural-text-fewepoch-analysis-approval-20261103-01/REPORT.md`.

## First owner message (verbatim)

> I approve OWNER-20261103-FEWEPOCH-ANALYSIS-01: the sealed few-epoch analysis of Runs B1 and B2, to be run once by me, with fewepoch_analysis.py fab5df60ab9d0acb66de225d3e04eb23b3ad442becaa5562d6a1d421ba63402b under source subject 62f05466d1f3c0ef09de3d9ed12e8683036c82912978e0d77a91eeb34be3602a, bound to Run B1 terminal 7b04d74b62d10847e288c8972a861f179d06e528e2f60ce31a432f04473c8ae2 and Run B2 terminal eef9f17516f836042b124b50c17a5a28a5d01cb8659b6e8b296d4c96d80ab95e, writing only to reports/natural-text-fewepoch-analysis-20261103-01, followed by the results report from make_results_report.py 91a61d0a4c074e095071416bc87e2edad07518e561199cfceed306a66e1a4a41. The shared-sequence correction and section 4c are accepted as written. Running now.

## Second owner message (verbatim)

> Analysis COMPLETE: M CAPACITY_BEYOND_MEMORIZATION, FALL CONTINUES_RISING, RISE RISES; NOT_OVERFIT passes at every width. Proceed with the results report from make_results_report.py, quoting labels and readings exactly.
> Also add a clearly labelled DESCRIPTIVE section (sealed secondaries, not a primary): at every readout E0.25-E3, the per-draw argmax width is 512 in 10/10 draws, and p* at 768 is below p* at 512 (for example E3 panel 0.098, 0.118, 0.104 at 384, 512, 768). The FALL slope over 384-768 stays positive because 768 sits above 384. State next to it, with equal prominence, the learning-rate caveat: on t00, 768 had lower validation NLL at 1e-4 than at 3e-4, so the drop at 768 may reflect a rate that is too high for 768. Verify every number from ANALYSIS.json.
> Then draft, do not build, a small confirmatory study on fresh WikiText-103 draws: a pre-registered interior-peak primary (p* at 512 above both 384 and 768 at E3), with 768 trained at both 3e-4 and 1e-4 as a pre-registered learning-rate control, plus power, time and disk. Stop for my decision.

**The console output did not arrive.** The second message gives the labels and verdicts in the owner's words, without the console text or the exit code. So no `OWNER_CONSOLE_OUTPUT.txt` exists for this run. The analysis folder's three files are what the report checks.

## As recorded

1. The sealed analysis was approved and run by the owner. The assistant stayed off D: from the approval until the owner reported back.
2. Write the results report from `make_results_report.py`, unchanged, quoting labels and readings exactly.
3. Add a labelled DESCRIPTIVE section, with the claims above checked against `ANALYSIS.json`, and the learning-rate caveat beside it with equal prominence.
4. Draft, and do not build, a small confirmatory study on fresh WikiText-103 draws, with its primary, its learning-rate control, power, time and disk.
5. Stop for the owner's decision.

## How the terms are used

- **The results report:** the output of `make_results_report.py` (`91a61d0a…`), whose order and wording were frozen before any outcome was opened. It is not edited. The DESCRIPTIVE section therefore sits in its own file beside it, since the frozen script's output must stay as the script writes it.
- **The DESCRIPTIVE section's origin:** the claims in it were put forward after the outcomes had been seen. They are not part of the frozen decision rule, and cannot change a label.
