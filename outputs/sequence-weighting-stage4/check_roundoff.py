"""Validate versioned numerical repair on the failure and paired control records."""
import ast
import sys
sys.dont_write_bytecode=True
import torch
from engine import ROOT,HERE,read,write,sha,utc
from diagnostics import decompose as original
from diagnostics_roundoff import decompose as repaired

for path in HERE.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'))
root=ROOT/'work/runs/baseline-v05-20260929-01'
checks=[]
for name,epoch,expected_failure in [
    ('confirm-U-w256-d46219-s603-g02-random',3,True),
    ('confirm-S-w64-d41843-s601-g00-random',30,False),
    ('confirm-U-w256-d46219-s603-g02-uniform',3,False)]:
    rec=torch.load(root/'runs'/name/'sequence_losses.pt',weights_only=True)
    cp=next(x for x in rec['checkpoints'] if x['epoch']==epoch)
    new=repaired(rec['weights'],rec['checkpoints'][0]['train'],cp['train'])
    result=read(root/'runs'/name/'result.json')
    assert new['primary']==next(h['p_star'] for h in result['history'] if h['epoch']==epoch)
    try:
        old=original(rec['weights'],rec['checkpoints'][0]['train'],cp['train'])
    except AssertionError:
        assert expected_failure
        assert not new['allocation']['gram_identity_check']['original_strict_pass']
        assert new['allocation']['gram_identity_check']['decimal_identity_error']<1e-50
    else:
        assert not expected_failure
        new['allocation'].pop('gram_identity_check',None)
        assert new==old
    checks.append(dict(name=name,epoch=epoch,original_strict_failure=expected_failure,primary_unchanged=True))
write(HERE/'NUMERICAL_CHECKS.json',dict(status='PASS',utc=utc(),checks=checks,
    source_sha256={n:sha(HERE/n) for n in ['diagnostics.py','diagnostics_roundoff.py','analyze_stage4_r1.py','check_roundoff.py']}))
print('PASS: 70-digit identity, unchanged primary fit, identical control diagnostics and uniform handling',flush=True)
