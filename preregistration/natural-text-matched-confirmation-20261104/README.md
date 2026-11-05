# Pre-registration: matched-progress confirmation on fresh WikiText-103 draws (N7, 4 November 2026)

This folder publishes the frozen protocol, the sealed code and the seeds of one confirmatory study **before any of its training runs**. Its purpose is to let anyone check that the test, the decision rules and the readings were fixed before any result existed.

## Status when published

- **No study data exists.** No activation has been built and no run of this study has started. No model has seen any of these draws, and no loss, gain or p\* of this study exists.
- **The seeds have been drawn,** once, by the owner, and the source is sealed and disabled: subject `7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56`. The corpus and the assignment of its articles to the draws exist, and this study has not trained on them.
- **The real-engine check passed,** run by the owner on real Torch, on synthetic tokens with the real seed rows. No corpus file was read, and no study loss was computed. Its smoke test trained tiny models on synthetic tokens with test seeds, and its receipts hold p\* on synthetic gains, which is not a study result (`engine-check-result/RESULT.md`).
- **The activation builder refuses until the merge commit of this registration is recorded in it.** The result will be added to this repository separately, with no change to anything in this folder.
- **`sealed-source/README.md` says that no real-engine check has happened.** That was true when the source was sealed, and the check came after. The line cannot change without moving the subject, and a moved subject would need a new check and a new registration.

## The question

The hypothesis is post hoc, and these draws are there to test it. A reanalysis of the peak confirmation (N6) found that, at learning rate 1e-4 after 3 epochs, p\* at width 512 exceeded p\* at width 768 when 768 was read at the training NLL that 512 reaches at epoch 3 (+0.0132 [+0.0106, +0.0158], 6/6), although at fixed updates 768 was higher (−0.0050 [−0.0090, −0.0010]). That figure was interpolated between epochs 2 and 3, so N6 and its draws cannot confirm it. This study asks the same question on draws never used, with readouts dense enough to replace most of the interpolation.

## Design

| | |
|---|---|
| **Corpus** | WikiText-103 (manifest `be911db7…`), with every article and text used by the earlier natural-text studies removed |
| **Draws** | Six fresh draws, m01–m06, of 16,384 sequences each. Corpus draws are the replication unit |
| **Models** | Depth 4, 4 heads, context 128, 4,096-token vocabulary; widths 512 and 768 |
| **Rates** | 1e-4 (primary) and 3e-4 (secondary), both fixed from earlier selection on validation NLL. p\* enters neither |
| **Training** | Each width pre-trained uniformly to E0, then weighted adaptation for 3.5 epochs (3,584 updates), with a width's arms sharing one E0 and every arm of a draw sharing its tokens, weights and batch order |
| **Readouts** | E0, E0.25, E0.5, E1, E2, E2.25, E2.5, E2.75, E3, E3.25, E3.5 |
| **Matching** | 768's p\* is read along its own path from E2 to E3.5, by linear interpolation, at the value 512 reaches at E3. A target outside that path makes the draw unavailable for that statistic |
| **Runs** | Run M1 (m01–m03), then Run M2 (m04–m06) |

## The primary

**P1, at 1e-4:** D4m_train = p\*(512, E3) − p\*(768, matched on training NLL), per draw, with a 95% t interval over the available draws (df = draws − 1).

| Label | Rule |
|---|---|
| **REVERSAL_CONFIRMED** | The interval is entirely above 0 |
| **NOT_REVERSED** | The interval is entirely below 0 |
| **INCONCLUSIVE** | Anything else |
| **UNAVAILABLE** | Fewer than 5 draws available |

## The fixed sequence

**P1 → S1 → S3 → S4 → S5 → S2.** Each step is read as a confirmation only while every earlier step is confirmed. A later step is still computed and reported, and it is labelled NOT_READ.

| Step | Statistic | Confirmed if the interval is |
|---|---|---|
| **P1** | D4m_train: 512 − 768 at 1e-4, matched on training NLL | entirely above 0 |
| **S1** | D4m on the gap | entirely above 0 |
| **S3** | Fixed-update D4 at E3, at 1e-4 | entirely below 0 |
| **S4** | D2m_train: 512 − 768 at 3e-4, matched on training NLL | entirely above 0 |
| **S5** | Fixed-update D2 at E3, at 3e-4 | entirely above 0 |
| **S2** | D4m on validation NLL | entirely above 0 |

The readings of every outcome, including the four forms of REVERSAL_CONFIRMED, are fixed in `sealed-source/PROTOCOL.md`, section 7. No reading claims a mechanism, and nothing about Jane Street's scale follows. Models are selected on validation NLL only, gains stay signed, and undefined fits stay undefined.

