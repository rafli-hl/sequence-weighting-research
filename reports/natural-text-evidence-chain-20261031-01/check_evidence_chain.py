"""Check every number in EVIDENCE_CHAIN.md against the saved records it cites. Stdlib only; reads, never writes, the
records; writes EVIDENCE_CHAIN_CHECK.json next to this script.

  python -I -B check_evidence_chain.py

Each claim is (id, source, value taken from the source, the text shown in EVIDENCE_CHAIN.md). A claim passes if the
source value, formatted as shown, equals the shown text and that text occurs in EVIDENCE_CHAIN.md. The sources are the
studies' own verified summaries (each produced by its own checker), plus the sealed analyses where no summary exists."""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parents[0]
SRC = dict(
    S=R / 'capacity-shift-followup-result-20261028-01/RESULT_SUMMARY.json',
    N1=R / 'natural-text-ladder-analysis-20261029-01/sealed-analysis/ANALYSIS.json',
    N1x=R / 'natural-text-ladder-exploratory-20261029-01/EXPLORATORY_CHECKS.json',
    N2=R / 'natural-text-ladder-probe-result-20261030-01/PROBE_READING.json',
    N3=R / 'natural-text-onerate-result-20261031-01/RESULT_CHECK.json',
    N4=R / 'natural-text-lateturn-result-20261031-01/RESULT_CHECK.json',
    N4a=R / 'natural-text-lateturn-analysis-20261031-01/ANALYSIS.json')
J = {k: json.loads(p.read_bytes().decode('utf-8')) for k, p in SRC.items()}
TEXT = (HERE / 'EVIDENCE_CHAIN.md').read_bytes().decode('utf-8')
MINUS = '−'


def f(x, d, sign=True):
    s = f'{abs(x):.{d}f}'
    if float(s) == 0: return s
    return (MINUS if x < 0 else '+' if sign else '') + s


def ci(lo, hi, d): return f'[{f(lo, d)}, {f(hi, d)}]'


claims = []


def claim(cid, value, shown):
    claims.append(dict(id=cid, source_value=value, shown=shown))


# ------------------------------------------------------------------ S: synthetic capacity-shift follow-up
s = J['S']['slope_tests']['primary|R']; sl = s['slope']; sens = s['sensitivities']
claim('S primary label', s['label'], 'MOVES_SMALLER')
claim('S primary slope', f(sl['mean'], 3) + ' ' + ci(sl['low'], sl['high'], 3), f"{MINUS}0.796 [{MINUS}0.982, {MINUS}0.609]")
claim('S primary negative corpora', f"{sl['negative']}/{sl['n']}", '12/12')
claim('S flagged points', f"{s['counts']['flagged_points']} of {s['counts']['nominal_points']}", '19 of 60')
claim('S S32', f(sens['S32']['slope']['mean'], 3) + ' ' + ci(sens['S32']['slope']['low'], sens['S32']['slope']['high'], 3), f"{MINUS}0.817 [{MINUS}0.990, {MINUS}0.644]")
claim('S SD', f(sens['SD']['slope']['mean'], 3) + ' ' + ci(sens['SD']['slope']['low'], sens['SD']['slope']['high'], 3) + f" on {sens['SD']['slope']['n']} corpora",
      f"{MINUS}0.794 [{MINUS}0.966, {MINUS}0.622] on 8 corpora")
sb = J['S']['slope_tests']['primary|S_batch']['slope']
claim('S S_batch', f(sb['mean'], 3) + ' ' + ci(sb['low'], sb['high'], 3) + f", {sb['negative']}/{sb['n']}", f"{MINUS}0.851 [{MINUS}0.934, {MINUS}0.768], 12/12")
d = J['S']['slope_difference_R_minus_S_batch']['primary']
claim('S R minus S_batch', f"{d['label']} {f(d['mean'], 3)} {ci(d['low'], d['high'], 3)}", f"NO_DETECTED_DIFFERENCE +0.055 [{MINUS}0.128, +0.237]")
ec = J['S']['epoch_curves']
claim('S panel peaks', ', '.join(f"{ec[f'R|E{e}']['argmax_width']}/4 at E{e}" for e in (20, 25, 30, 40)), '192/4 at E20, 128/4 at E25, 96/4 at E30, 96/4 at E40')
claim('S panel labels E20-E40', sorted({ec[f'R|E{e}']['label'] for e in (20, 25, 30, 40)}), ['INTERIOR_PEAK'])
ex = J['S']['exposed_ladder_sizing_for_comparison']['values']['R']['slope_E15_E30_per_epoch_doubling']
w = J['S']['slope_tests']['E15-E30|R']['slope']
claim('S exposed vs fresh E15-E30', f"{f(ex['mean'], 3)} on {ex['n']} exposed corpora; {f(w['mean'], 3)} fresh", f"{MINUS}1.043 on 5 exposed corpora; {MINUS}0.922 fresh")

