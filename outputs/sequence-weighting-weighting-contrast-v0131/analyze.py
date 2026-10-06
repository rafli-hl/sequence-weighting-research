"""Read-only v0128 fixed-policy contrast; no model construction or inference."""
import argparse
import csv
import hashlib
import json
import math
import os
import resource
import shutil
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'work/runs/rule-tying-v0128-20261001-01'
OUT = HERE / 'results-fixed-policy-v0131-20261003-01'
CORPORA = {88547: 98201, 88771: 98202, 88993: 98203, 89203: 98204, 89431: 98205}
WIDTHS = {64: 2, 128: 3, 256: 4}
SEEDS = (150101, 150201)
CONDITIONS = ('G1', 'G16')
ARMS = ('random', 'uniform')
EPOCHS = (1, 3, 5, 10, 20, 30)
COMPONENTS = ('shared', 'group', 'instance')
MAX_SECONDS = 300
MAX_BYTES = 64 * 2**20
RECEIPT_RESERVE = 2 * 2**20
FREE_RESERVE = 2 * 2**30
ANCHORS = {
    'TRAINING_COMPLETE.json': '2485f828ab75d4b7731199c693b76cd3b71cca422f7ac31ea391723689a4436f',
    'source_manifest.json': '90a6f6838e36ff9e69bee9e32932cb606195cda2c2160ef251ea0a488e283b2a',
    'environment.json': 'f3a15779199e355fa132232268e48b02ccb1b187bd4845d8bd82856f954e3b4f',
}
AUDIT = ROOT / 'outputs/sequence-weighting-stage11-v0128/results-scientific-audit-v0128-r2-20261002-01/AUDIT_RESULT.json'
AUDIT_SHA = 'c12e570e56c0d96df8df689651ea69404da18725374780f3162b103e3ee99397'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in
            sorted(HERE.glob('*.py')) + sorted(HERE.glob('*.md'))}


def verify_source(approved):
    if len(approved) != 64 or sha(HERE / 'MANIFEST.txt') != approved.lower():
        raise RuntimeError('Independently approved manifest SHA256 required')
    lines = (HERE / 'MANIFEST.txt').read_text(encoding='utf-8-sig').splitlines()
    listed = {}
    for line in lines:
        if line.startswith('sha256 '):
            _, digest, rel = line.split(' ', 2)
            if rel in listed or len(digest) != 64:
                raise RuntimeError('Invalid source manifest')
            listed[rel] = digest
    if listed != source_hashes():
        raise RuntimeError('Source differs from approved manifest')
    for name, digest in ANCHORS.items():
        if sha(OLD / name) != digest:
            raise RuntimeError('Historical anchor drift: ' + name)
    if sha(AUDIT) != AUDIT_SHA or read(AUDIT)['trajectories'] != 212:
        raise RuntimeError('Historical audit drift')
    historical = read(OLD / 'source_manifest.json')
    for name, digest in historical.items():
        if sha(OLD / 'source' / name) != digest:
            raise RuntimeError('Historical frozen source drift: ' + name)
    if len(read(OLD / 'TRAINING_COMPLETE.json')['completed']) != 212:
        raise RuntimeError('Historical completion count drift')


def budget(start):
    if time.monotonic() - start >= MAX_SECONDS:
        raise RuntimeError('Five-minute analysis ceiling reached')
    if shutil.disk_usage(ROOT).free < FREE_RESERVE:
        raise RuntimeError('2-GiB free-space reserve reached')
    size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    if size + RECEIPT_RESERVE > MAX_BYTES:
        raise RuntimeError('64-MiB additional-output cap reached')


def binding(path, inventory):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError('Input path escapes project')
    rel = path.relative_to(ROOT).as_posix()
    digest = sha(path)
    size = path.stat().st_size
    if rel in inventory and inventory[rel] != {'sha256': digest, 'bytes': size}:
        raise RuntimeError('Input changed during analysis: ' + rel)
    inventory[rel] = {'sha256': digest, 'bytes': size}
    return path


def tensor_hash(*tensors):
    h = hashlib.sha256()
    for value in tensors:
        value = value.detach().cpu().contiguous()
        h.update(str((tuple(value.shape), str(value.dtype))).encode('utf-8'))
        h.update(value.numpy().tobytes())
    return h.hexdigest()


