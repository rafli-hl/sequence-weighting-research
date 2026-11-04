# Natural-text studies, 27 October – 4 November 2026

This page indexes the synthetic follow-up and the five natural-text studies run after the Stage 10 record, the adversarial review of their claims, and the response to it. Every file listed here is byte-identical to its local source; hashes are in `PUBLICATION_MANIFEST.csv`. No experiment was rerun to prepare this copy.

**Read the final claims first:** [`RESPONSE.md` §5](reports/adversarial-review-response-20261104-01/RESPONSE.md). They govern every earlier summary. Earlier wording that the response retires is listed in [`SUPERSEDED_WORDING.md`](reports/natural-text-evidence-chain-20261104-01/SUPERSEDED_WORDING.md).

## Scope, in one paragraph

All models are small Transformers of depth 4 and width up to 768 (at most 34.7 M parameters), trained on a 4 GB laptop GPU. Each draw holds 0.2–2.1 M unique tokens. Jane Street's models run from tens of millions to hundreds of billions of parameters, so this work is a **small-scale methodological study of the estimator p\* under training-progress and learning-rate confounds, not a replication** of their findings. Sealed labels and readings stay as written in their own records. "Pre-registered" here means pre-specified and hash-sealed locally within one team; only the peak confirmation was registered publicly, and only after its data existed (see [PR #3](https://github.com/rafli-hl/sequence-weighting-research/pull/3) and [`NOTE_PUBLIC_REGISTRATION_EDITS.md`](reports/natural-text-peak-result-20261103-01/NOTE_PUBLIC_REGISTRATION_EDITS.md)).

## The studies

The review and the response label the studies S, N1 and N3–N6.

| Label | Study | Protocol and sealed source | Result | Tables |
|---|---|---|---|---|
| S | Synthetic capacity-shift follow-up, 12 fresh corpora | [`PROTOCOL.md`](work/capacity-shift-followup-source-20261027-01/PROTOCOL.md) | [`REPORT.md`](reports/capacity-shift-followup-result-20261028-01/REPORT.md) | [`analysis`](reports/capacity-shift-followup-analysis-20261027-01/) |
| N1 | WikiText-2 width ladder, per-width learning rates | [`PROTOCOL.md`](work/natural-text-ladder-source-20261028-02/PROTOCOL.md); [`AMENDMENT_01.md`](reports/natural-text-ladder-amendment-20261028-01/AMENDMENT_01.md); [`LR_SELECTION.json`](reports/natural-text-ladder-lr-selection-20261028-01/LR_SELECTION.json) | [`REPORT.md`](reports/natural-text-ladder-analysis-20261029-01/REPORT.md); [exploratory note](reports/natural-text-ladder-exploratory-20261029-01/EXPLORATORY_NOTE.md) | [`sealed-analysis`](reports/natural-text-ladder-analysis-20261029-01/sealed-analysis/) |
| N3 | WikiText-2 one-rate extension, 10 draws, 32 epochs at 3e-5 | [`PROTOCOL.md`](work/natural-text-onerate-source-20261030-02/PROTOCOL.md) | [`RESULT.md`](reports/natural-text-onerate-result-20261031-01/RESULT.md) | [`analysis`](reports/natural-text-onerate-analysis-20261030-02/) |
| N4 | WikiText-2 late-turn confirmation, 4 fresh draws | [`PROTOCOL.md`](work/natural-text-lateturn-source-20261031-01/PROTOCOL.md) | [`RESULT.md`](reports/natural-text-lateturn-result-20261031-01/RESULT.md) | [`analysis`](reports/natural-text-lateturn-analysis-20261031-01/) |
| N5 | WikiText-103 few-epoch study, 10 fresh draws, 3 epochs | [`PROTOCOL.md`](work/natural-text-fewepoch-source-20261101-01/PROTOCOL.md) | [`RESULT.md`](reports/natural-text-fewepoch-result-20261103-01/RESULT.md); [descriptive section](reports/natural-text-fewepoch-descriptive-20261103-01/DESCRIPTIVE.md) | [`analysis`](reports/natural-text-fewepoch-analysis-20261103-01/) |
| N6 | WikiText-103 peak confirmation, 6 fresh draws, two rates | [Pre-registration](preregistration/natural-text-peak-confirmation-20261103/README.md) (sealed source and seed registry) | [`RESULT.md`](reports/natural-text-peak-result-20261103-01/RESULT.md) | [`analysis`](reports/natural-text-peak-analysis-20261103-01/) |

Seed registries for S, N1, N4 and N5 are in `reports/*-seed-registry-*/` (`REGISTRY.json`, `SEED_REGISTRY_POLICY.md`, the draw and its exclusions).

## Failed attempts

Two runs failed and were rerun, on the same draws and seeds, under an owner ruling that each rerun was a new attempt. Neither failed attempt was analysed.

- **N1, Run B attempt 1:** a GPU game was running. [`FAILURE_REPORT.md`](reports/natural-text-ladder-run-b-failure-20261028-01/FAILURE_REPORT.md). Its list of what was read is incomplete; the correction of record is [`DECISION.md`](reports/natural-text-ladder-owner-decisions-20261104-01/DECISION.md), and any citation of this failure should cite both.
- **N3, attempt 1:** the charger was unplugged during a draw. [`FAILURE_REPORT.md`](reports/natural-text-onerate-failure-20261030-01/FAILURE_REPORT.md).

## Synthesis, review and response

- [Evidence chain, 31 Oct](reports/natural-text-evidence-chain-20261031-01/EVIDENCE_CHAIN.md) and [evidence chain, 4 Nov](reports/natural-text-evidence-chain-20261104-01/EVIDENCE_CHAIN.md), with its [superseded-wording note](reports/natural-text-evidence-chain-20261104-01/SUPERSEDED_WORDING.md).
- [Adversarial review](reports/adversarial-review-20261104-01/REVIEW.md): a read-only review by the project's own assistant under an adversarial brief, with its two recomputation scripts and their outputs. The matched-progress figures it introduces are post hoc and interpolated between readouts.
- [Response to the review](reports/adversarial-review-response-20261104-01/RESPONSE.md): a disposition of every point (concede, reword, reanalysis, partial rebuttal) and the final claims in §5.
- Owner decisions, `reports/natural-text-ladder-owner-decisions-*/`: the design decisions the protocols cite, and the 4 Nov record of the response's acceptance, the search incident and its ruling, and the closure of the experiments.

## Status

The experiments are closed. The only optional future run named in the record is a denser-readout run (epochs 2.25–3.5 on the 1e-4 arms of N6, about 2–3 hours) that would replace the interpolation behind the matched-progress figures. Nothing is authorized.

## Not included

Following [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md): run folders, model states, per-sequence arrays, dataset rows, preparation and probe packages, seed-package and approval folders, run and engine-check receipts and owner console output, the duplicated analysis rerun inside S's result folder, and the machine battery and power-event records of N3's failure diagnosis. Scripts in these folders that read run directories need those original inputs.
