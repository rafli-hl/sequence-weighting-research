"""Outcome-independent integration fixtures for the trajectory orchestration.

Uses known synthetic metric arrays and a one-parameter dummy model, not research
corpora or a GPU. Exercises real file/alias/checkpoint/selection boundaries.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch
import sys
sys.dont_write_bytecode = True
import torch
import stage11 as runner
from artifacts import write, read, sha, source_manifest


class Dummy(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scalar = torch.nn.Parameter(torch.tensor(0.))


class FixtureBudget:
    def check(self, storage=False):
        return 0.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    started = time.perf_counter()
    torch.set_num_threads(4)
    checks = []
    with tempfile.TemporaryDirectory(prefix='stage11-fixture-',dir=runner.ROOT/'work') as tmp:
        root = Path(tmp)
        write(root/'source_manifest.json',source_manifest())
        write(root/'SELECTION_FREEZE.json',{'fixture':True})
        (root/'assignments').mkdir()
        seed = 731991  # Fixture-only, not a research model/data seed.
        for arm in ['random','uniform']:
            w = torch.linspace(.1,1.9,512) if arm=='random' else torch.ones(512)
            torch.save({'weights':w,'orders':torch.arange(512).repeat(30,1)},root/'assignments'/f'{seed}-{arm}.pt')
        model = Dummy()
        starts,tests = [],[]
        def baseline(*unused):
            model.scalar.data.zero_()
            starts.append(float(model.scalar))
            return model,{'checkpoint_sha256':'fixture-baseline'}
        def dataset(unused_root, condition, unused_seed, splits):
            # Changed condition has a different own baseline; every config/arm
            # within condition receives byte-identical arrays.
            return {split:(torch.full((512,41),int(condition=='G1'),dtype=torch.long),
                           torch.zeros((512,40),dtype=torch.long)) for split in splits}
        def evaluate(m,ds):
            initial = 4. if int(ds[0][0,0]) else 5.
            value = initial-float(m.scalar)
            metrics = {'loss':value,**{k:{'loss':value,'accuracy':.5} for k in ['shared','group','instance']}}
            arrays = {'loss':torch.full((512,),value),'component_loss':torch.full((512,3),value),
                      'component_accuracy':torch.full((512,3),.5)}
            return metrics,arrays
        def train(m,*unused):
            m.scalar.data.add_(.001)
            return {'gradient_clip_fraction':.25,'gradient_norm_mean':.5,'gradient_norm_max':.75,'updates':16}
        cfg = dict(name='fixture-confirm-random',phase='confirmation',condition='G1',width=64,layers=2,
            data_seed=732991,seed=seed,pretrain_seed=733991,grid_index=runner.F_INDEX,
            lr=1e-4,wd=.1,clip=1.,arm='random')
        decisions = {'G1':{'64':dict(epoch=10,grid_index=runner.F_INDEX)}}
        with patch.object(runner,'pretrained',side_effect=baseline), \
             patch.object(runner,'load_data',side_effect=dataset), \
             patch.object(runner,'evaluate',side_effect=evaluate), \
             patch.object(runner,'train_epoch',side_effect=train), \
             patch.object(torch.cuda,'reset_peak_memory_stats'), \
             patch.object(torch.cuda,'synchronize'), \
             patch.object(torch.cuda,'max_memory_allocated',return_value=0), \
             patch.object(torch.cuda,'max_memory_reserved',return_value=0):
            runner.trajectory(root,cfg,FixtureBudget(),decisions)
            uniform = dict(cfg,name='fixture-confirm-uniform',arm='uniform')
            runner.trajectory(root,uniform,FixtureBudget(),decisions)
            tuning = dict(cfg,name='fixture-tuning-random',phase='tuning')
            runner.trajectory(root,tuning,FixtureBudget())
        assert starts == [0.,0.,0.]
        checks.append('All trajectories reset to one identical pretrained state')
        history = read(root/'runs'/cfg['name']/'history.json')
        assert [h['epoch'] for h in history] == [0]+runner.EPOCHS
        assert all('test' in h for h in history)
        assert all('test' not in h for h in read(root/'runs'/tuning['name']/'history.json'))
        checks.append('Confirmation test records at all declared checkpoints; tuning has no test metrics')
        retained = read(root/'runs'/cfg['name']/'retained_checkpoints.json')
        assert set(retained)=={'10','30'} and retained['10']['roles']==['F10','R']
        assert read(root/'runs'/uniform['name']/'history.json')[1]['fit']['reason']=='constant_weights'
        checks.append('F10/R identical checkpoint deduplicated; terminal retained; uniform fit undefined')
        assert len(list((root/'initial').iterdir()))==2
        config0 = read(root/'runs'/cfg['name']/'config.json')
        config1 = read(root/'runs'/uniform['name']/'config.json')
        for key in ['initial_alias','baseline_sha256','data_sha256','order_sha256']:
            assert config0[key]==config1[key]
        assert history[0]['fit']['reason']=='no_adaptation'
        checks.append('One canonical initial evaluation per condition/phase, with explicit no-adaptation')
        events = [json.loads(line) for line in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        assert sum(e['kind']=='initial_test_evaluation' for e in events)==1
        assert sum(e['kind']=='test_evaluation' for e in events)==12
        assert all('selection_sha256' in e for e in events if 'test_evaluation' in e['kind'])
        checks.append('Every test-evaluation event bound to the selection freeze')
    dependencies = ['stage11.py','artifacts.py','config.py','engine.py','policies.py',
                    'model.py','core.py','check_runner.py']
    write(args.output,dict(status='PASS',fixture_only=True,checks=checks,
        elapsed_seconds=time.perf_counter()-started,
        source_sha256={name:sha(runner.HERE/name) for name in dependencies}))
    print(json.dumps({'status':'PASS','checks':len(checks)}))


if __name__=='__main__':
    main()
