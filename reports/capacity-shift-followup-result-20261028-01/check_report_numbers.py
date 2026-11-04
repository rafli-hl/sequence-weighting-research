"""Check the numbers quoted in REPORT.md against RESULT_SUMMARY.json and VERIFICATION.json (read-only; stdlib).

  python -I -B check_report_numbers.py      -> REPORT_CHECKS.json
"""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
S = json.loads((HERE / 'RESULT_SUMMARY.json').read_bytes()); V = json.loads((HERE / 'VERIFICATION.json').read_bytes())
text = (HERE / 'REPORT.md').read_text(encoding='utf-8')
vr = {r['check'][:40]: r for r in V['results']}
def vget(prefix, key):
    return next(r for k, r in vr.items() if k.startswith(prefix))[key]
out = []
def f(x, d=3):
    s = f'{x:+.{d}f}' if x >= 0 else f'{x:.{d}f}'
    return s.replace('-', '−')
def need(label, value, quoted):
    out.append(dict(check=label, value=value, quoted=quoted, ok=quoted in text))

T = S['slope_tests']; R = T['primary|R']; SB = T['primary|S_batch']; W = T['E15-E30|R']; WS = T['E15-E30|S_batch']
need('decision', S['decision']['label'], '**MOVES_SMALLER** (G16, full weighting R; not censored)')
for name, t in (('primary R', R['slope']), ('S32', R['sensitivities']['S32']['slope']), ('SD', R['sensitivities']['SD']['slope'])):
    need(f'{name} mean', t['mean'], f(t['mean']).lstrip('+')); need(f'{name} interval', [t['low'], t['high']], f"[{f(t['low'])}, {f(t['high'])}]")
    need(f'{name} sd', t['sd'], f"{t['sd']:.3f}")
need('primary negative 12/12', R['slope']['negative'], '12/12')
need('SD corpora', R['sensitivities']['SD']['slope']['n'], '(df 7) | 8')
need('defined points', R['counts']['defined_points'], '59 of 60 corpus-epoch points are defined')
need('undefined point c01 E15 256/4', R['undefined_points'], 'c01 at E15, where the 256/4 fit')
need('flagged 19', R['counts']['flagged_points'], '19 of 60 points were flagged (31.7%')
need('unresolved 2', R['sensitivities']['S32']['unresolved_points'], '2 of the 19 bound-32 refits were unresolved')
need('refit mean change', R['refit_location_change']['mean'], f"{f(R['refit_location_change']['mean'])} on average (largest |change| {R['refit_location_change']['max_abs']:.3f})")
need('SD dropped', R['sensitivities']['SD']['corpora_dropped'], 'SD dropped ' + ', '.join(R['sensitivities']['SD']['corpora_dropped'][:-1]) + ' and ' + R['sensitivities']['SD']['corpora_dropped'][-1])
need('flagged by epoch', R['counts']['flagged_by_epoch'], '| ' + ' | '.join(str(v) for v in R['counts']['flagged_by_epoch'].values()) + ' | 19 / 60 |')
need('upper by epoch', R['counts']['fits_at_upper_by_epoch'], '| ' + ' | '.join(str(v) for v in R['counts']['fits_at_upper_by_epoch'].values()) + ' | ' + str(sum(R['counts']['fits_at_upper_by_epoch'].values())) + ' |')
for label, t in (('S_batch slope', SB['slope']), ('E15-E30 R', W['slope']), ('E15-E30 S', WS['slope'])):
    need(label, [t['mean'], t['sd'], t['low'], t['high']], f"{f(t['mean'])} | {t['sd']:.3f} | [{f(t['low'])}, {f(t['high'])}]")
d = S['slope_difference_R_minus_S_batch']
for k in ('primary', 'E15_E30'):
    need(f'difference {k}', [d[k]['label'], d[k]['mean'], d[k]['low'], d[k]['high']], f"{f(d[k]['mean'])} | — | [{f(d[k]['low'])}, {f(d[k]['high'])}]")
need('E15-E30 R sensitivities', [W['sensitivities']['S32']['slope']['mean'], W['sensitivities']['SD']['slope']['mean'], W['sensitivities']['SD']['slope']['n']],
     f"S32 {f(W['sensitivities']['S32']['slope']['mean'])}; SD on {W['sensitivities']['SD']['slope']['n']} corpora {f(W['sensitivities']['SD']['slope']['mean'])}")
for arm in ('R', 'S_batch'):
    t = S['two_point_E20_E30'][arm]
    need(f'two-point {arm}', [t['mean'], t['sd'], t['low'], t['high'], t['negative']], f"{f(t['mean'])} | {t['sd']:.3f} | [{f(t['low'])}, {f(t['high'])}] | {t['negative']}/12")
for arm in ('R', 'S_batch'):
    for e in ('E5', 'E10', 'E15', 'E20', 'E25', 'E30', 'E40'):
        c = S['epoch_curves'][f'{arm}|{e}']
        if 'argmax_width' in c: need(f'curve {arm} {e}', [c['label'], c['argmax_width'], c['location_width']], f"{c['label']} | {c['argmax_width']} ({c['location_width']:.0f})")
        else: need(f'curve {arm} {e}', [c['label'], c['undefined_fits']], f"UNDEFINED | — | {c['undefined_fits']}")
