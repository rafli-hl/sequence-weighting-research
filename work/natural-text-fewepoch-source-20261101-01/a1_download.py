"""A1: download the two WikiText-103 raw training parquet files (native Windows, stdlib). Owner-run, under the owner's
approval of the acquisition; the only step that uses the network.

  python.exe -I -B a1_download.py --approval-id <ID> --user-text <TEXT> --expected-subject <SUBJECT>

Each file is fetched from its pinned URL (dataset revision b08601e0...) into dataset/<name>.part, its byte count and SHA-256
are checked against the pins in acquire_plan.py, and only then is it renamed into place. A file whose size or hash differs,
or whose download fails or is interrupted by Ctrl+C, is kept as <name>.failed-<k> with A1_FAILED-<k>.json, and nothing is
renamed; a failed download is not a scientific outcome, and the same command may be run again while A1_RECORD.json does not
exist (review 1, finding 4). A part file left by an interruption that could not be recorded (a closed console, power loss,
a killed process) is kept as <name>.failed-<k> with a late record at the start of the next run, which then proceeds
(confirmation of review 1, N1). On success the approval id, the exact approval text and every pin are recorded in
A1_RECORD.json. Fixture mode (tests only) needs a FIXTURE id, a target outside the project root and a local base URL.
"""
import argparse, hashlib, json, os, platform, sys, urllib.request
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import acquire_plan as ap
import acquire_common as ac

USER_AGENT = 'sequence-weighting-research-acquisition/1 (owner-run; pinned revision)'


def url_for(name, base_url=None):
    if base_url is None: return ap.URL.format(dataset=ap.DATASET, revision=ap.REVISION, config=ap.CONFIG, name=name)
    return base_url.rstrip('/') + '/' + name


def fetch(url, part, expected_bytes, timeout=60, opener=urllib.request.urlopen):
    """Stream `url` into `part` (created new), never past the pinned size. Returns (bytes, sha256)."""
    h = hashlib.sha256(); n = 0
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with opener(request, timeout=timeout) as response, open(part, 'xb') as f:
        while True:
            block = response.read(1 << 20)
            if not block: break
            n += len(block)
            if n > expected_bytes: raise ValueError(f'more than the pinned {expected_bytes} bytes')
            h.update(block); f.write(block)
        f.flush(); os.fsync(f.fileno())
    return n, h.hexdigest()


def run(approval_id, user_text, expected_subject, fixture=False, target=None, base_url=None, here=HERE, root=ac.ROOT, fetcher=fetch):
    ac.check_approval(approval_id, fixture, user_text)
    if base_url is not None and not fixture: raise SystemExit('Real mode downloads only from the pinned URLs; nothing written')
    if fixture and base_url is None: raise SystemExit('Fixture mode needs a local base URL')
    ac.check_source(here, expected_subject)
    assets = ac.place(fixture, target, ap.ASSETS, root); ds = assets / 'dataset'
    meta_raw = (Path(root) / ap.METADATA[0]).read_bytes()
    if ac.sha(meta_raw) != ap.METADATA[1]: raise SystemExit('The saved dataset metadata differs from its pin; nothing written')
    if (assets / 'A1_RECORD.json').exists(): raise SystemExit('A1 has already completed; no second download')
    for d in ap.DOWNLOADS:
        if (ds / d['name']).exists(): raise SystemExit('A dataset file exists without an A1 record; preserve it and report; nothing written')
    ds.mkdir(parents=True, exist_ok=True)
    k = len(list(assets.glob('A1_FAILED-*.json'))) + 1
    left = [d['name'] for d in ap.DOWNLOADS if (ds / (d['name'] + '.part')).exists()]
    if left:                                                            # an unrecorded interruption (confirmation of review 1, N1)
        for nm in left: os.replace(ds / (nm + '.part'), ds / f'{nm}.failed-{k}')
        ac.write_new(assets / f'A1_FAILED-{k}.json', dict(step='A1', status='FAILED', approval_id=approval_id, problem='part file(s) left by an interruption that was not recorded at the time',
                                                         kept=[f'{nm}.failed-{k}' for nm in left], recorded_late=True, recorded_utc=ac.utc()))
        k += 1
    failed = sorted(p.name for p in assets.glob('A1_FAILED-*.json'))
    started = ac.utc(); files = []
    for d in ap.DOWNLOADS:
        url = url_for(d['name'], base_url); part = ds / (d['name'] + '.part')
        error = None
        try:
            n, h = fetcher(url, part, d['bytes'])
            problem = None if (n, h) == (d['bytes'], d['sha256']) else f'got {n} bytes, sha256 {h}; pinned {d["bytes"]} bytes, sha256 {d["sha256"]}'
        except BaseException as e:                                     # an interruption is recorded too, then re-raised (review 1, finding 4)
            problem = f'{type(e).__name__}: {str(e)[:300]}'; error = e
        if problem is not None:
            kept = []
            for e in ap.DOWNLOADS:                                     # every part file of this attempt is kept, none is renamed into place
                p = ds / (e['name'] + '.part')
                if p.exists(): os.replace(p, ds / f"{e['name']}.failed-{k}"); kept.append(f"{e['name']}.failed-{k}")
            ac.write_new(assets / f'A1_FAILED-{k}.json', dict(step='A1', status='FAILED', approval_id=approval_id, file=d['name'], url=url, problem=problem,
                                                             kept=kept, verified_before_failure=[f['name'] for f in files], interrupted=error is not None and not isinstance(error, Exception),
                                                             started_utc=started, failed_utc=ac.utc()))
            if error is not None and not isinstance(error, Exception): raise error
            raise SystemExit(f"A1 FAILED on {d['name']}: {problem}. Nothing further was downloaded. The same command may be run again; earlier files are kept.")
        files.append(dict(name=d['name'], url=url, bytes=n, sha256=h))
    for d in ap.DOWNLOADS: os.replace(ds / (d['name'] + '.part'), ds / d['name'])          # renamed only after every file matched its pin
    record = dict(step='A1', status='COMPLETE', approval_id=approval_id, user_text=user_text, fixture=bool(fixture), source_subject_sha256=expected_subject,
                  dataset=ap.DATASET, config=ap.CONFIG, revision=ap.REVISION, license=ap.LICENSE, metadata=dict(path=ap.METADATA[0], sha256=ac.sha(meta_raw)),
                  files=files, failed_attempts=failed, started_utc=started, finished_utc=ac.utc(), python=platform.python_version(), platform=platform.platform(),
                  assistant_must_not_launch=True)
    digest = ac.write_new(assets / 'A1_RECORD.json', record)
    return dict(record, record_sha256=digest)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--approval-id', required=True); p.add_argument('--user-text', required=True); p.add_argument('--expected-subject', required=True)
    p.add_argument('--fixture', action='store_true'); p.add_argument('--target'); p.add_argument('--base-url')
    a = p.parse_args()
    r = run(a.approval_id, a.user_text, a.expected_subject, a.fixture, Path(a.target) if a.target else None, a.base_url)
    print(json.dumps(dict(status=r['status'], files=r['files'], record_sha256=r['record_sha256']), indent=1))
