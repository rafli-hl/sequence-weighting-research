"""Planning estimate for the conditional 3e-5 sensitivity (Amendment 01, item 2), from Run A's bound benchmark and the frozen
stage_cap formula of the sealed source. Imports the sealed source read-only, patches plan.WIDTHS in memory only, and writes
SENSITIVITY_ESTIMATE.json next to this script. Planning arithmetic, not a guarantee: the sensitivity's own benchmark sets its cap.

  python -I -B sensitivity_estimate.py
"""
import hashlib, json, sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
SRC = ROOT / 'work/natural-text-ladder-source-20261028-01'; RUN_A = ROOT / 'work/runs/natural-text-ladder-a-20261028-01'
sha = lambda b: hashlib.sha256(b).hexdigest()
sys.path.insert(0, str(SRC)); import text_worker as w, text_plan as plan
term_raw = (RUN_A / 'TERMINAL.json').read_bytes(); term = json.loads(term_raw)
bench_raw = (RUN_A / 'BENCHMARK.json').read_bytes()
if sha(bench_raw) != term['benchmark']['sha256']: raise SystemExit('BENCHMARK.json differs from its binding in Run A terminal')
bench = json.loads(bench_raw); arch = bench['benchmark']['architectures']; L = plan.LIMITS
out = dict(status='PLANNING_ARITHMETIC_NOT_A_GUARANTEE', run_a_terminal_sha256=sha(term_raw), benchmark_sha256=sha(bench_raw),
           source_files={f: sha((SRC / f).read_bytes()) for f in ('text_worker.py', 'text_plan.py')},
           storage_rule='per stage: INPUTS and PRETRAINED as measured in Run A, one E0 state per width at its benchmark state size, E0 and readout arrays, one record at its cap; plus three benchmark states per width as in Run A')
full_widths = plan.WIDTHS
for name, widths in (('all_six_widths', full_widths), ('widths_64_96_only', (64, 96))):
    plan.WIDTHS = widths
    sc = w.stage_cap(bench['benchmark'], 'B', bench['partition_n'], bench['pool_n'])
    n, cap, c = sc['stages'], sc['stage_work_cap_seconds'], sc['counts']
    states = sum(arch[str(x)]['state_bytes'] for x in widths)
    stage_bytes = 38846 + 33928 + states + len(widths) * (c['e0_bytes'] + c['array_bytes'] + plan.RECORD_BYTES)
    out[name] = dict(widths=list(widths), stages=n, projected_stage_seconds=sc['projected_stage_seconds'], stage_cap_seconds=cap, feasible=sc['feasible'],
                     formula=sc['formula'], projected_run_hours=n * sc['projected_stage_seconds'] / 3600,
                     worst_case_wall_hours=(n * (cap + L['stage_slack_seconds']) + L['benchmark_seconds']) / 3600,
                     storage_GiB=(n * stage_bytes + 3 * states) / 2 ** 30)
plan.WIDTHS = full_widths
sa = w.stage_cap(bench['benchmark'], 'A', bench['partition_n'], bench['pool_n'])      # calibration: the same formula on Run A itself
out['run_a_measured'] = dict(elapsed_hours=term['elapsed_seconds'] / 3600, inventory_GiB=term['inventory']['bytes'] / 2 ** 30,
                             projected_hours_from_own_benchmark=sa['stages'] * sa['projected_stage_seconds'] / 3600)
(HERE / 'SENSITIVITY_ESTIMATE.json').write_text(json.dumps(out, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ('all_six_widths', 'widths_64_96_only', 'run_a_measured')}, indent=1))
