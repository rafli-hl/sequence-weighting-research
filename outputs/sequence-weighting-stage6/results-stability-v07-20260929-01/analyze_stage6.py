"""Frozen Stage6 panel replication analysis; crossed tuning panels and corpora."""
import argparse
import json
import math
import shutil
import statistics as st
import sys
import time
import traceback
import zipfile
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
import torch
from stage6 import ROOT,HERE,CAPS,EPOCHS,CONFIRM,VARIANTS,POLICIES,read,write,sha,utc
from analysis_core import (desc,replicated,fmt,table,csvwrite,initial_rows,flat_rows,diagnostics_analysis,
                           policy_analysis,audit_gates,baseline_analysis)


def crossed_stats(rows,metric):
    """Two separate marginal spreads, with no IID claim for crossed cells."""
    panels=sorted({r['panel'] for r in rows}); corpora=sorted({r['data_seed'] for r in rows})
    assert len(panels)==4 and len(corpora)==3
    matrix=[]; raw=[]
    for panel in panels:
        for corpus in corpora:
            group=[r for r in rows if r['panel']==panel and r['data_seed']==corpus]
            assert len(group)==3 and len({r['seed'] for r in group})==3
            stats=desc([r[metric] for r in group])
            matrix.append(dict(panel=panel,data_seed=corpus,**stats))
            raw.extend(dict(panel=panel,data_seed=corpus,seed=r['seed'],value=r[metric],
                source_name=r['name'],source_epoch=r['epoch'],canonical_zero=r['canonical_zero']) for r in group)
    panel_marginals=[dict(panel=p,**desc([c['mean'] for c in matrix if c['panel']==p])) for p in panels]
    corpus_marginals=[dict(data_seed=d,**desc([c['mean'] for c in matrix if c['data_seed']==d])) for d in corpora]
    panel_spread=desc([r['mean'] for r in panel_marginals]); corpus_spread=desc([r['mean'] for r in corpus_marginals])
    assert (panel_spread['mean'] is None)==(corpus_spread['mean'] is None)
    if panel_spread['mean'] is not None:
        assert math.isclose(panel_spread['mean'],corpus_spread['mean'],rel_tol=1e-12,abs_tol=1e-12)
    return dict(metric=metric,panels=panels,corpora=corpora,panel_corpus_matrix=matrix,raw_paired_values=raw,
        panel_marginals=panel_marginals,corpus_marginals=corpus_marginals,
        between_panel_marginals=panel_spread,between_corpus_marginals=corpus_spread,
        descriptive_grand_mean=panel_spread['mean'],
        unique_source_checkpoints=len({(r['source_name'],r['source_epoch']) for r in raw}),
        replication_note='4 tuning panels crossed with the SAME 3 corpora; model seeds nested; no pooled IID SD/SE/CI')


def choice_frequencies(selection):
    panels=sorted(selection['decisions']); assert len(panels)==4
    records=[]
    for policy in POLICIES:
        for variant in VARIANTS:
            for width,layers in CAPS:
                choices=[(p,selection['decisions'][p][policy][variant][str(width)]) for p in panels]
                counts=Counter((c['grid_index'],c['epoch'],c['lr'],c['wd']) for p,c in choices)
                settings=[dict(grid_index=g,epoch=e,lr=lr,wd=wd,count=n,
                    panels=[p for p,c in choices if (c['grid_index'],c['epoch'],c['lr'],c['wd'])==(g,e,lr,wd)])
                    for (g,e,lr,wd),n in sorted(counts.items(),key=lambda item:(item[0][1],item[0][2] or 0.,item[0][3] or 0.))]
                records.append(dict(policy=policy,variant=variant,width=width,total_panels=4,
                    no_adaptation_count=sum(c['epoch']==0 for p,c in choices),settings=settings))
    return records


