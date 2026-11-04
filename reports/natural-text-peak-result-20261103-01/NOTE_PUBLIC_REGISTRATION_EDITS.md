# The public registration: what section 7f does not say

**Date:** 4 Nov 2026. **Why this note exists:** the owner's instruction, "If section 7f omits the PR edits, record them in a separate note next to the report." Section 7f omits them, because the layout was frozen before they were made. **`RESULT.md` is unchanged:** `b06169a860ae331060919f6df07c9c081cedf661c5c2407622c7c1e5618fbd13`, as `make_results_report.py` wrote it. Read this note with section 7f.

**Check:** `check_pr3_note.py` gives `PR3_NOTE_CHECK.json`. The GitHub responses are saved in `pr3-gh-snapshot-20261104/`, from read-only `gh` calls.

## Measured

| Event | Time (UTC) | Source |
|---|---|---|
| Pull request 3 created | 2026-11-03T16:11:57Z | `pr.json` |
| Merged, head `315a1f17e2a3d44c8e17a9386cdc851ac3c39122` | 2026-11-03T16:14:41Z | `pr.json` |
| Description last edited, by `rafli-hl` | 2026-11-04T03:52:23Z | `edits.json` |
| [Addendum comment](https://github.com/rafli-hl/sequence-weighting-research/pull/3#issuecomment-6622066939) posted, by `rafli-hl`, not edited since | 2026-11-04T03:52:24Z | `comments.json` |
| `ANALYSIS.json` written, 4 min 48 s after the comment | 2026-11-04T03:57:12Z | `RESULT.md`, from the local file |

**The description.** "testing whether the drop at 768 is a learning-rate artifact" is gone. It now reads "It speaks only to the two rates tested (3e-4 and 1e-4); 384 is not trained at 1e-4, and the best rate for 768 is not located." A paragraph states the timing. The earlier wording stays in GitHub's edit history.

**The comment.** It gives the layout's SHA-256, `af2fecbd…`, and the analysis's, `3b6e1f1c…`; both equal the local files. Its section order equals the headings of `RESULT.md`. It also states the correction to the description and the timing.

**No file changed.** The edit and the comment added no commit, so the 31 sealed files are as the earlier check found them.

## How to read section 7f with this

| Sentence in 7f | Reading now |
|---|---|
| "This layout is not in it." | Still true of the pull request's files. But the layout's hash and section order have been public since 03:52:24Z, before `ANALYSIS.json` was written. |
| "The wording there is looser than the protocol's. Its description says…" | True when the layout was frozen, and out of date now. The description gave the looser wording until 03:52:23Z and has given the narrower one since. |
| The timing, the losses already existing, and what is not public | Unchanged. |

## What this does not show

- **When the analysis ran.** Its time comes from a local file. The public record shows when the hash was posted, not when the analysis ran.
- **The layout's content.** Only its hash and section order are public, so an outside reader has no file to check that hash against.
- **The data collection.** As the description and section 7f both say, the registration came about 22 minutes after Run C2 ended.

## Also on the pull request: two comments from a review bot

The same read found two inline comments from `chatgpt-codex-connector[bot]`, both rated P2, posted at 2026-11-03T16:16:33Z, after the merge. The bot's summary lists its findings as unresolved. Neither changes a number or a label in `RESULT.md`, and I answered neither.

1. **`peak_analysis.py`, line 59: neither terminal is checked against the published hashes.** This is accurate about the sealed code, which only checks that Run C2 was bound to the Run C1 terminal it was given. For this report, `make_results_report.py` closed that gap: it refuses to run unless both terminals' hashes equal the approved ones, which equal the public `HASHES.json`. An outside reader cannot repeat this, because the run outputs are not public.
2. **`sealed-source/README.md`, line 25: "no activation or run of this study exists".** The sentence was true when the source was sealed. It conflicts with the published status, which says both runs had completed. The file is sealed and cannot change, so this is wording for the owner to answer or leave.