for k in ('R|32/4|E15', 'R|32/4|E40', 'R|128/4|E15', 'R|128/4|E40', 'R|384/4|E15', 'R|384/4|E40'):
    v = S['losses'][k]; need(f'losses {k}', v, f"{v['train']:.3f} | {v['validation']:.3f} | {v['gap']:.3f} | {v['validation_instance']:.3f} |")
v = S['losses']['R-S_batch|128/4|E40|validation']; need('R-S validation 128/4 E40', v, f"{f(v['mean'])} [{f(v['low'])}, {f(v['high'])}]")
v = S['losses']['R-S_batch|384/4|E40|validation']; need('R-S validation 384/4 E40', v, f"{f(v['mean'])} [{f(v['low'])}, {f(v['high'])}]")
v = S['losses']['R-S_batch|384/4|E15|validation']; need('R-S validation 384/4 E15', v['mean'], f"{f(v['mean'])} at E15")
cf = [x['clip_fraction_mean'] for x in S['clipping'].values()]; need('clip fraction range', [min(cf), max(cf)], f'{min(cf):.2f}–{max(cf):.2f}')
gn = [x['gradient_norm_mean'] for k, x in S['clipping'].items() if 'E31-E40' in k]; need('gradient norm range E31-E40', [min(gn), max(gn)], f'{min(gn):.1f}–{max(gn):.1f}')
lc = S['landmark_crossings']
need('P50 crossings', [lc['R|384/4|P50'], lc['R|256/4|P50']['crossed'], lc['S_batch|256/4|P50']['crossed']],
     f"at 256/4 in {lc['R|256/4|P50']['crossed']}/12 (R) and {lc['S_batch|256/4|P50']['crossed']}/12 (S_batch)")
need('P90 never', all(v['crossed'] == 0 for k, v in lc.items() if k.endswith('P90')), 'P = 0.90 was never crossed')
need('P10 never at 32/4', [lc['R|32/4|P10']['crossed'], lc['S_batch|32/4|P10']['crossed']], 'never at 32/4')
sel = S['validation_selected_epochs']; need('selected E0/E40', [sel['R|E0'], sel['S_batch|E0'], sel['R|E40'], sel['S_batch|E40']],
     f"E0 for {sel['R|E0']}/96 R and {sel['S_batch|E0']}/96 S_batch trajectories, and at E40 for {sel['R|E40']} and {sel['S_batch|E40']}")
ex = S['exposed_ladder_sizing_for_comparison']['values']['R']['slope_E15_E30_per_epoch_doubling']['mean']; need('exposed ladder slope', ex, f'{f(ex)} on 5 corpora')
need('verification 23/23', [V['status'], V['checks']], '23/23 PASS')
need('owner elapsed', vget('owner claim', 'owner_elapsed'), f"{vget('owner claim', 'owner_elapsed'):,.1f} s")
need('worker elapsed', vget('owner claim', 'worker_elapsed'), f"Worker {vget('owner claim', 'worker_elapsed'):,.1f} s")
need('stage seconds range', vget('twelve stages', 'stage_seconds'), f"stages took {min(vget('twelve stages', 'stage_seconds')):.0f}–{max(vget('twelve stages', 'stage_seconds')):.0f} s")
need('cap', [vget('benchmark cap', 'cap'), vget('benchmark cap', 'projected')], f"Benchmark projection {vget('benchmark cap', 'projected'):.1f} s per stage, cap {vget('benchmark cap', 'cap')} s")
inv = vget('storage within', 'inventory'); need('inventory', inv, f"{inv['bytes']:,} bytes in {inv['files']} files")
pk = vget('sampled peaks', 'peaks'); need('peaks', pk, f"Sampled GPU {pk['device_used_sampled'] / 1e9:.2f} GB and worker RSS {pk['worker_peak_rss'] / 1e9:.2f} GB")
c = vget('counts: 147,456', 'counts'); need('eval batches', c['eval_batches'], f"{c['eval_batches']:,} evaluation batches")
need('landmark validations', vget('counts: 147,456', 'landmark_validations'), f"({vget('counts: 147,456', 'landmark_validations')} landmark validations)")
need('vanished bytes', vget('reconciliation', 'vanished_bytes'), f"one file of {vget('reconciliation', 'vanished_bytes'):,} bytes")
reg = vget('registry re-derives', 'exclusion_values'); need('exclusion values', reg, f'against {reg:,} exclusion values')
value = dict(status='PASS' if all(x['ok'] for x in out) else 'FAIL', checks=len(out), failed=[x['check'] for x in out if not x['ok']], results=out)
(HERE / 'REPORT_CHECKS.json').write_text(json.dumps(value, indent=2, default=str, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps(dict(status=value['status'], checks=len(out), failed=[(x['check'], x['quoted']) for x in out if not x['ok']]), indent=1, ensure_ascii=False))
