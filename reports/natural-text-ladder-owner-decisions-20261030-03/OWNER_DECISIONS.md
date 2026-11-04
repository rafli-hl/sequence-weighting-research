# Owner ruling after attempt 1 of the one-rate run: revision 02, the final attempt

**Date:** 30 Oct 2026. The owner made this ruling after the outcome-blind failure report `reports/natural-text-onerate-failure-20261030-01/FAILURE_REPORT.md`. No outcome of the study (p*, gain or loss) has been opened.

**Applies to:**
- the one-rate ladder extension, source subject 4ca9833cad1152165552a8b2a42ea8f2b003f8cab4c39a3e3ab2105d2698d672;
- its attempt 1: run `work/runs/natural-text-onerate-20261030-01`, TERMINAL.json 0b994ed9fbb59717534f5e8e84a19d7f0cd8672101c4715496b790b2aa12d90c, FAILED in d06 on the per-draw work cap;
- owner decisions 20261030-01 and -02, which are left unchanged.

## Owner message (verbatim)

> Decision: option 1. I rule that a fresh run of all ten draws after this power failure is a new attempt, not a retry, under these pre-registered conditions:
> 1. Attempt 1's folders are preserved and never analysed for outcomes, including d01-d05. The new analysis reads only the new run.
> 2. This is the final attempt for this study. If it fails for any reason after a draw folder exists, the study closes as UNAVAILABLE with no further attempt. A stop before any draw folder exists is not counted, as with Run B.
> 3. The final report discloses attempt 1, its cause as recorded in FAILURE_REPORT.md, and that its outputs were never analysed.
> Changes for revision 02: the power gate as you proposed (refuse to start on battery; check AC before every draw, waiting and rechecking up to 30 minutes, then stop), plus a power-source and power-plan log every few seconds during the run. Science, seeds, primaries, analysis and time cap unchanged. Fixture tests, one scoped review of only these changes, then stop for my approval with hashes and commands.
> I commit to keeping the charger plugged in, the lid open and the laptop in Turbo or Performance mode for the whole run.

## Decisions as recorded

1. **Revision 02 is a new attempt, not a retry.** It reruns all ten draws from scratch in new folders.
2. **Attempt 1 is preserved and never analysed** for outcomes, including d01–d05. The analysis reads only the revision 02 run.
3. **Revision 02 is the final attempt for this study.**
   - **Counted:** a failure for any reason after a draw folder (d01–d10) exists in the run folder closes the study as UNAVAILABLE, with no further attempt.
   - **Not counted:** a stop before any draw folder exists, as with Run B (owner decisions 20261029-02 and -03: the draw-folder test). A new attempt after such a stop needs new versioned source, the scoped review and a new approval, with the science unchanged.
4. **Disclosure:** the final report discloses attempt 1, its cause as recorded in FAILURE_REPORT.md, and that its outputs were never analysed.
5. **Changes for revision 02, all operational:**
   - **The power gate.** The owner script refuses to start on battery, claiming nothing. Before every draw it checks AC power: on battery it waits and rechecks for up to 30 minutes, then stops.
   - **The power log.** The power source and the active power plan are logged every few seconds while the run goes on.
6. **Unchanged:** the science, the seeds, the primaries, the analysis and the time cap.
7. **Process:** fixture tests, one scoped review of only these changes, then stop for the owner's approval with hashes and commands.
8. **Owner commitment:** the charger stays plugged in, the lid stays open, and the laptop stays in Turbo or Performance mode for the whole run.