def finite(value):
    x = float(value)
    if not math.isfinite(x):
        raise FloatingPointError('Nonfinite saved value')
    return x


def mean(values):
    values = [finite(v) for v in values]
    if not values:
        raise ValueError('Empty mean')
    return math.fsum(values) / len(values)


def close(a, b, tolerance=2e-6):
    return abs(finite(a) - finite(b)) <= tolerance


def aggregate(rows, key):
    corpora = []
    for d in CORPORA:
        values = [r[key] for r in rows if r['data_seed'] == d]
        if len(values) != 2:
            raise RuntimeError('Incomplete nested corpus pair')
        corpora.append({'data_seed': d, 'seed_values': values, 'mean': mean(values)})
    means = [x['mean'] for x in corpora]
    return {'pairs': [{'data_seed': r['data_seed'], 'seed': r['seed'], 'value': r[key]} for r in rows],
            'corpora': corpora, 'mean': mean(means), 'sd': statistics.stdev(means),
            'range': [min(means), max(means)]}


def validate_metrics(history, arrays):
    for split in ('train', 'validation', 'test'):
        record = arrays[split]
        metric = history[split]
        if len(record['loss']) != {'train':512, 'validation':256, 'test':512}[split]:
            raise RuntimeError('Wrong saved split length')
        if not close(record['loss'].double().mean(), metric['loss']):
            raise RuntimeError('Saved total scalar/array mismatch')
        for i, component in enumerate(COMPONENTS):
            if not close(record['component_loss'][:, i].double().mean(), metric[component]['loss']):
                raise RuntimeError('Saved component scalar/array mismatch')
            if not close(record['component_accuracy'][:, i].double().mean(), metric[component]['accuracy']):
                raise RuntimeError('Saved accuracy scalar/array mismatch')
        if not close(record['component_loss'].double().mean(1).mean(), record['loss'].double().mean()):
            raise RuntimeError('Saved component/total arithmetic mismatch')


