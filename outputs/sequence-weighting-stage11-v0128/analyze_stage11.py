"""Frozen collection/report layer for the Stage 11 descriptive analysis.

No selection from confirmation. Retains partial runs and nulls; refuses output
reuse. A later independent raw-array/binary audit is still required for final
experiment acceptance. This entry point does not start model computation.
"""
import argparse
import csv
import os
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
from config import ROOT, HERE, CAPS, CONDITIONS, ARMS, REPORT_SECONDS
from artifacts import read, write, bind, check_binding, source_manifest
from policies import confirmation_schedule
from analysis import summarize


def collect(root):
    root=Path(root).resolve()
    frozen = read(root/'FREEZE.json')
    assert source_manifest()==frozen['source_sha256'], 'Source drift'
    if not (root/'SELECTION_FREEZE.json').exists():
        assert (root/'FAILURE.json').exists(), 'No completed selection or failure record; do not analyze an active run'
        inputs=[bind(root/'FAILURE.json',root),bind(root/'tuning_schedule.json',root)]
        rows=[]
        for c in read(root/'tuning_schedule.json'):
            path=root/'runs'/c['name']/'history.json'
            history=read(path) if path.exists() else []
            if path.exists(): inputs.append(bind(path,root))
            rows.append(dict(config=c,status='complete' if (path.parent/'result.json').exists()
                else 'partial' if path.parent.exists() else 'not_run',saved_checkpoints=history))
        return dict(status='failed_before_selection',failure=read(root/'FAILURE.json'),
            planned_tuning=rows,confirmation='not_selected_or_run',readiness=None,
            scientific_effects=None,selection=None),inputs
    selection_freeze = read(root/'SELECTION_FREEZE.json')
    check_binding(selection_freeze['selection'],root)
    check_binding(selection_freeze['schedule'],root)
    selection = read(root/'selection.json')
    assert confirmation_schedule(selection['decisions'])==read(root/'confirmation_schedule.json')
    records,inputs = [],[]
    for c in confirmation_schedule(selection['decisions']):
        path = root/'runs'/c['name']/'history.json'
        if path.exists():
            inputs.append(bind(path,root))
            records += [h for h in read(path) if h['epoch']>0]
    if (root/'initial').exists():
        for path in sorted((root/'initial').glob('*/result.json')):
            row = read(path)
            if row['phase']=='confirmation':
                records.append(row); inputs.append(bind(path,root))
    return summarize(records,selection['decisions']),inputs


def show(value):
    return 'undefined / unavailable' if value is None else f'{value:.7g}'


