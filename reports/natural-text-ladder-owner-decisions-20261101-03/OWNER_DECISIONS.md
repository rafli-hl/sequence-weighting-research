# Owner approval of the WikiText-103 acquisition, and two decisions on the study

**Date:** 1 Nov 2026. **Applies to:** the few-epoch preparation (`reports/natural-text-fewepoch-preparation-20261101-01/REPORT.md`), acquisition source subject 2b8033ef98cfbd76a04858a8003d4344a904cc43a81c49dbc599c5357379adda.

## Owner message (verbatim)

> Holm labelling for M is kept, and your correction to the motivation is accepted (768 vs 384-512 only). No independent check of the N1 diff is needed; I reviewed it. Approving A1-A3 with the text below. I will report the free disk space after A3.

## Decisions as recorded

1. **M's label follows Holm,** not the unadjusted 95% interval. M can therefore read NOT_DETECTED while its unadjusted interval excludes 0. No file changes: `PROTOCOL.md` section 5 already says this.
2. **The motivation is as corrected in `PROTOCOL.md` section 6c:** 768 lies 0.016–0.022 below 384 and 512 at gaps 0.25 and 0.5. It lies only 0.001–0.015 below 128–256, and 128–512 are not nearly equal. No file changes.
3. **The N1 diff** (`review-01-confirmation/CHANGES_SINCE_CONFIRMATION.diff`) was reviewed by the owner. It had no independent review.
4. **A1–A3 approved,** owner-run.

## Note on the approval text

The message said "with the text below", but no text came through in it. The assistant filled the text it had proposed into the A1 command and asked the owner to say before running if a different wording was meant. `work/text-assets-wt103/A1_RECORD.json` records that text as `user_text`, and it is exactly the proposed text (`reports/natural-text-wt103-acquisition-result-20261101-01/ACQUISITION_VERIFICATION.json`).
