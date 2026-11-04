# Owner approval and report of Run B1, and the instruction for Run B2

**Date:** 2 Nov 2026. **Applies to:** `reports/natural-text-fewepoch-b-package-20261102-01/REPORT.md`.

## First owner message (verbatim)

> Approved: activation B1 and Run B1 once, with your approval text. NOT_OVERFIT stays as frozen (per width across the ten draws). After B1 ends, you may read only the input-hash field of t00/INPUTS.json for the promised comparison. Stay off D: until I report back.

## Second owner message (verbatim; the console output it carried is in `reports/natural-text-fewepoch-b1-result-20261102-01/OWNER_CONSOLE_OUTPUT.txt`)

> Run B1 COMPLETE: d01-d05, exit 0, 10,592 s, terminal 7b04d74b62d10847e288c8972a861f179d06e528e2f60ce31a432f04473c8ae2, all gates IDLE on the first check, 0 off-AC samples. Output below.
> 1. Verify B1 from status fields only, and now do the input-hash comparison from t00/INPUTS.json (that field only).
> 2. Prepare the B2 approval and commands bound to B1's terminal, with the disk check. Do not open any B1 outputs beyond status fields; no p*, gains or losses before the analysis.
> Stop for my approval.

## As recorded

1. Run B1 was approved and run by the owner. The assistant stayed off D: from the approval until the owner reported back.
2. NOT_OVERFIT stays as frozen: per width, across the ten draws.
3. The input-hash field of Run A's `t00/INPUTS.json`, and nothing else in that file, may be read for the comparison with the real-engine check.
4. Verify B1 from status fields only. Open no B1 output beyond them: no p\*, gains or losses before the analysis.
5. Prepare the B2 approval and commands, bound to B1's terminal, with the disk check, and stop for the owner's approval.

## How the terms are used

- **B1's status fields:** `TERMINAL.json`, which holds no loss; the activation's `OWNER_EXIT_RECEIPT.json`, `AUTHORIZATION.json` and `APPROVAL_RECORD.json`; hashes of the gate files and the power log; the battery percent in the power log; file names and sizes from a directory listing. No file under `d01/`–`d05/` is opened, and neither is B1's `BENCHMARK.json`.
- **The input-hash field:** `tensor_hashes`. The script parses the file and keeps only that field.
