# Owner decision on Approval 3 (the analysis of Run B): natural-text capacity ladder, revision 05

**Date:** 29 Oct 2026.

**Applies to:**
- source subject 2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d;
- Run B, TERMINAL.json sha256 277e38c747bb2082aec4139e5e549c4e581bf1a37eae1e540db48b49afd8504c;
- runner `reports/natural-text-ladder-analysis-preparation-20261029-01/run_text_analysis.py`, sha256 038917e91f1040a533a3e1da5a6d28216d31a3bb314c1062221a2cf9e6ac53cf, unchanged when this record was written;
- Amendment 01, sha256 adc19ccce9b02d959fb94a938b2e4371e09dc98e8be4f527014a6e1a8a789f22, unchanged.

The approval id is OWNER-20261029-TEXT-ANALYSIS-01, as suggested in the approval request. The authoritative copy of the approval text is the `user_text` field that the runner writes into `reports/natural-text-ladder-analysis-20261029-01/APPROVAL.json`.

## Owner message (verbatim)

> Approval 3 granted with your suggested text and both choices kept as they are. Running now.

## Suggested approval text that the owner adopted (from the approval request)

> I approve natural-text ladder Approval 3: the single analysis of revision 05 Run B, terminal 277e38c747bb2082aec4139e5e549c4e581bf1a37eae1e540db48b49afd8504c, under subject 2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d, by runner run_text_analysis.py sha256 038917e91f1040a533a3e1da5a6d28216d31a3bb314c1062221a2cf9e6ac53cf in real mode, once, with no retries, writing only reports/natural-text-ladder-analysis-20261029-01. Attempt 1 is not analysed. Amendment 01 sha256 adc19ccce9b02d959fb94a938b2e4371e09dc98e8be4f527014a6e1a8a789f22 applies unchanged, and its sensitivity, if triggered, needs its own approval. If the runner ends in any status other than COMPLETE, nothing is rerun until a new approval.

## Decisions

1. **Approval 3 is granted.** The owner runs the runner once in real mode. The assistant does not run it.
2. **The Amendment 01 interpretation note is applied on the final Primary B label only.** It applies when that label is INTERIOR_PEAK or RISE_AND_FALL_NOT_WITHIN_POINTS. It is not added when the saturation rule changes the label away from those. (This was choice 1 of the approval request, kept.)
3. **A report failure needs its own approval.** If the runner ends REPORT_FAILED after the sealed outputs exist, writing the report needs a separately approved report-only step. (This was choice 2, kept.)
4. **The Amendment 01 sensitivity is not part of Approval 3.** If Primary B is INTERIOR_PEAK, the sensitivity needs new versioned source, fixture tests, an independent review and its own approval.

## A note on the preparation folder

After the approval request, `REVIEW_FINAL_CHECK.md` in the preparation folder changed on disk. A blank line after the reviewer's first paragraph now reads `[REPORT.md](REPORT.md)`, and the file's sha256 changed from e6513153b088206ad56250d8d1ad186b580de296d1406b12447f2f8bf7804c8c to 012b752dcde04bd56ed4d9d5010ecf502da97a5682035c8b35bc8859827ebbb2. The assistant did not make this change and has not reverted it.

The change is not part of the reviewer's words. It does not touch the runner, whose hash is bound by the approval and is unchanged.
