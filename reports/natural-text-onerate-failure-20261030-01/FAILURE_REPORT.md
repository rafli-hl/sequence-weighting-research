# One-rate ladder run, attempt 1: failure report (outcome-blind)

**Date:** 30 Oct 2026. All times are local (SE Asia Standard Time, UTC+7).

**Run:** `work/runs/natural-text-onerate-20261030-01`, activation `work/natural-text-onerate-activation-20261030-01`. Approval OWNER-20261030-ONERATE-01, subject 4ca9833c…

**Status: FAILED in d06.** The owner receipt shows exit 1 and 6,724.1 s; TERMINAL.json is 0b994ed9fbb59717534f5e8e84a19d7f0cd8672101c4715496b790b2aa12d90c, and the receipt binds it. The ladder top was 768. Step 3, the analysis, was not run.

## Owner instruction (verbatim)

> The one-rate run FAILED in d06: exit 1, 6724.1 s, terminal 0b994ed9fbb59717534f5e8e84a19d7f0cd8672101c4715496b790b2aa12d90c, ladder top 768. I did not run step 3. Output below.
> Diagnose read-only and outcome-blind, as with attempt 1 of Run B:
> 1. Change, move or delete nothing in the activation or run folders. Run, build or retry nothing.
> 2. Read only TERMINAL.json error fields, OWNER_PROGRESS.log, GPU check files, stage status and timing fields, and guard and memory records. Do not open, print or compute any p*, gains, or training or validation losses from d01-d06.
> 3. Report: which width in d06 failed and when; the exact error (time cap, 2.5 GiB guard, CUDA out of memory, WSL or other); per-draw durations against the benchmark projection; the GPU readings, including why d01 needed two checks; any Windows-side cause you can find (GPU processes, sleep, power source, Windows Update); and whether every model file was recorded and deleted.
> 4. Give the status under the protocol and options for what comes next, with their pre-registration consequences. Build nothing; stop for my decision.
>
> Owner information: I unplugged the charger during the run, at roughly 16:00. Check whether the records support this as the cause: Windows power-source events (System log, Kernel-Power and battery events, or powercfg data), and whether draw or trajectory speed dropped after that time compared with earlier draws and the probe.
> If confirmed, include in the options a power gate for any new attempt: the owner script refuses to start on battery, and checks AC power before every draw, waiting and then stopping like the GPU gate.

No output followed "Output below".

## What was read

**Read:**
- TERMINAL.json: status, error, active stage, elapsed time, ladder, peaks, the stage receipts it holds, and the states deleted on failure;
- the per-draw receipts and `STATES_DELETED.json` (paths, sizes, hashes);
- BENCHMARK.json: timing, memory, ladder, cap and states;
- the GPU check files, OWNER_PROGRESS.log and the owner receipt;
- the modification times (not the contents) of the per-draw files;
- the Windows System log;
- `powercfg /batteryreport`.

**Not opened:** any `record.json`, `PRETRAINED.json`, `INPUTS.json`, arrays file or worker log. No p*, gain or loss was opened, printed or computed.

**Nothing was changed** in the activation or run folders.

Every number below comes from `DIAGNOSIS.json` (`diagnose.py` c4907d83…), `WINDOWS_POWER_EVENTS.json` (e9504ea4…) or `BATTERY_REPORT_20261030.html` (ca421b21…), all in this folder.

## Measured

### The failure

| Item | Value |
|---|---|
| Error | **TimeoutError "Original deadline exhausted"**: the per-draw work cap. It was not the 2.5 GiB guard, CUDA out of memory, WSL or the 6 h deadline (6,562.6 s elapsed). |
| Cap | 1,377 s per draw, from the run's own benchmark projection of 1,005.1 s per draw: ceil(1.25 × 1,005.1 + 120). |
| Draw and width | d06 started at 15:00:05. The cap was reached at about **15:23:02**, during the **512 adaptation**. It had started at 15:19:14, after the 768 adaptation was written, and had run about 228 s; in d01–d05 the 512 adaptation took 250–269 s. 96 and 64 had not started. |
| Memory | Not involved. The peak sampled device memory was 2,388,446,412 B (2.2244 GiB) in every draw, below the 2.25 GiB limit and the 2.5 GiB guard. The worker RSS was 1.93 GiB. |
| Exit | The worker recorded the exception and wrote TERMINAL.json at 15:23:22. The owner script observed the exit (exit 1) and wrote the FAILED receipt. |

