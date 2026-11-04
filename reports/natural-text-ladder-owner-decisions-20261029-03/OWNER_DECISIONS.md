# Addendum to the ruling on failures before d01: natural-text capacity ladder, revision 05

**Date:** 29 Oct 2026. The owner made this addendum while Run B was in progress and before any outcome existed.

**Applies to:**
- source subject 2ac27fe79e699805cd02087c13abd27c703c5adf937c0d2ebe2e2e0f2faf401d (revision 05, the second and final attempt);
- activation B, approval id OWNER-20261029-TEXT-B-02 (approval record sha256 b351b65f16ac4ad4dd6fd572e6b74433823f3144c1f338500e03e9b18ebeb9fb);
- `reports/natural-text-ladder-owner-decisions-20261029-01/OWNER_DECISIONS.md`, sha256 7225fec3241ecf7d4bfe3b550e8c0699307caeb242d725a4fd873e2d98f8f6b3;
- `reports/natural-text-ladder-owner-decisions-20261029-02/OWNER_DECISIONS.md`, sha256 49d05fcef779287ffaa59e83c67b73c05941d107d862ec76e3e46422e21aa3ba.

Both earlier records are left unchanged. This addendum closes the reading point in the second record (`-02`): what happens if the worker never writes `TERMINAL.json`. No sealed file is changed. To write this record, the assistant opened nothing in the run folder, nor any progress log or GPU check record.

## Owner addendum (verbatim)

> Closing the gap now, still before any outcome: if TERMINAL.json is missing or unreadable, the draw-folder test alone decides. No d01-d10 folder means the stop is covered and not the failed attempt; any draw folder means it is the final attempt. Record this as an addendum in a new decisions file.

## Decision

**If `TERMINAL.json` is missing or unreadable, the draw-folder test alone decides:**
- **No `d01` to `d10` folder in the run folder:** the stop is covered and is not the failed attempt.
- **Any draw folder:** the run is the final attempt. A failure then closes the natural-text ladder as UNAVAILABLE, and the failed run is not analysed.

If `TERMINAL.json` is present and readable, the two-part test of the second record (`-02`) applies unchanged. Everything else in the two earlier records stands.
