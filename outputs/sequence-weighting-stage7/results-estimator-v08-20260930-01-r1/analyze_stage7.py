"""Frozen CPU estimator-validity summaries; undefined outcomes are retained."""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import statistics as st
import sys
import time
import traceback
import zipfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
GROUP_FIELDS=['family','n','truth_p','generator_p','sigma','scale','c','control']
SCALES=[1.,1e-8,1e-14]
P_VALUES=[0.,.2,1.,4.]
SIGMAS=[0.,.5,2.,8.]
REPLICATES=64


def utc(): return datetime.now(timezone.utc).isoformat()


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def write(path,value): path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def quantile(values,probability):
    if not values: return None
    values=sorted(values); index=(len(values)-1)*probability; lower=int(math.floor(index)); upper=int(math.ceil(index))
    return values[lower]+(values[upper]-values[lower])*(index-lower)


def conditional_stats(values):
    values=list(values); assert all(math.isfinite(v) for v in values)
    return dict(n=len(values),mean=st.mean(values) if values else None,
        sd=st.stdev(values) if len(values)>1 else None,
        minimum=min(values) if values else None,maximum=max(values) if values else None,
        quantiles={str(q):quantile(values,q) for q in [.05,.25,.5,.75,.95]})


def summarize_group(rows,expected_replicates=REPLICATES):
    assert len(rows)==expected_replicates and len({r['replicate'] for r in rows})==expected_replicates
    condition={k:rows[0].get(k) for k in GROUP_FIELDS}
    assert all({k:r.get(k) for k in GROUP_FIELDS}==condition for r in rows)
    defined=[r for r in rows if r['p'] is not None]; undefined=[r for r in rows if r['p'] is None]
    assert all(r['reason'] is None and r['objective'] is not None for r in defined)
    assert all(r['reason'] is not None and r['objective'] is None for r in undefined)
    truth=condition['truth_p']; has_truth=truth is not None; eligible=has_truth and 0<=truth<=8
    estimates=[r['p'] for r in defined]; errors=[r['p']-truth for r in defined] if eligible else []
    error_stats=conditional_stats(errors)
    error_stats.update(bias=st.mean(errors) if errors else None,
        rmse=math.sqrt(st.mean(x*x for x in errors)) if errors else None,
        mae=st.mean(abs(x) for x in errors) if errors else None,
        truth_available=has_truth,recovery_eligible=eligible)
    misspecification=[r['p']-truth for r in defined] if has_truth and not eligible else []
    misspec_stats=conditional_stats(misspecification)
    misspec_stats.update(bias=st.mean(misspecification) if misspecification else None,
        rmse=math.sqrt(st.mean(x*x for x in misspecification)) if misspecification else None,
        mae=st.mean(abs(x) for x in misspecification) if misspecification else None)
    valid_all=eligible and not undefined
    digest=hashlib.sha256(json.dumps(condition,sort_keys=True).encode('utf-8')).hexdigest()[:16]
    return dict(group_id=digest,condition=condition,total=len(rows),defined=len(defined),undefined=len(undefined),
        undefined_by_reason=dict(sorted(Counter(r['reason'] for r in undefined).items())),
        undefined_rate=len(undefined)/len(rows),
        lower_boundary_count=sum(r['at_lower_bound'] for r in defined),
        upper_boundary_count=sum(r['at_upper_bound'] for r in defined),
        lower_boundary_rate_all=sum(r['at_lower_bound'] for r in defined)/len(rows),
        upper_boundary_rate_all=sum(r['at_upper_bound'] for r in defined)/len(rows),
        lower_boundary_rate_defined=sum(r['at_lower_bound'] for r in defined)/len(defined) if defined else None,
        upper_boundary_rate_defined=sum(r['at_upper_bound'] for r in defined)/len(defined) if defined else None,
        conditional_estimate=conditional_stats(estimates),conditional_error=error_stats,
        conditional_misspecification_error=misspec_stats,
        unconditional_recovery_mean=st.mean(estimates) if valid_all else None,
        unconditional_recovery_rmse=math.sqrt(st.mean(x*x for x in errors)) if valid_all else None,
        unconditional_recovery_reason=None if valid_all else 'no_identifiable_truth' if not has_truth else 'outside_search_interval' if not eligible else 'contains_undefined_fits',
        truth_relation='not_applicable' if not has_truth else 'outside_search_interval' if truth>8 or truth<0 else 'within_search_interval',
        conditional_objective=conditional_stats([r['objective'] for r in defined]),
        conditional_cancellation=conditional_stats([r['cancellation_ratio'] for r in defined if r['cancellation_ratio'] is not None]),
        all_available_cancellation=conditional_stats([r['cancellation_ratio'] for r in rows if r['cancellation_ratio'] is not None]),
        cancellation_undefined=sum(r['cancellation_ratio'] is None for r in rows),
        total_gain=conditional_stats([r['total_gain'] for r in rows]),
        total_gain_fsum=conditional_stats([r['total_gain_fsum'] for r in rows]),
        total_gain_sum_minus_fsum=conditional_stats([r['total_gain']-r['total_gain_fsum'] for r in rows]),
        guard_positive_undefined_count=sum(r['reason']=='nonpositive_total_gain' and 0<r['total_gain']<=1e-10 for r in rows),
        guard_nonpositive_undefined_count=sum(r['reason']=='nonpositive_total_gain' and r['total_gain']<=0 for r in rows),
        negative_gain_fraction=conditional_stats([r['negative_gain_fraction'] for r in rows]),
        fit_seconds=conditional_stats([r['fit_seconds'] for r in rows]),
        block_ids=[r['block_id'] for r in sorted(rows,key=lambda r:r['replicate'])])


