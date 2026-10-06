# Sequence weighting research

Controlled sequence-weighting studies, estimator diagnostics, and saved research summaries inspired by Jane Street's [A study of sequence weighting at scale](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/).

This publication copy contains versioned source, mathematical fixtures, protocols, compact tabular evidence, and figures. It is a curated distribution of local research records, not the complete experiment archive. No experiment was rerun to prepare it.

## Start here

- [Figure catalogue and backing tables](figure/INDEX.md)
- [Research note covering Stages 2–10](outputs/sequence-weighting-paper-track-v1/RESEARCH_NOTE.md)
- [Claim audit and limitations](outputs/sequence-weighting-paper-track-v1/CLAIMS.md)
- [Literature review](outputs/sequence-weighting-paper-track-v1/LITERATURE_REVIEW.md)
- [Stage 1 report](outputs/sequence-weighting-pilot/results-mechanism-v02/REPORT.md)
- [Stage 10 synthesis](outputs/sequence-weighting-stage10/SYNTHESIS_STAGE4_10.md)
- [Data availability and reproducibility limits](DATA_AVAILABILITY.md)
- [Distribution changes](PUBLICATION_NOTES.md)

The measured record includes completed pilot and subsequent synthetic/generalization/estimator studies. A synthetic middle-capacity peak alone does not establish an exact large-language-model replication, utility improvement, causal mechanism, or an interior-to-interior peak shift. Positive, negative, failed, and undefined outcomes remain represented in saved summaries. Later prospective source packages retain their original status statements; inclusion does not mean they ran. Active capacity-reader revisions are excluded.

## Source and dependencies

Source remains at its historical relative paths under `outputs/sequence-weighting-*`. Source fixtures generally live beside their implementation as `check_*.py`, `*_checks.py`, or `fixtures.py`. The Stage 0 notebook is a companion whose equivalent scripts ran; the notebook itself is not claimed to have executed end to end.

The measured Stage 1 Linux environment is pinned in [environment-lock-stage1.txt](outputs/sequence-weighting-pilot/environment-lock-stage1.txt); the migrated Linux lock is [environment-lock-D.txt](migration/environment-lock-D.txt). Use Python 3.12 with the PyTorch CUDA 12.6 package index for the recorded GPU build. In a fresh environment, from this copy's root:

```sh
python -m venv .venv
# Activate the environment using your platform's normal activation command.
python -m pip install --extra-index-url https://download.pytorch.org/whl/cu126 -r outputs/sequence-weighting-pilot/environment-lock-stage1.txt
```

This is the historical Linux/CUDA environment specification, not a newly tested installation recipe. The NVIDIA/Triton entries are Linux-specific. The older Windows requirements pin a different NumPy version; do not treat that file as the measured Linux environment.

For a dependency-free mathematical check, use a disposable copy if you want to preserve all delivered bytes:

```sh
python outputs/sequence-weighting-pilot/core_checks.py
```

That historical script writes `CORE_CHECKS.json` beside its source. It tests known exponent recovery, guards, the quadratic objective and synthetic generator invariants; it does not validate GPU training. Publication preparation only syntax-checked sources and inspected imports/links; it did not run historical fixtures, launch scripts, preparation phases, or training.

Historical stage READMEs contain original machine paths, approvals, budgets and run IDs as context. Follow the public data-availability notes before attempting reproduction; those launch commands are not portable release entry points. Use fresh unique run directories and root-relative paths for any new run. Some later preparation/analysis phases require excluded checkpoints or manifests; the dependency report identifies literal missing references.

No project-wide license has been selected. Included upstream license metadata describes those upstream assets only. This copy contains no model weights or dataset rows. The curated bundle has been published separately from the original local research repository.
