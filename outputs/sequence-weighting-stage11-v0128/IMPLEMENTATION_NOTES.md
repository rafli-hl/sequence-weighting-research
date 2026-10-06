# Stage 11 implementation and pre-outcome revisions

This source is new v0.12 code derived from Stage 6 and the independently reviewed
paper-track-v1 proposal. No historical source or measured result is replaced.
No research training has been run. A run-specific `FREEZE.json` and independent
implementation acceptance are required by the runner before its separate `run`
command can start. The writing package remains preserved as the prior proposal.

## Seed revision 1, before any research outcome

The complete read-only inventory examined 13,617 historical text files in
122.56 seconds and found no parse/decode omissions. Proposed model seeds
1501/1502 were previously used as derived Python weight RNG seeds (1000+501/502).
This is a cross-role identifier collision, not evidence of corpus overlap or
equal model/weight draws: the PRNG engines and uses differ.

To satisfy the all-role freshness check, the new model/weight seeds are:

- Tuning: 140101 and 140201, replacing 1401 and 1402.
- Confirmation: 150101 and 150201, replacing 1501 and 1502.

Their derived weight and batch streams were checked against the same inventory.
Spacing also separates the two models' 30-epoch Torch batch-stream intervals.
Reusing each model seed across confirmation corpora remains deliberate pairing.
Data/pretraining seeds, corpus counts, optimizer grid, estimands, guards and
go/stop rules are unchanged. `SEED_INVENTORY-20260930-r1.json` preserves the
original collisions and replacement check. The original proposal stays intact.

## Runtime and storage details

Canonical initial metrics are computed once per condition/capacity/data/model
tuple, with explicit aliases across optimizer and weighting arms. Every arm
loads the identical pretrained tensor state, full data tensors and frozen
assignment/order arrays. Each condition retains its own initial losses.
Tuning loads train/validation split files only. Confirmation can evaluate test
only after a selection/schedule freeze is written.

Cold/pretrained binaries, all terminal binaries, every F10 binary and the
distinct selected confirmation checkpoint are retained. Every declared point
has per-sequence losses, scalar metrics and model tensor hashes. Checkpoint
aliases name shared retention roles. Missing intermediate binaries cannot be
re-evaluated from hashes alone.

Source hashes are checked at freeze/launch and trajectory/resource boundaries;
the time/free-space guards are checked between epochs and evaluations. The
shared training budget includes pretraining, evaluation, diagnostics, selection,
hashing and serialization. Source drift, nonfinite values, insufficient storage
or exhausted time produces a failure record. A run cannot silently resume.

The preflight sequence uses only unrelated fixture data and synthetic metric
arrays. Its cumulative compute time, including seed inventory and freeze input
generation, must fit 300 seconds. Authoring and human/agent review time are not
model computation and are not counted as fixture execution.

The maximum raw run plus its compact archive must fit 4 GiB; checkpoints are
excluded from the archive but kept locally. The measured resource estimate is
a prerequisite, not an observed research outcome or permission to exceed caps.
