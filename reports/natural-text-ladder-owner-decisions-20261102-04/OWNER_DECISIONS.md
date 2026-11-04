# Owner approvals of the real-engine check and of Run A

**Date:** 2 Nov 2026. **Applies to:** `reports/natural-text-fewepoch-runa-package-20261102-02/REPORT.md`, sections 3 and 4.

## First owner message (verbatim)

> Approved: running the real-engine check (inputs, then smoke) with approval id OWNER-20261102-FEWEPOCH-ENGINECHECK-01. The corrected 64-token disclosure figures (mean 1.00%, largest 2.21% in d04) are accepted. I will send the output before anything else.

## Second owner message (verbatim; the console output it carried is in `reports/natural-text-fewepoch-engine-check-result-20261102-01/OWNER_CONSOLE_OUTPUT.txt`)

> Engine check PASS: inputs (all groups within the tie limit, receipt c8bb14ef…) and smoke (both modes, receipt d037617f…); output below. Approved: building activation A and running Run A once, with the approval text you gave. Please stay off D: until I report back.

## Approval text of Run A, as the owner passed it to the builder

Recorded by the builder in `work/natural-text-fewepoch-activation-a-20261101-01/APPROVAL_RECORD.json` (`b60e58a5…`), under approval id OWNER-20261102-FEWEPOCH-RUNA-01:

> I approve few-epoch Run A under source subject 62f05466d1f3c0ef09de3d9ed12e8683036c82912978e0d77a91eeb34be3602a and builder 36f5031c0911f39aaae91d14475243573a6ddaabcb606860c858803c86452ef9, one use, no retry.

## As recorded

1. The real-engine check was approved and run by the owner; result: `reports/natural-text-fewepoch-engine-check-result-20261102-01/RESULT.md`.
2. The corrected 64-token disclosure figures are accepted: mean 1.00%, largest 2.21% (d04), on all windows.
3. Run A was approved and run by the owner, after the check. The assistant stayed off D: from this approval until the owner reported back; it read only the two check receipts on C:.
