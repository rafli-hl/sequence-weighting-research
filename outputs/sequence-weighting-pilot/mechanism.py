"""Staged local experiments implementing PROTOCOL_STAGE1.md."""
import argparse
import copy
import hashlib
import json
import math
import platform
import random
import time
from pathlib import Path

import torch
from core import make_data_lists, exponent
from pilot import Model, losses, TYPES

HERE = Path(__file__).resolve().parent
CHECKPOINTS = [1, 3, 10, 30, 60, 120]


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def data(seed, regime, pretrain=False, include_test=False):
    raw, meta = make_data_lists(seed, regime, 2048 if pretrain else 512, 256,
                                512 if include_test else 0)
    allkeys = {}
    for name, (rows, _) in raw.items():
        # Same token marginals, disjoint combinations, without a phase token.
        # Permute all 32^3 keys once, then use nonoverlapping slices.
        pool = random.Random(991).sample(range(32**3), 32**3)
        namespace = 0 if pretrain and name == 'train' else 1 if name == 'train' else 2 if name == 'validation' else 3
        if pretrain and name == 'validation':
            pool = pool[4096:8192]
        else:
            pool = pool[namespace*8192:(namespace+1)*8192]
        keys = random.Random(seed + 77).sample(pool, len(rows))
        allkeys[name] = keys
        for row, key in zip(rows, keys):
            row[2:5] = [17 + key//1024, 17 + key//32 % 32, 17 + key % 32]
    # Pretraining training keys use first half of its namespace, validation second.
    if pretrain:
        pool = random.Random(991).sample(range(32**3), 32**3)[:4096]
        allkeys['train'] = random.Random(seed + 77).sample(pool, len(raw['train'][0]))
        for row, key in zip(raw['train'][0], allkeys['train']):
            row[2:5] = [17 + key//1024, 17 + key//32 % 32, 17 + key % 32]
    meta['sequence_keys_by_split'] = allkeys
    meta.pop('sequence_keys')
    meta['namespace_scheme'] = 'fixed permutation, disjoint phase slices'
    return {name: tuple(torch.tensor(x, dtype=torch.long) for x in pair)
            for name, pair in raw.items() if len(pair[0])}, meta


@torch.no_grad()
def evaluate(model, dataset):
    model.eval()
    total, component, accuracy = [], [], []
    for start in range(0, len(dataset[0]), 32):
        tokens, kinds = (x[start:start+32].cuda() for x in dataset)
        sl, tl, correct = losses(model, tokens, kinds)
        total.append(sl.cpu())
        comp, acc = [], []
        for j in range(3):
            mask = kinds == j
            count = mask.sum(1).clamp_min(1)
            comp.append(((tl*mask).sum(1)/count).cpu())
            acc.append(((correct*mask).sum(1)/count).cpu())
        component.append(torch.stack(comp, 1))
        accuracy.append(torch.stack(acc, 1))
    seq, comp, acc = torch.cat(total), torch.cat(component), torch.cat(accuracy)
    metrics = {'loss':float(seq.mean())}
    for j, typ in enumerate(TYPES):
        if (dataset[1] == j).any():
            metrics[typ] = {'loss':float(comp[:, j].mean()), 'accuracy':float(acc[:, j].mean())}
    return metrics, seq, comp, acc


def train_epoch(model, optimizer, dataset, weights, seed, epoch, clip):
    model.train()
    order = torch.randperm(len(weights), generator=torch.Generator().manual_seed(999+seed+epoch))
    norms = []
    for ids in order.split(32):
        tokens, kinds = (x[ids].cuda() for x in dataset)
        sl, _, _ = losses(model, tokens, kinds)
        loss = (sl * weights[ids].cuda()).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), math.inf if clip is None else clip)
        if not torch.isfinite(loss) or not torch.isfinite(norm):
            raise RuntimeError('Non-finite loss/gradient')
        optimizer.step()
        norms.append(float(norm))
    return {'gradient_norm_mean':sum(norms)/len(norms),
            'gradient_clip_fraction':0 if clip is None else sum(x>clip for x in norms)/len(norms)}


