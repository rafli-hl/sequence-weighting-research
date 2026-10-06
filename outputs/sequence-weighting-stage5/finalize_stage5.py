"""Presentation-only revision: retain all fit points and separate undefined labels."""
import argparse
import json
import shutil
import zipfile
import sys
sys.dont_write_bytecode=True
from engine import ROOT,HERE,read,write,sha,utc


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-id',required=True); args=ap.parse_args()
    original=HERE/f'results-{args.run_id}'; out=HERE/f'results-{args.run_id}-r1'
    assert not out.exists(), 'Preserve earlier presentation outputs'
    check=read(original/'ARCHIVE_CHECK.json'); assert check['crc']=='PASS'
    assert sha(original/'run-records.zip')==check['sha256']
    out.mkdir()
    for p in original.iterdir():
        if p.is_file() and p.name not in ['run-records.zip','ARCHIVE_CHECK.json']:
            shutil.copy2(p,out/p.name)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    summary=read(out/'policy-summary.json')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
    colors={'M':'#315b96','U':'#bd4e26'}; widths=[64,128,256]; x=np.arange(3)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained'); limits={}
    for col,policy in enumerate(['R','J']):
        objectives=[]
        for variant in ['M','U']:
            caps=summary['cells'][f'{variant}_{policy}']['arms']['random']['capacity']
            for row,metric in enumerate(['p','objective']):
                ax=axes[row,col]
                means=[c[metric]['between_corpora']['mean'] for c in caps]
                ax.plot(x,[np.nan if z is None else z for z in means],'-o',color=colors[variant],label=variant)
                for i,c in enumerate(caps):
                    vals=[q['value'] for q in c[metric]['values'] if q['value'] is not None]
                    ax.scatter(np.full(len(vals),i)+(-.045 if variant=='M' else .045),vals,s=13,alpha=.35,color=colors[variant])
                    if metric=='objective': objectives.extend(vals)
                    if metric=='p' and c['undefined_p']:
                        ax.annotate(f'{variant}: {c["undefined_p"]}/9 undefined\n(no mean point)',
                            xy=(i,.75 if variant=='U' else .62),xycoords=('data','axes fraction'),
                            ha='right' if i==2 else 'left',va='top',fontsize=9,color=colors[variant])
                ax.set_xticks(x,widths); ax.set_xlabel('Width'); ax.set_title(f'{policy}: random arm')
        axes[0,col].set_ylim(-.35,8.65); axes[0,col].axhline(8,ls=':',lw=.8,color='gray')
        axes[0,col].set_ylabel('p* (search interval 0..8)'); axes[0,col].legend(loc='upper left')
        ax=axes[1,col]; ax.set_yscale('symlog',linthresh=.001)
        upper=max(.001,max(objectives,default=0.))*1.5
        ax.set_ylim(0,upper); ax.set_ylabel('Fit objective (symlog; lower is better)')
        assert all(0<=value<upper for value in objectives)
        limits[policy]=dict(minimum=0,maximum=upper,largest_point=max(objectives,default=None),
                            every_defined_point_included=True)
    fig.suptitle('Selected signed-gain fits — dots are paired seeds; missing means retain undefined values')
    fig.savefig(out/'selected-fits.png'); plt.close(fig)
    report=(original/'REPORT.md').read_text(encoding='utf-8')
    report=report.replace('\n\n','\n\n**Revisi presentasi r1:** batas vertikal grafik objective diperluas agar semua titik terlihat penuh; '
        'label undefined dipindahkan dari garis nol. Catatan pasangan individual dan LR terpilih memperjelas pembacaan hasil. '
        'Semua data, estimasi dan audit identik dengan analisis awal yang tetap disimpan.\n\n',1)
    middle=next(c for c in summary['cells']['U_R']['arms']['random']['capacity'] if c['width']==128)
    negatives={metric:sum(x['value']<0 for x in middle[metric]['values']) for metric in ['delta_test','delta_validation']}
    note=(f"Kriteria di atas memakai rerata per korpus. Pada kapasitas menengah, {negatives['delta_test']}/9 pasangan "
          f"memiliki test NLL yang memburuk dan {negatives['delta_validation']}/9 memiliki validation NLL yang memburuk, "
          'meskipun ketiga rerata korpus memenuhi kriteria. Manfaat menengah yang kecil ini belum membuktikan '
          'kestabilan seleksi pada panel tuning lain.\n\n')
    report=report.replace('![Test utility](utility.png)',note+'![Test utility](utility.png)',1)
    choices=read(ROOT/'work/runs'/args.run_id/'selection.json')['decisions']
    selected_lrs={c['lr'] for policies in choices.values() for capacities in policies.values() for c in capacities.values() if c['epoch']>0}
    assert selected_lrs=={.0001}
    report=report.replace('![Selections](selection.png)',
        'Seluruh pilihan nonzero memakai LR1e-4; kandidat LR1e-5 dan3e-5 tidak terpilih. '
        'Karena itu manfaat yang terukur tidak dapat diatribusikan khusus pada penggunaan learning rate yang lebih kecil.\n\n'
        '![Selections](selection.png)',1)
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    unchanged={p.name:sha(p) for p in original.iterdir() if p.is_file() and p.name not in
               ['REPORT.md','selected-fits.png','run-records.zip','ARCHIVE_CHECK.json']}
    assert all(sha(out/name)==digest for name,digest in unchanged.items())
    write(out/'PRESENTATION_REVISION.json',dict(utc=utc(),original=str(original.relative_to(ROOT)),
        scientific_files_unchanged=unchanged,original_archive_sha256=check['sha256'],
        original_report_sha256=sha(original/'REPORT.md'),revised_report_sha256=sha(out/'REPORT.md'),
        original_figure_sha256=sha(original/'selected-fits.png'),revised_figure_sha256=sha(out/'selected-fits.png'),
        plot_limits=limits,primary_middle_negative_pairs=negatives,selected_nonzero_learning_rates=sorted(selected_lrs),
        revision_source_sha256=sha(HERE/'finalize_stage5.py')))
    shutil.copy2(HERE/'finalize_stage5.py',out/'finalize_stage5.py')
    archive=out/'run-records.zip'
    with zipfile.ZipFile(original/'run-records.zip') as old,zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for item in old.infolist():
            if item.filename.startswith('raw/'): z.writestr(item.filename,old.read(item.filename))
        for p in sorted(out.iterdir()):
            if p.is_file() and p!=archive: z.write(p,'report/'+p.name)
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    write(out/'ARCHIVE_CHECK.json',dict(utc=utc(),sha256=sha(archive),bytes=archive.stat().st_size,crc='PASS'))
    print(json.dumps(dict(output=str(out),scientific_files_unchanged=True,archive='PASS')),flush=True)


if __name__=='__main__': main()
