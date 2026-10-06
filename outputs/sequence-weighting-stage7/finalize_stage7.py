"""Presentation-only Stage7 r1; frozen simulation/analysis outputs are preserved."""
import argparse
import hashlib
import json
import math
import os
import shutil
import statistics as st
import sys
import time
import zipfile
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def write(path,value):
    with path.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,allow_nan=False); f.write('\n')


def utc(): return datetime.now(timezone.utc).isoformat()


def fmt(value): return 'undefined' if value is None else f'{value:.6g}'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])


def redraw_cancellation(out,summaries,rows):
    mpl=ROOT/'work/.matplotlib'; mpl.mkdir(parents=True,exist_ok=True); os.environ['MPLCONFIGDIR']=str(mpl)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import FixedLocator,FuncFormatter,NullLocator
    cs=[1e-12,.01,.1,1.]; colors={.2:'#2374a6',1.:'#b4532d'}
    plt.rcParams.update({'font.size':10,'figure.dpi':160,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,4,figsize=(17,8.5),layout='constrained')
    checks={}; total_points=0
    for row_index,n in enumerate([128,512]):
        estimate_extents=[0.,8.]; estimate_points=[]; objective_points=[]
        for p in [.2,1.]:
            x=np.arange(4)+(-.045 if p==.2 else .045)
            groups=[next(g for g in summaries if g['condition']['family']=='cancellation' and
                (g['condition']['n'],g['condition']['generator_p'],g['condition']['c'])==(n,p,c)) for c in cs]
            means=[g['conditional_estimate']['mean'] for g in groups]
            deviations=[g['conditional_estimate']['sd'] for g in groups]
            axes[row_index,0].errorbar(x,[np.nan if m is None else m for m in means],
                yerr=[np.nan if s is None else s for s in deviations],fmt='-o',capsize=3,color=colors[p],
                label=f'Generating p={p:g}')
            axes[row_index,0].axhline(p,color=colors[p],ls=':',lw=.8)
            axes[row_index,1].plot(x,[g['undefined_rate'] for g in groups],'-o',color=colors[p])
            axes[row_index,2].plot(x,[g['upper_boundary_rate_all'] for g in groups],'-o',color=colors[p])
            axes[row_index,3].plot(x,[np.nan if g['conditional_objective']['mean'] is None else g['conditional_objective']['mean']
                                      for g in groups],'-o',color=colors[p])
            for i,(c,g,mean,deviation) in enumerate(zip(cs,groups,means,deviations)):
                fitted=sorted([r for r in rows if r['family']=='cancellation' and r['n']==n and
                    r['generator_p']==p and r['c']==c and r['p'] is not None],key=lambda r:r['replicate'])
                assert len(fitted)==g['defined']
                estimates=[r['p'] for r in fitted]; objectives=[r['objective'] for r in fitted]
                if estimates:
                    assert st.mean(estimates)==mean and st.mean(objectives)==g['conditional_objective']['mean']
                    assert max(objectives)==g['conditional_objective']['maximum']
                if mean is not None: estimate_extents.extend([mean-(deviation or 0.),mean+(deviation or 0.)])
                points_x=np.full(len(fitted),x[i])+np.linspace(-.025,.025,len(fitted))
                axes[row_index,0].scatter(points_x,estimates,s=9,alpha=.3,color=colors[p])
                axes[row_index,3].scatter(points_x,objectives,s=9,alpha=.3,color=colors[p])
                estimate_points.extend(estimates); objective_points.extend(objectives); total_points+=len(fitted)
        for col,heading in enumerate(['p*: fits and conditional mean ± SD','Undefined fraction (all 64)','Upper-bound fraction (all 64)','Objective: fits and conditional mean']):
            ax=axes[row_index,col]; ax.set_xlim(-.3,3.3)
            ax.set_xticks(range(4),['1e-12','0.01','0.1','1'])
            ax.set_xlabel('Signal c (categories;\nspacing not numeric)')
            ax.set_title(f'n={n}: {heading}',fontsize=9)
        low,high=min(estimate_extents),max(estimate_extents); padding=max(.1,(high-low)*.07)
        axes[row_index,0].set_ylim(low-padding,high+padding)
        axes[row_index,0].axhline(0,color='gray',ls='--',lw=.7)
        axes[row_index,0].axhline(8,color='gray',ls='--',lw=.7)
        axes[row_index,0].set_ylabel('Estimated p*')
        assert all(low-padding<value<high+padding for value in estimate_points+estimate_extents)
        for col in [1,2]:
            axes[row_index,col].set_ylim(-.03,1.03); axes[row_index,col].set_ylabel('Fraction of 64 draws')
        ax=axes[row_index,3]; upper=max(.001,max(objective_points,default=0.))*1.4
        ax.set_yscale('symlog',linthresh=.001); ax.set_ylim(0,upper)
        ticks=[0.]+[10.**exponent for exponent in range(-3,22,3) if 10.**exponent<=upper]
        ax.yaxis.set_major_locator(FixedLocator(ticks)); ax.yaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value,position:'0' if value==0 else '$10^{'+str(int(round(math.log10(value))))+'}$'))
        ax.set_ylabel('Fit objective (symlog)')
        assert all(0<=value<upper for value in objective_points)
        checks[str(n)]=dict(defined_fits=len(estimate_points),p_limits=[low-padding,high+padding],
            objective_limits=[0,upper],objective_ticks=ticks,largest_objective=max(objective_points,default=None),
            all_defined_p_and_objective_points_retained=True,all_p_standard_deviation_bars_inside_axes=True)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2,frameon=False)
    fig.suptitle('Positive-signal cancellation: equally spaced conditions, every defined fit retained',fontsize=14)
    fig.savefig(out/'cancellation.png'); plt.close(fig)
    expected=sum(g['defined'] for g in summaries if g['condition']['family']=='cancellation' and g['condition']['c']>0)
    assert total_points==expected
    return dict(status='PASS',utc=utc(),x_categories=cs,x_spacing='categorical; not numeric distance',
        conditional_defined_denominators_per_cell=[g['defined'] for g in summaries if g['condition']['family']=='cancellation' and g['condition']['c']>0],
        plotted_positive_c_fits=total_points,panels=checks,visual_review='pending agent inspection of rendered image')


