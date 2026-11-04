"""Frozen per-width learning-rate selection from Run A (stdlib; validation NLL only; never p*).

  python -I -B select_lr.py <RUN_A_DIR> <NEW_OUT_DIR>      -> LR_SELECTION.json

Rule (pre-registered): for each width and each rate in the grid {3e-5, 1e-4, 3e-4}, take the lowest mean validation
NLL over the fixed readout epochs (E1..E32; E0 is excluded because it does not depend on the rate). The selected rate
has the lowest such value; ties go to the smaller rate. A rate at a grid edge is accepted and flagged; the grid is
never extended. The training-set arrays are not read, so no p* can enter the selection.

It also freezes the Run B plan from Run A's outcome-blind timing forecast only (owner rule of 28 Oct 2026):
B (one run of ten draws) if that forecast is feasible within 6 h; otherwise B1+B2 (two sequential runs of five draws,
identical science) if a five-draw run is feasible; otherwise UNAVAILABLE. No draw, epoch or width is ever cut.
Under plan B, Run B can still fall back to B1+B2 at its own start-up check, before any training (text_worker).
"""
import hashlib, json, math, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_worker


def sha(b): return hashlib.sha256(b).hexdigest()


def select(run_a):
    run_a = Path(run_a)
    term_raw = (run_a / 'TERMINAL.json').read_bytes(); term = json.loads(term_raw)
    if term.get('status') != 'COMPLETE' or term.get('mode') != 'A': raise SystemExit('Run A is not COMPLETE')
    receipt = json.loads((run_a / f'{plan.TUNING}-RECEIPT.json').read_bytes())
    if receipt.get('status') != 'COMPLETE': raise SystemExit('Tuning stage is not COMPLETE')
    table, chosen = {}, {}
    for w in plan.WIDTHS:
        rows = []
        for lr in plan.LR_GRID:
            base = run_a / plan.TUNING / f'w{w}' / text_worker.LR_TAGS[lr]
            rec = json.loads((base / 'record.json').read_bytes()); raw = (base / 'arrays.f32').read_bytes()
            if len(raw) != rec['arrays']['bytes'] or sha(raw) != rec['arrays']['sha256']: raise SystemExit('Array binding differs: ' + rec['arrays']['path'])
            if rec.get('lr') != lr or rec.get('width') != w or rec['layout']['block_epochs'] != list(plan.READOUTS): raise SystemExit(f'Record does not match width {w} and rate {lr}')
            n_tr, n_va = rec['layout']['train_rows'], rec['layout']['validation_rows']; per = n_tr + n_va
            values = {}
            for k, epoch in enumerate(rec['layout']['block_epochs']):
                a = array('f'); a.frombytes(raw[4 * (k * per + n_tr):4 * (k + 1) * per])     # validation rows only
                values[epoch] = math.fsum(a) / n_va
            best_epoch = min(values, key=lambda e: (values[e], e))
            rows.append(dict(lr=lr, min_validation_nll=values[best_epoch], at_epoch=best_epoch, validation_nll_by_epoch={str(e): v for e, v in values.items()}))
        best = min(rows, key=lambda r: (r['min_validation_nll'], r['lr']))
        chosen[str(w)] = best['lr']; table[str(w)] = dict(rows=rows, selected=best['lr'], at_grid_edge=best['lr'] in (plan.LR_GRID[0], plan.LR_GRID[-1]))
    bench_raw = (run_a / 'BENCHMARK.json').read_bytes(); bound = term.get('benchmark') or {}
    if len(bench_raw) != bound.get('bytes') or sha(bench_raw) != bound.get('sha256'): raise SystemExit('BENCHMARK.json differs from its binding in Run A terminal')
    bench = json.loads(bench_raw); fc = bench['run_b_forecast']
    for m in ('B', 'B1'):          # the plan re-derives from the bound benchmark, as check_fallback does (revision 04)
        if text_worker.stage_cap(bench['benchmark'], m, bench['partition_n'], bench['pool_n'])['feasible'] != fc[m]['feasible']: raise SystemExit('Run B forecast does not re-derive from the bound benchmark')
    plan_b = 'B' if fc['B']['feasible'] else 'B1+B2' if fc['B1']['feasible'] else 'UNAVAILABLE'
    run_b_plan = dict(plan=plan_b, rule='B if a ten-draw run is feasible in 6 h by the frozen cap formula on Run A\'s benchmark; else B1+B2 (d01-d05, d06-d10) if a five-draw run is; else UNAVAILABLE',
                      forecast={m: {k: fc[m][k] for k in ('projected_stage_seconds', 'stage_work_cap_seconds', 'feasible', 'formula')} for m in ('B', 'B1')})
    return dict(status='SELECTED', rule='per width, lowest validation NLL over readouts E1..E32; ties to the smaller rate; edges accepted and flagged; no grid extension; p* never used',
                run_a_terminal_sha256=sha(term_raw), run_a_subject=term.get('subject'), learning_rates=chosen, table=table,
                edge_flags=[w for w, v in table.items() if v['at_grid_edge']], run_b_plan=run_b_plan)


if __name__ == '__main__':
    run_a, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=False, exist_ok=False)
    value = select(run_a)
    (out / 'LR_SELECTION.json').write_bytes((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps(dict(learning_rates=value['learning_rates'], edge_flags=value['edge_flags'], run_b_plan=value['run_b_plan']['plan']), indent=1))