def report(output,summary):
    if summary.get('status')=='failed_before_selection':
        rows=summary['planned_tuning']
        text=['# Stage 11: incomplete before validation selection','',
            'No confirmation policy was selected, and no confirmation scientific effect is estimated.',
            'The failure and every planned tuning trajectory remain recorded. No missing policy is imputed.','',
            f'Failure: {summary["failure"].get("error")}',
            f'Planned tuning trajectories: {len(rows)}',
            f'Complete: {sum(r["status"]=="complete" for r in rows)}; '
            f'partial: {sum(r["status"]=="partial" for r in rows)}; '
            f'not run: {sum(r["status"]=="not_run" for r in rows)}.','',
            'See summaries.json for all saved tuning checkpoints and missing schedule entries.','']
        (output/'REPORT.md').write_text('\n'.join(text),encoding='utf-8')
        return
    lines = ['# Stage 11: paired group-rule sharing','',
        'Descriptive results from five corpus draws, with two nested model/weight seeds.',
        'Fixed F10 group-learning contrasts and validation-selected R utility answer different questions.',
        'No significance, large-LM replication, superior weighting method or peak-shift claim is implied.','',
        '## Prespecified readiness checks','',
        '| Check | Result |','| --- | --- |']
    for key,value in summary['readiness'].items():
        lines.append(f'| {key} | {value} |')
    lines += ['', 'Missing or undefined observations remain in the denominators. Passing a planning criterion does not launch another experiment.',
        '', '## Selected-policy held-out learning','',
        '| Condition | Arm | Width | Epoch | Test gain (corpus mean) | Utility | p* (corpus mean) |',
        '| --- | --- | ---: | ---: | ---: | --- | ---: |']
    for condition in CONDITIONS:
        for arm in ARMS:
            for width,_ in CAPS:
                cell = summary['cells']['R'][condition][arm][str(width)]
                lines.append(f'| {condition} | {arm} | {width} | {cell["epoch"]} | '
                    f'{show(cell["delta_test"]["between_corpora"]["mean"])} | {cell["utility"]["met"]} | '
                    f'{show(cell["p"]["between_corpora"]["mean"])} |')
    lines += ['', '## Availability and limits','',str(summary['counting_units']),'',
        'See summaries.json for all component losses, memorization, clipping, fit objectives, boundaries, signed gains, initial losses, all corpus/seed values and missing records.',
        'G1/G16 alter both target rules and subsequent teacher-forced context. Comparisons use each condition’s own baseline.',
        'The fixed intervention changes rule complexity and support together. Three capacities cannot show a shift between two interior peaks.',
        'This generated report requires independent raw-array, selected-checkpoint and figure review before final acceptance. Only scripts were executed.','']
    (output/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


def plots(output,summary):
    if summary.get('status')=='failed_before_selection':
        return  # No invented confirmation policies or scientific effect figures.
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'work'/'.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'figure.dpi':150})
    def panel(ax, series, ylabel):
        for x,(label,values) in enumerate(series):
            known = [(i,v) for i,v in enumerate(values) if v is not None]
            ax.scatter([x+(i-2)*.06 for i,v in known],[v for i,v in known],s=30)
            if len(known)<5:
                ax.annotate(f'{5-len(known)}/5 undefined',(x,0),xytext=(0,8),textcoords='offset points',ha='center')
        ax.set_xticks(range(len(series)),[label for label,values in series])
        ax.set_xlim(-.45,len(series)-.55)
        ax.axhline(0,color='black',lw=.7); ax.set_ylabel(ylabel); ax.grid(axis='y',alpha=.2)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    contrast=summary['primary_F10_group_contrast']; absolute=summary['primary_F10_G1_absolute_group_gain']
    panel(axes[0],[('G1 − G16',[r['mean'] for r in contrast['corpora']])],'F10 group-test gain contrast (nats)')
    panel(axes[1],[('G1',[r['mean'] for r in absolute['corpora']])],'G1 absolute F10 group-test gain (nats)')
    fig.suptitle('Primary width 128, random weights · five corpus means')
    fig.savefig(output/'group-learning.png'); plt.close(fig)
    for field,filename,label in [('delta_test','selected-utility.png','Selected test NLL gain (nats)'),('p','selected-p.png','Selected p* (undefined retained)')]:
        fig,axes=plt.subplots(1,2,figsize=(12,4),constrained_layout=True,sharey=True)
        for ax,condition in zip(axes,CONDITIONS):
            series=[]
            for width,_ in CAPS:
                cell=summary['cells']['R'][condition]['random'][str(width)]
                series.append((f'{width}\nepoch {cell["epoch"]}',[r['mean'] for r in cell[field]['corpora']]))
            panel(ax,series,label); ax.set_title(condition)
        fig.suptitle('Validation-selected random-arm policy · five corpus means')
        fig.savefig(output/filename); plt.close(fig)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); start=time.perf_counter()
    root=args.run.resolve(); output=args.output.resolve()
    assert root.is_relative_to(ROOT/'work'/'runs') and output.is_relative_to(ROOT/'outputs')
    assert not output.exists()
    summary,inputs=collect(root)
    output.mkdir(parents=True,exist_ok=False)
    write(output/'summaries.json',summary)
    write(output/'analysis_inputs.json',dict(run=str(root.relative_to(ROOT)),files=inputs,
        selection=bind(root/'selection.json',root) if (root/'selection.json').exists() else None,
        source_sha256=source_manifest()))
    report(output,summary); plots(output,summary)
    elapsed=time.perf_counter()-start
    if elapsed>REPORT_SECONDS:
        raise RuntimeError('Report-stage 1800-second ceiling exceeded; preserve partial output')
    write(output/'REPORT_STATUS.json',dict(status='generated_pending_independent_audit_and_visual_review',
        elapsed_seconds=elapsed,training_complete=(root/'TRAINING_COMPLETE.json').exists(),
        files=[bind(p,output) for p in sorted(output.iterdir()) if p.is_file()]))
    print({'status':'REPORT_GENERATED_REVIEW_PENDING','elapsed_seconds':elapsed})


if __name__=='__main__':
    main()
