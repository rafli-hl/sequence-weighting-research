# Owner decisions on revision 04: natural-text capacity ladder

**Date:** 28 Oct 2026.

**Applies to:**
- source subject 90e3f3ef1c7dcad6e4be54e5bf5ac0eab2f7feb9de2121aa2ed7ce658c8beded;
- builder `build_text_activation.py` 7c9da3f42a5ca042b26609a91f89ffa5a4c5ec85f585527427f81278051d7f45;
- PROTOCOL.md 530d962713b54cd87bbf2901ca93d318e538a24510072fe8ab8558b450b145f7.

This record is Markdown on purpose. The seed census in `text_registry.census` reads only `*.json` files, so this record cannot change the seed draw.

## Owner message (verbatim)

> Confirmed: I accept the 4,000-replicate re-measurement as the resolution of the 6.0% reading, and the extended UNAVAILABLE list. Approval 1 is granted with the text below; I am running the five commands now.

No approval text followed the message as it reached the assistant. The authoritative copy of the approval text is the `user_text` field that `build_text_activation.py --mode A` writes into the approval record of activation A.

## Decision 1: the 5% stop condition

The owner accepts the 4,000-replicate re-measurement as the resolution of the stop condition. The condition: stop if the null or epoch-mixing false-positive rate under correlated noise exceeds 5%.

The case is the null curve flat_then_drop_at_384, at sd 0.3 and ρ = 0.8. Its INTERIOR_PEAK rate, from three sources:
- `POWER_PRIMARY_B.json` (sha256 5d30d3945505225640eb5882b1bfa16191851533ff7ca7f1f8989c3d3f4fbfca): 24 of 400 replicates, 6.0%.
- `POWER_PRIMARY_B_REFINE.json` (sha256 2077feedfa3a9909463074eeec769a2734d5c551d7e87a2a6b2945a2a5907a80): 0.02625 at 4,000 replicates, 2.6%.
- The reviewer's independent estimate at 10,000 replicates, from `REVIEW_3.md` finding 9: 3.39%, with a 95% interval of about 3.0–3.7%.

The 400 and 4,000 figures were re-read from the files on 28 Oct 2026.

## Decision 2: the UNAVAILABLE list

The owner confirms the UNAVAILABLE list in PROTOCOL.md §9, including the items that go beyond the wording of the owner's rule (§11). The primaries are UNAVAILABLE if:
- Run A fails;
- the plan is UNAVAILABLE;
- Run B's start-up check finds even five draws over 6 h;
- Run B fails before or after its start-up check, other than through the fallback;
- B1 or B2 fails or stops; or
- a run ends without a TERMINAL.json.

## Approval 1

Approval 1 is granted, and **the owner runs the five commands**. The assistant ran none of them. The commands are as given in the approval request:
1. the corpus step;
2. the seed draw;
3. building activation A;
4. Run A;
5. the learning-rate selection and Run B plan.

Each runs once, with no retries. The owner stops at the first failure.