def panel_analysis(selection,rows,baselines,diagnostic_rows):
    summaries={}; all_selected=[]; gate_audits={}; fingerprints={}
    for panel in sorted(selection['decisions']):
        summary,selected=policy_analysis({'decisions':selection['decisions'][panel]},rows,baselines,diagnostic_rows)
        for key,cell in summary['cells'].items():
            choices=selection['decisions'][panel][cell['policy']][cell['variant']]
            fingerprint=(cell['variant'],tuple((w,choices[str(w)]['grid_index'],choices[str(w)]['epoch']) for w,l in CAPS))
            reference=fingerprints.get(fingerprint); fingerprints.setdefault(fingerprint,f'{panel}/{key}')
            cell['alias_across_panels']=reference
        gate_audits[panel]=audit_gates(summary,selected)
        for r in selected: r['panel']=panel
        summaries[panel]=summary; all_selected.extend(selected)
    crossed={}
    for policy in POLICIES:
        for variant in VARIANTS:
            for arm in ['random','uniform']:
                for width,layers in CAPS:
                    group=[r for r in all_selected if (r['policy'],r['variant'],r['arm'],r['width'])==(policy,variant,arm,width)]
                    crossed[f'{variant}_{policy}_{arm}_w{width}']={metric:crossed_stats(group,metric) for metric in
                        ['delta_test','delta_validation','p','test_nll','validation_nll','train_nll','objective','cancellation_ratio']}
    frequencies=choice_frequencies(selection)
    main_panels=[dict(panel=p,largest_no_adaptation=selection['decisions'][p]['R']['U']['256']['epoch']==0,
        middle_utility=summaries[p]['cells']['U_R']['arms']['random']['capacity'][1]['utility'],
        global_useful=summaries[p]['cells']['U_R']['arms']['random']['useful_adaptation_met'],
        scaling=summaries[p]['cells']['U_R']['arms']['random']['scaling']['met'],
        peak_verdict=summaries[p]['cells']['U_R']['arms']['random']['peak_verdict']) for p in sorted(summaries)]
    primary=dict(condition='U',selector='R',arm='random',panels=main_panels,
        largest_no_adaptation_count=sum(p['largest_no_adaptation'] for p in main_panels),
        middle_useful_adaptation_count=sum(p['middle_utility']['met'] for p in main_panels),total_panels=4,
        no_arbitrary_binary_stability_threshold=True,no_formal_significance_test=True)
    return dict(primary=primary,panels=summaries,choice_frequencies=frequencies,crossed=crossed,
        inference_limit='All 4 panels included. Shared confirmation corpora/checkpoints induce dependence; no panel selected by test or p*.'),all_selected,gate_audits


