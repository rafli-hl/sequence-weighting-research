"""Report only completed staged experiment records; no fabricated curves."""
import argparse
import csv
import json
import statistics as st
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import torch


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    selection=json.loads((args.root/'selection.json').read_text())
    frozen=json.loads((args.root/'frozen.json').read_text())
    runs=[json.loads(p.read_text()) for p in sorted((args.root/'runs').glob('*/result.json'))]
    byname={r['config']['name']:r for r in runs}
    confirm=[r for r in runs if r['config']['name'].startswith('confirm-') and r['config']['weighting']=='random']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for clip in [1,5,None]:
        cs=[c for c in selection['candidates'] if c['clip']==clip]
        ax.plot([c['lr'] for c in cs],[c['validation_nll'] for c in cs],marker='o',label=f'clip={clip}')
    ax.set(xscale='log',xlabel='Learning rate',ylabel='Mean validation NLL (nats/answer)',
           title='Calibration: paired random/uniform mean at epoch 30')
    ax.legend(); ax.grid(alpha=.2)
    fig.savefig(out/'calibration.png',dpi=160); plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for name,label,color in [('duration-random','pretrained, random weights','#1f77b4'),('duration-uniform','pretrained, uniform','#ff7f0e'),('duration-cold-random','cold start, random weights','#2ca02c')]:
        r=byname[name]; hs=r['history']
        ps=[h for h in hs if h.get('p_star',{}).get('p') is not None]
        if ps: axes[0].plot([h['epoch'] for h in ps],[h['p_star']['p'] for h in ps],marker='o',label=label,color=color)
        axes[1].plot([h['epoch'] for h in hs],[h['train']['instance']['accuracy']*100 for h in hs],marker='o',label=label,color=color)
        axes[2].plot([h['epoch'] for h in hs],[h['validation']['loss'] for h in hs],marker='o',label=label,color=color)
    for ax in axes: ax.set_xlabel('Epoch'); ax.grid(alpha=.2)
    axes[0].set(title='Training gain exponent',ylabel='p*',ylim=(0,None))
    axes[1].set(title='Instance training accuracy',ylabel='Accuracy (%)',ylim=(0,105))
    axes[1].axhline(6.25,color='grey',ls='--')
    axes[2].set(title='Validation answer loss',ylabel='NLL (nats/answer)')
    axes[2].legend(fontsize=7)
    fig.savefig(out/'duration-diagnostics.png',dpi=160); plt.close(fig)

    # Fit diagnostics retain signed gains, matching the original estimator.
    record=torch.load(args.root/'runs/duration-random/sequence_losses.pt',map_location='cpu',weights_only=True)
    fig,ax=plt.subplots(figsize=(7,4),layout='constrained')
    weights=record['weights'].double(); order=weights.argsort(); baseline=record['checkpoints'][0]['loss'].double()
    for ck in record['checkpoints'][1:]:
        gain=baseline-ck['loss'].double()
        if gain.sum()<=0: continue
        p=next(h['p_star']['p'] for h in byname['duration-random']['history'] if h['epoch']==ck['epoch'])
        ranks=torch.arange(1,len(weights)+1)/len(weights)
        line=ax.plot(ranks,(gain[order]/gain.sum()).cumsum(0),label=f'epoch {ck["epoch"]}')[0]
        predicted=weights[order].pow(p); predicted/=predicted.sum()
        ax.plot(ranks,predicted.cumsum(0),color=line.get_color(),ls='--',alpha=.65)
    ax.set(xlabel='Sequence rank by increasing weight',ylabel='Cumulative normalized gain',title='Measured allocation (solid), fitted weight exponent (dashed)')
    ax.legend(ncol=2,fontsize=8); ax.grid(alpha=.2)
    fig.savefig(out/'gain-fit.png',dpi=160); plt.close(fig)

    contrasts=[]
    reproducible=[]
    if confirm:
        widths=sorted({r['config']['width'] for r in confirm})
        epochs=[h['epoch'] for h in confirm[0]['history'][1:]]
        fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
        upper=1.15*max(h['p_star'].get('p') or 0 for r in confirm for h in r['history'][1:])
        for ax,regime in zip(axes,['shared','structured','mixed']):
            for epoch in epochs:
                means=[]; spreads=[]; params=[]
                for width in widths:
                    rs=[r for r in confirm if r['config']['regime']==regime and r['config']['width']==width]
                    vals=[next(h for h in r['history'] if h['epoch']==epoch)['p_star'].get('p') for r in rs]
                    vals=[v for v in vals if v is not None]
                    means.append(st.mean(vals) if vals else float('nan'))
                    spreads.append(st.stdev(vals) if len(vals)>1 else 0)
                    params.append(rs[0]['config']['parameters']/1e6)
                ax.errorbar(params,means,yerr=spreads,marker='o',capsize=2,label=f'epoch {epoch}')
            ax.set(xscale='log',xlabel='Parameters (millions)',ylabel='p*',title=regime,ylim=(0,upper))
            ax.grid(alpha=.2)
        axes[-1].legend(fontsize=7)
        fig.suptitle('Fresh-data confirmation: mean ± seed SD (3 seeds; not confidence intervals)')
        fig.savefig(out/'capacity-curves.png',dpi=160); plt.close(fig)
        for regime in ['shared','structured','mixed']:
            for epoch in epochs:
                for middle in widths[1:-1]:
                    seed_diffs=[]
                    component_pass=[]
                    for seed in frozen['training_seeds']:
                        group=sorted([r for r in confirm if r['config']['regime']==regime and r['config']['seed']==seed],key=lambda r:r['config']['width'])
                        hs=[next(h for h in r['history'] if h['epoch']==epoch) for r in group]
                        vals=[h['p_star'].get('p') for h in hs]
                        j=widths.index(middle)
                        if any(v is None for v in vals):
                            seed_diffs.append(None); component_pass.append(False); continue
                        seed_diffs.append(vals[j]-max(vals[0],vals[-1]))
                        component_pass.append(regime=='mixed' and hs[-1]['train']['instance']['accuracy']>=.25
                            and hs[-1]['train']['instance']['accuracy']>hs[0]['train']['instance']['accuracy']
                            and all(h['train']['shared']['accuracy']>=.95 for h in hs))
                    peak=all(v is not None and v>0 for v in seed_diffs)
                    entry={'regime':regime,'epoch':epoch,'interior_width':middle,
                           'paired_interior_minus_max_endpoint':seed_diffs,'peak_in_all_seeds':peak,
                           'component_transition_in_all_seeds':all(component_pass)}
                    contrasts.append(entry)
                    if peak: reproducible.append(entry)

    rows=[]
    for r in runs:
        c=r['config']
        for h in r['history'][1:]:
            rows.append({**{k:c[k] for k in ['name','width','layers','parameters','seed','data_seed','regime','weighting','cold','lr','clip']},
                         'epoch':h['epoch'],'p_star':h['p_star'].get('p'),
                         'p_from_random_baseline':h['p_from_random_baseline'].get('p'),
                         'train_nll':h['train']['loss'],'validation_nll':h['validation']['loss'],
                         'instance_train_accuracy':h['train'].get('instance',{}).get('accuracy'),
                         'instance_validation_accuracy':h['validation'].get('instance',{}).get('accuracy'),
                         'clip_fraction_at_checkpoint_epoch':h['gradient_clip_fraction'],
                         'negative_gain_fraction':h['negative_gain_fraction']})
    with (out/'all-checkpoints.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    gate=any(e['peak_in_all_seeds'] and e['component_transition_in_all_seeds'] for e in contrasts)
    summary={'selected':selection['selected'],'frozen':frozen,'completed_runs':len(runs),
             'confirmation_runs':len([r for r in runs if r['config']['name'].startswith('confirm-')]),
             'reproducible_interior_peaks':reproducible,'contrasts':contrasts,
             'external_text_gate_passed':gate,
             'training_evaluation_seconds':sum(r['elapsed_seconds'] for r in runs),
             'max_allocated_mib':max(r['peak_allocated_mib'] for r in runs),
             'max_reserved_mib':max(r['peak_reserved_mib'] for r in runs),
             'limitations':['3 seeds only; SD is not a confidence interval','one fresh confirmation dataset seed',
                            'fixed weight decay, not fully tuned heavy regularization','synthetic shared-only pretraining',
                            'three capacities permit only one interior peak location; epoch movement to a boundary is not a demonstrated shift between interior peaks']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
