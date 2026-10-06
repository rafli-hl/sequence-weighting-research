"""Local JSON, provenance and resource guards for the new Stage 11 run."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from datetime import datetime, timezone
from config import ROOT, HERE, TRAIN_SECONDS, NEW_STORAGE_BYTES, FREE_RESERVE_BYTES


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def bind(path, base=ROOT):
    path = Path(path).resolve()
    return dict(path=path.relative_to(base).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def check_binding(item, base=ROOT):
    path = (base / item['path']).resolve()
    assert path.is_relative_to(ROOT), path
    assert sha(path) == item['sha256'], path
    assert path.stat().st_size == item['bytes'], path


def source_manifest():
    return {p.name: sha(p) for p in sorted(HERE.iterdir())
            if p.is_file() and p.suffix in {'.py', '.md'}}


def event(root, kind, **details):
    with (root/'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(utc=utc(), kind=kind, **details), allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


class Budget:
    def __init__(self, root, archive_reserve=256*2**20):
        self.root = root
        self.start = time.perf_counter()
        self.start_utc = datetime.now(timezone.utc)
        self.archive_reserve = archive_reserve
        self.sources = read(root/'source_manifest.json')
        self.last_storage = 0

    def check(self, storage=False):
        elapsed = max(time.perf_counter()-self.start,
                      (datetime.now(timezone.utc)-self.start_utc).total_seconds())
        if elapsed > TRAIN_SECONDS:
            raise RuntimeError('Shared 5400-second training-stage budget exhausted')
        if shutil.disk_usage(ROOT).free < FREE_RESERVE_BYTES:
            raise RuntimeError('2 GiB free-space reserve reached')
        if storage:
            if source_manifest() != self.sources:
                raise RuntimeError('Frozen source drift')
            self.last_storage = sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
            if self.last_storage + self.archive_reserve > NEW_STORAGE_BYTES:
                raise RuntimeError('Raw run plus reserved compact archive exceeds 4 GiB')
        return elapsed
