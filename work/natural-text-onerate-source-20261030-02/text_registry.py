"""Outcome-blind seed registry for the natural-text ladder (stdlib only; no data, framework or outcome access).

Derived from work/capacity-shift-followup-source-20261027-01/ladder_registry.py: the same census, exclusive claim,
single entropy draw, ordered acceptance and re-derivation, with the natural-text roles.
Policy (frozen in SEED_REGISTRY_POLICY.md before any draw):
1. Exclusion set E = previous exclusion list U the frozen confirmation registry U the capacity-ladder and capacity-shift
   follow-up registries and their exclusion lists U a fresh census of saved project JSON files (keys containing 'seed',
   'stream', 'schedule' or 'corpus').
2. One OS entropy request of 1024 bytes, persisted before interpretation, decoded as 256 little-endian uint32 candidates.
3. A candidate is accepted iff it is more than 2048 away from every value in E and every earlier acceptance (streams
   derive 1000+seed and 999+seed+epoch <= +1031). The first 46 acceptances fill the fixed role order: partition_seed;
   then for t00, d01..d10 the init, weight, pre-training order and adaptation order seeds; then the benchmark seed.
   Fewer than 46 acceptances stops the registry: no redraw, no replacement.
4. An exclusive claim file prevents a second draw; the registry is a pure function of DRAW.json and EXCLUSIONS.json.
5. The draw requires the frozen corpus manifest (the tokenizer is trained and frozen first) and records its SHA-256 in
   the claim and the registry; builders and the worker refuse a corpus that differs from it.
"""
import hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_data

ROOT = Path(r'D:\sequence-weighting-research')
PREVIOUS = ROOT / 'reports/v0128-fresh-seed-registry-20261021-01'
EARLIER_REGISTRIES = (ROOT / 'reports/capacity-ladder-seed-registry-20261026-01', ROOT / 'reports/capacity-shift-followup-seed-registry-20261027-01')
KEYS = ('seed', 'stream', 'schedule', 'corpus')
SKIP_PARTS = {'.git', '.venv-wsl', 'site-packages', 'wheels', 'wheels-linux', 'wheels-text', '.idea'}
NEIGHBORHOOD = 2048
CANDIDATES = 256
ROLES = ('init_seed', 'weight_seed', 'pretrain_order_seed', 'adapt_order_seed')
ROLE_ORDER = (('partition', 'partition_seed'),) + tuple((g, r) for g in plan.GROUPS for r in ROLES) + (('benchmark', 'benchmark_seed'),)
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


def registry_values(reg):
    """Every role value of an earlier drawn registry (ladder or follow-up format)."""
    out = {v for row in reg['corpus_pairs'] for k, v in row.items() if k != 'corpus_slot'}
    return out | {reg['benchmark']['benchmark_seed']}


def exclusions(root=ROOT, skip=()):
    previous = json.loads((PREVIOUS / 'EXPOSED_SEED_ROLES.json').read_bytes())
    registry = json.loads((PREVIOUS / 'ADMITTED_SEEDS.json').read_bytes())
    frozen = {v for row in registry['corpus_pairs'] for k, v in row.items() if k != 'corpus_slot'}
    frozen |= {v for row in registry['namespace_role_values'] for k, v in row.items() if k != 'corpus_slot'}
    frozen |= set(registry['fixed_schedules'])
    earlier, prov_earlier = set(), []
    for d in EARLIER_REGISTRIES:
        ex_raw, reg_raw = (d / 'EXCLUSIONS.json').read_bytes(), (d / 'REGISTRY.json').read_bytes()
        ex, vals = set(json.loads(ex_raw)['values']), registry_values(json.loads(reg_raw))
        earlier |= ex | vals
        prov_earlier.append(dict(directory=str(d.relative_to(root)) if str(d).startswith(str(root)) else str(d), exclusions_sha256=sha(ex_raw),
                                 exclusion_values=len(ex), registry_sha256=sha(reg_raw), registry_values=len(vals)))
    found, provenance = census(root, skip)
    union = sorted(set(previous) | frozen | earlier | found)
    return union, dict(previous_list_sha256=sha((PREVIOUS / 'EXPOSED_SEED_ROLES.json').read_bytes()), previous_values=len(previous),
                       frozen_registry_sha256=sha((PREVIOUS / 'ADMITTED_SEEDS.json').read_bytes()), frozen_values=len(frozen),
                       earlier_registries=prov_earlier, census_values=len(found), union_values=len(union), **provenance)


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
    """Pure re-derivation of (partition_seed, group rows, benchmark row, decisions) from DRAW.json bytes and the exclusions."""
    d = json.loads(draw_raw); raw = bytes.fromhex(d['entropy_hex'])
    if len(raw) != 4 * CANDIDATES or d.get('bytes') != len(raw): raise ValueError('Draw length')
    candidates = [int.from_bytes(raw[4 * i:4 * i + 4], 'little') for i in range(CANDIDATES)]
    accepted, decisions = accept(candidates, excluded)
    if len(accepted) < len(ROLE_ORDER): return None, None, None, decisions
    rows = {}
    for (slot, role), value in zip(ROLE_ORDER, accepted): rows.setdefault(slot, dict(group=slot))[role] = value
    return rows['partition']['partition_seed'], [rows[g] for g in plan.GROUPS], rows['benchmark'], decisions


