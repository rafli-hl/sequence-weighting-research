"""Preserved presentation revision: distinguish recorded timer from UTC interval."""
import argparse
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime
sys.dont_write_bytecode=True
from engine import ROOT,HERE,read,write,sha,utc


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-id',required=True); args=ap.parse_args()
    raw=ROOT/'work/runs'/args.run_id
    original=HERE/f'results-{args.run_id}-analysis-r1'; revised=HERE/f'results-{args.run_id}-r2'
    assert (original/'ARCHIVE_CHECK.json').exists(), 'Wait until original analysis/archive completes'
    assert not revised.exists(),'Preserve presentation revisions'
    complete=read(raw/'COMPLETE.json')
    events=[json.loads(line) for line in (raw/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    starts=[e for e in events if e['kind']=='experiment_started']; assert len(starts)==1
    interval=(datetime.fromisoformat(complete['utc'])-datetime.fromisoformat(starts[0]['utc'])).total_seconds()
    timer=complete['elapsed_seconds']; difference=interval-timer
    assert interval<=10800 and timer<=10800
    frozen=json.loads((raw/'analysis-source/manifest.json').read_text(encoding='utf-8-sig'))
    assert sha(HERE/'analyze_stage4.py')==frozen['sha256']['analyze_stage4.py']
    assert sha(HERE/'analysis_checks.py')==frozen['sha256']['analysis_checks.py']
    original_archive=read(original/'ARCHIVE_CHECK.json')
    assert sha(original/'run-records.zip')==original_archive['sha256']
    revised.mkdir()
    for p in original.iterdir():
        if p.is_file() and p.name not in ['run-records.zip','ARCHIVE_CHECK.json']:
            shutil.copy2(p,revised/p.name)
    report=(original/'REPORT.md').read_text(encoding='utf-8')
    old=f'Training wall time {timer/60:.1f} menit mencakup pretraining,'
    assert old in report
    report=report.replace(old,f'Timer `perf_counter` mencatat {timer/60:.1f} menit untuk pretraining,',1)
    marker='setup, evaluasi dan penyimpanan; tidak mencakup persiapan, audit dan laporan.\n'
    assert marker in report
    note=(f'Interval dari timestamp UTC awal hingga COMPLETE adalah **{interval/60:.1f} menit** '
          f'({interval:.3f} detik), sedangkan timer mencatat {timer:.3f} detik. '
          f'Selisihnya {difference:.3f} detik; penyebab perbedaan kedua catatan waktu '
          'tidak ditetapkan dari bukti yang tersedia. Keduanya di bawah batas tiga jam. '
          'Nilai timer asli tetap disimpan tanpa perubahan; perbedaan ini tidak mengubah '
          'seleksi, hasil model, atau kontras statistik.\n\n')
    report=report.replace(marker,marker+'\n'+note,1)
    caution=re.search(r'Pada U/F/C30, \*\*.*?\n\n',report,flags=re.S).group(0)
    assert report.count(caution)==1
    report=report.replace(caution,'',1).replace('![Matched adaptation](matched.png)',caution+'![Matched adaptation](matched.png)',1)
    report=report.replace('![Selected policies](selected.png)',
        '![Selected policies](selected.png)\n\nTitik mean p* U pada kapasitas terbesar tidak ditampilkan: '
        'satu dari sembilan nilai undefined membuat mean yang dipropagasikan juga undefined; '
        'nilainya tidak diimputasi atau dihapus dari agregasi.',1)
    report=report.replace('\n\n','\n\n**Revisi presentasi r2:** memperjelas timer proses dan interval timestamp UTC, '
        'menempatkan peringatan kualitas fit di dekat hasil utama, dan menjelaskan titik undefined pada grafik. Data, estimasi, audit, dan gambar '
        'ilmiah identik dengan laporan analisis-r1 yang tetap disimpan.\n\n',1)
    (revised/'REPORT.md').write_text(report,encoding='utf-8')
    unchanged={p.name:sha(p) for p in original.iterdir() if p.is_file() and p.name not in
               ['REPORT.md','run-records.zip','ARCHIVE_CHECK.json']}
    assert all(sha(revised/name)==h for name,h in unchanged.items())
    write(revised/'PRESENTATION_REVISION.json',dict(utc=utc(),original=str(original.relative_to(ROOT)),
        scientific_files_unchanged=unchanged,original_archive_sha256=original_archive['sha256'],
        original_report_sha256=sha(original/'REPORT.md'),revised_report_sha256=sha(revised/'REPORT.md'),
        timer_elapsed_seconds=timer,utc_interval_seconds=interval,difference_seconds=difference,
        both_time_records_below_limit=True,cause_of_clock_difference='not established',
        analysis_source_matches_preinspection_snapshot=True,revision_source_sha256=sha(HERE/'finalize_stage4.py')))
    shutil.copy2(HERE/'finalize_stage4.py',revised/'finalize_stage4.py')
    archive=revised/'run-records.zip'
    with zipfile.ZipFile(original/'run-records.zip') as oldzip, zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for item in oldzip.infolist():
            if item.filename.startswith('raw/') or item.filename=='README.md':
                z.writestr(item.filename,oldzip.read(item.filename))
        for p in revised.iterdir():
            if p.is_file() and p!=archive: z.write(p,'report/'+p.name)
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    write(revised/'ARCHIVE_CHECK.json',dict(sha256=sha(archive),bytes=archive.stat().st_size,crc='PASS'))
    print(json.dumps(dict(output=str(revised),scientific_files_unchanged=True,archive='PASS',
        timer_minutes=timer/60,utc_minutes=interval/60)),flush=True)


if __name__=='__main__': main()