def baseline(root, width, layers, seed, preseed):
    folder = root / 'baselines' / f'w{width}-l{layers}-s{seed}-d{preseed}'
    checkpoint = folder / 'states.pt'
    model = Model(width, layers, 40).cuda()
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        model.load_state_dict(saved['pretrained'])
        return model, saved, json.loads((folder/'result.json').read_text())
    folder.mkdir(parents=True)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    model = Model(width, layers, 40).cuda()
    cold = {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    ds, meta = data(preseed, 'shared', pretrain=True)
    opt = torch.optim.AdamW(model.parameters(), lr=.0003, weight_decay=.1)
    history = []
    for epoch in range(1,5):
        stats = train_epoch(model,opt,ds['train'],torch.ones(2048),seed,epoch,5)
        val = evaluate(model,ds['validation'])[0]
        history.append({'epoch':epoch,'validation':val,**stats})
    saved = {'cold':cold,'pretrained':{k:v.detach().cpu().clone() for k,v in model.state_dict().items()}}
    torch.save(saved,checkpoint)
    result = {'width':width,'layers':layers,'seed':seed,'data_seed':preseed,
              'history':history,'data':meta,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest()}
    write(folder/'result.json',result)
    print(f'PRETRAIN w={width} seed={seed} shared-val={val["shared"]["accuracy"]:.3f}',flush=True)
    return model,saved,result


def run(root, name, width, layers, seed, dseed, preseed, regime, lr, clip, epochs,
        weighting='random', cold=False, test=False):
    folder = root/'runs'/name
    if (folder/'result.json').exists():
        return json.loads((folder/'result.json').read_text())
    if folder.exists():
        raise RuntimeError(f'Incomplete run needs a new name: {folder}')
    folder.mkdir(parents=True)
    model, states, pre = baseline(root,width,layers,seed,preseed)
    ds, meta = data(dseed,regime,include_test=test)
    prekeys = set(sum(pre['data']['sequence_keys_by_split'].values(),[]))
    allkeys = sum(meta['sequence_keys_by_split'].values(),[])
    assert len(set(allkeys)) == len(allkeys) and prekeys.isdisjoint(allkeys)
    model.load_state_dict(states['cold'])
    random_initial = evaluate(model,ds['train'])
    if not cold:
        model.load_state_dict(states['pretrained'])
    initial = evaluate(model,ds['train'])
    val_initial = evaluate(model,ds['validation'])[0]
    rng = random.Random(1000+seed)
    w = torch.tensor([math.exp(rng.uniform(math.log(.01),math.log(10))) for _ in range(512)])
    if weighting == 'uniform': w.fill_(1)
    w /= w.mean()
    optimizer = torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=.1)
    config = dict(name=name,width=width,layers=layers,seed=seed,data_seed=dseed,
                  pretrain_seed=preseed,regime=regime,lr=lr,clip=clip,epochs=epochs,
                  weighting=weighting,cold=cold,test_evaluated=test,weight_decay=.1,
                  parameters=sum(p.numel() for p in model.parameters()),
                  baseline_sha256=pre['checkpoint_sha256'],
                  source_sha256={p:hashlib.sha256((HERE/p).read_bytes()).hexdigest()
                                 for p in ['mechanism.py','pilot.py','core.py']})
    write(folder/'config.json',config)
    write(folder/'data.json',meta)
    torch.save({'weights':w,'data':ds},folder/'data.pt')
    history = [{'epoch':0,'train':initial[0],'validation':val_initial}]
    records = [{'epoch':0,'loss':initial[1],'component_loss':initial[2]}]
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    start = time.perf_counter()
    for epoch in range(1,epochs+1):
        stats = train_epoch(model,optimizer,ds['train'],w,seed,epoch,clip)
        if epoch not in CHECKPOINTS and epoch != epochs: continue
        current = evaluate(model,ds['train'])
        val = evaluate(model,ds['validation'])[0]
        gain = initial[1]-current[1]
        fit = exponent(w.tolist(),gain.tolist())
        order = w.argsort()
        bins = [ids.tolist() for ids in order.tensor_split(5)]
        item = {'epoch':epoch,'train':current[0],'validation':val,'p_star':fit,
                'p_from_random_baseline':exponent(w.tolist(),(random_initial[1]-current[1]).tolist()),
                'negative_gain_fraction':float((gain<0).float().mean()),
                'weight_quintiles':[{'weight_mean':float(w[ids].mean()),
                    'gain_mean':float(gain[ids].mean()),
                    'instance_accuracy':float(current[3][ids,2].mean()) if regime=='mixed' else None}
                    for ids in bins],**stats}
        history.append(item)
        records.append({'epoch':epoch,'loss':current[1],'component_loss':current[2]})
        write(folder/'history.json',history)
    final_test = evaluate(model,ds['test'])[0] if test else None
    torch.cuda.synchronize()
    result = {'config':config,'history':history,'final_test':final_test,
              'pretrain_validation':pre['history'][-1]['validation'],
              'elapsed_seconds':time.perf_counter()-start,
              'peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20,
              'peak_reserved_mib':torch.cuda.max_memory_reserved()/2**20}
    torch.save({'weights':w,'random_initial_loss':random_initial[1],
                'checkpoints':records},folder/'sequence_losses.pt')
    torch.save({k:v.detach().cpu() for k,v in model.state_dict().items()},folder/'model.pt')
    write(folder/'result.json',result)
    print(f'DONE {name}: val={val["loss"]:.4f} p={fit["p"]} instance-train={current[0].get("instance",{}).get("accuracy")} seconds={result["elapsed_seconds"]:.1f}',flush=True)
    return result


