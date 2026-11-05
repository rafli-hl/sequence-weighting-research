# Owner answers on N7: addendum to OWNER_DECISIONS.md

**Given on 4 Nov 2026, in three messages, before any output of the seed draw reached the assistant.** A fourth message reported the draw. This file was saved after that, because the owner told the assistant to stay off D: while the draw ran. `OWNER_DECISIONS.md` in this folder is bound in subject `1e96d8d8…` and is not edited. Where the messages differ, the later one replaces the earlier.

## The owner's first message, verbatim

> Owner answers, 4 Nov 2026 (record in reports/natural-text-ladder-owner-decisions-20261104-02/ as an addendum; no code change needed for 1–2):
> 1. A run killed with no terminal counts for nothing — keep as sealed.
> 2. A stop before any stage folder exists is not counted, not analysed, and left to the owner — confirmed.
> 3. M4: keep the real seed rows in engine_check.py. Its receipt must state that no corpus file was read and no study loss was computed.
> 4. Item 5 applied to either run: confirmed. Token-level overlaps: not measured; add this to the protocol's limitations in the post-draw pin revision, not now.
> I am running the seed draw now. Stay off D: until I paste the output.

## The owner's second message, verbatim

> On your three items: (1) Do not add an exception to the pin tool; keep the new seal strictly pins-only. Put the token-overlap limitation in the post-draw disclosure and in the public-registration README, and state "no study loss was computed" in the engine-check result report. engine_check.py stays unchanged. (2) The L3 fix is fine; report the new hashes. (3) Keep "no value reported" under the closure rule as sealed. The assistant verified on the laptop that SOURCE_SUBJECT.json (1e96d8d8…), run_seed_draw.py, post_draw_disclosure.py and the seed policy match your command, and that no draw exists yet. I am running the draw now.

## The owner's third message, verbatim

> Pin step authorized: after reading the draw output, apply the pins and re-seal, strictly pins-only. Name the addendum by its SHA-256 in the public-registration README. If DISCLOSURE_FIGURES.md does not state the token-overlap limitation, do not edit it; I'll state it in the README instead. Then report the new subject hash and stop before the real-engine check.

## The owner's fourth message, verbatim

> Draw output below: exit=0, all post-draw checks PASS. The assistant verified on the laptop that REGISTRY.json is bee578826fbdb5e66fbb36d577e45929af756e05b12b62d6cd141b4b5da7ea64 and PARTITION.json is b7eb3d3ba200b86046c6d731d2f0200ff657b6c2aaeebd43423cd4aec530e33b, and that DISCLOSURE_FIGURES.md already states the token-overlap limitation (line 29). Proceed with your four steps, then stop before the real-engine check.

## As recorded

1. **A run with no terminal:** counts for nothing, as sealed.
2. **A stop before any stage folder:** not counted, not analysed, left to the owner, as sealed.
3. **The real-engine check:** the six real seed rows stay. The check's code is unchanged apart from the `EXPECTED_SUBJECT` pin that the pin tool writes. "No study loss was computed" goes in the engine-check result report, which replaces the first message's receipt requirement.
4. **Either run failing:** the closure applies to either run, as sealed. A closed analysis reports no value, as sealed.
5. **Token-level overlaps:** not measured. The limitation goes in the post-draw disclosure and in the public-registration README, which replaces the first message's protocol change. `DISCLOSURE_FIGURES.md` line 29 states that exact token sequences and 64-token runs were not measured, so that file was not edited.
6. **The pin tool:** no exception. The new seal is strictly pins-only, so this addendum is not bound in it. The public-registration README names it by its SHA-256.
7. **The L3 correction in `review-02/REVIEW_FOLLOWUP.md`:** accepted, with the new hashes to be reported.
8. **The pin step:** authorized. The assistant reports the new subject hash and stops before the real-engine check.

**The laptop checks in the second and fourth messages** were not made in the assistant's session that recorded this file. That session did not touch D: while the draw was running. Afterwards it hashed `REGISTRY.json` and `PARTITION.json` and read `DISCLOSURE_FIGURES.md` itself, and these agree with the fourth message.
