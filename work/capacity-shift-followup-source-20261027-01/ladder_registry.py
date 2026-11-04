"""Outcome-blind seed registry for the capacity-shift follow-up (stdlib only; no data, framework or outcome access).

Derived from work/capacity-ladder-source-20261026-01/ladder_registry.py (twelve corpora, 256 candidates, the ladder
registry and its exclusions added to E).
Policy (frozen in SEED_REGISTRY_POLICY.md before any draw):
1. Exclusion set E = previous exclusion list (reports/v0128-fresh-seed-registry-20261021-01/EXPOSED_SEED_ROLES.json)
   U every base and namespace value of the frozen confirmation registry 820d2443...
   U every value of the capacity-ladder exclusion list and every role value of the drawn capacity-ladder registry
     (reports/capacity-ladder-seed-registry-20261026-01)
   U a fresh census, at draw time, of every non-negative integer below 2**32 found under a JSON key whose name
     contains 'seed', 'stream', 'schedule' or 'corpus' in any saved project JSON file (conservative over-exclusion).
2. One OS entropy request of 1024 bytes, persisted before interpretation, decoded as 256 little-endian uint32 candidates.
3. Candidates are examined in order; a candidate is accepted iff it is at least 2049 away from every value in E and
   from every previously accepted candidate (engine streams derive seed+77, 1000+seed and 999+seed+epoch<=1039).
   The first 61 accepted values fill the fixed role order (c01..c12 x adaptation, pretraining, weight, order, init;
   then the benchmark role). Fewer than 61 acceptances stops the registry: no redraw, no replacement.
4. A claim file, created exclusively before the draw, prevents a second draw. The registry is a pure function of
   DRAW.json and EXCLUSIONS.json; the builder and the worker re-derive it and refuse any mismatch.
   Outcome blindness: nothing here reads tensors, losses or fits.
"""
import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(r'D:\sequence-weighting-research')
PREVIOUS = ROOT / 'reports/v0128-fresh-seed-registry-20261021-01'
LADDER_REGISTRY = ROOT / 'reports/capacity-ladder-seed-registry-20261026-01'
KEYS = ('seed', 'stream', 'schedule', 'corpus')
SKIP_PARTS = {'.git', '.venv-wsl', 'site-packages', 'wheels', 'wheels-linux', 'wheels-text', '.idea'}
NEIGHBORHOOD = 2048
CANDIDATES = 256
SLOTS = tuple(f'c{i:02d}' for i in range(1, 13))
ROLES = ('adaptation_seed', 'pretraining_seed', 'weight_seed', 'order_seed', 'init_seed')
ROLE_ORDER = tuple((c, r) for c in SLOTS for r in ROLES) + (('benchmark', 'benchmark_seed'),)
MAX_JSON_BYTES = 256 * 2 ** 20


