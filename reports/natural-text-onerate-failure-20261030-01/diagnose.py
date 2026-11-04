"""Outcome-blind diagnosis of the FAILED one-rate run (owner instruction of 30 Oct 2026). Native Python 3.12, -I -B.
Writes DIAGNOSIS.json next to itself. Read-only on the activation and run folders.

It reads only operational records (owner list):
- TERMINAL.json: status, error, active stage, elapsed time, ladder, peaks, the stage receipts it holds, and the states
  deleted on failure;
- the per-draw receipts (status, timing, guard and memory fields) and STATES_DELETED.json (paths, sizes, hashes);
- BENCHMARK.json: per-width timing and memory, the ladder decision, the cap, and the benchmark states deleted;
- the GPU check files (pre-start, requests and verdicts), OWNER_PROGRESS.log and the owner receipt;
- WINDOWS_POWER_EVENTS.json (this folder);
- file modification times (not contents) of the run's per-draw files, for the timeline.
It never opens a record.json, PRETRAINED.json, INPUTS.json, an arrays file or the worker logs, and computes no p*, gain or loss.
"""
import datetime as dt, hashlib, json, os, sys
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
ACT = ROOT / 'work/natural-text-onerate-activation-20261030-01'; RUN = ROOT / 'work/runs/natural-text-onerate-20261030-01'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
jl = lambda p: json.loads(Path(p).read_bytes().decode('utf-8-sig'))
mt = lambda p: os.stat(p).st_mtime if Path(p).exists() else None
hm = lambda t: dt.datetime.fromtimestamp(t).strftime('%H:%M:%S') if t else None
DRAWS = [f'd{i:02d}' for i in range(1, 11)]

term = jl(RUN / 'TERMINAL.json'); bench = jl(RUN / 'BENCHMARK.json'); receipt = jl(ACT / 'OWNER_EXIT_RECEIPT.json')
out = dict(note='Operational records and file times only; no p*, gain or loss was opened or computed.',
           terminal=dict(sha256=sha(RUN / 'TERMINAL.json'), **{k: term.get(k) for k in ('status', 'error', 'active_stage', 'elapsed_seconds', 'ladder', 'peaks', 'inventory', 'run_b_verified')}),
           receipt={k: receipt.get(k) for k in ('status', 'exit_observed', 'exit_code', 'elapsed_seconds', 'terminal_sha256', 'ladder_top', 'ladder_reason', 'stop_reason', 'gpu_prestart', 'gpu_gates')})
out['receipt_binds_terminal'] = receipt['terminal_sha256'] == out['terminal']['sha256']
caps = bench['caps']
out['benchmark'] = dict(projected_stage_seconds=caps['projected_stage_seconds'], stage_work_cap_seconds=caps['stage_work_cap_seconds'], ladder=bench['ladder'], failure=bench['failure'],
                        per_width={w: dict(peak_sampled=v['peaks']['device_used_sampled'], seconds_per_update=v['seconds_per_update'], seconds_per_pretraining_update=v['seconds_per_pretraining_update'],
                                           seconds_per_eval_batch=v['seconds_per_eval_batch']) for w, v in sorted(bench['benchmark']['architectures'].items(), key=lambda kv: int(kv[0]))},
                        states_deleted=len(bench['states']['deleted']), states_deleted_bytes=bench['states']['deleted_bytes'], state_errors=bench['states']['errors'], ledger_released=bench['states']['ledger_released'])

# Per-draw timeline from receipts and file times (modification times only).
rows = {}
for d in DRAWS:
    if not (RUN / d).exists(): continue
    t = dict(gate=mt(RUN / 'gpu-checks' / f'{d}.json'), inputs=mt(RUN / d / 'INPUTS.json'), e0_768=mt(RUN / d / 'w768' / 'E0.f32'), e0_512=mt(RUN / d / 'w512' / 'E0.f32'), pretrained=mt(RUN / d / 'PRETRAINED.json'),
             **{f'adapt_{w}_done': mt(RUN / d / f'w{w}' / 'onerate' / 'arrays.f32') for w in (768, 512, 96, 64)}, receipt=mt(RUN / f'{d}-RECEIPT.json'))
    seg = lambda a, b: round(t[b] - t[a], 1) if t[a] and t[b] else None
    r = jl(RUN / f'{d}-RECEIPT.json') if (RUN / f'{d}-RECEIPT.json').exists() else None
    sd = jl(RUN / d / 'STATES_DELETED.json') if (RUN / d / 'STATES_DELETED.json').exists() else None
    rows[d] = dict(times_local={k: hm(v) for k, v in t.items()},
                   phases_seconds=dict(pretrain_768=seg('inputs', 'e0_768'), pretrain_512=seg('e0_768', 'e0_512'), adapt_768=seg('pretrained', 'adapt_768_done'), adapt_512=seg('adapt_768_done', 'adapt_512_done'),
                                       adapt_96=seg('adapt_512_done', 'adapt_96_done'), adapt_64=seg('adapt_96_done', 'adapt_64_done')),
                   receipt=None if r is None else dict(status=r['status'], seconds=r['seconds'], peaks=r['peaks'], states_deleted=r['states_deleted'], state_deletion_errors=r['state_deletion_errors']),
                   states_deleted=None if sd is None else dict(files=len(sd['deleted']), bytes=sd['deleted_bytes'], errors=sd['errors']))