def draw(out_dir, corpus_manifest, entropy=os.urandom, root=ROOT, skip=()):
    out = Path(out_dir)
    claim = out / 'DRAW_CLAIM.json'
    if (out / 'DRAW.json').exists(): raise SystemExit('Registry already drawn; no redraw')
    policy = out / 'SEED_REGISTRY_POLICY.md'
    if not policy.exists(): raise SystemExit('Frozen policy must exist before the draw')
    corpus_manifest = Path(corpus_manifest)
    if not corpus_manifest.is_file(): raise SystemExit('The frozen corpus manifest must exist before the draw (tokenizer first)')
    try: text_data.validate_manifest(json.loads(corpus_manifest.read_bytes()), {f: sha((HERE / f).read_bytes()) for f in text_data.CODE_FILES})
    except (ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as e: raise SystemExit('Not a valid corpus manifest of the sealed code; nothing claimed: ' + repr(e)[:200])
    manifest_sha = sha(corpus_manifest.read_bytes())
    try:
        with claim.open('xb') as f: f.write(encoded(dict(status='CLAIMED_BEFORE_DRAW', policy_sha256=sha(policy.read_bytes()), corpus_manifest_sha256=manifest_sha)))
    except FileExistsError: raise SystemExit('Registry already claimed; no redraw')
    excluded, provenance = exclusions(root, skip)
    (out / 'EXCLUSIONS.json').write_bytes(encoded(dict(values=excluded, provenance=provenance)))
    raw = entropy(4 * CANDIDATES)
    if not isinstance(raw, bytes) or len(raw) != 4 * CANDIDATES: raise SystemExit('Entropy source returned wrong length')
    (out / 'DRAW.json').write_bytes(encoded(dict(entropy_hex=raw.hex(), bytes=len(raw), decoding=f'{CANDIDATES} little-endian uint32 in order')))
    partition_seed, groups, bench, decisions = derive((out / 'DRAW.json').read_bytes(), excluded)
    if groups is None:
        (out / 'REGISTRY_STOPPED.json').write_bytes(encoded(dict(status='STOPPED_INSUFFICIENT_ACCEPTANCES', accepted=sum(d['accepted'] for d in decisions), decisions=decisions)))
        raise SystemExit(f'Fewer than {len(ROLE_ORDER)} acceptable candidates; registry stopped without redraw')
    registry = dict(status='FROZEN_DRAWN', schema=2, partition_seed=partition_seed, groups=groups, benchmark=bench, corpus_manifest_sha256=manifest_sha,
                    policy_sha256=sha(policy.read_bytes()), exclusions_sha256=sha((out / 'EXCLUSIONS.json').read_bytes()),
                    draw_sha256=sha((out / 'DRAW.json').read_bytes()), decisions=decisions, neighborhood=NEIGHBORHOOD,
                    outcome_blind_policy=f'Single precommitted {4 * CANDIDATES}-byte OS entropy draw; deterministic ordered acceptance against saved exclusions only.')
    raw_registry = encoded(registry); (out / 'REGISTRY.json').write_bytes(raw_registry)
    return registry, sha(raw_registry)


def validate(registry, exclusions_raw, draw_raw):
    """Admission check (builder and worker): the registry must be exactly the re-derivation from its own bytes."""
    if registry.get('status') != 'FROZEN_DRAWN' or len(registry.get('groups', [])) != len(plan.GROUPS): raise ValueError('Registry status/count')
    if not isinstance(registry.get('corpus_manifest_sha256'), str) or len(registry['corpus_manifest_sha256']) != 64: raise ValueError('Registry is not bound to a corpus manifest')
    if registry.get('exclusions_sha256') != sha(exclusions_raw) or registry.get('draw_sha256') != sha(draw_raw): raise ValueError('Registry draw/exclusion hashes')
    excluded = json.loads(exclusions_raw)['values']
    partition_seed, groups, bench, decisions = derive(draw_raw, excluded)
    if (partition_seed != registry.get('partition_seed') or groups != registry['groups'] or bench != registry.get('benchmark')
            or decisions != registry.get('decisions')): raise ValueError('Registry differs from its re-derivation')
    values = [registry['partition_seed']]
    for g, row in zip(plan.GROUPS, registry['groups']):
        if row.get('group') != g: raise ValueError('Registry group order')
        for role in ROLES:
            v = row.get(role)
            if type(v) is not int or not 0 <= v < 2 ** 32: raise ValueError('Role value')
            values.append(v)
    values.append(registry['benchmark']['benchmark_seed'])
    accepted, _ = accept(values, excluded)
    if accepted != values: raise ValueError('Registry value collides with exclusions or another role')
    return registry


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != 'draw': raise SystemExit('usage: text_registry.py draw <registry_dir> <CORPUS_MANIFEST.json>')
    reg, digest = draw(Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(dict(registry_sha256=digest, partition_seed=reg['partition_seed'], groups=reg['groups'], benchmark=reg['benchmark']), indent=1))
