"""Outcome-independent panel selection checks using only fictitious losses."""
import argparse
import ast
import tempfile
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from stage6 import (HERE,ROOT,CAPS,VARIANTS,GRID,EPOCHS,PANELS,TUNE,CONFIRM,
                    tuning_schedule,selection_key,select,write,utc,sha,SOURCES)


def checks():
    for path in HERE.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'))
    schedule=tuning_schedule()
    assert len(schedule)==576 and len(PANELS)==4 and len(TUNE)==8 and len(CONFIRM)==9
    for pos in range(3):
        assert len({x[pos] for x in TUNE})==8
        assert {x[pos] for x in TUNE}.isdisjoint(x[pos] for x in CONFIRM)
    zero=dict(validation_nll=1.,epoch=0,lr=None,wd=None)
    early=dict(validation_nll=1.,epoch=1,lr=.00001,wd=.1)
    assert selection_key(zero)<selection_key(early)
    assert selection_key(dict(early,validation_nll=.999))<selection_key(zero)
    assert selection_key(early)<selection_key(dict(early,lr=.00003))
    assert selection_key(early)<selection_key(dict(early,wd=1.))
    with tempfile.TemporaryDirectory(prefix='stage6-selection-',dir=ROOT/'work') as temp:
        root=Path(temp)
        for c in schedule:
            folder=root/'runs'/c['name']; folder.mkdir(parents=True)
            offset=list(PANELS).index(c['panel'])
            history=[dict(epoch=0,validation=dict(loss=2.))]
            for epoch in EPOCHS:
                loss=3.
                if c['variant']=='U' and c['grid_index']==offset and epoch==1:
                    loss=1. if c['arm']=='random' else 4.
                if c['variant']=='U' and c['grid_index']==offset+1 and epoch==3:
                    loss=1.5 if c['arm']=='random' else 0.
                history.append(dict(epoch=epoch,validation=dict(loss=loss)))
            write(folder/'history.json',history)
        result=select(root)
        assert result['planned_confirmation']==270  # five unique U grids, not eight panel choices
        for panel in PANELS:
            offset=list(PANELS).index(panel)
            for width,_ in CAPS:
                for policy in ['R','J']:
                    z=result['decisions'][panel][policy]['M'][str(width)]
                    assert z['epoch']==0 and z['grid_index'] is None
                    assert len(result['all_scores'][f'{panel}-{policy}-M-{width}'])==37
                r=result['decisions'][panel]['R']['U'][str(width)]
                j=result['decisions'][panel]['J']['U'][str(width)]
                assert (r['grid_index'],r['epoch'])==(offset,1)
                assert (j['grid_index'],j['epoch'])==(offset+1,3)
        assert all(c['variant']=='U' and c['panel'] is None for c in result['run_schedule'])
        assert len({c['name'] for c in result['run_schedule']})==270
        for c in schedule:
            path=root/'runs'/c['name']/'history.json'
            write(path,[dict(epoch=e,validation=dict(loss=2. if e==0 else 3.)) for e in [0]+EPOCHS])
        result=select(root)
        assert result['run_schedule']==[] and result['planned_confirmation']==0
        assert result['baseline_test_evaluations']==54
    return dict(status='PASS',utc=utc(),no_experimental_outcomes_used=True,
        checks=['all Python sources parse','fresh disjoint panel/phase seeds','canonical zero candidate',
                'full precision/epoch/LR/WD tie rule','panel-isolated R/J winners on fictitious histories',
                'cross-panel union deduplicates repeated configurations','all-zero policy retains 54 initial tests'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); args=ap.parse_args()
    path=Path(args.output); assert not path.exists(),'Preserve prior checks'
    result=checks(); result['source_sha256']={n:sha(HERE/n) for n in SOURCES}
    write(path,result); print(result,flush=True)