out['draws'] = rows
done = [rows[d]['phases_seconds']['adapt_768'] for d in DRAWS[:5]]
out['adapt_768_d01_d05'] = dict(min=min(done), max=max(done), mean=round(sum(done) / len(done), 1))
out['adapt_768_d06_over_mean_d01_d05'] = round(rows['d06']['phases_seconds']['adapt_768'] / out['adapt_768_d01_d05']['mean'], 2)
d06_start = rows['d06']['times_local']['gate']
out['d06'] = dict(work_cap_reached_local=hm(mt(RUN / 'gpu-checks' / 'd06.json') + caps['stage_work_cap_seconds']), states_on_failure=term.get('states_on_failure'),
                  failed_in='the 512 adaptation (768 adapted and recorded at 15:19:14; no 512 arrays)', started_local=d06_start)
out['measured_over_projected_d01_d05'] = [round(rows[d]['receipt']['seconds'] / caps['projected_stage_seconds'], 3) for d in DRAWS[:5]]

# GPU checks (Windows nvidia-smi), from the owner's verdict files.
gates = {}
for p in [ACT / 'gpu-checks' / 'PRESTART.json'] + sorted((ACT / 'gpu-checks').glob('d*-RESPONSE.json')):
    g = jl(p)
    gates[p.name] = [dict(started_utc=c['started_utc'], verdict=c['verdict'], mean_utilization_percent=c['mean_utilization_percent'], utilization=[s['utilization_percent'] for s in c['samples']],
                          memory_used_mib=[s['memory_used_mib'] for s in c['samples']], failed_samples=c['failed_samples']) for c in g['checks']]
out['gpu_checks'] = gates
out['owner_progress_log'] = (ACT / 'OWNER_PROGRESS.log').read_text(encoding='utf-8').splitlines()
# Windows power events (saved in this folder).
ev = jl(HERE / 'WINDOWS_POWER_EVENTS.json')['events']
pick = lambda e: dict(time_local=e['time_local'], provider=e['provider'].replace('Microsoft-Windows-', ''), id=e['id'], message=e['message'],
                      data={k: e['data'][k] for k in ('AcOnline', 'RemainingCapacity', 'FullChargeCapacity', 'LidOpenState', 'BatteryRemainingCapacityOnEnter', 'BatteryRemainingCapacityOnExit', 'PowerStateAc', 'DurationInUs', 'ShutdownActionType', 'ShutdownReason') if k in (e.get('data') or {})})
out['windows_power_events'] = [pick(e) for e in ev if e['id'] in (105, 506, 507, 109, 577) or 'WindowsUpdate' in e['provider'] or 'UserModePower' in e['provider']]
out['model_states'] = dict(benchmark=len(bench['states']['deleted']), draws_d01_d05=sum(rows[d]['states_deleted']['files'] for d in DRAWS[:5]), d06_on_failure=len(term['states_on_failure']['d06']['deleted']),
                           total_files=len(bench['states']['deleted']) + sum(rows[d]['states_deleted']['files'] for d in DRAWS[:5]) + len(term['states_on_failure']['d06']['deleted']),
                           total_bytes=bench['states']['deleted_bytes'] + sum(rows[d]['states_deleted']['bytes'] for d in DRAWS[:5]) + term['states_on_failure']['d06']['deleted_bytes'],
                           errors=bench['states']['errors'] + [e for d in DRAWS[:5] for e in rows[d]['states_deleted']['errors']] + term['states_on_failure']['d06']['errors'],
                           left_in_run_folder=sorted(p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file() and (p.name.endswith('.pt') or p.name.endswith('.pt.part'))))
out['diagnose_py_sha256'] = sha(Path(__file__))
(HERE / 'DIAGNOSIS.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ('receipt_binds_terminal', 'adapt_768_d01_d05', 'adapt_768_d06_over_mean_d01_d05', 'd06', 'measured_over_projected_d01_d05', 'model_states')}, indent=1, default=str))