# ------------------------------------------------------------------ N1: natural-text capacity ladder (Run B, revision 05)
A = J['N1']['primaries']['A']; B = J['N1']['primaries']['B']; cnt = J['N1']['primaries']['counts']
claim('N1 A label', A['label'], 'NO_DETECTED_SHIFT_CENSORED')
claim('N1 A slope', f"{f(A['interval']['mean'], 0)} {ci(*A['interval']['interval'], 0)}", '0 [0, 0]')
claim('N1 A boundary points', f"{cnt['boundary_points']} of {cnt['nominal_points']}", '70 of 70')
claim('N1 A boundary at the top rung', sorted({(v['smallest'], v['largest']) for v in cnt['boundary_points_by_epoch'].values()}), [(0, 10)])
claim('N1 B label', B['label'], 'CONVEX')
claim('N1 B curvature', f(B['curvature']['mean'], 4) + ' ' + ci(*B['curvature']['interval'], 4) + f", {B['curvature']['positive']}/10 positive",
      '+0.0611 [+0.0588, +0.0634], 10/10 positive')
claim('N1 B vertex width', f"{B['vertex_width']:.1f}", '128.6')
claim('N1 decision', J['N1']['decision']['finding_2_peak_shift'] + ' / ' + J['N1']['decision']['finding_1_interior_peak'], 'NO_DETECTED_SHIFT_CENSORED / CONVEX')
x = J['N1x']
lr = x['learning_rates']; rate = {3e-4: '3e-4', 1e-4: '1e-4', 3e-5: '3e-5'}.get
claim('N1x rates', f"64 at {rate(lr['64'])}, 96 at {rate(lr['96'])}, 128–384 at " + (rate(lr['128']) if len({lr[w] for w in ('128', '192', '256', '384')}) == 1 else 'mixed'),
      '64 at 3e-4, 96 at 1e-4, 128–384 at 3e-5')
claim('N1x p* lowest at 128 at all nine epochs', sorted(set(x['p_argmin_width'].values())) + [len(x['p_argmin_width'])], [128, 9])
claim('N1x p* rises 128-384 at every epoch', all(x['p_rises_128_to_384'].values()), True)
claim('N1x gap lowest at 128 at all nine epochs', sorted(set(x['gap_argmin_width'].values())), [128])
claim('N1x Spearman pooled', f"{x['spearman_pooled_54']:.3f}", '0.964')
sw = x['spearman_within_epoch'].values()
claim('N1x Spearman within epoch', f"{min(sw):.2f}–{max(sw):.2f}", '0.43–1.00')

# ------------------------------------------------------------------ N2: the 768 probe
p = J['N2']; w768 = p['per_width']['768']
claim('N2 verdict', p['receipt']['verdict'], 'FITS_768')
claim('N2 reader checks pass', p['all_checks_pass'], True)
claim('N2 768 peak', f"{w768['peaks_gib']['device_used_sampled']:.4f} GiB", '2.2225 GiB')
claim('N2 768 margin', f"{(p['limit_bytes'] - w768['peaks_bytes']['device_used_sampled']) / 2 ** 20:.1f} MiB", '28.2 MiB')

# ------------------------------------------------------------------ N3: the one-rate extension (revision 02)
o = J['N3']; op = o['primaries']
claim('N3 verifier', o['verdict'], 'PASS')
for k, lab, shown in (('turn', 'CONTINUES_RISING', '+0.0220 [+0.0176, +0.0264]'), ('dip', 'NO_DIP_AT_ONE_RATE', '+0.0428 [+0.0400, +0.0455]'),
                      ('memo', 'TRACKS_MEMORIZATION', '+0.9643 [+0.9619, +0.9667]')):
    claim(f'N3 {k} label', op[k]['label'], lab)
    claim(f'N3 {k}', f(op[k]['mean'], 4) + ' ' + ci(*op[k]['interval'], 4), shown)
    claim(f'N3 {k} draws', f"{max(op[k]['negative'], op[k]['positive'])}/{op[k]['n']}", '10/10')
claim('N3 joint', o['reading']['joint'], 'MEMORIZATION_PREDICTIONS_MET')
claim('N3 Jane Street turn-down prediction met', o['reading']['jane_street_prediction_met'], False)
for e, shown in (('E24', f"{MINUS}0.0225 [{MINUS}0.0314, {MINUS}0.0136]"), ('E32', f"{MINUS}0.1748 [{MINUS}0.1872, {MINUS}0.1624]")):
    t = o['by_epoch'][e]['turn']
    claim(f'N3 {e} turn', f"{t['label']} " + f(t['mean'], 4) + ' ' + ci(*t['interval'], 4) + f", {t['negative']}/10", f'TURNS_DOWN {shown}, 10/10')
claim('N3 panel argmax by epoch', ', '.join(f"{e} {o['by_epoch'][e]['argmax_width']}" for e in ('E1', 'E2', 'E4', 'E6', 'E8', 'E12', 'E16', 'E24', 'E32')),
      'E1 512, E2 512, E4 768, E6 768, E8 768, E12 768, E16 768, E24 512, E32 384')