### Per-draw durations

From the receipts and the file times. Projection: 1,005.1 s per draw, from the run's own benchmark.

| Draw | Work seconds | / projection | Pre-train 768 | Pre-train 512 | Adapt 768 | Adapt 512 | Adapt 96 | Adapt 64 |
|---|---|---|---|---|---|---|---|---|
| d01 | 1,008.6 | 1.003 | 75 | 40 | 499 | 263 | 68 | 68 |
| d02 | 1,011.9 | 1.007 | 81 | 43 | 515 | 269 | 66 | 58 |
| d03 | 993.6 | 0.989 | 80 | 42 | 499 | 258 | 69 | 63 |
| d04 | 944.3 | 0.939 | 78 | 41 | 479 | 250 | 67 | 57 |
| d05 | 972.2 | 0.967 | 78 | 42 | 500 | 259 | 67 | 63 |
| d06 | cap 1,377 | — | 79 | 42 | **1,028** | stopped | — | — |

- **d06's pre-training was normal.** The 768 adaptation took **2.06 ×** the d01–d05 mean (498.3 s; range 478.8–515.1).
- **The benchmark and the probe were on AC.** The run's benchmark gave 0.1340 s per update at 768; the probe gave 0.1341 s.

### Windows side

| Time | Record | Event |
|---|---|---|
| 10:44:56 | Kernel-Power 105 | AC online. It is the last power-source change before the run, so the probe (about 11:27) and d01–d05 ran on AC. |
| 13:31:23 | Pre-start GPU check | IDLE: mean utilization 3.1%, 510–536 MiB used |
| **15:04:47** | **Kernel-Power 105** | **AcOnline=false.** This is the only power-source change during the run, with 23,685 of 29,711 mWh. It came **4 min 42 s into d06** and 2 min 41 s into its 768 adaptation. |
| 15:04:50 | UserModePowerService 12 | ASUS Armoury Crate switched the power scheme from {6fecc5ae…} **Turbo** to {64a64f24…} **Silent**. |
| 15:08:51 | Kernel-Power 506 | **LidOpenState=false**: the lid was closed, and the system entered Modern Standby on battery with 19,819 mWh. |
| 15:10:22–23 | WindowsUpdateClient 43, 20 | A store-app update (ASUS PC Assistant) started and failed within 1 s. |
| 15:21:19 | Kernel-Power 507 | Standby exit, the lid opened, still on battery with 7,288 mWh. Standby lasted 748 s, and SleepEntered=false: the system was not asleep. |
| 15:23:22 | Run | TERMINAL.json written: the run had ended. |
| 15:24:34–15:24:56 | Kernel-Power 506, 507 | The lid was closed briefly. |
| 15:26:42–15:27:01 | Battery report; Kernel-Power 109, 577 | Suspended or shutdown transition at 12% battery, after the run. |
| 19:41:15 | Battery report | AC back. |

The battery report gives the same sequence. It shows Active on AC from 11:27:24, Active on Battery from 15:04:50 at 80%, Connected standby from 15:08:52 at 67%, Active from 15:21:19 at 25%, and Suspended from 15:26:42 at 12%.

### GPU checks (Windows nvidia-smi)

- **Before start:** IDLE.
- **Before d02–d06:** IDLE on the first check, at 0–0.5% mean utilization, with 358–708 MiB used (recorded, not gated).
- **The request records:** the worker's own WSL-side device use, as each request records it, was 866 MiB before every draw.
- **d01 needed two checks:**
  - The first began at 13:33:24, 0.4 s after the benchmark finished, and read **BUSY**: mean 23.2%, single readings 3–54%, 559–630 MiB.
  - The recheck 72.7 s later read IDLE: 0.3%, 429–434 MiB.
  - The records do not say which process used the GPU. Two candidates are work left over from the end of the benchmark, or a Windows-side app.
  - The wait was outside the draw's work cap and had no effect on the failure.

### Model files

