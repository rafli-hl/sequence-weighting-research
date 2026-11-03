"""Outcome-blind seed registry of the peak confirmation (stdlib only; it reads the corpus manifest and saved seed records, no
loss, array or model).

Derived from work/natural-text-fewepoch-source-20261101-01/fewepoch_registry.py (reviewed; the few-epoch seeds were drawn
with it): the same census, exclusive claim, single entropy draw, ordered acceptance and re-derivation. Changes:
- the roles: partition_seed; the init, weight, pre-training order and adaptation order seeds of c01-c06; the benchmark seed
  (26 values);
- one more exclusion source: the few-epoch registry (its exclusion list and its 46 role values);
- the pins: the policy here; the corpus manifest, the few-epoch registry and partition from a byte copy of fewepoch_plan.py;
- before the claim: the few-epoch registry must equal its pin, and its partition must re-derive to its pin, and the fresh
  pool (peak_data.fresh_pool) must fill the six groups; the registry records the pool's counts and hash.
Policy: reports/natural-text-peak-seed-registry-20261103-01/SEED_REGISTRY_POLICY.md (frozen before any draw).
"""
import hashlib, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wt103_corpus
import fewepoch_plan as fp
import peak_data

ROOT = Path(r'D:\sequence-weighting-research')
PREVIOUS = ROOT / 'reports/v0128-fresh-seed-registry-20261021-01'
EARLIER_REGISTRIES = (ROOT / 'reports/capacity-ladder-seed-registry-20261026-01', ROOT / 'reports/capacity-shift-followup-seed-registry-20261027-01')
TEXT_REGISTRIES = (ROOT / 'reports/natural-text-ladder-seed-registry-20261028-01', ROOT / 'reports/natural-text-lateturn-seed-registry-20261031-01', ROOT / fp.REGISTRY['directory'])
POLICY_SHA256 = 'c102baf77b2a49802697b56dca5a300ad8d4d357401ca24c1897188f07bd79ac'
KEYS = ('seed', 'stream', 'schedule', 'corpus')
SKIP_PARTS = {'.git', '.venv-wsl', 'site-packages', 'wheels', 'wheels-linux', 'wheels-text', '.idea'}
NEIGHBORHOOD = 2048
CANDIDATES = 256
GROUPS = peak_data.GROUPS
ROLES = ('init_seed', 'weight_seed', 'pretrain_order_seed', 'adapt_order_seed')
ROLE_ORDER = (('partition', 'partition_seed'),) + tuple((g, r) for g in GROUPS for r in ROLES) + (('benchmark', 'benchmark_seed'),)
MAX_JSON_BYTES = 256 * 2 ** 20
SOURCE_FILES = ('peak_registry.py', 'peak_data.py', 'fewepoch_data.py', 'fewepoch_plan.py', 'wt103_corpus.py', 'acquire_plan.py', 'acquire_common.py', 'a1_download.py', 'a2_rows.py',
                'text_data.py', 'text_plan.py')
APPROVAL_ID = re.compile(r'^OWNER-[0-9]{8}-[A-Z0-9-]{2,60}$')


