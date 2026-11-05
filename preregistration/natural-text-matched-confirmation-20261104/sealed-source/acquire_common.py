"""Shared checks of the WikiText-103 acquisition steps (stdlib only): the sealed source, the approval id, targets and
records. Every refusal happens before the step writes anything."""
import hashlib, json, os, re, time
from pathlib import Path

import acquire_plan as ap

ROOT = Path('/mnt/d/sequence-weighting-research') if os.name == 'posix' else Path(r'D:\sequence-weighting-research')


def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(x): return (json.dumps(x, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
def utc(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def sha_file(p):
    h = hashlib.sha256(); n = 0
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk); n += len(chunk)
    return h.hexdigest(), n


def check_source(here, expected_subject):
    """The step runs only from the sealed acquisition source: SOURCE_SUBJECT.json must hash to the subject the owner
    approved, and every file it lists must be unchanged."""
    raw = (Path(here) / 'SOURCE_SUBJECT.json').read_bytes()
    if not expected_subject or sha(raw) != expected_subject: raise SystemExit('Acquisition source subject differs from the approved one; nothing written')
    subject = json.loads(raw)
    if subject.get('status') != 'SEALED' or subject.get('kind') != 'wikitext-103 acquisition source': raise SystemExit('Not the sealed acquisition source; nothing written')
    for row in subject['files']:
        b = (Path(here) / row['path']).read_bytes()
        if len(b) != row['bytes'] or sha(b) != row['sha256']: raise SystemExit('Changed acquisition source: ' + row['path'] + '; nothing written')
    return subject


def check_approval(approval_id, fixture, user_text=None):
    if fixture:
        if not str(approval_id).startswith('FIXTURE'): raise SystemExit('Fixture mode needs a FIXTURE approval id')
    elif not isinstance(approval_id, str) or approval_id.upper().startswith('FIXTURE') or not re.match(ap.APPROVAL_PATTERN, approval_id):
        raise SystemExit('An owner approval id (OWNER-YYYYMMDD-..., never FIXTURE) is required; nothing written')
    if user_text is not None and not user_text.strip(): raise SystemExit('The exact owner approval text is required; nothing written')
    return approval_id


def under_root(p, root=ROOT):
    p, r = Path(p).resolve(), Path(root).resolve()
    return p == r or r in p.parents


def place(fixture, given, real, root=ROOT):
    """Real mode: the bound path only (no override). Fixture mode: a target outside the project root."""
    if fixture:
        if given is None or under_root(given, root): raise SystemExit('Fixture mode needs a target outside the project root')
        return Path(given)
    if given is not None: raise SystemExit('Real mode writes only to its bound path')
    return Path(root) / real


def write_new(path, value):
    """An immutable record: written once, never overwritten."""
    with open(path, 'xb') as f: f.write(encoded(value)); f.flush(); os.fsync(f.fileno())
    return sha(Path(path).read_bytes())


def read_record(path, step, approval_id, subject):
    """A completed earlier step's record, bound to the same approval and the same sealed source."""
    path = Path(path)
    if not path.is_file(): raise SystemExit(f'{step} has not completed ({path.name} missing); nothing written')
    raw = path.read_bytes(); r = json.loads(raw)
    if r.get('step') != step or r.get('status') != 'COMPLETE': raise SystemExit(f'{step} record is not COMPLETE; nothing written')
    if r.get('approval_id') != approval_id or r.get('source_subject_sha256') != subject: raise SystemExit(f'{step} ran under another approval or source; nothing written')
    return r, sha(raw)
