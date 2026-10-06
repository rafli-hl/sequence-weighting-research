"""Presentation-only revision from frozen Stage8 metrics; no profile calculations."""
import inspect
import json
import shutil
import time
import zipfile
from pathlib import Path
import analyze_stage8 as frozen


def main():
    started=time.perf_counter()
    run='precision-v09-20260930-01'
    base=frozen.HERE/f'results-{run}'
    out=frozen.HERE/f'results-{run}-r1'
    raw=frozen.ROOT/'work/runs'/run
    assert not out.exists(), 'Preserve every prior presentation'
    source=frozen.read(raw/'source_manifest.json')
    for name,digest in source.items():
        assert frozen.sha(frozen.HERE/name)==frozen.sha(raw/'source'/name)==digest
    previous=frozen.read(base/'ARCHIVE_CHECK.json')
    assert previous['status']=='PASS' and frozen.sha(base/'run-records.zip')==previous['sha256']
    numerical=['profile-metrics.jsonl','summaries.json','summaries.csv','SUMMARY_AUDIT.json','AUDIT.json','raw-manifest.json']
    source_text=inspect.getsource(frozen.figures)
    old_tick="magnitudes=[10.**e for e in range(-18,31,6) if 10.**e<=high]"
    new_tick="magnitudes=[10.**e for e in range(-12,31,6) if 10.**e<=high]"
    old_rates="""        axes[r,0].text(.01,.04,'Comparable profiles by category: '+','.join(str(g['both_defined'])+'/64' for g in cellgroups),"""
    new_rates="""        rate_values=[g['methods'][name]['pairwise'][metric] for g in cellgroups for name in METHODS
                     for metric in ['float_tie_rate_on_reference_strict','strict_reversal_rate']
                     if g['methods'][name]['pairwise'][metric] is not None]
        maximum=max(rate_values,default=0.)
        if maximum>0:
            axes[r,1].set_ylim(-.03*maximum,1.15*maximum)
            axes[r,1].ticklabel_format(axis='y',style='sci',scilimits=(-3,3))
        axes[r,1].set_ylabel('Fraction of reference-strict pairs')
        low_rate,high_rate=axes[r,1].get_ylim()
        assert all(low_rate<v<high_rate for v in rate_values)
        limits[f'pair_rates_{n}_{p}']=dict(minimum=low_rate,maximum=high_rate,
            points=len(rate_values),all_points_inside=True)
        axes[r,0].text(.01,.04,'Comparable profiles by category: '+','.join(str(g['both_defined'])+'/64' for g in cellgroups),"""
    assert source_text.count(old_tick)==source_text.count(old_rates)==1
    revised=source_text.replace(old_tick,new_tick).replace(old_rates,new_rates)
    out.mkdir()
    exclude={'REPORT.md','run-records.zip','ARCHIVE_CHECK.json','PLOT_CHECKS.json',
             'grid-ranking.png','contrast-errors.png','reference-regret.png'}
    for path in base.iterdir():
        if path.is_file() and path.name not in exclude: shutil.copy2(path,out/path.name)
    shutil.copy2(base/'REPORT.md',out/'REPORT-original.md')
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    figure_source=out/'figure-source-r1.py'
    figure_source.write_text('from analyze_stage8 import *\n\n'+revised,encoding='utf-8')
    namespace=dict(vars(frozen))
    exec(compile(revised,str(figure_source),'exec'),namespace)
    profiles=[json.loads(line) for line in (base/'profile-metrics.jsonl').read_text(encoding='utf-8').splitlines()]
    cells=frozen.read(base/'summaries.json')['cells']
    namespace['figures'](out,profiles,cells)
    note=('# Presentation r1\n\n'
          'This revision makes small pairwise error rates visible and removes overlapping symlog tick labels near zero. '
          'Legacy J64 and naive D64 have identical ranking counts, so their lines overlap. '
          'All profile metrics, summaries, audited raw records and scientific conclusions are byte-identical to the original release. '
          'The original report and archive remain preserved. No experiment, reference profile or fit was rerun.\n\n')
    (out/'REPORT.md').write_text(note+(base/'REPORT.md').read_text(encoding='utf-8'),encoding='utf-8')
    unchanged={name:frozen.sha(base/name) for name in numerical}
    assert all(frozen.sha(out/name)==digest for name,digest in unchanged.items())
    raw_manifest=frozen.read(base/'raw-manifest.json')
    assert {p.relative_to(raw).as_posix() for p in raw.rglob('*') if p.is_file()}==set(raw_manifest)
    assert all(frozen.sha(raw/name)==digest for name,digest in raw_manifest.items())
    frozen.write(out/'PRESENTATION_CHANGE.json',dict(status='PASS',utc=frozen.utc(),
        original_archive_sha256=previous['sha256'],original_report_sha256=frozen.sha(base/'REPORT.md'),
        unchanged_numerical_sha256=unchanged,unchanged_raw_files=len(raw_manifest),
        finalizer_sha256=frozen.sha(Path(__file__)),figure_source_sha256=frozen.sha(figure_source),
        frozen_analyzer_sha256=source['analyze_stage8.py'],new_profiles_or_fits=False,
        changes=['Pairwise rate axes include zero and all values with 15% headroom; exact fractions unchanged.',
                 'Remove +/-1e-18 major tick labels beside zero; symlog scale and all points/limits unchanged.',
                 'Explain identical Legacy/Naive ranking lines in presentation note.'],visual_review='pending'))
    archive=out/'run-records.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(raw.rglob('*')):
            if path.is_file(): z.write(path,'raw/'+path.relative_to(raw).as_posix())
        for path in sorted(out.iterdir()):
            if path.is_file() and path!=archive: z.write(path,'report/'+path.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert sum(name.startswith('raw/') for name in z.namelist())==len(raw_manifest)
    frozen.write(out/'ARCHIVE_CHECK.json',dict(status='PASS',crc='PASS',utc=frozen.utc(),
        sha256=frozen.sha(archive),bytes=archive.stat().st_size,raw_files=len(raw_manifest),
        elapsed_seconds=time.perf_counter()-started,original_archive_sha256=previous['sha256']))
    print(json.dumps(dict(status='PASS',output=str(out),unchanged_raw_files=len(raw_manifest))),flush=True)


if __name__=='__main__': main()