def revise_report(original,summaries):
    header='Max conditional |Δp*|'
    assert original.count(header)==1
    report=original.replace(header,'Maximum absolute p* difference',1)
    positive=sorted([g for g in summaries if g['condition']['family']=='cancellation' and g['condition']['c']>0],
        key=lambda g:(g['condition']['n'],g['condition']['generator_p'],g['condition']['c']))
    assert len(positive)==16
    headers=['n','Generating p','c','Defined /64','Conditional RMSE','Conditional mean p*','Conditional SD p*',
             'Upper /64','Lower /64','Objective maximum','Conditional mean cancellation ratio']
    values=[[g['condition']['n'],g['condition']['generator_p'],g['condition']['c'],g['defined'],
        fmt(g['conditional_error']['rmse']),fmt(g['conditional_estimate']['mean']),fmt(g['conditional_estimate']['sd']),
        g['upper_boundary_count'],g['lower_boundary_count'],fmt(g['conditional_objective']['maximum']),fmt(g['conditional_cancellation']['mean'])]
        for g in positive]
    subsection=('### Positive-signal cancellation: all 16 conditions\n\n'
        'Each row has 64 independent draws. Means, SD, RMSE, objective maxima and cancellation ratios below are conditional on defined fits; '
        'the defined count is shown explicitly. Boundary counts use all 64 draws. Every value comes from the existing audited summaries.\n\n'+
        table(headers,values)+'\n\nThe revised figure spaces c values as categories so each condition and label is readable. '
        'Horizontal distances do not represent numeric differences in c. Dots show every defined fit; error bars show conditional SD, not a confidence interval.\n\n')
    anchor='![Cancellation diagnostics](cancellation.png)'; assert report.count(anchor)==1
    report=report.replace(anchor,subsection+anchor,1)
    noiseless=[g for g in summaries if g['condition']['family']=='recovery' and g['condition']['sigma']==0 and g['condition']['scale'] in [1.,1e-8]]
    assert all(g['defined']==64 for g in noiseless)
    exact_error=max(max(abs(g['conditional_error']['minimum']),abs(g['conditional_error']['maximum'])) for g in noiseless)
    tiny=[g for g in summaries if g['condition']['family']=='recovery' and g['condition']['scale']==1e-14]
    tiny_total=sum(g['total'] for g in tiny); tiny_guard=sum(g['undefined_by_reason'].get('nonpositive_total_gain',0) for g in tiny)
    noisy=next(g for g in summaries if g['condition']['family']=='recovery' and
        (g['condition']['n'],g['condition']['truth_p'],g['condition']['sigma'],g['condition']['scale'])==(512,4.,8.,1.))
    weakest=[g for g in positive if g['condition']['c']==1e-12]
    weakest_range=[min(g['conditional_error']['rmse'] for g in weakest),max(g['conditional_error']['rmse'] for g in weakest)]
    interpretation=('### Measured interpretation\n\n'
        f'- Noiseless in-range recovery above the guard matched the generating exponent to numerical precision: maximum absolute error **{fmt(exact_error)}** across n=128/512 and scales 1/1e-8.\n'
        f'- At scale 1e-14, **{tiny_guard}/{tiny_total}** recovery evaluations were undefined under the fixed total-gain guard, despite unchanged normalized gain profiles.\n'
        f'- Noise produced substantial dispersion: at n=512, p=4, sigma=8 and scale=1, **{noisy["defined"]}/64** fits were defined, conditional RMSE was **{fmt(noisy["conditional_error"]["rmse"])}**, and **{noisy["upper_boundary_count"]}/64** reached the upper search boundary.\n'
        f'- At c=1e-12, **{sum(g["defined"] for g in weakest)}/{sum(g["total"] for g in weakest)}** fits were defined across four conditions, yet their conditional RMSEs ranged from **{fmt(weakest_range[0])} to {fmt(weakest_range[1])}**, with large objectives and boundary fits. A defined estimate does not establish accurate recovery.\n\n'
        'These observations describe the prespecified cells; they introduce no quality filter, exclusion threshold or new selection rule.\n\n')
    anchor='## Design and recovery'; assert report.count(anchor)==1
    report=report.replace(anchor,interpretation+anchor,1)
    note=('**Presentation revision r1:** the cancellation figure now uses readable categorical spacing and sparse objective ticks. '
        'The scale-table header is repaired, and the positive-c table and short interpretation expose existing audited results. '
        'The original report, figures, frozen sources and numerical summaries remain preserved.\n\n')
    report=report.replace('\n\n','\n\n'+note,1)
    scale_header=next(line for line in report.splitlines() if 'Maximum absolute p* difference' in line)
    assert len(scale_header.split('|'))-2==7
    return report,dict(positive_c_table_group_ids=[g['group_id'] for g in positive],positive_c_table_rows=values,
        interpretation_evidence=dict(noiseless_max_absolute_error=exact_error,tiny_scale_guard_count=tiny_guard,
            tiny_scale_total=tiny_total,noisy_example_group_id=noisy['group_id'],weakest_c_rmse_range=weakest_range))