def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(x): return (json.dumps(x, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
def source_hashes(): return {f: sha((HERE / f).read_bytes()) for f in SOURCE_FILES}


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


def text_registry_values(reg):
    """Every role value of a natural-text registry (partition, group rows, benchmark)."""
    out = {reg['partition_seed'], reg['benchmark']['benchmark_seed']}
    return out | {v for row in reg['groups'] for k, v in row.items() if k != 'group'}


def exclusions(root=ROOT, skip=()):
    previous = json.loads((PREVIOUS / 'EXPOSED_SEED_ROLES.json').read_bytes())
    registry = json.loads((PREVIOUS / 'ADMITTED_SEEDS.json').read_bytes())
    frozen = {v for row in registry['corpus_pairs'] for k, v in row.items() if k != 'corpus_slot'}
    frozen |= {v for row in registry['namespace_role_values'] for k, v in row.items() if k != 'corpus_slot'}
    frozen |= set(registry['fixed_schedules'])
    earlier, prov_earlier = set(), []
    for d, values_of in [(d, registry_values) for d in EARLIER_REGISTRIES] + [(d, text_registry_values) for d in TEXT_REGISTRIES]:
        ex_raw, reg_raw = (d / 'EXCLUSIONS.json').read_bytes(), (d / 'REGISTRY.json').read_bytes()
        ex, vals = set(json.loads(ex_raw)['values']), values_of(json.loads(reg_raw))
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
    return rows['partition']['partition_seed'], [rows[g] for g in GROUPS], rows['benchmark'], decisions


def check_approval_id(approval_id, fixture):
    if fixture: return approval_id
    if not isinstance(approval_id, str) or approval_id.upper().startswith('FIXTURE') or not APPROVAL_ID.match(approval_id):
        raise SystemExit('An owner approval id (OWNER-YYYYMMDD-..., never FIXTURE) is required; nothing claimed')
    return approval_id


def draw(out_dir, corpus_manifest, approval_id, entropy=os.urandom, root=ROOT, skip=(), fixture=False, policy_sha256=None, manifest_sha256=None):
    """The single draw. Every refusal happens before the claim, so a refusal writes nothing. Fixture use (tests only)
    passes fixture=True, its own entropy and its own manifest pin; the command line never does."""
    out = Path(out_dir)
    check_approval_id(approval_id, fixture)
    if not fixture and manifest_sha256 is not None: raise SystemExit('Real draws bind the plan pins only; nothing claimed')
    policy_sha256 = policy_sha256 or POLICY_SHA256; manifest_sha256 = manifest_sha256 or fp.CORPUS_MANIFEST_SHA256
    claim = out / 'DRAW_CLAIM.json'
    if (out / 'DRAW.json').exists(): raise SystemExit('Registry already drawn; no redraw')
    policy = out / 'SEED_REGISTRY_POLICY.md'
    if not policy.exists(): raise SystemExit('Frozen policy must exist before the draw')
    if sha(policy.read_bytes()) != policy_sha256: raise SystemExit('Policy differs from the frozen policy pinned in the plan; nothing claimed')
    corpus_manifest = Path(corpus_manifest)
    if not corpus_manifest.is_file(): raise SystemExit('The frozen corpus manifest must exist before the draw')
    manifest_sha = sha(corpus_manifest.read_bytes())
    if manifest_sha != manifest_sha256: raise SystemExit('Corpus manifest differs from the frozen one; nothing claimed')
    try: wt103_corpus.validate_manifest(json.loads(corpus_manifest.read_bytes()), {f: sha((HERE / f).read_bytes()) for f in wt103_corpus.CODE_FILES})
    except (ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as e: raise SystemExit('Not a valid corpus manifest of the sealed code; nothing claimed: ' + repr(e)[:200])
    code = source_hashes()
    manifest = json.loads(corpus_manifest.read_bytes()); fewepoch_raw = (ROOT / fp.REGISTRY['directory'] / 'REGISTRY.json').read_bytes()
    if sha(fewepoch_raw) != fp.REGISTRY['registry_sha256']: raise SystemExit('The few-epoch registry differs from its pin; nothing claimed')
    try:
        assigned = peak_data.assigned_articles(manifest, json.loads(fewepoch_raw)['partition_seed']); pool = peak_data.fresh_pool(manifest, assigned)
        peak_data.partition(manifest, assigned, 0)
    except (ValueError, KeyError) as e: raise SystemExit('The few-epoch partition or the fresh pool does not hold; nothing claimed: ' + repr(e)[:200])
    pool_record = dict({k: v for k, v in pool.items() if k != 'articles'}, articles_sha256=sha(peak_data.encoded(pool['articles'])))
    try:
        with claim.open('xb') as f: f.write(encoded(dict(status='CLAIMED_BEFORE_DRAW', policy_sha256=sha(policy.read_bytes()), corpus_manifest_sha256=manifest_sha,
                                                         approval_id=approval_id, fixture=fixture, registry_source_sha256=code)))
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
    registry = dict(status='FROZEN_DRAWN', schema=2, kind='peak confirmation', partition_seed=partition_seed, groups=groups, benchmark=bench, fresh_pool=pool_record,
                    fewepoch_registry_sha256=sha(fewepoch_raw), fewepoch_partition_sha256=fp.PARTITION_SHA256, corpus_manifest_sha256=manifest_sha, policy_sha256=sha(policy.read_bytes()), exclusions_sha256=sha((out / 'EXCLUSIONS.json').read_bytes()),
                    draw_sha256=sha((out / 'DRAW.json').read_bytes()), decisions=decisions, neighborhood=NEIGHBORHOOD, approval_id=approval_id, fixture=fixture,
                    registry_source_sha256=code,
                    outcome_blind_policy=f'Single precommitted {4 * CANDIDATES}-byte OS entropy draw; deterministic ordered acceptance against saved exclusions only.')
    raw_registry = encoded(registry); (out / 'REGISTRY.json').write_bytes(raw_registry)
    return registry, sha(raw_registry)


def validate(registry, exclusions_raw, draw_raw, manifest_sha256=None):
    """Admission check (builder and worker): the registry must be exactly the re-derivation from its own bytes, bound to
    the corpus manifest pin (the plan's, or a fixture's in tests) and to the frozen policy."""
    manifest_sha256 = manifest_sha256 or fp.CORPUS_MANIFEST_SHA256
    if registry.get('status') != 'FROZEN_DRAWN' or len(registry.get('groups', [])) != len(GROUPS): raise ValueError('Registry status/count')
    if manifest_sha256 is None or registry.get('corpus_manifest_sha256') != manifest_sha256: raise ValueError('Registry is not bound to the frozen corpus manifest')
    if registry.get('policy_sha256') != POLICY_SHA256: raise ValueError('Registry is not bound to the frozen policy')
    if registry.get('fewepoch_registry_sha256') != fp.REGISTRY['registry_sha256'] or registry.get('fewepoch_partition_sha256') != fp.PARTITION_SHA256: raise ValueError('Registry is not bound to the few-epoch registry and partition')
    if registry.get('exclusions_sha256') != sha(exclusions_raw) or registry.get('draw_sha256') != sha(draw_raw): raise ValueError('Registry draw/exclusion hashes')
    excluded = json.loads(exclusions_raw)['values']
    partition_seed, groups, bench, decisions = derive(draw_raw, excluded)
    if (partition_seed != registry.get('partition_seed') or groups != registry['groups'] or bench != registry.get('benchmark')
            or decisions != registry.get('decisions')): raise ValueError('Registry differs from its re-derivation')
    values = [registry['partition_seed']]
    for g, row in zip(GROUPS, registry['groups']):
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
    if len(sys.argv) != 6 or sys.argv[1] != 'draw' or sys.argv[4] != '--approval-id':
        raise SystemExit('usage: peak_registry.py draw <registry_dir> <CORPUS_MANIFEST.json> --approval-id <OWNER-YYYYMMDD-...>')
    reg, digest = draw(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[5])
    print(json.dumps(dict(registry_sha256=digest, partition_seed=reg['partition_seed'], groups=reg['groups'], benchmark=reg['benchmark'], fresh_pool=reg['fresh_pool']), indent=1))
