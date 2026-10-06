"""Presentation-only Stage9 r2: prevent tick selection from expanding plot limits."""
import argparse
import hashlib
import inspect
import json
import resource
import shutil
import sys
import time
import zipfile
sys.dont_write_bytecode=True
import analyze_stage9_r1 as analysis
from common_stage9 import ROOT,HERE,read,sha,utc,write,verify_source,verify_inputs

NUMERIC=['profile-metrics.jsonl','policy-reference-metrics.jsonl','profile-metrics.csv',
    'policy-reference-metrics.csv','summaries.json','summaries.csv','SUMMARY_AUDIT.json',
    'raw-manifest.json','AUDIT.json','ANALYSIS_REPAIR.json','ANALYSIS_REPAIR_CHECKS.json',
    'ORIGINAL_ANALYSIS_FAILURE.json']
IMAGES=['grid-agreement.png','contrast-errors.png','model-context.png']


def corrected_figure_source():
    source=inspect.getsource(analysis.figures)
    start=source.index('    def scaled(')
    end=source.index('\n    fig, axes =',start)
    fixed='''    def scaled(ax, axis, values):
        if not values:
            return
        nonzero = [abs(v) for v in values if v]
        threshold = max(1e-300, 10. ** (math.floor(math.log10(min(nonzero))) - 1)) if nonzero else 1.
        low, high = min(values), max(values)
        if low > 0:
            bounds = (low / 2., high * 2.)
        elif high < 0:
            bounds = (low * 2., high / 2.)
        elif low == high == 0:
            bounds = (-threshold, threshold)
        else:
            bounds = (low * 2. if low < 0 else -threshold, high * 2. if high > 0 else threshold)
        getattr(ax, 'set_' + axis + 'scale')('symlog', linthresh=threshold)
        setter = getattr(ax, 'set_' + axis + 'lim')
        setter(bounds)
        ticks = [v for v in getattr(ax, 'get_' + axis + 'ticks')()
                 if bounds[0] <= v <= bounds[1] and (v == 0 or abs(v) > threshold * 1.01)]
        getattr(ax, 'set_' + axis + 'ticks')(ticks)
        setter(bounds)  # Fixed ticks may expand limits; reapply the data-derived bounds.
'''
    return source[:start]+fixed+source[end:]


def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); args=p.parse_args()
    assert args.run_id.startswith('model-precision-v010-') and '/' not in args.run_id and '\\' not in args.run_id
    raw=ROOT/'work/runs'/args.run_id
    prior=HERE/f'results-{args.run_id}-r1'; out=HERE/f'results-{args.run_id}-r2'
    assert not out.exists()
    start=time.perf_counter(); verify_source(raw); verify_inputs(raw)
    old_archive=read(prior/'ARCHIVE_CHECK.json')
    assert old_archive['status']==old_archive['crc']=='PASS'
    assert sha(prior/'run-records.zip')==old_archive['sha256']
    with zipfile.ZipFile(prior/'run-records.zip') as z: assert z.testzip() is None
    numeric={name:sha(prior/name) for name in NUMERIC}
    profiles=[json.loads(x) for x in (prior/'profile-metrics.jsonl').read_text(encoding='utf-8').splitlines()]
    aliases=[json.loads(x) for x in (prior/'policy-reference-metrics.jsonl').read_text(encoding='utf-8').splitlines()]
    cells=read(prior/'summaries.json')['cells']
    assert len(profiles)==186 and len(aliases)==324 and len(cells)==36
    out.mkdir()
    excluded=set(IMAGES+['run-records.zip','ARCHIVE_CHECK.json','PLOT_CHECKS.json','REPORT.md'])
    for path in prior.iterdir():
        if path.is_file() and path.name not in excluded: shutil.copy2(path,out/path.name)
    try:
        source=corrected_figure_source(); namespace=vars(analysis).copy()
        exec(compile(source,'<Stage9-presentation-r2-figures>','exec'),namespace)
        namespace['figures'](out,profiles,aliases,cells)
        original=(prior/'REPORT.md').read_text(encoding='utf-8')
        note='Presentation r2 fixes axis-limit expansion in the error and stored-point plots. Every numerical table, model-context value and raw record is byte-identical to r1. The preserved r1 report documents the separate null-handling repair.\n\n'
        heading,rest=original.split('\n\n',1)
        (out/'REPORT.md').write_text(heading+'\n\n'+note+rest,encoding='utf-8')
        assert all(sha(out/name)==digest for name,digest in numeric.items())
        shutil.copy2(HERE/'finalize_stage9_r2.py',out/'finalize_stage9_r2.py')
        write(out/'PRESENTATION_R2.json',dict(status='PASS',utc=utc(),revision='r2',
            prior_report=prior.relative_to(ROOT).as_posix(),prior_archive_sha256=old_archive['sha256'],
            prior_archive_crc='PASS',prior_archive_bytes=old_archive['bytes'],
            preserved_numeric_sha256=numeric,profiles_sha256=sha(raw/'profiles.jsonl'),
            parent_figure_source_sha256=sha(HERE/'analyze_stage9_r1.py'),
            finalizer_sha256=sha(HERE/'finalize_stage9_r2.py'),
            derived_figure_function_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
            modified_plots=IMAGES,change='Only nested symlog axis bounds/ticks; data, statistics and eligibility unchanged',
            recomputed_objectives=False,recomputed_numerical_summaries=False,visual_review='pending'))
        manifest=read(out/'raw-manifest.json')
        assert set(manifest)=={p.relative_to(raw).as_posix() for p in raw.rglob('*') if p.is_file()}
        for name,digest in manifest.items(): assert sha(raw/name)==digest
        archive=out/'run-records.zip'
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for name in sorted(manifest): z.write(raw/name,'raw/'+name)
            for path in sorted(out.iterdir()):
                if path.is_file() and path!=archive: z.write(path,'report/'+path.name)
        with zipfile.ZipFile(archive) as z: assert z.testzip() is None
        write(out/'ARCHIVE_CHECK.json',dict(status='PASS',crc='PASS',utc=utc(),sha256=sha(archive),
            bytes=archive.stat().st_size,raw_files=len(manifest),analysis_elapsed_seconds=time.perf_counter()-start,
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            scope='Presentation revision only; original analysis runtime remains copied from r1'))
        print(json.dumps(dict(status='PASS',output=str(out),archive=read(out/'ARCHIVE_CHECK.json'))),flush=True)
    except BaseException as exc:
        write(out/'PRESENTATION_FAILURE.json',dict(status='FAILED',utc=utc(),error=repr(exc)))
        raise


if __name__=='__main__': main()
