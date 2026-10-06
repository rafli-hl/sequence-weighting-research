"""Render prospective report fixtures for complete and all-missing evidence."""
import argparse
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
from artifacts import write, sha, source_manifest
from config import HERE
from check_analysis import decisions, saved_records
from analysis import summarize
from analyze_stage11 import report, plots, collect
from policies import tuning_schedule


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); start=time.perf_counter()
    args.output.mkdir(parents=True,exist_ok=False)
    selection=decisions()
    for name,records in [('complete',saved_records(selection)),('all-missing',[])]:
        folder=args.output/name; folder.mkdir()
        summary=summarize(records,selection)
        write(folder/'summaries.json',summary)
        report(folder,summary); plots(folder,summary)
        assert len(list(folder.glob('*.png')))==3
        if not records:
            assert 'undefined / unavailable' in (folder/'REPORT.md').read_text(encoding='utf-8')
    partial=args.output/'failed-before-selection'; partial.mkdir()
    write(partial/'FREEZE.json',{'source_sha256':source_manifest()})
    write(partial/'FAILURE.json',{'error':'fixture budget failure before selection','completed':[]})
    write(partial/'tuning_schedule.json',tuning_schedule())
    (partial/'runs'/tuning_schedule()[0]['name']).mkdir(parents=True)
    summary,_=collect(partial)
    report(partial,summary); plots(partial,summary)
    assert summary['selection'] is None and summary['scientific_effects'] is None
    assert len(summary['planned_tuning'])==72 and not list(partial.glob('*.png'))
    assert sum(r['status']=='partial' for r in summary['planned_tuning'])==1
    assert sum(r['status']=='not_run' for r in summary['planned_tuning'])==71
    write(args.output/'CHECK.json',dict(status='PASS',fixture_only=True,
        elapsed_seconds=time.perf_counter()-start,scenarios=['complete','all-missing','failed-before-selection'],
        visual_review_pending=True,source_sha256={n:sha(HERE/n) for n in
            ['config.py','policies.py','analysis.py','check_analysis.py','analyze_stage11.py','check_report.py']}))
    print({'status':'PASS','elapsed_seconds':time.perf_counter()-start})


if __name__=='__main__':
    main()
