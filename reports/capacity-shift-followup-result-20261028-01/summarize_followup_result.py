"""Extract the report tables from the frozen follow-up analysis (read-only; stdlib).

  python -I -B summarize_followup_result.py

Reads reports/capacity-shift-followup-analysis-20261027-01/ANALYSIS.json (reproduced byte for byte by the sealed
re-run, VERIFICATION.json) and the ladder's exposed sizing file. Writes RESULT_SUMMARY.json next to this script.
Every number in REPORT.md comes from this file. Nothing is refitted; no new estimator is applied.
"""
import hashlib, json, math, sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
ANA = ROOT / 'reports/capacity-shift-followup-analysis-20261027-01/ANALYSIS.json'
SIZING = ROOT / 'reports/capacity-ladder-result-20261027-01/FOLLOWUP_SIZING.json'
raw = ANA.read_bytes(); a = json.loads(raw)
WIDTHS = [32, 48, 64, 96, 128, 192, 256, 384]

def iv(t): return dict(n=t['n'], df=t['df'], mean=t['mean'], sd=t['sd'], low=t['interval'][0], high=t['interval'][1], negative=t['negative'], positive=t['positive'])

def test(t):
    out = dict(label=t['label'], primary_label=t.get('primary_label'), censored=t.get('censored'), slope=iv(t['primary']) if t.get('primary') else None,
               counts={k: t['counts'][k] for k in ('nominal_points', 'defined_points', 'undefined_points', 'flagged_points', 'flagged_by_epoch', 'fits_at_upper_by_epoch', 'boundary_points')},
               corpus_slopes=t.get('slopes'))
    undefined = [dict(corpus=c['corpus'], epoch=p['epoch'], widths=[w for w, v in zip(WIDTHS, p['p']) if v is None], reasons=sorted({r for r in p['reasons'] if r}))
                 for c in t['per_corpus'] for p in c['points'] if not p['defined']]
    out['undefined_points'] = undefined
    sens = {}
    for k, s in t['sensitivities'].items():
        d = {x: s.get(x) for x in ('required', 'reason', 'required_because', 'computable', 'label', 'refitted_points', 'unresolved_points', 'refitted_fits_at_32',
                                    'refitted_points_with_a_fit_at_32', 'boundary_points_after_refit', 'corpora_dropped', 'corpora_kept') if x in s}
        if 'interval' in s: d['slope'] = iv(s['interval'])
        sens[k] = d
    out['sensitivities'] = sens
    refits = [dict(corpus=c['corpus'], epoch=p['epoch'], location_bound8=p['location'], location_bound32=p['s32']['location'], max_fit_bound32=max(p['s32']['p']), unresolved=p['s32']['unresolved'])
              for c in t['per_corpus'] for p in c['points'] if 's32' in p]
    out['refits'] = refits
    if refits: out['refit_location_change'] = dict(mean=sum(r['location_bound32'] - r['location_bound8'] for r in refits) / len(refits),
                                                   max_abs=max(abs(r['location_bound32'] - r['location_bound8']) for r in refits))
    return out

tests = {k: test(v) for k, v in a['slope_tests'].items()}
curves = {}
for arm, ec in a['epoch_curves'].items():
    for e, v in ec.items():
        row = dict(label=v['label'], undefined_fits=v['counts']['undefined_fits'], fits_at_upper_by_rung=v['counts']['at_upper_by_rung'],
                   fits_at_upper=sum(v['counts']['at_upper_by_rung']), flagged_points=v['counts']['flagged_points'])
        if 'curve' in v:
            row.update(argmax_width=v['argmax_width'], location_log2=v['location_log2'], location_width=2 ** v['location_log2'], kind=v['kind'], curve=v['curve'],
                       rise=iv(v['rise']), fall=iv(v['fall']), end=iv(v['end']), upper_at_argmax=v['upper_at_argmax'])
        curves[f'{arm}|{e}'] = row
diff = {k: dict(label=v['label'], **(iv(v['interval']) if 'interval' in v else {})) for k, v in a['slope_difference_R_minus_S_batch'].items()}
two = {k: dict(label=v['label'], flagged_points=v.get('flagged_points'), **(iv(v['interval']) if 'interval' in v else {})) for k, v in a['two_point_E20_E30'].items()}
losses = {}
for arm in ('R', 'S_batch'):
    for w in (32, 96, 128, 384):
        for e in (15, 30, 40):
            losses[f'{arm}|{w}/4|E{e}'] = a['losses'][f'{arm}|{w}/4|E{e}']
for w in (32, 96, 128, 384):
    for e in (15, 30, 40):
        v = a['losses'][f'R-S_batch|{w}/4|E{e}|validation']; losses[f'R-S_batch|{w}/4|E{e}|validation'] = iv(v)
clip = {k: v for k, v in a['clipping_summary'].items() if any(f'|{w}/4|' in k for w in (32, 128, 384))}
selected = Counter((r['arm'], r['selected_epoch']) for r in a['validation_selected_view'])
crossings = a['landmark_crossings']   # every arm, rung and landmark
sizing = json.loads(SIZING.read_bytes())
value = dict(note='Extracted from the frozen ANALYSIS.json; descriptive sections are marked in REPORT.md. Location units: log2 width; slope units: log2 width per doubling of epochs.',
             analysis_sha256=hashlib.sha256(raw).hexdigest(), status=a['status'], decision=a['decision'], slope_tests=tests, slope_difference_R_minus_S_batch=diff,
             two_point_E20_E30=two, epoch_curves=curves, losses=losses, clipping=clip, landmark_crossings=crossings,
             validation_selected_epochs={f'{arm}|E{e}': n for (arm, e), n in sorted(selected.items())},
             exposed_ladder_sizing_for_comparison=dict(source=str(SIZING.relative_to(ROOT)), note='Five exposed ladder corpora; motivation only, not a test.',
                                                      values={arm: {k: {x: sizing['summary'][arm][k][x] for x in ('n', 'mean', 'sd', 't4', 'negative')} for k in ('slope_E15_E30_per_epoch_doubling', 'delta_E20_E30')} for arm in ('R', 'S_batch')}))
(HERE / 'RESULT_SUMMARY.json').write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
r = tests['primary|R']
print(json.dumps(dict(decision=a['decision']['label'], R=r['slope'], undefined=r['undefined_points'], refit_change=r.get('refit_location_change'),
                      refits=[(x['corpus'], x['epoch'], round(x['location_bound8'], 3), round(x['location_bound32'], 3), round(x['max_fit_bound32'], 3)) for x in r['refits']],
                      selected=value['validation_selected_epochs'], sizing_keys=list(sizing)[:30]), indent=1))