def summarize(rows,expected_replicates=REPLICATES):
    grouped=defaultdict(list)
    for row in rows: grouped[tuple(row.get(k) for k in GROUP_FIELDS)].append(row)
    summaries=[summarize_group(group,expected_replicates) for group in grouped.values()]
    return sorted(summaries,key=lambda x:json.dumps(x['condition'],sort_keys=True))


def scale_comparisons(rows,expected_replicates=REPLICATES):
    blocks=defaultdict(dict)
    for row in rows:
        if row['family']=='recovery':
            key=(row['block_id'],row['n'],row['replicate'],row['truth_p'],row['sigma'])
            assert row['scale'] not in blocks[key]
            blocks[key][row['scale']]=row
    pairs=[]
    for key,scales in sorted(blocks.items(),key=lambda item:str(item[0])):
        assert set(scales)==set(SCALES)
        reference=scales[1.]
        assert len({r['weights_sha256'] for r in scales.values()})==1
        assert len({(r['seed_weights'],r['seed_noise']) for r in scales.values()})==1
        for scale in SCALES[1:]:
            target=scales[scale]; both=reference['p'] is not None and target['p'] is not None
            pairs.append(dict(block_id=key[0],n=key[1],replicate=key[2],truth_p=key[3],sigma=key[4],
                reference_scale=1.,scale=scale,reference_id=reference['id'],target_id=target['id'],
                reference_p=reference['p'],target_p=target['p'],reference_reason=reference['reason'],target_reason=target['reason'],
                both_defined=both,absolute_p_difference=abs(reference['p']-target['p']) if both else None))
    grouped=defaultdict(list)
    for row in pairs: grouped[row['n'],row['truth_p'],row['sigma'],row['scale']].append(row)
    comparisons=[]
    for key,group in sorted(grouped.items()):
        assert len(group)==expected_replicates and len({r['replicate'] for r in group})==expected_replicates
        differences=[r['absolute_p_difference'] for r in group if r['both_defined']]
        comparisons.append(dict(n=key[0],truth_p=key[1],sigma=key[2],scale=key[3],reference_scale=1.,
            total_pairs=len(group),both_defined=len(differences),any_undefined=len(group)-len(differences),
            reference_undefined=sum(r['reference_p'] is None for r in group),target_undefined=sum(r['target_p'] is None for r in group),
            reference_guard_count=sum(r['reference_reason']=='nonpositive_total_gain' for r in group),
            target_guard_count=sum(r['target_reason']=='nonpositive_total_gain' for r in group),
            conditional_absolute_difference=conditional_stats(differences),
            unconditional_absolute_difference_mean=st.mean(differences) if len(differences)==len(group) else None,
            unconditional_reason=None if len(differences)==len(group) else 'contains_undefined_pair',
            paired_records=group))
    return comparisons,pairs


