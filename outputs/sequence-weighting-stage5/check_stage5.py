"""Outcome-independent selection/zero-path regression checks on synthetic histories."""
import argparse
import ast
import tempfile
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from stage5 import (HERE,ROOT,CAPS,VARIANTS,GRID,EPOCHS,TUNE,CONFIRM,tuning_schedule,
                    selection_key,select,write,utc,sha,SOURCES)


def checks():
    for p in HERE.glob('*.py'): ast.parse(p.read_text(encoding='utf-8'))
    assert len(tuning_schedule())==144 and len(TUNE)==2 and len(CONFIRM)==9
    assert {x[0] for x in TUNE}.isdisjoint(x[0] for x in CONFIRM)
    zero=dict(validation_nll=1.,epoch=0,lr=None,wd=None)
    early=dict(validation_nll=1.,epoch=1,lr=.00001,wd=.1)
    assert selection_key(zero)<selection_key(early)
    assert selection_key(dict(early,validation_nll=.999))<selection_key(zero)
    assert selection_key(early)<selection_key(dict(early,lr=.00003))
    assert selection_key(early)<selection_key(dict(early,wd=1.))
    # No training and no model/data outcome is used: all losses are fictitious.
    with tempfile.TemporaryDirectory(prefix='stage5-selection-',dir=ROOT/'work') as temp:
        root=Path(temp)
        for c in tuning_schedule():
            folder=root/'runs'/c['name']; folder.mkdir(parents=True)
            history=[dict(epoch=0,validation=dict(loss=2.))]
            for e in EPOCHS:
                # M: every adapted candidate worse. U: R selects g0/e1;
                # J selects g1/e3 due to uniform differences.
                loss=3.
                if c['variant']=='U' and c['grid_index']==0 and e==1:
                    loss=1. if c['arm']=='random' else 4.
                if c['variant']=='U' and c['grid_index']==1 and e==3:
                    loss=1.5 if c['arm']=='random' else 0.
                history.append(dict(epoch=e,validation=dict(loss=loss)))
            write(folder/'history.json',history)
        result=select(root)
        assert result['planned_confirmation']==108
        for w,l in CAPS:
            for policy in ['R','J']:
                z=result['decisions'][policy]['M'][str(w)]
                assert z['epoch']==0 and z['grid_index'] is None
                assert len(result['all_scores'][f'{policy}-M-{w}'])==37
            assert result['decisions']['R']['U'][str(w)]['grid_index']==0
            assert result['decisions']['R']['U'][str(w)]['epoch']==1
            assert result['decisions']['J']['U'][str(w)]['grid_index']==1
            assert result['decisions']['J']['U'][str(w)]['epoch']==3
        assert all(c['variant']=='U' for c in result['run_schedule'])
        assert len({c['name'] for c in result['run_schedule']})==108
        # Make no adaptation win everywhere, yielding zero confirmation adaptation.
        for c in tuning_schedule():
            path=root/'runs'/c['name']/'history.json'
            write(path,[dict(epoch=e,validation=dict(loss=2. if e==0 else 3.)) for e in [0]+EPOCHS])
        result=select(root)
        assert result['run_schedule']==[] and result['planned_confirmation']==0
        assert result['baseline_test_evaluations']==54
    return dict(status='PASS',utc=utc(),no_experimental_outcomes_used=True,
        checks=['all Python sources parse','fresh phase seeds','canonical zero candidate',
                'full precision/epoch/LR/WD tie rule','independent R/J winners from synthetic histories',
                'union deduplication and null config omission','all-zero selected policy retains 54 baseline tests'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); args=ap.parse_args()
    path=Path(args.output); assert not path.exists(), 'Preserve prior checks'
    result=checks(); result['source_sha256']={n:sha(HERE/n) for n in SOURCES}
    write(path,result); print(result,flush=True)