**Every model file was recorded by sha256 and size and then deleted:**
- the benchmark's 12 states (643,289,136 B), which were also released from the ledger;
- 4 states for each of d01–d05;
- d06's 4 states, deleted on failure: 768, 512, and the copies of 96 and 64, 214,429,712 B in all.

That is 36 files and 1,929,867,408 B, with 0 errors and no `.pt` or `.pt.part` left. The run folder holds 91 files (2.2 MB).

## Interpretation (not a measurement)

**The records support the unplugged charger as the cause.** The time recorded is **15:04:47**, not about 16:00.
- d01–d05 and d06's pre-training ran at the benchmark's speed on AC.
- The slowdown appears only after the power-source change. Then the Silent scheme came on, and from 15:08:51 the lid was closed in Modern Standby.

**How much slower.** If the first 161 s of d06's 768 adaptation ran at the d01–d05 speed (about 32% of 498 s), the remaining work, about 337 s at that speed, took about 867 s, roughly **2.6 × slower**. File times cannot separate the effect of battery with the Silent scheme from that of Modern Standby. At the d01–d05 speed, d06 would have taken about 1,000 s against its 1,377 s cap.

**Other causes.** No other cause is visible: no GPU app was seen at the before-draw checks, there was no sleep, no WSL error and no memory event. The store-app update attempt lasted 1 s.

**What a gate can and cannot do.** A power check before each draw would not have prevented this failure, because the unplugging came 4 min 42 s *into* d06. It would prevent a draw from starting on battery.

## Status under the protocol

- **Primaries UNAVAILABLE.** PROTOCOL §10 says any failure after the start-up benchmark ends the run FAILED and makes the primaries UNAVAILABLE.
- **No retry and no resume.** This follows from §10's fail-closed rule and from the approval text.
- **Analysis only by owner decision.** Under the approval text, a FAILED run "is not analysed without my decision".
- **Never opened:** the per-sequence outputs of d01–d05, and d06's 768 trajectory.

## Options (for the owner's decision; nothing is built)

1. **A new attempt, revision 02, with a power gate.**
   - **Ruling:** the owner rules it a new attempt, not a retry, as for Run B's revision 05.
   - **What runs:** all ten draws from scratch in new -02 folders. Attempt 1 is preserved and never analysed, and the report discloses it.
   - **Unchanged:** the science, seeds, draws, primaries, analysis, start-up fallback and cap formula.
   - **Operational additions:**
     - **Power gate (owner request):** the owner script refuses to start on battery, and claims nothing. Before every draw it checks AC power: on battery it waits and rechecks for up to 30 minutes, then stops with a clear status, for example POWER_NOT_AC_30_MIN. Every check is recorded, as the GPU gate does. It can share the existing before-draw request, so the worker needs no new step.
     - **Recommended:** the owner script also records the AC state and the active power scheme every few seconds while the worker runs. Any change goes to the progress log and the receipt. A mid-draw unplug, as here, would then be visible in the receipt without searching the event log.
     - **Owner commitments:** plugged in and lid open for the whole run. Optionally, the pre-start check records the lid-close action and the power scheme (Turbo on AC). It would not change them.
   - **Pre-registration consequence:** outcome-blindness holds, because no outcome of this study has been opened. The rerun repeats the same computations on the same draws.
   - **Cost:** about 2.7 h of run time, plus preparation: the owner-script change, fixtures, one scoped review and approval.
2. **Resume:** keep attempt 1's d01–d05 and run d06–d10 in a new run. Its consequences:
   - It contradicts the pre-registered no-resume rule and the approval text.
   - The analysis would need to read two runs (a code change and review).
   - It stays outcome-blind, but it is a disclosed deviation.
   - It saves about 1.4 h.
3. **Analyse attempt 1 descriptively** (d01–d05 only; primaries UNAVAILABLE). This opens those outcomes, so no later attempt on these draws could be outcome-blind for 64, 96, 512 or 768. In effect it ends the R1 line.
4. **Close the study as UNAVAILABLE**, without analysis.

**Optional with option 1, not recommended:** raise the per-draw cap to the formula's maximum for ten draws (2,010 s, about 2.0 × the projection). This changes a frozen operational rule. It might have survived a slowdown like this one, but that is not certain. The power gate addresses the cause instead.

**Recommendation:** option 1, with the power gate and the AC recording, and the cap unchanged.