def flatten_summary(group):
    row=dict(group['condition'],group_id=group['group_id'])
    for key,value in group.items():
        if key in ['condition','group_id','block_ids']: continue
        if not isinstance(value,dict): row[key]=value; continue
        for sub,item in value.items():
            if isinstance(item,dict):
                for name,number in item.items(): row[f'{key}_{sub}_{name}']=number
            else: row[f'{key}_{sub}']=item
    row['undefined_by_reason_json']=json.dumps(group['undefined_by_reason'],sort_keys=True)
    return row


def csvwrite(path,rows):
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader(); writer.writerows(rows)


def fmt(value): return 'undefined' if value is None else f'{value:.6g}'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def figures(out,summaries,comparisons,raw_rows):
    mpl=ROOT/'work/.matplotlib'; mpl.mkdir(parents=True,exist_ok=True); os.environ['MPLCONFIGDIR']=str(mpl)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'figure.dpi':160,'axes.spines.top':False,'axes.spines.right':False})
    def recovery(n,p,sigma,scale):
        return next(x for x in summaries if x['condition']==dict(family='recovery',n=n,truth_p=p,generator_p=None,sigma=sigma,scale=scale,c=None,control=None))
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    groups=[[recovery(512,p,sigma,1.) for sigma in SIGMAS] for p in P_VALUES]
    for ax,field,title in zip(axes,['rmse','undefined'],['Conditional RMSE among defined fits','Undefined outcomes / 64 independent draws']):
        data=np.array([[g['conditional_error']['rmse'] if field=='rmse' else g['undefined_rate'] for g in row] for row in groups],dtype=float)
        upper=max(1e-8,float(np.nanmax(data))) if np.isfinite(data).any() else 1.
        im=ax.imshow(np.ma.masked_invalid(data),vmin=0,vmax=upper if field=='rmse' else 1.,cmap='YlOrRd')
        for i,row in enumerate(groups):
            for j,g in enumerate(row):
                label=f"{fmt(g['conditional_error']['rmse'])}\n{g['defined']}/64 defined" if field=='rmse' else f"{g['undefined']}/64"
                dark=np.isfinite(data[i,j]) and data[i,j]>(upper if field=='rmse' else 1.)*.6
                ax.text(j,i,label,ha='center',va='center',fontsize=9,color='white' if dark else 'black')
        ax.set_xticks(range(4),SIGMAS); ax.set_yticks(range(4),P_VALUES); ax.set_xlabel('Noise sigma'); ax.set_ylabel('Generating exponent p')
        ax.set_title(title); fig.colorbar(im,ax=ax,shrink=.8,label='RMSE' if field=='rmse' else 'Undefined fraction')
    fig.suptitle('Recovery at n=512, scale=1 — failures retained; conditional accuracy excludes undefined fits')
    fig.savefig(out/'recovery.png'); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(15,8),layout='constrained'); conditions=[(p,sigma) for p in P_VALUES for sigma in SIGMAS]
    labels=[f'{p:g}/{s:g}' for p,s in conditions]; x=np.arange(len(conditions)); palette={1.:'#4a5568',1e-8:'#2374a6',1e-14:'#b4532d'}
    plot_limits={}
    for row,n in enumerate([128,512]):
        all_differences=[]
        for scale in SCALES[1:]:
            group=[next(c for c in comparisons if (c['n'],c['truth_p'],c['sigma'],c['scale'])==(n,p,sigma,scale)) for p,sigma in conditions]
            means=[c['conditional_absolute_difference']['mean'] for c in group]
            axes[row,0].plot(x,[np.nan if v is None else v for v in means],'-o',ms=3,color=palette[scale],label=f'{scale:g} vs 1')
            for i,c in enumerate(group):
                vals=[r['absolute_p_difference'] for r in c['paired_records'] if r['both_defined']]
                all_differences.extend(vals)
                axes[row,0].scatter(np.full(len(vals),i),vals,s=6,alpha=.2,color=palette[scale])
        for scale in SCALES:
            values=[recovery(n,p,sigma,scale)['undefined_by_reason'].get('nonpositive_total_gain',0)/REPLICATES for p,sigma in conditions]
            axes[row,1].plot(x,values,'-o',ms=3,color=palette[scale],label=f'scale {scale:g}')
        for col in [0,1]:
            axes[row,col].set_xticks(x,labels,rotation=55,ha='right',fontsize=8); axes[row,col].set_xlabel('Generating p / noise sigma')
            axes[row,col].legend(fontsize=8)
        axes[row,0].set_yscale('symlog',linthresh=1e-10)
        high=max(1e-10,max(all_differences,default=0.))*1.4
        axes[row,0].set_ylim(-high*.005,high)
        assert all(0<=value<high for value in all_differences)
        plot_limits[f'scale_n{n}']=dict(minimum=-high*.005,maximum=high,defined_points=len(all_differences),all_points_inside=True)
        axes[row,0].set_title(f'n={n}: conditional mean |p*(scale) − p*(1)|')
        axes[row,0].set_ylabel('Paired absolute difference (symlog)')
        axes[row,0].text(.02,.98,'Missing curve/points: no jointly defined pairs',transform=axes[row,0].transAxes,ha='left',va='top',fontsize=8)
        axes[row,1].set_ylim(-.03,1.03); axes[row,1].set_title(f'n={n}: total-gain guard activations / 64')
        axes[row,1].set_ylabel('Guard fraction (all 64 draws)')
    fig.suptitle('Scale comparisons use the exact same weights/noise — conditional differences and guard rates are separate')
    fig.savefig(out/'scale-invariance.png'); plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(17,8),layout='constrained'); cs=[1e-12,.01,.1,1.]; colors={.2:'#2374a6',1.:'#b4532d'}
    for row,n in enumerate([128,512]):
        objectives=[]; estimate_extent=[0.,8.]
        for p in [.2,1.]:
            groups=[next(g for g in summaries if g['condition']['family']=='cancellation' and
                (g['condition']['n'],g['condition']['truth_p'],g['condition']['c'])==(n,p,c)) for c in cs]
            means=[g['conditional_estimate']['mean'] for g in groups]; sd=[g['conditional_estimate']['sd'] for g in groups]
            axes[row,0].errorbar(cs,[np.nan if v is None else v for v in means],yerr=[np.nan if v is None else v for v in sd],
                marker='o',capsize=3,color=colors[p],label=f'generating p={p:g}')
            axes[row,0].axhline(p,color=colors[p],ls=':',lw=.8)
            axes[row,1].plot(cs,[g['undefined_rate'] for g in groups],'-o',color=colors[p])
            axes[row,2].plot(cs,[g['upper_boundary_rate_all'] for g in groups],'-o',color=colors[p])
            axes[row,3].plot(cs,[np.nan if g['conditional_objective']['mean'] is None else g['conditional_objective']['mean'] for g in groups],'-o',color=colors[p])
            for c,mean,deviation in zip(cs,means,sd):
                if mean is not None:
                    estimate_extent.extend([mean-(deviation or 0.),mean+(deviation or 0.)])
                defined=[r for r in raw_rows if r['family']=='cancellation' and r['n']==n and r['truth_p']==p and r['c']==c and r['p'] is not None]
                axes[row,0].scatter(np.full(len(defined),c),[r['p'] for r in defined],s=6,alpha=.2,color=colors[p])
                values=[r['objective'] for r in defined]; objectives.extend(values)
                axes[row,3].scatter(np.full(len(values),c),values,s=6,alpha=.2,color=colors[p])
        for col,heading in enumerate(['Conditional p* mean ± SD','Undefined / 64','Upper-bound fits / 64','Conditional fit objective mean']):
            axes[row,col].set_xscale('log'); axes[row,col].set_xticks(cs,[f'{c:g}' for c in cs]); axes[row,col].set_xlabel('Positive signal c (log scale)')
            axes[row,col].set_title(f'n={n}: {heading}',fontsize=10)
        axes[row,0].axhline(8,color='gray',ls='--',lw=.7); axes[row,0].legend(fontsize=8)
        axes[row,1].set_ylim(-.03,1.03); axes[row,2].set_ylim(-.03,1.03); axes[row,3].set_yscale('symlog',linthresh=.001)
        low,high=min(estimate_extent),max(estimate_extent); pad=(high-low)*.07
        axes[row,0].set_ylim(low-pad,high+pad)
        upper=max(.001,max(objectives,default=0.))*1.4; axes[row,3].set_ylim(0,upper)
        assert all(0<=value<upper for value in objectives)
        plot_limits[f'cancellation_objective_n{n}']=dict(minimum=0,maximum=upper,defined_points=len(objectives),all_points_inside=True)
    fig.suptitle('Cancellation stress test — c>0 has generating truth; c≤0 controls are reported separately; no filtering')
    fig.savefig(out/'cancellation.png'); plt.close(fig)
    write(out/'PLOT_CHECKS.json',dict(status='PASS',limits=plot_limits,visual_review='pending',
        note='Every defined paired scale-difference and positive-c cancellation objective is plotted; p error bars also within axes.'))


