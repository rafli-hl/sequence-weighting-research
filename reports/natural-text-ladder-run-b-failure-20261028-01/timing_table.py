"""Per-trajectory wall durations of Run A (t00) and Run B (d01, d02) from Windows file modification times, plus the
operational fields of Run B's TERMINAL.json, BENCHMARK.json, d01 receipt and owner exit receipt. Outcome-blind: it reads
no arrays.f32 or record.json content (only their mtimes) and computes no loss or p*. Writes TIMING.json next to this script.

  python -I -B timing_table.py
"""
import datetime, hashlib, json, sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
RUN_A, RUN_B = ROOT / 'work/runs/natural-text-ladder-a-20261028-01', ROOT / 'work/runs/natural-text-ladder-b-20261028-01'
ACT_B = ROOT / 'work/natural-text-ladder-activation-b-20261028-01'
WIDTHS = (64, 96, 128, 192, 256, 384)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
mt = lambda p: p.stat().st_mtime
iso = lambda t: datetime.datetime.fromtimestamp(t).isoformat(timespec='seconds')


def stage_rows(stage_dir, start, adapt_dirs):
    """E0 write interval per width (pretraining), then adaptation interval per trajectory (record.json mtime to the previous)."""
    rows, prev = [], start
    for w in WIDTHS:
        p = stage_dir / f'w{w}' / 'E0.pt'
        if p.exists(): rows.append(dict(kind='pretrain', width=w, end=iso(mt(p)), seconds=round(mt(p) - prev, 1))); prev = mt(p)
    for w in WIDTHS:
        for tag in adapt_dirs:
            p = stage_dir / f'w{w}' / tag / 'record.json'
            if p.exists(): rows.append(dict(kind='adapt', width=w, tag=tag, end=iso(mt(p)), seconds=round(mt(p) - prev, 1))); prev = mt(p)
    return rows, prev


out = dict(source='Windows file mtimes (one-second-or-better resolution); seconds are wall intervals between consecutive writes', files={})
a_rows, _ = stage_rows(RUN_A / 't00', mt(RUN_A / 't00' / 'INPUTS.json'), ('lr3e-05', 'lr1e-04', 'lr3e-04'))
out['run_a_t00'] = a_rows
b_term = json.loads((RUN_B / 'TERMINAL.json').read_bytes()); out['files']['run_b_TERMINAL.json'] = sha(RUN_B / 'TERMINAL.json')
d01_rows, d01_end = stage_rows(RUN_B / 'd01', mt(RUN_B / 'd01' / 'INPUTS.json'), ('selected',))
d02_rows, d02_last = stage_rows(RUN_B / 'd02', mt(RUN_B / 'd02' / 'INPUTS.json'), ('selected',))
out['run_b_d01'], out['run_b_d02'] = d01_rows, d02_rows
out['run_b_d02_in_progress'] = dict(width=384, started_after=iso(d02_last), terminal_written=iso(mt(RUN_B / 'TERMINAL.json')),
                                    seconds_without_finishing=round(mt(RUN_B / 'TERMINAL.json') - d02_last, 1))
bench = json.loads((RUN_B / 'BENCHMARK.json').read_bytes()); out['files']['run_b_BENCHMARK.json'] = sha(RUN_B / 'BENCHMARK.json')
rcpt = json.loads((ACT_B / 'OWNER_EXIT_RECEIPT.json').read_bytes()); out['files']['OWNER_EXIT_RECEIPT.json'] = sha(ACT_B / 'OWNER_EXIT_RECEIPT.json')
out['run_b_operational'] = dict(status=b_term['status'], error=b_term.get('error'), active_stage=b_term.get('active_stage'), elapsed_seconds=b_term['elapsed_seconds'],
                                completed_stages=[dict(stage=s['stage'], status=s['status'], seconds=s['seconds']) for s in b_term['stages']],
                                benchmark_projected_stage_seconds=bench['caps']['projected_stage_seconds'], stage_work_cap_seconds=bench['caps']['stage_work_cap_seconds'],
                                cap_formula=bench['caps']['formula'], peaks=b_term['peaks'], inventory=b_term['inventory'],
                                owner_receipt=dict(status=rcpt['status'], exit_code=rcpt['exit_code'], elapsed_seconds=rcpt['elapsed_seconds'], terminal_sha256=rcpt['terminal_sha256']))
adapt = lambda rows: {r['width']: r['seconds'] for r in rows if r['kind'] == 'adapt'}
a_mean = {w: round(sum(r['seconds'] for r in a_rows if r['kind'] == 'adapt' and r['width'] == w) / 3, 1) for w in WIDTHS}
out['adapt_seconds_by_width'] = {str(w): dict(run_a_mean_of_3=a_mean[w], run_b_d01=adapt(d01_rows).get(w), run_b_d02=adapt(d02_rows).get(w),
                                              d02_over_d01=round(adapt(d02_rows)[w] / adapt(d01_rows)[w], 2) if w in adapt(d02_rows) else None) for w in WIDTHS}
(HERE / 'TIMING.json').write_text(json.dumps(out, indent=2, allow_nan=False) + '\n', encoding='utf-8')
print(json.dumps(dict(adapt_seconds_by_width=out['adapt_seconds_by_width'], d02_in_progress=out['run_b_d02_in_progress'],
                      pretrain=dict(d01=[r['seconds'] for r in d01_rows if r['kind'] == 'pretrain'], d02=[r['seconds'] for r in d02_rows if r['kind'] == 'pretrain'],
                                    run_a=[r['seconds'] for r in a_rows if r['kind'] == 'pretrain'])), indent=1))
