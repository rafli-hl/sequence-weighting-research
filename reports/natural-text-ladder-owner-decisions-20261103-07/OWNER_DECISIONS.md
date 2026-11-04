# Owner approval and report of Run C2, the public pre-registration, and the instruction for the sealed analysis

**Date:** 3 Nov 2026. **Applies to:** `reports/natural-text-peak-c2-approval-20261103-01/REPORT.md`.

## First owner message (verbatim)

> I approve OWNER-20261103-PEAK-C2-01: one build by builder 026709dcc1fce8daa62c79a0734713c4c1588defc80831e4a65a6f2ae6219b89 and one Run C2 of the peak confirmation, c04 to c06, under source subject 0d9e8f9adee4544bd24550f43a09c309e935ec6816a90769e04625e764711e28, bound to Run C1 terminal 77988d64f5b0e97a75789270202a40f99b9ee0baf4714b847d31777c6149d360, run by me. One use, no retry. The sealed analysis needs my separate approval.

## Second owner message (verbatim)

> Run C2 COMPLETE: c04-c06, exit 0, 7,438.2 s, terminal d7dee4370e03bdafab3fcddec9d47484804da32eecc3358f85b64a86fd7cd205, 0 off-AC samples; c05's gate needed 3 checks. Output below. The protocol is now publicly pre-registered: https://github.com/rafli-hl/sequence-weighting-research/pull/3 (created 2026-11-03T16:11:57Z, before any analysis). Verify C2 from status fields only, then prepare the sealed-analysis approval with the results report layout frozen first. No p*, gains or losses before my approval.

The console output followed, and is kept unchanged in `reports/natural-text-peak-c2-result-20261103-01/OWNER_CONSOLE_OUTPUT.txt`.

## As recorded

1. Run C2 was approved, built and run by the owner, once. The assistant stayed off D: from the approval until the owner reported back.
2. The owner published the protocol at the link above, on their own initiative. The assistant did not publish anything.
3. Verify C2 from status fields only.
4. Prepare the approval of the sealed analysis, with the results report's layout frozen first.
5. No p\*, gains or losses before the owner's approval.

## How the terms are used

**C2's status fields,** as for C1: `TERMINAL.json`, which holds no loss; the activation's `OWNER_EXIT_RECEIPT.json`, `AUTHORIZATION.json`, `APPROVAL_RECORD.json` and `OWNER_PROGRESS.log`; the gate files, which hold GPU and power readings; the battery percent in the power log; file names and sizes from a directory listing. No file under `c04/`–`c06/` is opened, nor the `-RECEIPT.json` files, whose fields are in the terminal, nor C2's `BENCHMARK.json`.

**The layout:** the results report written after the analysis. Its order and wording are fixed before any outcome is opened, in a script that is frozen and bound by hash. The sealed analysis's own output is unchanged, since the source subject cannot change.
