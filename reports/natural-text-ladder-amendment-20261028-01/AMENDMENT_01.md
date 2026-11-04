# Amendment 01 (outcome-blind): natural-text capacity ladder

**Recorded 28 Oct 2026, before Run B, at the owner's request.** It applies to source subject 90e3f3ef1c7dcad6e4be54e5bf5ac0eab2f7feb9de2121aa2ed7ce658c8beded. It supplements PROTOCOL.md §8 and §10 (530d962713b54cd87bbf2901ca93d318e538a24510072fe8ab8558b450b145f7) and does not edit them.

It changes no decision rule, label or analysis code, and no data, seed, limit or source file. The sealed source and the pinned builder (7c9da3f42a5ca042b26609a91f89ffa5a4c5ec85f585527427f81278051d7f45) are unchanged. Approval 2 binds this file through its sha256 in the approval text.

**What had been seen when it was written:** only the Approval 1 outputs:
- the corpus manifest (72daa1e1…);
- the seed registry (8ce7d597…);
- Run A on the tuning group t00 (terminal 6c6e7fe2…, COMPLETE);
- its learning-rate selection and Run B plan (`LR_SELECTION.json`, cb059387…).

Run B does not exist. No p* has been computed on any group: `select_lr.py` reads only validation rows (PROTOCOL §5), and Run A's JSON records contain no p* field.

**Basis** (`LR_SELECTION.json`: lowest validation NLL over E1–E32; grid {3e-5, 1e-4, 3e-4}, edges accepted and not extended):

| Width | 64 | 96 | 128 | 192 | 256 | 384 |
|---|---|---|---|---|---|---|
| Selected rate | 3e-4 (top edge) | 1e-4 | 3e-5 (bottom edge) | 3e-5 (bottom edge) | 3e-5 (bottom edge) | 3e-5 (bottom edge) |

## 1. Interpretation note (owner)

Five of six widths selected an edge rate: 64 at the top, and 128–384 at the bottom. The rate drops tenfold between 64 and 128, inside the rise segment.

**If Primary B is INTERIOR_PEAK or RISE_AND_FALL_NOT_WITHIN_POINTS,** the report's reading under §8 and its limitations under §10 must state that **the rise may be partly due to the learning-rate change, not only width**.

Precision, added in drafting: the tenfold drop is two threefold steps, 64 → 96 and 96 → 128. At a point whose break is at 128 or above, the whole drop lies in the rise segment. At a point whose break is at 96, the 96 → 128 step lies in the fall segment, so at that point the fall may also be partly due to the rate change. The report gives how many points have each break (`POINTS.csv` `break_width`; `ANALYSIS.json` `break_widths`).

## 2. Conditional sensitivity (pre-registered now)

- **Trigger.** The sensitivity runs only if Run B's Primary B label, as computed by the sealed `text_analysis`, is INTERIOR_PEAK. Otherwise it is not run.
- **Design.** Everything is the same as in Run B:
  - the same ten draws, d01–d10 of registry 8ce7d597…;
  - the same corpus, partition, seeds, uniform pre-training and recipe.

  The only change: the adaptation learning rate is **3e-5 for every width**. At 128–384 this is the rate Run B uses; at 64 and 96 it replaces 3e-4 and 1e-4.
- **Reporting.**
  - The sensitivity is analysed by the same sealed `primaries()`.
  - It is reported **next to the primary and never replaces it**. No rule combines the two, and the primary label stands as computed.
  - It uses the same draws, so it is a paired check, not an independent replication.
- **Known limitation** (measured on t00 in Run A, `LR_SELECTION.json`). At 3e-5, widths 64 and 96 reached their lowest validation NLL at E32, the last readout (5.938 and 5.783). At their selected rates the lowest values were 5.894 and 5.780. So at the two smallest widths the sensitivity may swap the rate difference for under-training.
- **Approval.** The sensitivity needs new versioned source, native fixture tests, an independent review and its own owner approval. It is not part of Approval 2.
- **Estimate** (`SENSITIVITY_ESTIMATE.json`; `sensitivity_estimate.py`). This is planning arithmetic, not a guarantee: the sensitivity's own benchmark sets its cap. It uses Run A's bound benchmark (09e8d193…) and the frozen `stage_cap` formula. As specified, all six widths over ten draws:
  - **projected 1.95 h, worst case 3.19 h**;
  - **about 1.13 GiB** on disk.

  The same formula projects 0.52 h for Run A, which measured 0.50 h and 0.34 GiB. D: had 5.9 GiB free on 28 Oct 2026 after Run A, and Run B plans 1.12 GiB. That leaves about 4.8 GiB at the sensitivity's admission, above the frozen 4 GiB minimum.
