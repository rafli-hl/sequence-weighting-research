# Owner decisions on Amendment 01 and Approval 2: natural-text capacity ladder

**Date:** 28 Oct 2026.

**Applies to:**
- source subject 90e3f3ef1c7dcad6e4be54e5bf5ac0eab2f7feb9de2121aa2ed7ce658c8beded;
- builder 7c9da3f42a5ca042b26609a91f89ffa5a4c5ec85f585527427f81278051d7f45;
- `reports/natural-text-ladder-amendment-20261028-01/AMENDMENT_01.md`, sha256 adc19ccce9b02d959fb94a938b2e4371e09dc98e8be4f527014a6e1a8a789f22.

The amendment file is left unchanged; this separate record does not alter its hash.

## Owner message (verbatim)

> Amendment 01 accepted as written, including your three additions; the sensitivity stays the full ten-draw rerun at 3e-5. Approval 2 granted with the text below; I am running the commands now.

No approval text followed the message as it reached the assistant. The authoritative copy is the `user_text` field that `build_text_activation.py --mode B` writes into the approval record of activation B.

## Decisions

1. **Amendment 01 is accepted as written** (sha256 adc19ccc…). This includes the three additions made in drafting:
   - a point whose break is at 96 may also have its fall partly due to the rate change;
   - the known limitation of the sensitivity: at 3e-5, widths 64 and 96 reached their lowest validation NLL at E32 on t00;
   - the design is fixed as below.
2. **The sensitivity design is the full ten-draw rerun at 3e-5 for all six widths.** The cheaper variant was not chosen: rerunning only widths 64 and 96 and reusing Run B's 128–384.

   The planning estimate is projected 1.95 h, worst case 3.19 h and about 1.13 GiB (`SENSITIVITY_ESTIMATE.json`, ade7543b…). The sensitivity remains conditional on Primary B being INTERIOR_PEAK, and needs its own source, tests, review and approval.
3. **Approval 2 is granted.** The owner runs:
   - the build of activation B (approval id OWNER-20261028-TEXT-B-01);
   - the single Run B.

   Each runs once, with no retries. A start-up fallback or any failure stops the work until a new approval. The assistant runs neither command.