def validate():
    pre,pm = data(9001,'shared',True)
    mix,mm = data(1729,'mixed',include_test=True)
    shared,sm = data(1729,'shared',include_test=True)
    keys = sum(pm['sequence_keys_by_split'].values(),[]) + sum(mm['sequence_keys_by_split'].values(),[])
    assert len(keys)==len(set(keys))
    for name in mix:
        assert torch.equal(mix[name][0][:,:5],shared[name][0][:,:5])
        assert torch.equal(mix[name][0][:,6::3],shared[name][0][:,6::3])
        assert mix[name][1].shape[1]==40
    _, without_test = data(1729,'mixed')
    assert mm['sequence_keys_by_split']['train']==without_test['sequence_keys_by_split']['train']
    assert mm['sequence_keys_by_split']['validation']==without_test['sequence_keys_by_split']['validation']
    print('PASS: disjoint pretrain/adaptation/validation/test keys, paired interventions, stable splits',flush=True)


def calibrate(root):
    candidates = []
    for lr in [.0001,.0003,.001]:
        for clip in [1,5,None]:
            results = []
            for weighting in ['random','uniform']:
                name=f'cal-lr{lr}-clip{clip}-{weighting}'
                results.append(run(root,name,128,3,42,1729,9001,'mixed',lr,clip,30,weighting))
            candidates.append({'lr':lr,'clip':clip,'validation_nll':sum(r['history'][-1]['validation']['loss'] for r in results)/2,
                               'runs':[r['config']['name'] for r in results]})
    choice = min(candidates,key=lambda x:x['validation_nll'])
    write(root/'selection.json',{'criterion':'mean final validation NLL of random/uniform arms at epoch 30',
                                'candidates':candidates,'selected':choice,'test_used':False})
    print('SELECTED '+json.dumps(choice),flush=True)
    extended = []
    for weighting in ['random','uniform']:
        extended.append(run(root,'duration-'+weighting,128,3,42,1729,9001,'mixed',choice['lr'],choice['clip'],120,weighting))
    run(root,'duration-cold-random',128,3,42,1729,9001,'mixed',choice['lr'],choice['clip'],120,cold=True)
    uniform = extended[1]
    passing = [h['epoch'] for h in uniform['history'] if h['epoch'] in [30,60,120]
               and h['train']['shared']['accuracy']>=.95 and h['train']['group']['accuracy']>=.4
               and h['train']['instance']['accuracy']>=.25]
    ready = bool(passing) and uniform['pretrain_validation']['shared']['accuracy']>=.95
    frozen = {'ready':ready,'lr':choice['lr'],'clip':choice['clip'],
              'epochs':min(passing) if ready else None,'confirmation_data_seed':2718,
              'training_seeds':[42,43,44],'capacities':[[64,2],[128,3],[256,4]],
              'test_used_for_selection':False,'gate':'pretraining shared>=95%; uniform train shared>=95%, group>=40%, instance>=25%'}
    write(root/'frozen.json',frozen)
    print('FROZEN '+json.dumps(frozen),flush=True)


def confirm(root):
    frozen=json.loads((root/'frozen.json').read_text())
    if not frozen['ready']:
        print('Confirmation deferred: learnability gate did not pass.',flush=True)
        return
    for width,layers in frozen['capacities']:
        for seed in frozen['training_seeds']:
            for regime in ['shared','structured','mixed']:
                run(root,f'confirm-w{width}-s{seed}-{regime}',width,layers,seed,2718,9002,regime,
                    frozen['lr'],frozen['clip'],frozen['epochs'],test=True)
            if width==128:
                run(root,f'confirm-w128-s{seed}-mixed-uniform',width,layers,seed,2718,9002,'mixed',
                    frozen['lr'],frozen['clip'],frozen['epochs'],'uniform',test=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('stage',choices=['validate','calibrate','confirm'])
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    if not torch.cuda.is_available(): raise RuntimeError('Local CUDA required')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.stage=='validate': validate(); return
    write(args.output/'runtime.json',{'torch':torch.__version__,'python':platform.python_version(),
                                     'gpu':torch.cuda.get_device_name(0),'precision':'float32'})
    {'calibrate':calibrate,'confirm':confirm}[args.stage](args.output)


if __name__=='__main__': main()
