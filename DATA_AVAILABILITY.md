# Data availability and reproducibility

## Included

Versioned Python/scripts and prospective protocols, dependency locks, mathematical/analysis fixture source, compact CSV/JSON results, saved summary/audit classifications, figure assets and backing tables, and source/archive provenance where small. `PUBLICATION_MANIFEST.csv` records the distribution bytes and hashes. Local preparation verification is retained separately by the publisher.

## Intentionally local-only

All full `work/runs/` trees, checkpoints/optimizer states, pretraining assets, raw per-sequence tensors/loss traces, ZIP archives, downloaded wheels and installers, environments/caches, raw dataset rows, private chat, host receipts, user approvals/accounting and copied operational handoffs. No archives are included, so archive-member secret scanning was not needed for this distribution.

The supplied files support reading code/protocols, inspecting reported outcomes and backing tables, and running self-contained mathematical fixtures after environment setup. They do not support bit-for-bit regeneration of every historical training result or fixed-input numerical audit. Scripts that consume saved run directories will need those original inputs. No external dataset/checkpoint hosting or download availability is promised.

## Public text assets

`work/text-assets/provenance.json`, `model-metadata.json` and `dataset-metadata.json` retain pinned model/dataset revisions, filenames and hash metadata. `work/fetch_text_assets.py` is the historical download helper; it uses `curl.exe` and reads those metadata files. It is a Windows helper rather than a cross-platform installer. Model weights, tokenizer assets and WikiText rows are excluded. Model metadata records Apache-2.0; dataset metadata records CC-BY-SA-3.0. Review current upstream terms and attribution before fetching or redistributing; no redistribution license is granted here.

## Provenance and public derivatives

Most copied files are byte-identical to their local source. Personal home prefixes in selected narrative/JSON records were replaced with `<LOCAL_USER_HOME>` only in this publication copy. `PUBLICATION_TRANSFORMATIONS.json` records source and publication SHA-256 values. Original local records were not changed. Historical manifests/source-hash claims describe original measured files, not newly signed release provenance. Unavailable Markdown targets are shown as plain text marked unavailable, with a machine-readable list; historical links to original external websites were retained without a fresh comprehensive external-link audit.

No dataset independence, global-optimality certificate, new execution success or publication novelty is implied by this packaging. Signed gains, nonpositive-gain guards, failed utility gates and historical undefined estimates retain their original scientific meaning.
