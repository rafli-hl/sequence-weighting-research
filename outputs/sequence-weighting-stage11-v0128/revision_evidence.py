"""Exact reuse audit and complete input equality; no model computations."""
import ast
from pathlib import Path
from config import ROOT, HERE
from artifacts import read, sha, bind, check_binding

OLD = ROOT/'outputs'/'sequence-weighting-stage11'
FAILED = ROOT/'work'/'runs'/'rule-tying-v012-20260930-01'
UNCHANGED = ['config.py','core.py','model.py','engine.py','policies.py',
             'analysis.py','artifacts.py','analyze_stage11.py','check_stage11.py',
             'check_analysis.py','check_runner.py','check_report.py',
             'benchmark_stage11.py','inventory_seeds.py','PROTOCOL_STAGE11.md',
             'IMPLEMENTATION_NOTES.md']


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def inside_binding(item, base):
    # One fresh target per invocation; both containment checks cover the
    # same pathname subsequently hashed and sized. Never cache across calls.
    path = (base/item['path']).resolve()
    require(path.is_relative_to(base.resolve()),
            'Input manifest escapes run: '+item['path'])
    require(path.is_relative_to(ROOT), 'Input manifest escapes project: '+item['path'])
    require(sha(path)==item['sha256'], 'Input manifest hash changed: '+item['path'])
    require(path.stat().st_size==item['bytes'], 'Input manifest size changed: '+item['path'])


def functions(path):
    return {n.name:n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}


def verify_reuse():
    review = read(OLD/'INDEPENDENT_REVIEW.json')
    require(review['status']=='PASS_IMPLEMENTATION_READY','Old review status')
    for name, digest in review['source_sha256'].items():
        require(sha(OLD/name)==digest,'Old source changed: '+name)
    for item in review['evidence']:
        check_binding(item)
    for name in UNCHANGED:
        require(sha(HERE/name)==review['source_sha256'][name],
                'Reused dependency changed: '+name)
    for name in ['PARENT_SOURCES.json','RESOURCE_ACCEPTANCE.json']:
        require(sha(HERE/name)==sha(OLD/name),'Inherited JSON changed: '+name)
    for item in read(HERE/'PARENT_SOURCES.json')['files']:
        require(sha(ROOT/item['parent_path'])==item['parent_sha256'],
                'Historical parent changed: '+item['parent_path'])
    before, after = functions(OLD/'stage11.py'), functions(HERE/'stage11.py')
    scientific = set(before)-{'freeze','run_path','run','main'}
    for name in scientific:
        require(ast.dump(before[name])==ast.dump(after[name]),
                'Scientific runner function changed: '+name)
    expected = before['run']
    expected.body.insert(1,ast.parse('assert_launchable(root)').body[0])
    require(ast.dump(expected)==ast.dump(after['run']),
            'Training entry changed beyond preparation launch guard')
    audit = read(OLD/'REVIEW_PREPARATION_FAILURE.json')
    require(audit['status']=='PASS_FAIL_CLOSED_PREPARATION_STOP','Old failure audit')
    for item in audit['evidence']:
        check_binding(item)
    for name in audit['absent_artifacts']:
        require(not (FAILED/name).exists(),'Failed run acquired research artifact: '+name)
    for name,digest in read(FAILED/'source_manifest.json').items():
        require(sha(FAILED/'source'/name)==digest,'Failed-run source changed: '+name)
    old_inputs = read(FAILED/'INPUT_MANIFEST.json')['files']
    for item in old_inputs:
        inside_binding(item,FAILED)
    return dict(status='PASS_EXACT_DEPENDENCY_REUSE',
        unchanged_source_sha256={n:sha(HERE/n) for n in UNCHANGED},
        scientific_runner_functions=sorted(scientific),
        training_entry_change='single preparation launch precondition',
        old_review=bind(OLD/'INDEPENDENT_REVIEW.json'),
        failure_review=bind(OLD/'REVIEW_PREPARATION_FAILURE.json'),
        old_inputs=bind(FAILED/'INPUT_MANIFEST.json'),
        old_evidence_count=len(review['evidence']),old_input_count=len(old_inputs),
        historical_accounting=read(OLD/'PREPARATION_ATTEMPTS.json'),
        historical_freeze_elapsed_seconds=None,
        historical_freeze_status='exceeded original cumulative 300-second cap')


def equal_nested(left, right, path='value'):
    import torch
    if isinstance(left,torch.Tensor):
        require(isinstance(right,torch.Tensor) and left.dtype==right.dtype
                and left.shape==right.shape and torch.equal(left,right),
                'Tensor inequality: '+path)
        return 1
    require(type(left) is type(right),'Type inequality: '+path)
    if isinstance(left,dict):
        require(left.keys()==right.keys(),'Key inequality: '+path)
        return sum(equal_nested(left[k],right[k],path+'/'+str(k)) for k in left)
    if isinstance(left,(list,tuple)):
        require(len(left)==len(right),'Length inequality: '+path)
        return sum(equal_nested(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(left,right)))
    require(left==right,'Value inequality: '+path)
    return 0


def compare_prepared(root, guard):
    import torch
    records=[]
    for item in read(FAILED/'INPUT_MANIFEST.json')['files']:
        relative=Path(item['path'])
        if relative.parts[0] not in {'corpora','assignments','support'}:
            continue
        guard.check('compare '+relative.as_posix())
        inside_binding(item,FAILED)
        prior,new=FAILED/relative,root/relative
        if prior.suffix=='.pt':
            count=equal_nested(torch.load(prior,weights_only=True),
                               torch.load(new,weights_only=True),relative.as_posix())
        else:
            count=equal_nested(read(prior),read(new),relative.as_posix())
        records.append(dict(path=relative.as_posix(),equal=True,tensor_count=count,
                            old=bind(prior),new=bind(new,root)))
    expected={p.relative_to(root).as_posix() for sub in ['corpora','assignments','support']
              for p in (root/sub).rglob('*') if p.is_file()}
    require({r['path'] for r in records}==expected,'Prepared input coverage mismatch')
    return dict(status='PASS_FULL_TENSOR_AND_METADATA_EQUALITY',files=records,
                tensor_count=sum(x['tensor_count'] for x in records),
                serialization_bytes_not_used_as_tensor_equality=True)
