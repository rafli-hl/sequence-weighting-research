# Stage 7 presentation revision r1

The frozen README.md, source files, numeric summaries and original PLOT_CHECKS.json are copied verbatim. PLOT_CHECKS_R1.json describes the revised cancellation figure; PRESENTATION_REVISION.json lists source/summary hashes and the two changed presentation files.

From the project root in the existing Ubuntu WSL environment:

```sh
work/.venv-wsl/bin/python outputs/sequence-weighting-stage7/finalize_stage7.py --run-id estimator-v08-20260930-01
```

The command requires the original completed/audited run and report, creates the r1 directory once, and refuses an existing r1 destination. It does not rerun any simulation or fit; existing numerical summary files are copied unchanged. All raw entries in the original archive are retained byte for byte; the external ARCHIVE_CHECK.json verifies the new archive and records presentation runtime. Separate visual inspection is still required.
