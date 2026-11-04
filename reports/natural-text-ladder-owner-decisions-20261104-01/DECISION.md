# Owner decisions after the adversarial review: the four proposals, the search incident, and closure

**Date:** 4 Nov 2026. **Applies to:** `reports/adversarial-review-response-20261104-01/RESPONSE.md` (`d265bbffca504e7fad7cfba4864c2c338511bca0af7cfdaff5c631aa88600523`), which is unchanged.

## First owner message (verbatim)

> Accept all four of your proposals (§3.2 REANALYSIS with the uniform-arm limitation; §3.3 and §3.12 CONCEDE; the N3 label wording; the D3 bullet under claim 5).
>
> Wording cleanup only. Do not run any experiment or verify_*/check_* script, and do not edit any sealed file or anything under reports/ except as listed.
> 1. RESEARCH_GOAL.md: fix lines ~444, ~479 and ~484 (and any other place in the file) that still say "reproduced in direction", call N4's P3 a separate confirmation, read CAPACITY_BEYOND_MEMORIZATION as capacity, read RATE_DEPENDENT causally, or link N6 to Jane Street's finding (1). Use the wording in RESPONSE.md §5. Where a passage is a dated historical record, leave the text and add "(superseded 4 Nov 2026; see RESPONSE.md §5)" instead of rewriting it.
> 2. HANDOFF.md, INDEX.md, NEXT_EXPERIMENT.md: same rule. Add a link to RESPONSE.md in each. In NEXT_EXPERIMENT.md, record that the experiments are closed and that the only optional future run is the denser-readout run (E2.25–E3.5, 1e-4 arms, ~2–3 h), and that nothing is authorized.
> 3. Search the repo (excluding work/*-source-*, sealed reports, and the review folder) for any other occurrence of "Reproduced in direction", "CAPACITY_BEYOND_MEMORIZATION" used as a finding, or "rate-dependent" used causally; list each with file:line and what you did.
> 4. Report SHA-256 of every changed file and git status. Do not commit.

## Second owner message (verbatim)

> Owner decisions, 4 Nov 2026. Do not run any experiment or verify_*/check_* script. Do not open, read or search anything under work/runs/ (in particular never work/runs/natural-text-onerate-20261030-01 or the N1 Run B attempt-1 folder); exclude work/runs/ from every search from now on.
>
> 1. docs/RESEARCH_ACCOUNT_2026-10-27.md line 210: add the tag "(superseded 4 Nov 2026; see reports/adversarial-review-response-20261104-01/RESPONSE.md §5)". Leave the two drafts unchanged.
> 2. Create reports/natural-text-ladder-owner-decisions-20261104-01/DECISION.md recording, in the style of the earlier owner-decision files:
>    a. Acceptance of the four proposals in RESPONSE.md §1 (§3.2 REANALYSIS with the uniform-weight-arm limitation; §3.3 and §3.12 CONCEDE; the N3 label wording "MEMORIZATION_PREDICTIONS_MET, for the E4–E32 averages only; at E24 and E32 the by-epoch secondaries read TURNS_DOWN"; the D3 bullet under claim 5). RESPONSE.md (d265bbff…) is unchanged; this file is the record of acceptance.
>    b. The search incident: on 4 Nov the wording-cleanup search scanned text files in work/runs/natural-text-onerate-20261030-01 (attempt 1) for three wording phrases; it returned no lines, so no content was displayed. Owner ruling: no outcome information was exposed, since the phrases are unrelated to training outcomes and nothing matched; attempt 1 remains never analysed; future searches exclude work/runs/.
>    c. Closure: the experiments are closed. The only optional future run is the denser-readout run (E2.25–E3.5, 1e-4 arms, ~2–3 h); nothing is authorized. The final claims are RESPONSE.md §5; re-score 70/100 on the original scale.
> 3. Add one line to HANDOFF.md section 55 and INDEX.md linking to the new DECISION.md.
> 4. Report SHA-256 of every new or changed file and git status. Do not commit.

## As recorded

### a. The four proposals are accepted

`RESPONSE.md` section 1 still marks these as proposals, and it stays unchanged. **This file is the record of acceptance.**

1. **§3.2:** REANALYSIS, with the uniform-weight-arm limitation.
2. **§3.3:** CONCEDE.
3. **§3.12:** CONCEDE.
4. **The N3 label in §3.11, and the D3 bullet under claim 5.** The label's wording is "MEMORIZATION_PREDICTIONS_MET, for the E4–E32 averages only; at E24 and E32 the by-epoch secondaries read TURNS_DOWN".

### b. The search incident

**What happened:** on 4 Nov the wording-cleanup search scanned text files in `work/runs/natural-text-onerate-20261030-01` (attempt 1) for three wording phrases. It returned no lines, so no content was displayed.

**Owner ruling:**
- No outcome information was exposed, since the phrases are unrelated to training outcomes and nothing matched.
- Attempt 1 remains never analysed.
- Future searches exclude `work/runs/`.

### c. Closure

1. The experiments are closed.
2. The only optional future run is the denser-readout run (E2.25–E3.5, 1e-4 arms, about 2–3 h).
3. Nothing is authorized.
4. The final claims are `RESPONSE.md` section 5.
5. The re-score is 70/100 on the original scale.

## The tag on the research account

`docs/RESEARCH_ACCOUNT_2026-10-27.md` line 210 now carries the tag, and the two drafts are unchanged. Before the tag the file's SHA-256 was `f111a95eebc8b7cfc592d3f7fdb787c67d53028e34326cbe8224f64efdd7b1a9`. `docs/research-account-2026-10-27/ACCOUNT_CHECKS.json` names that hash as `account_sha256`, so it describes the text before the tag. That record is unchanged and its check was not re-run.

## Recorded by the assistant; not part of the owner's ruling

These facts come from this session's transcript, using its tool calls and the run-folder names in what they returned. Nothing under `work/runs/` was opened to establish them. They are recorded so that the ruling above can be read against the full scope, and the owner has not ruled on them.

**1. The incident's scan was wider than one folder.**
- **Calls:** one Grep and three runs of one Python scan; the first run stopped on an error. All were on 4 Nov.
- **Pattern:** the three phrases, plus `RATE_DEPENDENT` and "depends on the rate", ignoring case.
- **Reach:** text files across all of `work/runs/`, including N1 Run B's attempt 1 (`work/runs/natural-text-ladder-b-20261028-01`).
- **Returned:** no line from any folder under `work/runs/`.
- **File metadata:** two `find` calls over `work/` compared file times. One count of attempt 1's files gave 91, of which 58 have text-type extensions. These opened no file.

**2. Three earlier repo-wide content searches had no `work/runs/` exclusion.** Neither attempt-1 folder appears in what any of them returned.

| When (UTC) | Pattern | Files searched | Run folder in what it returned |
|---|---|---|---|
| 31 Oct 04:02 | `groups_possible\|groups possible\|max_groups` | `*.json` | `work/runs/natural-text-corpus-20261028-01`, one line; not an attempt-1 folder |
| 31 Oct 04:37 | `train-rows\.json\|text-assets\|wikitext` | `*.py`, `*.md` | None |
| 4 Nov 04:13 | `evidence[- ]chain` | `*.md`, `*.json`, `*.txt`, `*.csv` | None |

**3. Operational records of both attempts were read directly when each failed.**
- **N1 Run B attempt 1, 28 Oct:** `TERMINAL.json`, `d01-RECEIPT.json`, `BENCHMARK.json` and file listings.
- **One-rate attempt 1, 30 Oct:** `TERMINAL.json`, `BENCHMARK.json` and `STATES_DELETED.json` of d01–d05.
- **Disclosure:** the one-rate protocol, section 11, says "only the operational records listed in FAILURE_REPORT.md were read". N1 has its own failure report. This file did not compare either list with the reads above.
- **What was displayed:** a word count of those outputs finds no "loss", "NLL" or "p\*"; the word "train" does occur. This is a word count, not a review of the content.

## Owner ruling, addendum

**Date:** 4 Nov 2026.

1. **The ruling extends** to the wider 4 Nov scan (all of `work/runs/`, including `work/runs/natural-text-ladder-b-20261028-01`, and the extra terms `RATE_DEPENDENT` and "depends on the rate") and to the three earlier searches without a `work/runs/` exclusion (two on 31 Oct, one on 4 Nov). **Reason:** the search terms are unrelated to training outcomes, and no line was returned from either attempt-1 folder; the one line returned came from `work/runs/natural-text-corpus-20261028-01`, which is not an attempt-1 folder.
2. **The direct reads** of attempt-1 operational records on 28 and 30 Oct (`TERMINAL.json`, `BENCHMARK.json`, `d01-RECEIPT.json`, `STATES_DELETED.json`) are the failure diagnosis disclosed at the time: `reports/natural-text-ladder-run-b-failure-20261028-01/FAILURE_REPORT.md` (line 48: only file times and operational fields of `TERMINAL.json`, `BENCHMARK.json` and the receipts) and `reports/natural-text-onerate-failure-20261030-01/FAILURE_REPORT.md` (lines 26–34, including "Not opened: any record.json, PRETRAINED.json, INPUTS.json, arrays file or worker log"). They were within protocol and contain no outcome fields. Attempt 1 of both runs remains never analysed.
3. **`ACCOUNT_CHECKS.json`** keeps the pre-tag hash `f111a95e…` as a historical record; it is not re-run, and the tag on line 210 is the only change to the account since then.

### Assistant's note on item 2; not part of the ruling

The list under "Recorded by the assistant" above left out one read, which was the assistant's omission. Item 2 does not cover it, and the owner has not ruled on it.

- **Also read on 28 Oct:** the last 6,000 bytes of `WORKER_STDERR.log` and the last 2,000 bytes of `WORKER_STDOUT.log`, in `work/natural-text-ladder-activation-b-20261028-01`, which is not under `work/runs/`. N1's failure report does not mention them. The word count above includes this output.
- **Line 48's "only" describes `timing_table.py`,** not everything that was read. On 28 Oct `TERMINAL.json` and `d01-RECEIPT.json` were also printed whole.
- **The limit of the check:** "no outcome fields" could be compared only with what was displayed, by that word count. The files themselves were not reopened, under the rule on `work/runs/`.

## Owner ruling, second addendum

**Date:** 4 Nov 2026.

1. **Item 2 extends** to the 28 Oct reads of the last 6,000 bytes of `WORKER_STDERR.log` and the last 2,000 bytes of `WORKER_STDOUT.log` in `work/natural-text-ladder-activation-b-20261028-01`, and to `TERMINAL.json` and `d01-RECEIPT.json` being printed whole. **Reason:** the same failure diagnosis, before any ruling or analysis; the displayed output contained no "loss", "NLL" or "p\*" by word count; N1's results use attempt 2 only.
2. **Disclosure correction:** `reports/natural-text-ladder-run-b-failure-20261028-01/FAILURE_REPORT.md` did not list these reads. That report stays unchanged; this file is the correction of record, and any write-up citing N1's failure must cite this file too.