def figures(out,summary,selection):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    panels=sorted(summary['panels']); widths=[w for w,l in CAPS]; colors={'M':'#315b96','U':'#bd4e26'}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
    rowkeys=[(p,q) for p in panels for q in POLICIES]; cols=[(v,w) for v in VARIANTS for w in widths]
    epochs=np.array([[selection['decisions'][p][q][v][str(w)]['epoch'] for v,w in cols] for p,q in rowkeys])
    fig,ax=plt.subplots(figsize=(14,8),layout='constrained')
    im=ax.imshow(epochs,cmap='Blues',vmin=0,vmax=30,aspect='auto')
    for i,(panel,policy) in enumerate(rowkeys):
        for j,(variant,width) in enumerate(cols):
            c=selection['decisions'][panel][policy][variant][str(width)]
            label='0: no adaptation' if c['epoch']==0 else f'e{c["epoch"]} / g{c["grid_index"]}\n{c["lr"]:g} / {c["wd"]:g}'
            ax.text(j,i,label,ha='center',va='center',fontsize=8,color='white' if c['epoch']>18 else 'black')
    ax.set_yticks(range(len(rowkeys)),[f'{p} / {q}' for p,q in rowkeys]); ax.set_xticks(range(6),[f'{v} width {w}' for v,w in cols])
    ax.set_title('All frozen validation choices — nonzero cells: epoch / grid, LR / WD')
    ax.axvline(2.5,color='black',lw=1); fig.colorbar(im,ax=ax,label='Selected epoch')
    fig.savefig(out/'selection-panels.png'); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,5),layout='constrained')
    corpus_ids=summary['crossed']['U_R_random_w64']['delta_test']['corpora']
    for ax,width in zip(axes,widths):
        stats=summary['crossed'][f'U_R_random_w{width}']['delta_test']
        array=np.array([[next(r['mean'] for r in stats['panel_corpus_matrix'] if r['panel']==p and r['data_seed']==d)
                         for d in corpus_ids] for p in panels])
        bound=max(1e-6,float(np.abs(array).max()))
        im=ax.imshow(array,cmap='RdBu',vmin=-bound,vmax=bound,aspect='auto')
        for i in range(4):
            for j in range(3):
                ax.text(j,i,f'{array[i,j]:+.6f}',ha='center',va='center',fontsize=9,
                        color='white' if abs(array[i,j])>.7*bound else 'black')
        ax.set_xticks(range(3),[str(d) for d in corpus_ids]); ax.set_yticks(range(4),panels)
        ax.set_title(f'U / R / random: width {width}'); ax.set_xlabel('Shared confirmation corpus')
        fig.colorbar(im,ax=ax,label='Initial test NLL − selected NLL',shrink=.75)
    fig.suptitle('Primary paired test gains — each cell is mean of 3 model seeds; color scales differ by capacity')
    fig.savefig(out/'crossed-gains.png'); plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained'); x=np.arange(4)
    for col,width in enumerate(widths):
        for row,metric in enumerate(['delta_test','delta_validation']):
            ax=axes[row,col]; stats=summary['crossed'][f'U_R_random_w{width}'][metric]
            means=[r['mean'] for r in stats['panel_marginals']]; sd=[r['sd'] for r in stats['panel_marginals']]
            ax.errorbar(x,means,yerr=sd,fmt='o',capsize=4,color=colors['U'],label='Panel mean ± corpus SD')
            for i,panel in enumerate(panels):
                vals=[r['mean'] for r in stats['panel_corpus_matrix'] if r['panel']==panel]
                ax.scatter(np.array([i-.08,i,i+.08]),vals,color=colors['U'],alpha=.45,s=22)
            labels=[p+'\ne'+str(selection['decisions'][p]['R']['U'][str(width)]['epoch']) for p in panels]
            ax.set_xticks(x,labels); ax.axhline(0,color='black',lw=.8)
            ax.set_ylabel('Initial NLL − selected NLL'); ax.set_title(f'Width {width}: '+('test' if metric=='delta_test' else 'validation'))
        passed=[p for p in panels if next(c for c in summary['panels'][p]['cells']['U_R']['arms']['random']['capacity'] if c['width']==width)['utility']['met']]
        axes[0,col].set_xlabel('Useful adaptation: '+(', '.join(passed) if passed else 'none'))
    handles,labels=axes[0,0].get_legend_handles_labels(); fig.legend(handles,labels,loc='outside lower center')
    fig.suptitle('U / R / random utility by panel — spread across 3 shared corpora, no pooled uncertainty')
    fig.savefig(out/'utility-panels.png'); plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(16,8),layout='constrained'); x=np.arange(3); limits={}
    for col,panel in enumerate(panels):
        objectives=[]; missing={}
        for variant in VARIANTS:
            caps=summary['panels'][panel]['cells'][f'{variant}_R']['arms']['random']['capacity']
            missing[variant]=[c['undefined_p'] for c in caps]
            for row,metric in enumerate(['p','objective']):
                ax=axes[row,col]; means=[c[metric]['between_corpora']['mean'] for c in caps]
                ax.plot(x,[np.nan if z is None else z for z in means],'-o',color=colors[variant],label=variant)
                for i,c in enumerate(caps):
                    values=[q['value'] for q in c[metric]['values'] if q['value'] is not None]
                    ax.scatter(np.full(len(values),i)+(-.045 if variant=='M' else .045),values,s=13,alpha=.4,color=colors[variant])
                    if metric=='objective': objectives.extend(values)
                ax.set_xticks(x,widths); ax.set_xlabel('Width')
        axes[0,col].set_ylim(-.35,8.65); axes[0,col].axhline(8,ls=':',lw=.8,color='gray')
        axes[0,col].set_title(panel+' / R random\nUndefined /9 by capacity:\n'+
            f'M {missing["M"]}; U {missing["U"]}',fontsize=9)
        axes[0,col].set_ylabel('p* (range 0..8)')
        upper=max(.001,max(objectives,default=0.))*1.5
        axes[1,col].set_yscale('symlog',linthresh=.001); axes[1,col].set_ylim(0,upper)
        axes[1,col].set_ylabel('Fit objective (symlog)'); axes[1,col].set_title(panel+' — every defined point retained')
        assert all(0<=value<upper for value in objectives)
        limits[panel]=dict(minimum=0,maximum=upper,largest_point=max(objectives,default=None),every_defined_point_included=True)
    handles,labels=axes[0,0].get_legend_handles_labels(); fig.legend(handles,labels,loc='outside lower center',ncol=2)
    fig.suptitle('Selected signed-gain fits — dots: nested model seeds; undefined values suppress means')
    fig.savefig(out/'selected-fits.png'); plt.close(fig)
    write(out/'PLOT_CHECKS.json',dict(status='PASS',objective_limits=limits,
        condition='All defined objective points lie inside displayed axes; no missing-value imputation',visual_review='pending'))