def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(x): return (json.dumps(x, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def _collect(value, under_key, out):
    if isinstance(value, dict):
        for k, v in value.items():
            _collect(v, under_key or any(s in str(k).lower() for s in KEYS), out)
    elif isinstance(value, list):
        for v in value: _collect(v, under_key, out)
    elif under_key and type(value) is int and 0 <= value < 2 ** 32:
        out.add(value)


def census(root=ROOT, skip=()):
    """Conservative seed census of saved JSON records. Returns (values, provenance)."""
    values, files, failures = set(), [], []
    for p in sorted(Path(root).rglob('*.json')):
        if any(part in SKIP_PARTS for part in p.parts) or any(str(p).startswith(str(s)) for s in skip): continue
        try:
            size = p.stat().st_size
            if size > MAX_JSON_BYTES: failures.append(dict(path=str(p), reason='too_large')); continue
            found = set(); _collect(json.loads(p.read_bytes()), False, found)
        except (OSError, ValueError, UnicodeDecodeError, RecursionError) as e:
            failures.append(dict(path=str(p), reason=type(e).__name__)); continue
        if found: files.append(dict(path=str(p.relative_to(root)), values=len(found)))
        values |= found
    return values, dict(json_files_with_values=len(files), unreadable_or_skipped=failures[:200], unreadable_count=len(failures))


def exclusions(root=ROOT, skip=()):
    previous = json.loads((PREVIOUS / 'EXPOSED_SEED_ROLES.json').read_bytes())
    registry = json.loads((PREVIOUS / 'ADMITTED_SEEDS.json').read_bytes())
    frozen = {v for row in registry['corpus_pairs'] for k, v in row.items() if k != 'corpus_slot'}
    frozen |= {v for row in registry['namespace_role_values'] for k, v in row.items() if k != 'corpus_slot'}
    frozen |= set(registry['fixed_schedules'])
    ladder_ex_raw, ladder_reg_raw = (LADDER_REGISTRY / 'EXCLUSIONS.json').read_bytes(), (LADDER_REGISTRY / 'REGISTRY.json').read_bytes()
    ladder_ex = set(json.loads(ladder_ex_raw)['values']); ladder_reg = json.loads(ladder_reg_raw)
    ladder = {v for row in ladder_reg['corpus_pairs'] for k, v in row.items() if k != 'corpus_slot'} | {ladder_reg['benchmark']['benchmark_seed']}
    found, provenance = census(root, skip)
    union = sorted(set(previous) | frozen | ladder_ex | ladder | found)
    return union, dict(previous_list_sha256=sha((PREVIOUS / 'EXPOSED_SEED_ROLES.json').read_bytes()), previous_values=len(previous),
                       frozen_registry_sha256=sha((PREVIOUS / 'ADMITTED_SEEDS.json').read_bytes()), frozen_values=len(frozen),
                       ladder_exclusions_sha256=sha(ladder_ex_raw), ladder_exclusion_values=len(ladder_ex),
                       ladder_registry_sha256=sha(ladder_reg_raw), ladder_registry_values=len(ladder),
                       census_values=len(found), union_values=len(union), **provenance)


def accept(candidates, excluded, needed=len(ROLE_ORDER)):
    """Deterministic ordered acceptance; returns (accepted, decisions). Pure function."""
    import bisect
    ex = sorted(set(excluded)); accepted, decisions = [], []
    for value in candidates:
        i = bisect.bisect_left(ex, value)
        near = [ex[j] for j in (i - 1, i) if 0 <= j < len(ex) and abs(ex[j] - value) <= NEIGHBORHOOD]
        mutual = [a for a in accepted if abs(a - value) <= NEIGHBORHOOD]
        ok = not near and not mutual and len(accepted) < needed
        decisions.append(dict(value=value, accepted=ok, near_excluded=near[:2], near_accepted=mutual[:2]))
        if ok: accepted.append(value)
    return accepted, decisions


def derive(draw_raw, excluded):
    """Pure re-derivation of the role values from DRAW.json bytes and the exclusion values."""
    d = json.loads(draw_raw); raw = bytes.fromhex(d['entropy_hex'])
    if len(raw) != 4 * CANDIDATES or d.get('bytes') != len(raw): raise ValueError('Draw length')
    candidates = [int.from_bytes(raw[4 * i:4 * i + 4], 'little') for i in range(CANDIDATES)]
    accepted, decisions = accept(candidates, excluded)
    if len(accepted) < len(ROLE_ORDER): return None, None, decisions
    rows = {}
    for (slot, role), value in zip(ROLE_ORDER, accepted): rows.setdefault(slot, dict(corpus_slot=slot))[role] = value
    return [rows[c] for c in SLOTS], rows['benchmark'], decisions


def draw(out_dir, entropy=os.urandom, root=ROOT, skip=()):
    out = Path(out_dir)
    claim = out / 'DRAW_CLAIM.json'
    if (out / 'DRAW.json').exists(): raise SystemExit('Registry already drawn; no redraw')
    policy = out / 'SEED_REGISTRY_POLICY.md'
    if not policy.exists(): raise SystemExit('Frozen policy must exist before the draw')
    try:
        with claim.open('xb') as f: f.write(encoded(dict(status='CLAIMED_BEFORE_DRAW', policy_sha256=sha(policy.read_bytes()))))
    except FileExistsError: raise SystemExit('Registry already claimed; no redraw')
    excluded, provenance = exclusions(root, skip)
    (out / 'EXCLUSIONS.json').write_bytes(encoded(dict(values=excluded, provenance=provenance)))
    raw = entropy(4 * CANDIDATES)
    if not isinstance(raw, bytes) or len(raw) != 4 * CANDIDATES: raise SystemExit('Entropy source returned wrong length')
    (out / 'DRAW.json').write_bytes(encoded(dict(entropy_hex=raw.hex(), bytes=len(raw), decoding=f'{CANDIDATES} little-endian uint32 in order')))
    pairs, bench, decisions = derive((out / 'DRAW.json').read_bytes(), excluded)
    if pairs is None:
        (out / 'REGISTRY_STOPPED.json').write_bytes(encoded(dict(status='STOPPED_INSUFFICIENT_ACCEPTANCES', accepted=sum(d['accepted'] for d in decisions), decisions=decisions)))
        raise SystemExit(f'Fewer than {len(ROLE_ORDER)} acceptable candidates; registry stopped without redraw')
    registry = dict(status='FROZEN_DRAWN', schema=1, corpus_pairs=pairs,
                    benchmark=bench, policy_sha256=sha(policy.read_bytes()), exclusions_sha256=sha((out / 'EXCLUSIONS.json').read_bytes()),
                    draw_sha256=sha((out / 'DRAW.json').read_bytes()), decisions=decisions, neighborhood=NEIGHBORHOOD,
                    outcome_blind_policy=f'Single precommitted {4 * CANDIDATES}-byte OS entropy draw; deterministic ordered acceptance against saved exclusions only.')
    raw_registry = encoded(registry); (out / 'REGISTRY.json').write_bytes(raw_registry)
    return registry, sha(raw_registry)


def validate(registry, exclusions_raw, draw_raw):
    """Admission check of a drawn registry (builder and worker, before any generation): the registry must be
    exactly the re-derivation from its own DRAW.json and EXCLUSIONS.json bytes."""
    if registry.get('status') != 'FROZEN_DRAWN' or len(registry.get('corpus_pairs', [])) != len(SLOTS): raise ValueError('Registry status/count')
    if registry.get('exclusions_sha256') != sha(exclusions_raw) or registry.get('draw_sha256') != sha(draw_raw): raise ValueError('Registry draw/exclusion hashes')
    excluded = json.loads(exclusions_raw)['values']
    pairs, bench, decisions = derive(draw_raw, excluded)
    if pairs != registry['corpus_pairs'] or bench != registry.get('benchmark') or decisions != registry.get('decisions'): raise ValueError('Registry differs from its re-derivation')
    values = []
    for i, row in enumerate(registry['corpus_pairs'], 1):
        if row.get('corpus_slot') != f'c{i:02d}': raise ValueError('Registry slot order')
        for role in ROLES:
            v = row.get(role)
            if type(v) is not int or not 0 <= v < 2 ** 32: raise ValueError('Role value')
            values.append(v)
    values.append(registry['benchmark']['benchmark_seed'])
    accepted, _ = accept(values, excluded)
    if accepted != values: raise ValueError('Registry value collides with exclusions or another role')
    return registry


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != 'draw': raise SystemExit('usage: ladder_registry.py draw <registry_dir>')
    reg, digest = draw(Path(sys.argv[2]))
    print(json.dumps(dict(registry_sha256=digest, corpus_pairs=reg['corpus_pairs'], benchmark=reg['benchmark']), indent=1))