def figures(primary, components, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    labels = [str(d) for d in CORPORA]
    xs = range(5)
    axes[0].axhline(0, color='black', lw=.8)
    for i, row in enumerate(primary['corpora']):
        axes[0].plot([i, i], row['seed_values'], color='#93a8b6', lw=2)
        axes[0].scatter([i, i], row['seed_values'], color='#93a8b6', s=22)
        axes[0].scatter(i, row['mean'], color='#0b526d', s=50, zorder=3)
    axes[0].set_xticks(list(xs), labels)
    axes[0].set_title('G1 width 128, F10 paired test NLL')
    axes[0].set_ylabel('Random minus uniform (nats)')
    colors = {'shared':'#2379a3','group':'#dda15e','instance':'#7d4c86'}
    pos, neg = [0.]*5, [0.]*5
    for component in COMPONENTS:
        values = [row[component] for row in components]
        bottoms = [pos[i] if v >= 0 else neg[i] for i, v in enumerate(values)]
        axes[1].bar(list(xs), values, bottom=bottoms, color=colors[component], label=component)
        for i, value in enumerate(values):
            if value >= 0: pos[i] += value
            else: neg[i] += value
    axes[1].axhline(0, color='black', lw=.8)
    axes[1].set_xticks(list(xs), labels)
    axes[1].set_title('Test component contributions / 3')
    axes[1].legend(frameon=False)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--approved-manifest-sha256', required=True)
    args = parser.parse_args()
    if OUT.exists():
        raise RuntimeError('Unique output already exists; no resume/retry')
    start = time.monotonic()
    verify_source(args.approved_manifest_sha256)
    budget(start)
    OUT.mkdir(parents=True, exist_ok=False)
    try:
        import torch
        inputs, pairs = {}, []
        completed = set(read(OLD / 'TRAINING_COMPLETE.json')['completed'])
        historical_source = read(OLD / 'source_manifest.json')
        selection_sha = sha(binding(OLD / 'SELECTION_FREEZE.json', inputs))
        corpus_cache, assignment_cache, baseline_cache = {}, {}, {}
        for condition in CONDITIONS:
            for width, layers in WIDTHS.items():
                for data_seed, preseed in CORPORA.items():
                    for seed in SEEDS:
                        budget(start)
                        arms = {}
                        for arm in ARMS:
                            name = f'confirm-{condition}-w{width}-d{data_seed}-s{seed}-g02-{arm}'
                            if name not in completed:
                                raise RuntimeError('Missing historical completed arm: ' + name)
                            folder = OLD / 'runs' / name
                            paths = {k: binding(folder / v, inputs) for k, v in {
                                'config':'config.json', 'result':'result.json', 'history':'history.json',
                                'arrays':'sequence_losses.pt', 'retained':'retained_checkpoints.json'}.items()}
                            config, result = read(paths['config']), read(paths['result'])
                            if result['status'] != 'complete' or result['config'] != config or config['name'] != name:
                                raise RuntimeError('Historical result/config mismatch: ' + name)
                            if result['history_sha256'] != sha(paths['history']) or result['arrays_sha256'] != sha(paths['arrays']):
                                raise RuntimeError('Historical result binding mismatch: ' + name)
                            if config['source_sha256'] != historical_source or (config['width'],config['layers'],config['data_seed'],
                                    config['seed'],config['pretrain_seed'],config['grid_index'],config['arm'],config['lr'],
                                    config['wd'],config['clip']) != (width,layers,data_seed,seed,preseed,2,arm,1e-4,.1,1.):
                                raise RuntimeError('Nonfixed policy/source: ' + name)
                            if config['phase'] != 'confirmation' or config['selection_sha256'] != selection_sha:
                                raise RuntimeError('Historical selection binding mismatch')
                            retained = read(paths['retained'])
                            if 'F10' not in retained['10']['roles'] or sha(binding(folder / 'epoch-10.pt', inputs)) != retained['10']['sha256']:
                                raise RuntimeError('F10 role/binary mismatch: ' + name)
                            history = read(paths['history'])
                            arrays = torch.load(paths['arrays'], weights_only=True, map_location='cpu')
                            if [h['epoch'] for h in history] != [0,*EPOCHS] or [a['epoch'] for a in arrays] != [0,*EPOCHS]:
                                raise RuntimeError('Saved epoch inventory mismatch: ' + name)
                            for h, a in zip(history[1:], arrays[1:]):
                                validate_metrics(h, a)
                            arms[arm] = {'config':config,'history':history,'arrays':arrays}
                        cr, cu = arms['random']['config'], arms['uniform']['config']
                        shared_fields = ('condition','width','layers','data_seed','seed','pretrain_seed','phase','grid_index',
                                         'lr','wd','clip','baseline_sha256','data_sha256','order_sha256','initial_alias','source_sha256')
                        if any(cr[k] != cu[k] for k in shared_fields):
                            raise RuntimeError('Pair config/data/baseline/order mismatch')
                        baseline = OLD / 'baselines' / f'U-w{width}-s{seed}-d{preseed}' / 'pretrained.pt'
                        bkey = (width, seed, preseed)
                        if bkey not in baseline_cache:
                            bp = binding(baseline, inputs)
                            br = read(binding(baseline.parent / 'result.json', inputs))
                            if br['checkpoint_sha256'] != sha(bp): raise RuntimeError('U baseline mismatch')
                            baseline_cache[bkey] = sha(bp)
                        if cr['baseline_sha256'] != baseline_cache[bkey]:
                            raise RuntimeError('Pair U checkpoint mismatch')
                        ckey = (condition, data_seed)
                        if ckey not in corpus_cache:
                            corpus_cache[ckey] = {}
                            for split in ('train','validation','test'):
                                cp = binding(OLD / 'corpora' / f'{condition}-{data_seed}' / f'{split}.pt', inputs)
                                corpus_cache[ckey][split] = tensor_hash(*torch.load(cp, weights_only=True, map_location='cpu'))
                        if corpus_cache[ckey] != cr['data_sha256']:
                            raise RuntimeError('Complete data tensor mismatch')
                        assignments = {}
                        for arm in ARMS:
                            akey = (seed, arm)
                            if akey not in assignment_cache:
                                ap = binding(OLD / 'assignments' / f'{seed}-{arm}.pt', inputs)
                                assignment_cache[akey] = torch.load(ap, weights_only=True, map_location='cpu')
                            assignments[arm] = assignment_cache[akey]
                            if tensor_hash(assignments[arm]['weights']) != arms[arm]['config']['weight_sha256'] or (
                                    tensor_hash(assignments[arm]['orders']) != cr['order_sha256']):
                                raise RuntimeError('Assignment tensor mismatch')
                        if not torch.equal(assignments['random']['orders'], assignments['uniform']['orders']):
                            raise RuntimeError('Full batch-order pairing mismatch')
                        if not torch.all(assignments['uniform']['weights'] == 1):
                            raise RuntimeError('Uniform assignment changed')
                        w = assignments['random']['weights']
                        if len(w) != 512 or not torch.isfinite(w).all() or not (w > 0).all():
                            raise RuntimeError('Random assignment invalid')
                        alias = cr['initial_alias']
                        ip = binding(OLD / 'initial' / alias / 'sequence_losses.pt', inputs)
                        ir = read(binding(ip.parent / 'result.json', inputs))
                        if ir['arrays_sha256'] != sha(ip) or ir['baseline_sha256'] != cr['baseline_sha256']:
                            raise RuntimeError('Initial alias mismatch')
                        initial = torch.load(ip, weights_only=True, map_location='cpu')
                        if ir['data_sha256'] != cr['data_sha256']:
                            raise RuntimeError('Initial alias data mismatch')
                        for split in ('train','validation','test'):
                            for key in ('loss','component_loss','component_accuracy'):
                                if not torch.isfinite(initial[split][key]).all():
                                    raise FloatingPointError('Nonfinite initial array')
                        for epoch in EPOCHS:
                            index = EPOCHS.index(epoch) + 1
                            hr, hu = arms['random']['history'][index], arms['uniform']['history'][index]
                            ar, au = arms['random']['arrays'][index], arms['uniform']['arrays'][index]
                            total = mean(ar['test']['loss'].double().tolist()) - mean(au['test']['loss'].double().tolist())
                            component = {name: (mean(ar['test']['component_loss'][:,i].double().tolist()) -
                                                mean(au['test']['component_loss'][:,i].double().tolist()))/3
                                         for i,name in enumerate(COMPONENTS)}
                            if not close(total, math.fsum(component.values())):
                                raise RuntimeError('Paired test component arithmetic failed')
                            for split in ('train','validation','test'):
                                if not close(mean(ar[split]['loss'].double().tolist())-
                                             mean(au[split]['loss'].double().tolist()),
                                             hr[split]['loss']-hu[split]['loss']):
                                    raise RuntimeError('Paired scalar/array difference mismatch')
                            row = {'condition':condition,'width':width,'data_seed':data_seed,'seed':seed,'epoch':epoch,
                                   'test_random_minus_uniform':total,'test_component_contributions':component,
                                   'train_random_minus_uniform':hr['train']['loss']-hu['train']['loss'],
                                   'validation_random_minus_uniform':hr['validation']['loss']-hu['validation']['loss'],
                                   'random_metrics':{s:hr[s] for s in ('train','validation','test')},
                                   'uniform_metrics':{s:hu[s] for s in ('train','validation','test')},
                                   'random_fit_saved':hr['fit'],'uniform_fit_saved':hu['fit'],
                                   'random_clipped_fraction':hr['clipping'],'uniform_clipped_fraction':hu['clipping']}
                            if epoch == 10:
                                order = sorted(range(512), key=lambda i: (float(w[i]), i))
                                low, high = order[:128], order[-128:]
                                base = initial['train']['loss'].double()
                                random_gain = base-ar['train']['loss'].double()
                                uniform_gain = base-au['train']['loss'].double()
                                contrast = random_gain-uniform_gain
                                quartile_row = {
                                    'low':mean(contrast[low].tolist()),'high':mean(contrast[high].tolist()),
                                    'high_minus_low':mean(contrast[high].tolist())-mean(contrast[low].tolist()),
                                    'low_indices':low,'high_indices':high}
                                component_quartiles = {}
                                for i, name in enumerate(COMPONENTS):
                                    base_component = initial['train']['component_loss'][:,i].double()
                                    component_contrast = ((base_component-ar['train']['component_loss'][:,i].double())-
                                                          (base_component-au['train']['component_loss'][:,i].double()))
                                    low_mean = mean(component_contrast[low].tolist())
                                    high_mean = mean(component_contrast[high].tolist())
                                    component_quartiles[name] = {'low':low_mean,'high':high_mean,
                                                                 'high_minus_low':high_mean-low_mean}
                                for key in ('low','high','high_minus_low'):
                                    if not close(quartile_row[key],mean(component_quartiles[name][key] for name in COMPONENTS)):
                                        raise RuntimeError('Training quartile component identity failed')
                                quartile_row['components'] = component_quartiles
                                quartile_row['component_units'] = 'component training NLL nats, not divided by three'
                                row['quartile_train_gain_contrast'] = quartile_row
                            pairs.append(row)
        if len(pairs) != 360:
            raise RuntimeError('Expected 60 pairs x six epochs')
        primary = [r for r in pairs if r['condition']=='G1' and r['width']==128 and r['epoch']==10]
        if len(primary) != 10:
            raise RuntimeError('Primary pair count mismatch')
        estimate = aggregate(primary, 'test_random_minus_uniform')
        quartile = {key:aggregate([{'data_seed':r['data_seed'],'seed':r['seed'],key:r['quartile_train_gain_contrast'][key]}
                                   for r in primary],key)
                    for key in ('low','high','high_minus_low')}
        quartile['components'] = {
            name:{key:aggregate([{'data_seed':r['data_seed'],'seed':r['seed'],
                                   key:r['quartile_train_gain_contrast']['components'][name][key]}
                                  for r in primary],key)
                  for key in ('low','high','high_minus_low')}
            for name in COMPONENTS}
        quartile['component_units'] = 'component training NLL nats, not divided by three'
        for key in ('low','high','high_minus_low'):
            if not close(quartile[key]['mean'],mean(quartile['components'][name][key]['mean'] for name in COMPONENTS)):
                raise RuntimeError('Primary quartile summary component identity failed')
            for i, data_seed in enumerate(CORPORA):
                if not close(quartile[key]['corpora'][i]['mean'],
                             mean(quartile['components'][name][key]['corpora'][i]['mean'] for name in COMPONENTS)):
                    raise RuntimeError('Corpus quartile summary component identity failed')
        component_table = []
        for d in CORPORA:
            rows = [r for r in primary if r['data_seed']==d]
            cell = {'data_seed':d,'total':mean([r['test_random_minus_uniform'] for r in rows])}
            cell.update({name:mean([r['test_component_contributions'][name] for r in rows]) for name in COMPONENTS})
            if not close(cell['total'],math.fsum(cell[name] for name in COMPONENTS)):
                raise RuntimeError('Corpus component arithmetic failed')
            component_table.append(cell)
        summary = {'status':'EXPLORATORY_ANALYSIS_COMPLETE_PENDING_INDEPENDENT_RECONCILIATION',
                   'primary':estimate,'quartile_diagnostic':quartile,'component_table':component_table,
                   'secondary_pairs':60,'secondary_checkpoint_comparisons':360,
                   'interpretation':'positive primary means random weighting has higher test NLL; quartile association is not mediation',
                   'no_new_model_evaluation':True,'no_p_refit':True}
        budget(start)
        write(OUT/'INPUT_BINDINGS.json',{'approved_manifest_sha256':args.approved_manifest_sha256.lower(),
              'source_sha256':source_hashes(),'historical_anchors':ANCHORS,'audit_sha256':AUDIT_SHA,'files':inputs})
        write(OUT/'PAIRS.json',pairs)
        write(OUT/'SUMMARY.json',summary)
        with (OUT/'COMPONENT_TABLE.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=('data_seed','total',*COMPONENTS))
            writer.writeheader(); writer.writerows(component_table)
        figures(estimate, component_table, OUT/'PAIRED_FIGURE.png')
        write(OUT/'ANALYSIS_COMPLETE.json',{'utc':datetime.now(timezone.utc).isoformat(),
              'elapsed_seconds_before_receipt':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'pairs_sha256':sha(OUT/'PAIRS.json'),'summary_sha256':sha(OUT/'SUMMARY.json'),
              'inputs_sha256':sha(OUT/'INPUT_BINDINGS.json'),'component_table_sha256':sha(OUT/'COMPONENT_TABLE.csv'),
              'figure_sha256':sha(OUT/'PAIRED_FIGURE.png'),'paired_trajectories':60,'paired_checkpoints':360})
        budget(start)
        print('complete fixed-policy weighting contrast; 60 pairs, 360 checkpoint comparisons',flush=True)
    except BaseException as exc:
        (OUT/'ANALYSIS_COMPLETE.json').unlink(missing_ok=True)
        write(OUT/'FAILURE.json',{'error':repr(exc),'elapsed_seconds':time.monotonic()-start})
        raise


if __name__ == '__main__':
    main()