## If a run fails

Fixed in advance, in `sealed-source/PROTOCOL.md` and the owner's decisions:
- a FAILED Run M1 admits Run M2 if at least 2 of its draws completed, counted from operational records only; with fewer, the study closes UNAVAILABLE;
- if either run did not complete, the completed draws are read only if P1 has at least 5 available draws; otherwise nothing is read, no value is reported, and the study closes UNAVAILABLE;
- a run that leaves no terminal counts for nothing, whatever is on disk: Run M2 is not admitted after such a Run M1, the analysis is not run, and the study closes UNAVAILABLE;
- a stop before any stage folder exists is not counted and not analysed, and the next step is the owner's. A re-run would need a new run folder, and so a new revision, a new real-engine check and a new registration;
- if the manipulation check fails, the label stands and its reading is prefixed, with no re-run, data increase or replacement draw as a remedy.

## The owner's decisions

`owner-decisions/OWNER_DECISIONS.md` is bound in the seal. **The owner's later answers are in `owner-decisions/OWNER_DECISIONS_ADDENDUM.md`, SHA-256 `c68095be0071e8aae9ead3ddce8f77f2edb765b7a4963d615c819d70150d7a4b`.** It was written after the seed draw, and it is not bound in the seal, because the seal after the draw changed only the pins. This file names it by that hash instead. The owner's later messages are in `owner-decisions/OWNER_DECISIONS_ADDENDUM-02.md`.

## A limitation: token-level overlaps were not measured

Exact token sequences and 64-token runs were not measured across m01–m06, the earlier studies' draws, the validation set and the pool, because the draw step could open only the corpus manifest. **So how far token runs recur across these draws is not known.** For scale, N6's groups had 64-token runs recurring in another fresh group at a mean of 0.15%; that is N6's figure and not a measurement of these draws. Every draw also shares the validation set, the pool and the tokenizer with the others. Draws are treated as independent in every interval, and these figures do not measure how far that is true (`seed-registry/DISCLOSURE_FIGURES.md`, "Not measured"; `sealed-source/PROTOCOL.md`, section 12).

## Tied weights

Real Torch counted 3, 4, 1, 1, 1, 1 tied values in m01–m06, within the limit of 16. The draw's numpy disclosure counted 0 for m03 and the same for the other five. The weights used are divided by Torch's mean, so the real-Torch counts are the ones the results report must carry.

## Contents

| Path | What it is |
|---|---|
| `sealed-source/` | The sealed study source. `SOURCE_SUBJECT.json` lists every file's SHA-256, and its own SHA-256 is the source subject |
| `sealed-source/PROTOCOL.md` | Design, primary, sequence, readings, power, limitations and failure policy. Its status line says when it was frozen |
| `seed-registry/` | The owner-run draw: registry, frozen policy, exclusions, entropy record, partition, post-draw checks, disclosure and receipt |
| `owner-decisions/` | The owner's decisions and the two addenda |
| `engine-check-result/` | The result report, the two receipts, the two guard records, the verification and the owner's approval |
| `HASHES.json` | Hashes binding all of this, including files that are not published here |

**Not included, by design:** the corpus, which is not redistributed here. The real-engine check's scripts, the builder, the owner's console output and the verification script are named by hash in `HASHES.json`; the last two hold local paths of the research machine, which is why `RESULT.md` names files that are not in this folder. Other records bound in the seal are named by hash in `sealed-source/SOURCE_SUBJECT.json`. The review records, including the one `PROTOCOL.md` section 6 cites for its simulated figures, are named by hash in `HASHES.json`.

## How to verify

```sh
sha256sum sealed-source/SOURCE_SUBJECT.json   # 7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56
sha256sum owner-decisions/OWNER_DECISIONS_ADDENDUM.md   # c68095be0071e8aae9ead3ddce8f77f2edb765b7a4963d615c819d70150d7a4b
python3 - <<'PY'
import json, hashlib, pathlib
s = pathlib.Path('sealed-source'); d = json.loads((s / 'SOURCE_SUBJECT.json').read_text())
bad = [f['path'] for f in d['files'] if hashlib.sha256((s / f['path']).read_bytes()).hexdigest() != f['sha256']]
print('mismatched files:', bad)
PY
```

## Scope and limits

Small models (depth 4, 16.9 M and 34.7 M parameters), one corpus family, constant learning rates, two widths, and no claim about Jane Street's scale. The hypothesis is post hoc, so a confirmation here is of that hypothesis on these draws, and it does not show a capacity mechanism. Paths inside the code refer to the original research machine and are not portable entry points.
