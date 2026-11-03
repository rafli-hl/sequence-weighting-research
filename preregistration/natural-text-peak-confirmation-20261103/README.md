# Pre-registration: peak confirmation on fresh WikiText-103 draws (3 November 2026)

This folder publishes the frozen protocol and the sealed code of one confirmatory study **before its analysis was run**. Its purpose is to let anyone check that the test, the decision rules and the readings were fixed before any result existed.

## Status when published

- The training runs C1 (draws c01–c03) and C2 (c04–c06) had completed; their terminal hashes are in `HASHES.json`.
- **The sealed analysis (`sealed-source/peak_analysis.py`) had not been approved or run.** No p\* value, gain or loss from these draws had been opened.
- The result will be added to this repository separately, with no change to anything in this folder.

## The question

The few-epoch study (WikiText-103, 3 epochs, no detected overfitting) showed, descriptively, that p\* was highest at width 512 in every draw at every readout, with p\* lower at 768. Width 768 had a lower validation loss at a smaller learning rate, so the drop could be a learning-rate artifact. This study tests both on draws never used before:

- **Primary (INTERIOR_PEAK):** at epoch 3 and rate 3e-4, the 95% lower limits of p\*(512) − p\*(384) and p\*(512) − p\*(768) are both above 0 (six draws, df 5).
- **Control (read only if the primary passes):** p\*(512) − p\*(768) with both widths at 1e-4.
- **Readings, fixed in advance:** see `sealed-source/PROTOCOL.md`, section 7. "No peak confirmed" is not a claim of absence; "rate-dependent" is reserved for 768 above 512 at 1e-4.

The hypothesis was formed after seeing earlier draws, as the protocol discloses; those draws are excluded from this study.

## Contents

| Path | What it is |
|---|---|
| `sealed-source/` | The sealed study source: protocol, worker, analysis, data and registry code, and the vendored estimator. `SOURCE_SUBJECT.json` lists every file's SHA-256; its own SHA-256 is the source subject. |
| `sealed-source/PROTOCOL.md` | Design, primary, control, secondary, readings, manipulation check, limitations and failure policy. |
| `seed-registry/` | The owner-run seed registry and its frozen policy. |
| `HASHES.json` | Hashes binding the source, builder, real-engine check, registry, partition, corpus manifest, rate selection and both run terminals. |

## How to verify

```sh
sha256sum sealed-source/SOURCE_SUBJECT.json   # 0d9e8f9adee4544bd24550f43a09c309e935ec6816a90769e04625e764711e28
python3 - <<'PY'
import json, hashlib, pathlib
s = pathlib.Path('sealed-source'); d = json.loads((s / 'SOURCE_SUBJECT.json').read_text())
bad = [f['path'] for f in d['files'] if hashlib.sha256((s / f['path']).read_bytes()).hexdigest() != f['sha256']]
print('mismatched files:', bad)
PY
```

## Scope and limits

Small models (depth 4, at most 34.7 M parameters), one corpus family, a constant learning rate, and no claim about Jane Street's scale. Paths inside the code refer to the original research machine and are not portable entry points. Run outputs, approval receipts and owner records are excluded, following `PUBLICATION_NOTES.md`; this pre-registration is a deliberate exception to the rule that unfinished packages are not published.