def report(root,out,rows,summaries,comparisons,audit,complete):
    defined=[r for r in rows if r['p'] is not None]; reasons=Counter(r['reason'] for r in rows if r['p'] is None)
    text='# Stage 7 v0.8 — finite-estimator validity under signed gains\n\n'
    text+=f'Run `{root.name}` completed **{len(rows):,} CPU fits**, with **{len(summaries)} conditions × 64 independent draws per condition**. '
    text+=f'There are **{len({r["block_id"] for r in rows})} independent weight/noise blocks**: 64 at n=128 and 64 at n=512. '
    text+='The 65 conditions within each block reuse weights/noise and are paired observations.\n\n'
    text+='## Findings and accounting\n\n'
    text+=f'**{len(defined):,}/{len(rows):,} estimates are defined**; **{len(rows)-len(defined):,} are undefined**. '
    text+='Undefined outcomes are retained by reason, with no fit threshold, favorable subset selection, or replacement draws.\n\n'
    text+=table(['Undefined reason','Condition evaluations'],[[reason,count] for reason,count in sorted(reasons.items())])+'\n\n'
    text+='Counts pooled over conditions are descriptive evaluation counts, not independent trials. Conditional means/errors/objectives use only defined fits '
    text+='and give their denominator. Unconditional recovery mean and RMSE are null if any fit is undefined or no identifiable truth is assigned. '
    text+='Boundary frequency is reported against all 64 draws and against defined draws in the accompanying summary.\n\n'
    text+=f"Of the guarded outcomes, **{sum(g['guard_positive_undefined_count'] for g in summaries):,}** have a positive total no larger than 1e-10; "
    text+=f"**{sum(g['guard_nonpositive_undefined_count'] for g in summaries):,}** have a nonpositive total. Both the original sum and math.fsum totals are preserved.\n\n"
    text+='## Design and recovery\n\n'
    text+='The unchanged Stage6 estimator fits its original cumulative discrepancy on [0,8]. Gains remain signed. Uniform weights are undefined; '
    text+='the inherited total-gain guard is `sum(gain) <= 1e-10`, including small positive totals. Its historical reason label '
    text+='`nonpositive_total_gain` therefore also covers these small positive cases.\n\n'
    text+='Recovery: normalized q = w^p / mean(w^p), with p∈{0,.2,1,4}, iid normal noise z, sigma∈{0,.5,2,8}, '
    text+='and gain = scale·(q+sigma·z), scale∈{1,1e-8,1e-14}. No p*/objective-based model or sample selection is performed.\n\n'
    text+='![Recovery and undefined frequency](recovery.png)\n\n'
    noiseless=[g for g in summaries if g['condition']['family']=='recovery' and g['condition']['sigma']==0 and g['condition']['n']==512]
    text+=table(['n=512 noiseless p','Scale','Defined /64','Conditional bias','Conditional RMSE','Unconditional RMSE'],[
        [g['condition']['truth_p'],g['condition']['scale'],g['defined'],fmt(g['conditional_error']['bias']),
         fmt(g['conditional_error']['rmse']),fmt(g['unconditional_recovery_rmse'])] for g in noiseless])+'\n\n'
    text+='All 130 conditions, signed gain/cancellation statistics, bias/RMSE/MAE, 5/25/50/75/95% quantiles and lower/upper-bound counts '
    text+='are available in `summaries.json` and `summaries.csv`. Quantiles use linear interpolation between ordered samples. '
    text+='A lower-bound estimate when true p=0, or upper-bound estimate when true p=8, is not automatically a failure.\n\n'
    text+='## Matched scale comparisons\n\n'
    text+='Scaling gains by a positive constant leaves their normalized cumulative profile mathematically unchanged when normalization is defined. '
    text+='The fixed absolute guard can change estimator availability. Paired comparisons match n, replicate/block, p and sigma, with identical weight/noise seeds and weight hashes. '
    text+='Absolute p* differences are computed only when both fits exist; a missing paired fit remains undefined in unconditional comparison summaries.\n\n'
    scale_rows=[]
    for n in [128,512]:
        for scale in SCALES[1:]:
            group=[c for c in comparisons if c['n']==n and c['scale']==scale]
            differences=[r['absolute_p_difference'] for c in group for r in c['paired_records'] if r['both_defined']]
            scale_rows.append([n,scale,sum(c['both_defined'] for c in group),sum(c['total_pairs'] for c in group),
                fmt(max(differences) if differences else None),sum(c['reference_guard_count'] for c in group),sum(c['target_guard_count'] for c in group)])
    text+=table(['n','Scale vs1','Both defined','Matched condition pairs','Max conditional |Δp*|','Guard at scale1','Guard at target'],scale_rows)+'\n\n'
    text+='These aggregate pair counts span 16 paired p/sigma conditions per draw; they are not extra independent replications. '
    text+='`scale-comparisons.json` and `scale-pairs.csv` retain every match, denominator and undefined reason.\n\n![Matched scaling](scale-invariance.png)\n\n'
    text+='## Cancellation and controls\n\n'
    text+='Cancellation uses gain = c·q + centered unit-RMS noise, with generating p∈{.2,1}, c∈{1,.1,.01,1e-12,0,-.01}. '
    text+='Only c>0 is assigned recovery truth. Centering occurs on each finite noise draw; floating-point residuals and the guard remain part of the measured implementation. '
    text+='The cancellation ratio |sum(gain)|/sum(|gain|) is undefined only when its denominator is zero.\n\n'
    text+='Changing c changes signal-to-noise ratio and cancellation together; it does not isolate a causal effect of cancellation alone. '
    text+='The two generator_p conditions remain separate even when c≤0 and their recovery truth is null.\n\n'
    text+='![Cancellation diagnostics](cancellation.png)\n\n'
    controls=[g for g in summaries if g['condition']['family']=='control']
    text+=table(['Control','n','Truth p','Defined /64','Upper /64','Lower /64','Conditional mean p*','Eligible recovery RMSE','Out-of-range error RMSE'],[
        [g['condition']['control'],g['condition']['n'],g['condition']['truth_p'],g['defined'],g['upper_boundary_count'],g['lower_boundary_count'],
         fmt(g['conditional_estimate']['mean']),fmt(g['conditional_error']['rmse']),fmt(g['conditional_misspecification_error']['rmse'])] for g in controls])+'\n\n'
    text+='The p=10 control deliberately lies outside the estimator’s [0,8] search range: its error is **constrained model misspecification**, '
    text+='not evidence that the estimator can recover an out-of-range exponent. Uniform-weight, zero-gain, negative-gain and c≤0 conditions have no assigned recovery truth. '
    text+='Defined estimates, if any, in no-truth conditions remain reported descriptively without recovery bias/RMSE.\n\n'
    nonpositive=[g for g in summaries if g['condition']['family']=='cancellation' and g['condition']['c']<=0]
    text+=table(['n','c','Generator p','Defined /64','Undefined /64','Conditional mean p*','Conditional objective max'],[
        [g['condition']['n'],g['condition']['c'],g['condition']['generator_p'],g['defined'],g['undefined'],
         fmt(g['conditional_estimate']['mean']),fmt(g['conditional_objective']['maximum'])] for g in nonpositive])+'\n\n'
    text+='## Audit, provenance and limits\n\n'
    text+=f"Independent audit: **{audit['status']}**. Frozen source hashes, exact gain arrays/weights, draw pairing, saved fits and undefined cases are retained in the raw record. "
    text+='Outcome-independent analysis fixtures check undefined propagation, no-truth errors, deterministic grouping and paired scale matching. '
    text+='CPU fit timing is recorded per evaluation; no GPU training or new language-model replication was performed.\n\n'
    text+='The historical integrity check covers prior versioned output artifacts and raw top-level records/source snapshots. '
    text+='Historical model/sequence arrays were preserved but not all rehashed; this is not a full repeat of the earlier training audits.\n\n'
    text+='Completion metadata (recorded without renaming timer fields):\n\n```json\n'+json.dumps(complete,indent=2,allow_nan=False)+'\n```\n\n'
    text+='This experiment diagnoses an unchanged finite estimator under specified gain-generating families. Generating exponents under noisy gains describe the signal construction; '
    text+='they do not guarantee finite-sample identification. The grid has 64 independent draws per condition, two sequence counts and one weight/noise design. '
    text+='For one cell frequency, the worst-case binomial Monte Carlo standard error is .0625; paired conditions do not increase its independent replicate count. '
    text+='Conditional accuracy can look favorable when difficult draws become undefined. No significance test, quality cutoff, novelty claim or publication guarantee is made.\n\n'
    text+='See [the Stage4–6 synthesis](SYNTHESIS_STAGE4_6.md) for the preceding adaptation evidence. Estimator validity and adaptation utility answer different questions; '
    text+='these synthetic estimator results do not establish a large-LM scaling claim.\n\n'
    text+=f"Protocol SHA256: `{sha(HERE/'PROTOCOL_STAGE7.md')}`. All sources and raw evidence are preserved in the SHA/CRC-checked compact archive. "
    text+='Scientific figures require a separate visual review after generation; this script does not assert that review.\n'
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def main():
    analysis_start=time.perf_counter(); analysis_start_utc=datetime.now(timezone.utc)
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True); args=parser.parse_args()
    assert Path(args.run_id).name==args.run_id
    root=ROOT/'work/runs'/args.run_id; out=HERE/f'results-{args.run_id}'
    assert not out.exists(),'Preserve earlier complete or partial analysis'
    assert (root/'COMPLETE.json').exists() and (root/'AUDIT.json').exists()
    audit=read(root/'AUDIT.json'); assert audit['status']=='PASS'
    complete=read(root/'COMPLETE.json')
    assert sha(root/'results.jsonl')==audit['results_sha256']==complete['results_sha256']
    manifest=read(root/'source_manifest.json')
    assert audit['source_sha256']==manifest
    assert {'core.py','stage7.py','audit_stage7.py','analyze_stage7.py','analysis_checks.py','PROTOCOL_STAGE7.md'}<=set(manifest)
    assert all(sha(HERE/name)==digest and sha(root/'source'/name)==digest for name,digest in manifest.items())
    out.mkdir()
    try:
        rows=[json.loads(line) for line in (root/'results.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        assert len(rows)==8320 and len({r['id'] for r in rows})==8320 and len({r['block_id'] for r in rows})==128
        summaries=summarize(rows); assert len(summaries)==130
        assert sum(g['defined'] for g in summaries)==audit['defined_fits']
        assert sum(g['guard_positive_undefined_count'] for g in summaries)==audit['guard_positive_total_count']
        comparisons,pairs=scale_comparisons(rows); assert len(comparisons)==64 and len(pairs)==4096
        write(out/'summaries.json',dict(replication='64 independent draws per condition; 65 paired conditions per block, independent n groups',groups=summaries))
        csvwrite(out/'summaries.csv',[flatten_summary(g) for g in summaries])
        write(out/'scale-comparisons.json',comparisons); csvwrite(out/'scale-pairs.csv',pairs)
        write(out/'SUMMARY_AUDIT.json',dict(status='PASS',rows=len(rows),groups=len(summaries),paired_scale_cells=len(comparisons),
            paired_scale_records=len(pairs),undefined_propagated=True,no_threshold_or_filter=True,utc=utc()))
        figures(out,summaries,comparisons,rows); report(root,out,rows,summaries,comparisons,audit,complete)
        for name in manifest: shutil.copy2(root/'source'/name,out/name)
        shutil.copy2(root/'AUDIT.json',out/'AUDIT.json')
        write(out/'analysis-provenance.json',dict(utc=utc(),source_sha256=manifest,source_snapshot_verified=True,visual_review='pending'))
        write(out/'ANALYSIS_RUNTIME.json',dict(utc=utc(),pre_archive_elapsed_seconds=time.perf_counter()-analysis_start,
            pre_archive_utc_elapsed_seconds=(datetime.now(timezone.utc)-analysis_start_utc).total_seconds(),
            includes='source verification, summaries, figures and report; total including archive is in ARCHIVE_CHECK.json'))
        raw_manifest={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
        write(out/'raw-manifest.json',raw_manifest); archive=out/'run-records.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as stream:
            for p in sorted(root.rglob('*')):
                if p.is_file(): stream.write(p,'raw/'+str(p.relative_to(root)))
            for p in sorted(out.iterdir()):
                if p.is_file() and p!=archive: stream.write(p,'report/'+p.name)
        with zipfile.ZipFile(archive) as stream: assert stream.testzip() is None
        archive_hash=sha(archive)
        write(out/'ARCHIVE_CHECK.json',dict(status='PASS',crc='PASS',sha256=archive_hash,bytes=archive.stat().st_size,raw_files=len(raw_manifest),utc=utc(),
            analysis_elapsed_seconds=time.perf_counter()-analysis_start,
            analysis_utc_elapsed_seconds=(datetime.now(timezone.utc)-analysis_start_utc).total_seconds()))
        print(json.dumps(dict(output=str(out),rows=len(rows),groups=len(summaries),defined=sum(r['p'] is not None for r in rows),audit='PASS',archive='PASS')),flush=True)
    except Exception:
        write(out/'ANALYSIS_FAILURE.json',dict(utc=utc(),traceback=traceback.format_exc(),instruction='Preserve failed outputs and use a new version for any repair.'))
        raise


if __name__=='__main__': main()