def report(root,out,selection,summary,baseline,diagnostic,evidence,results,initial_results):
    primary=summary['primary']; panels=sorted(summary['panels']); complete=read(root/'COMPLETE.json')
    text='# Stage 6 v0.7 — replikasi panel tuning untuk kebijakan tanpa adaptasi\n\n'
    text+=f'Run `{root.name}`: **576 tuning + {selection["planned_confirmation"]} confirmation trajectories**, **102 pretrained models**, '
    text+='dan **54 evaluasi awal test**. Empat panel tuning baru memakai korpus konfirmasi yang sama.\n\n'
    text+='## 1. Hasil utama\n\n'
    text+=f"Pada **U / R / random**, kapasitas terbesar memilih tanpa adaptasi pada **{primary['largest_no_adaptation_count']}/4 panel**. "
    text+=f"Kriteria adaptasi berguna kapasitas menengah terpenuhi pada **{primary['middle_useful_adaptation_count']}/4 panel**. "
    text+='Ini adalah frekuensi deskriptif pada empat panel; tidak diberi label biner “stabil” berdasarkan threshold baru dan tidak diuji dengan uji signifikansi.\n\n'
    text+=table(['Panel','Terbesar epoch0','Menengah update>0','3 korpus Δtest>0','3 korpus val≤awal','Menengah berguna','Global berguna','Scaling','K verdict'],[
        [p['panel'],p['largest_no_adaptation'],p['middle_utility']['nonzero_updates'],p['middle_utility']['all_corpora_positive'],
         p['middle_utility']['all_corpora_validation_improves'],p['middle_utility']['met'],p['global_useful'],p['scaling'],p['peak_verdict']]
        for p in primary['panels']])+'\n\n'
    text+='Δtest = initial test NLL − selected test NLL. Utility pada satu kapasitas memerlukan update nonzero, Δtest mean positif di setiap korpus, '
    text+='dan validation mean tidak lebih buruk dari model awal pada setiap korpus. Epoch0 memberi delta tepat nol dan p* undefined. '
    text+='Scaling adalah gerbang terpisah: test NLL turun ketat sepanjang kapasitas dan validation≤awal di seluruh kapasitas/korpus.\n\n'
    text+='**Desain replikasi:** 4 panel tuning × **3 korpus konfirmasi yang sama**, masing-masing dengan 3 seed model/bobot bersarang. '
    text+='Ke-12 sel panel×korpus bukan 12 korpus independen, dan 36 pasangan per kapasitas bukan 36 replikasi data independen. '
    text+='Konfigurasi terpilih yang sama memakai checkpoint konfirmasi yang sama. Tidak ada panel dipilih berdasarkan test, p*, atau peak.\n\n'
    text+='## 2. Seluruh keputusan validation dan frekuensinya\n\n'
    text+='R memilih validation random; J memilih gabungan random/uniform. Setiap panel memakai dua pasangan corpus/model tuning tersendiri. '
    text+='Variasi panel mencakup data tuning, seed model/bobot, dan data pretraining; tidak mengisolasi efek korpus tuning saja. '
    text+='Kandidat epoch0 kanonik dibandingkan dengan enam optimizer×enam epoch; tie full precision, epoch terdini, LR lalu WD terkecil.\n\n'
    text+=table(['Selektor','Kondisi','Lebar','Epoch0 /4','Frekuensi setting (grid/epoch: panel)'],[
        [r['policy'],r['variant'],r['width'],r['no_adaptation_count'],'; '.join(
         f"g{s['grid_index']}/e{s['epoch']}: {s['count']}/4 ({','.join(s['panels'])})" for s in r['settings'])]
        for r in summary['choice_frequencies']])+'\n\n![All selections](selection-panels.png)\n\n'
    text+='Semua candidate scores, LR/WD, pilihan, dan union konfirmasi dibekukan di `selection.json`. Detail setting identik/alias dipertahankan di `panel-summary.json`. '
    text+='Union optimizer dijalankan dalam kedua arm sampai epoch30; semua enam checkpoint terdeklarasi dievaluasi, tanpa pemilihan ulang memakai konfirmasi.\n\n'
    text+='## 3. Matriks gain silang dan dua marginal terpisah\n\n'
    text+='Setiap sel adalah rerata tiga seed pada pasangan panel/korpus. “SD panel” adalah SD empat marginal panel setelah merata-ratakan tiga korpus; '
    text+='“SD korpus” adalah SD tiga marginal korpus setelah merata-ratakan empat panel. Keduanya mengukur sumber variasi berbeda, '
    text+='bukan standard error/CI dan bukan estimasi dengan asumsi seluruh sel independen. Tidak ada SD gabungan 12 sel/36 pasangan yang dipakai untuk inferensi.\n\n'
    text+=table(['Lebar','Δtest grand mean','SD marginal panel (n=4)','SD marginal korpus (n=3)','Sumber checkpoint unik /36'],[
        [w,fmt(summary['crossed'][f'U_R_random_w{w}']['delta_test']['descriptive_grand_mean']),
         fmt(summary['crossed'][f'U_R_random_w{w}']['delta_test']['between_panel_marginals']['sd']),
         fmt(summary['crossed'][f'U_R_random_w{w}']['delta_test']['between_corpus_marginals']['sd']),
         summary['crossed'][f'U_R_random_w{w}']['delta_test']['unique_source_checkpoints']] for w,l in CAPS])+'\n\n'
    text+='![Crossed primary gains](crossed-gains.png)\n\n![Panel utility](utility-panels.png)\n\n'
    text+='`crossed-summary.json` menyimpan matriks, setiap marginal, seluruh 36 nilai pasangan dan referensi checkpoint. '
    text+='`policy-cells.csv` mempertahankan loss/accuracy semua komponen, clipping, gain, p*, dan alasan undefined untuk setiap kebijakan.\n\n'
    text+='## 4. Semua kebijakan dan kualitas fit\n\n'
    text+=table(['Panel','Kebijakan','Arm','Useful global','Scaling','K mean','Undefined K /9','K positif /9','Verdict'],[
        [p,key,arm,a['useful_adaptation_met'],a['scaling']['met'],fmt(a['peak']['between_corpora']['mean']),
         a['peak']['all_pairs']['undefined'],a['peak']['all_pairs']['positive'],a['peak_verdict']]
        for p in panels for key,cell in summary['panels'][p]['cells'].items() for arm,a in cell['arms'].items()])+'\n\n'
    text+='K = p* tengah − max(p* kecil,p* besar). Setiap undefined dipropagasikan ke rerata dan kontras. '
    text+='Uniform selalu undefined. Tiga kapasitas tidak dapat membuktikan perpindahan antara dua peak interior.\n\n'
    text+=table(['Panel','Kondisi / R random','Lebar','Epoch','p* mean','Undefined /9','Batas atas /9','Objective mean','Cancellation mean','Δtest negatif /9','Δvalidation negatif /9'],[
        [p,v,c['width'],c['selection']['epoch'],fmt(c['p']['between_corpora']['mean']),c['undefined_p'],c['upper_boundary'],
         fmt(c['objective']['between_corpora']['mean']),fmt(c['cancellation_ratio']['between_corpora']['mean']),
         c['delta_test']['all_pairs']['negative'],c['delta_validation']['all_pairs']['negative']]
        for p in panels for v in VARIANTS for c in summary['panels'][p]['cells'][f'{v}_R']['arms']['random']['capacity']])+'\n\n'
    text+='P* memakai signed gain asli dan rentang pencarian [0,8]. Gain nonpositive/di bawah guard, no adaptation dan bobot uniform tetap undefined. '
    text+='Cancellation ratio = |Σgain|/Σ|gain|, undefined bila semua gain nol. Nilai batas dan objective buruk membatasi interpretasi, '
    text+='tanpa filtering atau perubahan rentang estimator. Gambar objective mempertahankan semua titik; mean dihilangkan bila satu saja nilai undefined.\n\n![Selected fits](selected-fits.png)\n\n'
    text+=table(['Panel','Kebijakan','Arm','Lebar','Train NLL','Validation NLL','Test NLL','Instance train accuracy','Clipping'],[
        [p,key,arm,c['width'],fmt(c['train_nll']['between_corpora']['mean']),fmt(c['validation_nll']['between_corpora']['mean']),
         fmt(c['test_nll']['between_corpora']['mean']),fmt(c['train_instance_accuracy']['between_corpora']['mean']),fmt(c['clipping']['between_corpora']['mean'])]
        for p in panels for key,cell in summary['panels'][p]['cells'].items() for arm,a in cell['arms'].items() for c in a['capacity']])+'\n\n'
    text+='Clipping epoch0 undefined karena tidak ada update. Diagnosis component, group+instance, oracle-reference, signed allocation/Gram, '
    text+='massa gain positif/negatif dan seluruh checkpoint tetap disimpan. Diagnosis ini tidak mengganti estimator utama dan tidak menjadi kriteria seleksi.\n\n'
    text+='## 5. Manipulasi baseline dan audit\n\n'
    text+=f"Manipulation check: **{sum(c['passed'] for c in baseline['checks'])}/{len(baseline['checks'])}** kapasitas/korpus lulus. "
    text+='U harus menurunkan initial group/instance validation NLL terhadap M dengan shared accuracy≥95%.\n\n'
    text+=table(['Lebar','Korpus','U group','M group','U instance','M instance','U shared accuracy','Lulus'],[
        [c['width'],c['data_seed'],fmt(c['values']['U']['validation_group_loss']),fmt(c['values']['M']['validation_group_loss']),
         fmt(c['values']['U']['validation_instance_loss']),fmt(c['values']['M']['validation_instance_loss']),
         fmt(c['values']['U']['validation_shared_accuracy']),c['passed']] for c in baseline['checks']])+'\n\n'
    text+='M/U pasangan memakai full token/label, cold state, assignment/order yang sama. U mengubah objective pretraining dan mungkin representasi/dinamika; '
    text+='U−M tidak mengisolasi pengaruh satu angka baseline. Check bukan asesmen kalibrasi probabilitas lengkap.\n\n'
    text+=f"Audit integritas independen: **{evidence['status']}**; utility/scaling/K setiap panel diperiksa ulang. "
    text+='Audit meliputi frozen source, histori Stage0–5, regenerasi data lengkap, seed split, cold/pretrained equality, weights/orders, '
    text+='candidate/tie/schedule seluruh panel, alias epoch0, serta test setelah selection freeze.\n\n'
    da=diagnostic['audit']
    text+=f"Gram original strict absolute-check failures: **{len(da['original_strict_failures'])}**; "
    text+='semuanya dicatat dan harus melewati verifikasi 70 digit/batas akumulasi float64 yang telah dipraspesifikasikan. '
    text+=f"Normalisasi cumulative-primary undefined: **{len(da['undefined_primary_cumulative_comparisons'])}**, disimpan null+alasan. "
    text+='Tidak ada toleransi lain yang dilonggarkan; fit/gain/seleksi tetap. Detail `DIAGNOSTIC_AUDIT.json`.\n\n'
    text+='## 6. Runtime dan keterbatasan penyimpanan\n\n'
    perf=complete['elapsed_seconds']; wall=complete['utc_elapsed_seconds']
    text+=f'Timer training: perf_counter **{perf/60:.2f} menit**, UTC **{wall/60:.2f} menit**; '
    text+=f'selisih UTC−perf_counter **{wall-perf:.6f} detik**, tanpa mengasumsikan penyebab. Budget180 menit memakai timer yang lebih besar; CPU analisis tidak termasuk.\n\n'
    groups=[('Pretraining',[read(p) for p in sorted((root/'baselines').glob('*/result.json'))]),
            ('Initial evaluation',list(initial_results.values())),('Adaptation',list(results.values()))]
    text+=table(['Tahap','Jumlah','Peak allocated MiB','Peak reserved MiB'],[
        [label,len(group),fmt(max(r['peak_allocated_mib'] for r in group)),fmt(max(r['peak_reserved_mib'] for r in group))]
        for label,group in groups])+'\n\n'
    text+='**Penyimpanan model:** cold/pretrained dan model epoch30 disimpan penuh. Model adaptasi epoch1/3/5/10/20 tidak disimpan sebagai biner; '
    text+='map SHA tensor model dicatat saat runtime, beserta seluruh per-sequence losses/metrics setiap checkpoint. Audit dapat memeriksa loss/fit/seleksi '
    text+='dari rekaman tersebut, tetapi tidak dapat menghitung ulang hash bobot intermediate dari biner yang tidak disimpan. '
    text+='Model intermediate harus diregenerasi dengan rerun jika dibutuhkan; ketersediaan hash bukan bukti ekuivalen dengan audit ulang binary checkpoint.\n\n'
    text+='Model penuh yang tersedia tetap lokal dan dikecualikan dari archive ringkas; semua raw files dicatat SHA, dataset/losses/assignment/orders/source '
    text+='disertakan, archive diuji CRC dan SHA. Tidak ada retry implisit, seed pengganti, cloud, upload atau publikasi.\n\n'
    text+='## 7. Batas ilmiah dan provenance\n\n'
    text+='Empat panel memperluas replikasi proses seleksi; hanya tiga korpus konfirmasi dibagi bersama. Grid optimizer/horizon terbatas, task sintetis dan tiga kapasitas '
    text+='tidak membuktikan optimum global, scaling umum, exact large-LM replication, novelty atau kesiapan venue. '
    text+='Tidak ada notebook yang diklaim telah dieksekusi; script eksperimen digunakan. Interpretasi Stage5 memotivasi desain, bukan data konfirmasi tambahan.\n\n'
    text+=f"Protocol SHA256: `{sha(HERE/'PROTOCOL_STAGE6.md')}`. Selection SHA256: `{sha(root/'selection.json')}`. "
    text+='Manifest source/environment/checks lengkap tersedia dalam raw archive. Arahan literatur dan batas klaim mengikuti `LITERATURE_CHECK.md`; '
    text+='tidak ada klaim kebaruan baru dalam tahap ini.\n'
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def verify_analysis_source(root):
    manifest=read(root/'analysis_source_manifest.json')
    assert {'analyze_stage6.py','analysis_core.py','analysis_checks.py','audit_stage6.py'} <= set(manifest)
    for name,digest in manifest.items():
        assert sha(root/'analysis-source'/name)==digest and sha(HERE/name)==digest,name
    checks=read(root/'ANALYSIS_CHECKS.json'); assert checks['status']=='PASS'
    return dict(status='PASS',source_sha256=manifest,fixture_checks=checks)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True); parser.add_argument('--wait',action='store_true')
    args=parser.parse_args(); assert Path(args.run_id).name==args.run_id
    root=ROOT/'work/runs'/args.run_id; out=HERE/f'results-{args.run_id}'
    assert not out.exists(),'Preserve completed or partial analysis'
    torch.set_num_threads(4)
    if args.wait:
        print('Waiting for training completion; no measured outcomes inspected.',flush=True)
        while not (root/'COMPLETE.json').exists():
            if (root/'EXPERIMENT_FAILURE.json').exists() or list(root.rglob('failure.json')): raise RuntimeError('Training failure; preserve records')
            time.sleep(10)
    assert (root/'COMPLETE.json').exists(); out.mkdir()
    try:
        source=verify_analysis_source(root); write(out/'ANALYSIS_SOURCE_AUDIT.json',source)
        from audit_stage6 import audit
        evidence,selection,results,records,initial_results,initial_records=audit(root)
        write(out/'AUDIT.json',evidence); print('Independent integrity audit PASS.',flush=True)
        rows=flat_rows(results,initial_results); baselines=initial_rows(initial_results)
        csvwrite(out/'all-checkpoints.csv',rows); csvwrite(out/'canonical-initial.csv',baselines)
        diagnostic,diag_rows=diagnostics_analysis(results,records,initial_results,initial_records)
        write(out/'diagnostics.json',diagnostic); write(out/'DIAGNOSTIC_AUDIT.json',diagnostic['audit']); csvwrite(out/'diagnostics.csv',diag_rows)
        summary,selected,gates=panel_analysis(selection,rows,baselines,diag_rows)
        write(out/'panel-summary.json',summary); write(out/'crossed-summary.json',summary['crossed'])
        write(out/'choice-frequencies.json',summary['choice_frequencies']); csvwrite(out/'policy-cells.csv',selected)
        write(out/'GATE_AUDIT.json',dict(status='PASS',panels=gates))
        matrix_rows=[]
        for key,metrics in summary['crossed'].items():
            for metric,value in metrics.items():
                matrix_rows.extend(dict(policy_capacity=key,metric=metric,**cell) for cell in value['panel_corpus_matrix'])
        csvwrite(out/'crossed-matrix.csv',matrix_rows)
        baseline=baseline_analysis(baselines); write(out/'baseline-summary.json',baseline)
        figures(out,summary,selection); report(root,out,selection,summary,baseline,diagnostic,evidence,results,initial_results)
        write(out/'analysis-provenance.json',dict(utc=utc(),source_sha256=source['source_sha256'],
            protocol_sha256=sha(HERE/'PROTOCOL_STAGE6.md'),selection_sha256=sha(root/'selection.json'),visual_review='pending'))
        for name in source['source_sha256']: shutil.copy2(HERE/name,out/name)
        for name in ['README.md','PROTOCOL_STAGE6.md']: shutil.copy2(HERE/name,out/name)
        print('Report and four figures ready; hashing raw records and compact archive.',flush=True)
        manifest={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}; write(out/'raw-manifest.json',manifest)
        archive=out/'run-records.zip'; omitted=[]
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(root.rglob('*')):
                if not p.is_file(): continue
                rel=str(p.relative_to(root))
                if p.name in ['cold.pt','pretrained.pt'] or (p.name.startswith('model-e') and p.suffix=='.pt'):
                    omitted.append(rel); continue
                z.write(p,'raw/'+rel)
            write(out/'archive-omissions.json',dict(reason='Available model binaries remain local; full SHA256 retained; intermediate adaptation model binaries were not saved by design',files=omitted))
            for p in sorted(out.iterdir()):
                if p.is_file() and p!=archive: z.write(p,'report/'+p.name)
        with zipfile.ZipFile(archive) as z: assert z.testzip() is None
        write(out/'ARCHIVE_CHECK.json',dict(utc=utc(),sha256=sha(archive),bytes=archive.stat().st_size,crc='PASS',
            raw_files=len(manifest),omitted_model_binaries=len(omitted),retained_raw_files=len(manifest)-len(omitted)))
        print(json.dumps(dict(output=str(out),audit='PASS',archive='PASS',primary=summary['primary'])),flush=True)
    except Exception:
        write(out/'ANALYSIS_FAILURE.json',dict(utc=utc(),traceback=traceback.format_exc(),
            instruction='Preserve partial outputs; diagnose under a new version before changing frozen scientific code.'))
        raise


if __name__=='__main__': main()