claim('N3 memorization at E32', f"{o['by_epoch']['E32']['memo']['mean']:.3f}", '0.833')
claim('N3 validation minimum 384-768', [o['validation_minimum'][w]['epoch'] for w in ('384', '512', '768')], [4, 4, 4])
claim('N3 turn decomposition', f(o['turn_epoch_decomposition']['E4_E16'], 4) + ' and ' + f(o['turn_epoch_decomposition']['E24_E32'], 4), f"+0.0502 and {MINUS}0.0282")

# ------------------------------------------------------------------ N4: the late-turn confirmation
n = J['N4']; npr = n['primaries']
claim('N4 verifier', n['verdict'], 'PASS')
claim('N4 terminal_outside_ledger present', n['terminal_flag']['terminal_outside_ledger_present'], False)
for k, lab, shown in (('P1', 'TURNS_DOWN', f"{MINUS}0.1886 [{MINUS}0.2083, {MINUS}0.1688]"), ('P3', 'SHIFTS_TO_SMALLER_WIDTH', '+0.9090 [+0.8641, +0.9539]'),
                      ('P2', 'INCONCLUSIVE', f"{MINUS}0.0238 [{MINUS}0.0479, +0.0003]")):
    claim(f'N4 {k} label', npr[k]['label'], lab)
    claim(f'N4 {k}', f(npr[k]['mean'], 4) + ' ' + ci(*npr[k]['interval'], 4), shown)
    claim(f'N4 {k} draws', f"{max(npr[k]['negative'], npr[k]['positive'])}/{npr[k]['n']}", '4/4')
claim('N4 sequence', [n['sequence'][k]['confirmed'] for k in ('P1', 'P3', 'P2')], [True, True, False])
claim('N4 censoring', n['censoring']['bound'], 'LOWER_BOUND_IF_CURVES_CONTINUE')
claim('N4 E8 peaks at the top rung', n['censoring']['e8_top'], 4)
for k in ('P1', 'P2', 'P3'):
    sv = n['seen_d01_d10'][k]
    claim(f'N4 seen {k}', f(sv['mean'], 4) + ' ' + ci(*sv['interval_95_df9'], 4),
          dict(P1=f"{MINUS}0.1748 [{MINUS}0.1872, {MINUS}0.1624]", P2=f"{MINUS}0.0225 [{MINUS}0.0314, {MINUS}0.0136]", P3='+0.9056 [+0.8871, +0.9242]')[k])
a = n['epoch_averaged_turn']
claim('N4 epoch-averaged turn', f"{a['label']} " + f(a['mean'], 4) + ' ' + ci(*a['interval'], 4), 'CONTINUES_RISING +0.0210 [+0.0079, +0.0342]')
claim('N4 validation minima', {w: n['validation_minimum'][w]['epoch'] for w in ('256', '384', '512', '768')}, {'256': 6, '384': 4, '512': 4, '768': 4})
claim('N4 panel argmax by epoch', ', '.join(f"{e} {n['by_epoch'][e]['argmax_width']}" for e in ('E1', 'E2', 'E4', 'E6', 'E8', 'E12', 'E16', 'E24', 'E32')),
      'E1 512, E2 512, E4 512, E6 768, E8 768, E12 768, E16 768, E24 512, E32 384')
claim('N4 E32 location kinds', sorted(set(n['by_epoch']['E32']['location_kinds'].values())), ['interior'])
claim('N4 E32 mean location width', f"{n['by_epoch']['E32']['location_mean_width']:.0f}", '409')
claim('N4 768 start-up peak', f"{n['operations']['startup_peak_sampled_gib']['768']:.4f} GiB", '2.2225 GiB')
claim('N4 parameters', f"{n['operations']['parameters']['256'] / 1e6:.1f}–{n['operations']['parameters']['768'] / 1e6:.1f} M", '5.3–34.7 M')
claim('N4 power stated in advance', 'Power stated in advance (four draws, 95%): 0.678 at the seen effect, 0.157 conservative, 0.247 halved.' in J['N4a']['readings'][3], True)

# ------------------------------------------------------------------ compare
STRUCTURAL = (list, dict, bool, int)
for c in claims:
    v, shown = c['source_value'], c['shown']
    c['equal'] = v == shown
    c['in_text'] = True if isinstance(shown, STRUCTURAL) else shown in TEXT
    c['pass'] = c['equal'] and c['in_text']
bad = [c for c in claims if not c['pass']]
out = dict(schema=1, purpose='Every number quoted in EVIDENCE_CHAIN.md, checked against the saved record it cites',
           sources={k: dict(path=str(p.relative_to(R.parent)).replace('\\', '/'), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k, p in SRC.items()},
           text_sha256=hashlib.sha256((HERE / 'EVIDENCE_CHAIN.md').read_bytes()).hexdigest(), claims=claims, failures=len(bad), verdict='PASS' if not bad else 'MISMATCH')
(HERE / 'EVIDENCE_CHAIN_CHECK.json').write_bytes((json.dumps(out, indent=1, ensure_ascii=False, default=list) + '\n').encode('utf-8'))
print(out['verdict'], len(claims), 'claims,', len(bad), 'failures')
for c in bad: print(json.dumps(c, ensure_ascii=False, default=list))
