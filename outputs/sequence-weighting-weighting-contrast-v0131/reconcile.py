"""Independent saved-array reconciliation of the v0131 derived analysis."""
import argparse
import csv
import hashlib
import json
import math
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
CORPORA = (88547,88771,88993,89203,89431)
SEEDS = (150101,150201)
WIDTHS = (64,128,256)
EPOCHS = (1,3,5,10,20,30)
COMPONENTS = ('shared','group','instance')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def near(a,b,tol=2e-6):
    a,b=float(a),float(b)
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol


def budget(start):
    if time.monotonic()-start>=300:
        raise RuntimeError('Five-minute independent reconciliation ceiling')
    if shutil.disk_usage(ROOT).free<2*2**30:
        raise RuntimeError('2-GiB free-space reserve')
    if sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())+2*2**20>64*2**20:
        raise RuntimeError('64-MiB additional-output cap')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--approved-manifest-sha256',required=True)
    args=parser.parse_args()
    start=time.monotonic()
    if (OUT/'RECONCILIATION.json').exists() or (OUT/'RECONCILIATION_FAILURE.json').exists():
        raise RuntimeError('Reconciliation already attempted; no automatic retry')
    if not (OUT/'ANALYSIS_COMPLETE.json').exists() or (OUT/'FAILURE.json').exists():
        raise RuntimeError('Complete analysis with no failure marker required')
    try:
        import torch
        inputs=read(OUT/'INPUT_BINDINGS.json')
        if sha(HERE/'MANIFEST.txt')!=args.approved_manifest_sha256.lower() or (
                inputs['approved_manifest_sha256']!=args.approved_manifest_sha256.lower()):
            raise RuntimeError('Approved source manifest mismatch')
        current={p.relative_to(ROOT).as_posix():sha(p) for p in
                 sorted(HERE.glob('*.py'))+sorted(HERE.glob('*.md'))}
        if current!=inputs['source_sha256']:
            raise RuntimeError('Analysis/reconciliation source drift')
        for rel,stored in inputs['files'].items():
            budget(start)
            path=(ROOT/rel).resolve()
            if not path.is_relative_to(ROOT) or sha(path)!=stored['sha256'] or path.stat().st_size!=stored['bytes']:
                raise RuntimeError('Frozen input drift: '+rel)
        completion=read(OUT/'ANALYSIS_COMPLETE.json')
        for filename,key in (('PAIRS.json','pairs_sha256'),('SUMMARY.json','summary_sha256'),
                             ('INPUT_BINDINGS.json','inputs_sha256'),('COMPONENT_TABLE.csv','component_table_sha256'),
                             ('PAIRED_FIGURE.png','figure_sha256')):
            if sha(OUT/filename)!=completion[key]:
                raise RuntimeError('Analysis output binding mismatch: '+filename)
        if completion['paired_trajectories']!=60 or completion['paired_checkpoints']!=360:
            raise RuntimeError('Wrong analysis coverage')
        pairs=read(OUT/'PAIRS.json')
        summary=read(OUT/'SUMMARY.json')
        if len(pairs)!=360:
            raise RuntimeError('Wrong pair row count')
        index={(r['condition'],r['width'],r['data_seed'],r['seed'],r['epoch']):r for r in pairs}
        if len(index)!=360:
            raise RuntimeError('Duplicate pair identity')
        checked=0
        quartile_checked=0
        primary=[]
        for condition in ('G1','G16'):
            for width in WIDTHS:
                for d in CORPORA:
                    for seed in SEEDS:
                        budget(start)
                        name=lambda arm:f'confirm-{condition}-w{width}-d{d}-s{seed}-g02-{arm}'
                        folder_r=OLD/'runs'/name('random')
                        folder_u=OLD/'runs'/name('uniform')
                        r=torch.load(folder_r/'sequence_losses.pt',weights_only=True,map_location='cpu')
                        u=torch.load(folder_u/'sequence_losses.pt',weights_only=True,map_location='cpu')
                        hr=read(folder_r/'history.json')
                        hu=read(folder_u/'history.json')
                        if [x['epoch'] for x in r]!=[0,*EPOCHS] or [x['epoch'] for x in u]!=[0,*EPOCHS]:
                            raise RuntimeError('Epoch inventory drift')
                        for e in EPOCHS:
                            k=(condition,width,d,seed,e)
                            if k not in index:
                                raise RuntimeError('Missing paired checkpoint')
                            row=index[k]
                            pos=EPOCHS.index(e)+1
                            rr,uu=r[pos],u[pos]
                            tr=rr['test']['loss'].double().tolist()
                            tu=uu['test']['loss'].double().tolist()
                            total=statistics.fmean(tr)-statistics.fmean(tu)
                            if not near(total,row['test_random_minus_uniform']):
                                raise RuntimeError('Raw test contrast disagreement')
                            components=[]
                            for i,c in enumerate(COMPONENTS):
                                rv=rr['test']['component_loss'][:,i].double().tolist()
                                uv=uu['test']['component_loss'][:,i].double().tolist()
                                value=(statistics.fmean(rv)-statistics.fmean(uv))/3
                                components.append(value)
                                if not near(value,row['test_component_contributions'][c]):
                                    raise RuntimeError('Raw component contrast disagreement')
                            if not near(total,sum(components)):
                                raise RuntimeError('Raw component identity disagreement')
                            for split in ('train','validation'):
                                value=statistics.fmean(rr[split]['loss'].double().tolist())-statistics.fmean(uu[split]['loss'].double().tolist())
                                if not near(value,row[split+'_random_minus_uniform']):
                                    raise RuntimeError('Raw '+split+' contrast disagreement')
                            if row['random_fit_saved']!=hr[pos]['fit'] or row['uniform_fit_saved']!=hu[pos]['fit']:
                                raise RuntimeError('Saved fit provenance disagreement')
                            checked+=1
                            if e==10:
                                weights=torch.load(OLD/'assignments'/f'{seed}-random.pt',weights_only=True,map_location='cpu')['weights']
                                rank=sorted(range(512),key=lambda i:(float(weights[i]),i))
                                if row['quartile_train_gain_contrast']['low_indices']!=rank[:128] or (
                                        row['quartile_train_gain_contrast']['high_indices']!=rank[-128:]):
                                    raise RuntimeError('Quartile membership disagreement')
                                # The common baseline cancels algebraically, but confirm its saved alias exists.
                                cr=read(folder_r/'config.json')
                                alias=OLD/'initial'/cr['initial_alias']/'sequence_losses.pt'
                                baseline_record=torch.load(alias,weights_only=True,map_location='cpu')['train']
                                baseline=baseline_record['loss'].double()
                                gain_r=baseline-rr['train']['loss'].double()
                                gain_u=baseline-uu['train']['loss'].double()
                                diff=gain_r-gain_u
                                low=statistics.fmean(diff[rank[:128]].tolist())
                                high=statistics.fmean(diff[rank[-128:]].tolist())
                                q=row['quartile_train_gain_contrast']
                                if not (near(low,q['low']) and near(high,q['high']) and near(high-low,q['high_minus_low'])):
                                    raise RuntimeError('Quartile gain contrast disagreement')
                                if q['component_units']!='component training NLL nats, not divided by three':
                                    raise RuntimeError('Quartile component units changed')
                                component_quartiles={}
                                for i,c in enumerate(COMPONENTS):
                                    baseline_component=baseline_record['component_loss'][:,i].double()
                                    component_gain_r=baseline_component-rr['train']['component_loss'][:,i].double()
                                    component_gain_u=baseline_component-uu['train']['component_loss'][:,i].double()
                                    component_diff=component_gain_r-component_gain_u
                                    c_low=statistics.fmean(component_diff[rank[:128]].tolist())
                                    c_high=statistics.fmean(component_diff[rank[-128:]].tolist())
                                    component_quartiles[c]={'low':c_low,'high':c_high,'high_minus_low':c_high-c_low}
                                    if any(not near(component_quartiles[c][key],q['components'][c][key])
                                           for key in ('low','high','high_minus_low')):
                                        raise RuntimeError('Quartile component gain disagreement')
                                for key,total_value in (('low',low),('high',high),('high_minus_low',high-low)):
                                    if not near(total_value,statistics.fmean(component_quartiles[c][key] for c in COMPONENTS)):
                                        raise RuntimeError('Quartile component identity disagreement')
                                quartile_checked+=1
                                if condition=='G1' and width==128:
                                    primary.append((d,seed,total,components,low,high,component_quartiles))
        if checked!=360 or quartile_checked!=60 or len(primary)!=10:
            raise RuntimeError('Incomplete reconciliation')
        def check_quartile_aggregate(node, values):
            expected={(d,s):value for d,s,value in values}
            if len(expected)!=10 or len(node['pairs'])!=10 or len(node['corpora'])!=5:
                raise RuntimeError('Quartile summary coverage mismatch')
            seen=set()
            for row in node['pairs']:
                pair=(row['data_seed'],row['seed'])
                if pair in seen or pair not in expected or not near(row['value'],expected[pair]):
                    raise RuntimeError('Quartile summary pair mismatch')
                seen.add(pair)
            corpus_values=[]
            for i,d in enumerate(CORPORA):
                row=node['corpora'][i]
                nested=[expected[d,s] for s in SEEDS]
                if row['data_seed']!=d or len(row['seed_values'])!=2 or (
                        any(not near(row['seed_values'][j],nested[j]) for j in range(2))):
                    raise RuntimeError('Quartile summary corpus membership mismatch')
                value=statistics.fmean(nested)
                if not near(row['mean'],value):
                    raise RuntimeError('Quartile summary corpus mean mismatch')
                corpus_values.append(value)
            if not (near(node['mean'],statistics.fmean(corpus_values)) and
                    near(node['sd'],statistics.stdev(corpus_values)) and
                    near(node['range'][0],min(corpus_values)) and
                    near(node['range'][1],max(corpus_values))):
                raise RuntimeError('Quartile summary descriptive statistics mismatch')
        qsummary=summary['quartile_diagnostic']
        if qsummary['component_units']!='component training NLL nats, not divided by three':
            raise RuntimeError('Quartile summary component units changed')
        for key in ('low','high','high_minus_low'):
            total_values=[(x[0],x[1],x[4] if key=='low' else x[5] if key=='high' else x[5]-x[4])
                          for x in primary]
            check_quartile_aggregate(qsummary[key],total_values)
            for component in COMPONENTS:
                component_values=[(x[0],x[1],x[6][component][key]) for x in primary]
                check_quartile_aggregate(qsummary['components'][component][key],component_values)
            for i,d in enumerate(CORPORA):
                if not near(qsummary[key]['corpora'][i]['mean'],
                            statistics.fmean(qsummary['components'][c][key]['corpora'][i]['mean'] for c in COMPONENTS)):
                    raise RuntimeError('Quartile summary corpus component identity mismatch')
            if not near(qsummary[key]['mean'],
                        statistics.fmean(qsummary['components'][c][key]['mean'] for c in COMPONENTS)):
                raise RuntimeError('Quartile summary global component identity mismatch')
        corpus_means=[]
        for d in CORPORA:
            rows=[x for x in primary if x[0]==d]
            if len(rows)!=2:
                raise RuntimeError('Incomplete primary corpus')
            value=statistics.fmean(x[2] for x in rows)
            reported=next(x for x in summary['primary']['corpora'] if x['data_seed']==d)
            if not near(value,reported['mean']):
                raise RuntimeError('Corpus mean mismatch')
            component_row=next(x for x in summary['component_table'] if x['data_seed']==d)
            if not near(value,component_row['total']):
                raise RuntimeError('Component table total mismatch')
            for i,c in enumerate(COMPONENTS):
                if not near(statistics.fmean(x[3][i] for x in rows),component_row[c]):
                    raise RuntimeError('Component table part mismatch')
            corpus_means.append(value)
        if not near(statistics.fmean(corpus_means),summary['primary']['mean']) or (
                not near(statistics.stdev(corpus_means),summary['primary']['sd'])) or (
                not near(min(corpus_means),summary['primary']['range'][0])) or (
                not near(max(corpus_means),summary['primary']['range'][1])):
            raise RuntimeError('Primary descriptive summary mismatch')
        with (OUT/'COMPONENT_TABLE.csv').open(encoding='utf-8',newline='') as f:
            csv_rows=list(csv.DictReader(f))
        if len(csv_rows)!=5:
            raise RuntimeError('Component CSV row count mismatch')
        for item in csv_rows:
            reported=next(x for x in summary['component_table'] if x['data_seed']==int(item['data_seed']))
            if any(not near(float(item[k]),reported[k]) for k in ('total',*COMPONENTS)):
                raise RuntimeError('Component CSV mismatch')
        budget(start)
        write(OUT/'RECONCILIATION.json',{'status':'CANDIDATE_INDEPENDENT_RECONCILIATION_PASS_PENDING_OUTPUT_REVIEW',
              'utc':datetime.now(timezone.utc).isoformat(),'paired_checkpoints':checked,
              'f10_quartile_pairs':quartile_checked,'primary_pairs':len(primary),
              'primary_mean':statistics.fmean(corpus_means),'analysis_completion_sha256':sha(OUT/'ANALYSIS_COMPLETE.json'),
              'elapsed_seconds_before_receipt':time.monotonic()-start,
              'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'no_training_or_model_evaluation':True,'no_p_refit':True})
        budget(start)
        print('complete independent reconciliation; 360 paired checkpoints',flush=True)
    except BaseException as exc:
        (OUT/'RECONCILIATION.json').unlink(missing_ok=True)
        write(OUT/'RECONCILIATION_FAILURE.json',{'status':'NONPASSING','error':repr(exc),
              'elapsed_seconds':time.monotonic()-start})
        raise


if __name__=='__main__':
    main()
