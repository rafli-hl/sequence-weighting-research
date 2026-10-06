"""Timed, fail-closed v0.12.8 entry point. Starts before heavy imports."""
import time
START_MONO = time.perf_counter()
START_WALL = time.time()
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from preparation import Preparation, assert_launchable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path):
    path=path.resolve()
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=digest(path),bytes=path.stat().st_size)


def planned_inputs(names):
    from config import TUNE, CONFIRM, CONDITIONS, ARMS
    paths=['source/'+n for n in names]
    paths+=['source_manifest.json','environment.json','design.json','tuning_schedule.json',
            'DEPENDENCY_REUSE.json','INPUT_EQUALITY.json','INPUT_MANIFEST.json']
    for d in sorted({d for d,s,p in TUNE+CONFIRM}):
        for condition in CONDITIONS:
            paths += [f'corpora/{condition}-{d}/{n}' for n in
                      ['train.pt','validation.pt','test.pt','metadata.json']]
    for p in sorted({p for d,s,p in TUNE+CONFIRM}):
        paths += [f'corpora/U-{p}/{n}' for n in ['train.pt','validation.pt','metadata.json']]
    for s in sorted({s for d,s,p in TUNE+CONFIRM}):
        paths += [f'assignments/{s}-{arm}.pt' for arm in ARMS+['pretrain']]
    paths += [f'support/{condition}-d{d}-s{s}-{arm}.json'
              for d,s,p in TUNE+CONFIRM for condition in CONDITIONS for arm in ARMS]
    return sorted(set(paths))


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('freeze');p.add_argument('--run-id',required=True);p.add_argument('--review',required=True)
    p=sub.add_parser('run');p.add_argument('--run-id',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'rule-tying-v0128-[a-zA-Z0-9-]+',args.run_id):
        raise ValueError('Use a new rule-tying-v0128-* run ID')
    root=ROOT/'work'/'runs'/args.run_id
    if args.command=='run':
        assert_launchable(root,source_root=HERE,evidence_root=ROOT)
        from stage11 import run
        run(args)
        return
    root.mkdir(parents=True,exist_ok=False)
    guard=Preparation(root,START_MONO,START_WALL,limit=180,source_root=HERE,evidence_root=ROOT)
    try:
        guard.check('source snapshot and planned artifacts')
        sources=[p for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in {'.py','.md'}]
        guard.planned=planned_inputs([p.name for p in sources])
        for path in sources:
            guard.source_sha256[path.name]=digest(path)
        review_path=Path(args.review).resolve()
        guard.evidence=[binding(review_path)]
        review=json.loads(review_path.read_text(encoding='utf-8-sig'))
        guard.evidence += review.get('evidence',[])
        guard.metadata_capture_complete=True
        guard.check('heavy imports')
        from stage11 import prepare_inputs
        payload=prepare_inputs(args,root,guard)
        receipt=guard.finish(payload)
    except BaseException as exc:
        if not (root/'PREPARATION_FAILURE.json').exists():
            guard.failure(exc)
        raise
    print(json.dumps(dict(status='FROZEN_NOT_RUN',run=str(root),
        receipt_elapsed_seconds=receipt['elapsed_seconds'],
        postwrite_checkpoint=str(root/'PREPARATION_CHECKPOINT.json'))),flush=True)


if __name__=='__main__':
    main()