def main():
    start=time.perf_counter(); start_utc=datetime.now(timezone.utc)
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True); args=parser.parse_args()
    assert args.run_id and args.run_id not in ['.','..'] and '/' not in args.run_id and '\\' not in args.run_id
    raw=ROOT/'work/runs'/args.run_id; original=HERE/f'results-{args.run_id}'; out=HERE/f'results-{args.run_id}-r1'
    assert not out.exists(),'Preserve earlier presentation revision'
    manifest=read(raw/'source_manifest.json'); assert Path(__file__).name not in manifest
    for name,digest in manifest.items(): assert sha(HERE/name)==sha(raw/'source'/name)==digest,name
    complete=read(raw/'COMPLETE.json'); audit=read(raw/'AUDIT.json'); assert audit['status']=='PASS'
    assert sha(raw/'results.jsonl')==complete['results_sha256']==audit['results_sha256']
    archive_check=read(original/'ARCHIVE_CHECK.json'); assert archive_check['crc']=='PASS'
    assert sha(original/'run-records.zip')==archive_check['sha256']
    original_manifest={p.name:sha(p) for p in original.iterdir() if p.is_file()}
    out.mkdir()
    for p in original.iterdir():
        if p.is_file() and p.name not in ['run-records.zip','ARCHIVE_CHECK.json']: shutil.copy2(p,out/p.name)
    summaries=read(original/'summaries.json')['groups']
    rows=[json.loads(line) for line in (raw/'results.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    plot_checks=redraw_cancellation(out,summaries,rows); write(out/'PLOT_CHECKS_R1.json',plot_checks)
    report,evidence=revise_report((original/'REPORT.md').read_text(encoding='utf-8'),summaries)
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    unchanged={name:digest for name,digest in original_manifest.items() if name not in
        ['REPORT.md','cancellation.png','run-records.zip','ARCHIVE_CHECK.json']}
    assert all(sha(out/name)==digest for name,digest in unchanged.items())
    revision=dict(utc=utc(),revision='presentation-r1',original_output=str(original.relative_to(ROOT)),
        original_archive_sha256=archive_check['sha256'],frozen_source_sha256=manifest,
        unchanged_original_files=unchanged,
        changed_original_files={name:dict(before=original_manifest[name],after=sha(out/name)) for name in ['REPORT.md','cancellation.png']},
        no_estimator_or_numerical_summary_change=True,raw_results_sha256=complete['results_sha256'],
        finalizer_sha256=sha(Path(__file__)),**evidence)
    write(out/'PRESENTATION_REVISION.json',revision)
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    (out/'REVISION_README.md').write_text('# Stage 7 presentation revision r1\n\n'
        'The frozen README.md, source files, numeric summaries and original PLOT_CHECKS.json are copied verbatim. '
        'PLOT_CHECKS_R1.json describes the revised cancellation figure; PRESENTATION_REVISION.json lists source/summary hashes and the two changed presentation files.\n\n'
        'From the project root in the existing Ubuntu WSL environment:\n\n'
        '```sh\nwork/.venv-wsl/bin/python outputs/sequence-weighting-stage7/finalize_stage7.py --run-id '+args.run_id+'\n```\n\n'
        'The command requires the original completed/audited run and report, creates the r1 directory once, and refuses an existing r1 destination. '
        'It does not rerun any simulation or fit; existing numerical summary files are copied unchanged. All raw entries in the original archive are retained byte for byte; '
        'the external ARCHIVE_CHECK.json verifies the new archive and records presentation runtime. Separate visual inspection is still required.\n',encoding='utf-8')
    archive=out/'run-records.zip'; raw_hashes={}
    with zipfile.ZipFile(original/'run-records.zip') as old,zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as new:
        assert old.testzip() is None
        for entry in old.infolist():
            if entry.filename.startswith('raw/'):
                data=old.read(entry.filename); raw_hashes[entry.filename]=hashlib.sha256(data).hexdigest()
                new.writestr(entry.filename,data)
        for p in sorted(out.iterdir()):
            if p.is_file() and p!=archive: new.write(p,'report/'+p.name)
    with zipfile.ZipFile(archive) as final:
        assert final.testzip() is None
        assert {e.filename for e in final.infolist() if e.filename.startswith('raw/')}==set(raw_hashes)
        assert all(hashlib.sha256(final.read(name)).hexdigest()==digest for name,digest in raw_hashes.items())
    assert all(sha(p)==original_manifest[p.name] for p in original.iterdir() if p.is_file())
    for name,digest in manifest.items(): assert sha(HERE/name)==sha(raw/'source'/name)==digest,name
    digest=sha(archive)
    write(out/'ARCHIVE_CHECK.json',dict(status='PASS',utc=utc(),crc='PASS',sha256=digest,bytes=archive.stat().st_size,
        original_archive_sha256=archive_check['sha256'],raw_archive_entries=len(raw_hashes),raw_archive_entries_byte_identical=True,
        original_output_unchanged=True,scientific_files_unchanged=True,
        presentation_elapsed_seconds=time.perf_counter()-start,
        presentation_utc_elapsed_seconds=(datetime.now(timezone.utc)-start_utc).total_seconds()))
    print(json.dumps(dict(output=str(out),archive='PASS',scientific_files_unchanged=True,
        raw_entries_unchanged=len(raw_hashes),positive_c_table_rows=len(evidence['positive_c_table_rows']))),flush=True)


if __name__=='__main__': main()
