"""Check every number in EVIDENCE_CHAIN.md against the saved records it cites. Stdlib only; reads, never writes, the
records; writes EVIDENCE_CHAIN_CHECK.json next to this script.

  python -I -B check_evidence_chain.py

Each claim is (id, source, value taken from the source, the text shown in EVIDENCE_CHAIN.md). A claim passes if the
source value, formatted as shown, equals the shown text and that text occurs in EVIDENCE_CHAIN.md. The sources are the
studies' own verified summaries (each produced by its own checker), plus the sealed analyses where no summary exists."""
import csv, hashlib, io, json
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
    N4a=R / 'natural-text-lateturn-analysis-20261031-01/ANALYSIS.json',
    N5=R / 'natural-text-fewepoch-analysis-20261103-01/ANALYSIS.json',
    N5c=R / 'natural-text-fewepoch-result-20261103-01/RESULT_CHECK.json',
    N5p=R / 'natural-text-fewepoch-analysis-20261103-01/POINTS.csv',
    N5r=R / 'natural-text-fewepoch-result-20261103-01/RESULT.md',
    N6=R / 'natural-text-peak-analysis-20261103-01/ANALYSIS.json',
    N6c=R / 'natural-text-peak-result-20261103-01/RESULT_CHECK.json',
    N6p=R / 'natural-text-peak-analysis-20261103-01/POINTS.csv',
    N6r=R / 'natural-text-peak-result-20261103-01/RESULT.md',
    N6n=R / 'natural-text-peak-result-20261103-01/PR3_NOTE_CHECK.json')
J = {k: json.loads(p.read_bytes().decode('utf-8')) for k, p in SRC.items() if p.suffix == '.json'}
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

# ------------------------------------------------------------------ N5: the few-epoch study
F = J['N5']; points = lambda k: list(csv.DictReader(io.StringIO(SRC[k].read_bytes().decode('utf-8')))); result = lambda k: SRC[k].read_bytes().decode('utf-8')
def est(i, d=4): return f(i['mean'], d) + ' ' + ci(*i['interval'], d)
def quoted(cid, source_text, shown): claim(cid, shown if shown in source_text else 'NOT IN THE SOURCE', shown)
def sci(p): return f'{p:.2e}'.replace('-', MINUS)
def source_has(cid, source_text, phrase): claim(cid, phrase in source_text, True)
claim('N5 check', J['N5c']['status'], 'PASS')
claim('N5 all widths NOT_OVERFIT', F['not_overfit']['all_widths'], True)
claim('N5 fit bounds', F['fit_bounds'], dict(upper=0, lower=0, undefined=0))
for k, lab, shown, adj, draws in (('M', 'CAPACITY_BEYOND_MEMORIZATION', f"{MINUS}0.0066 [{MINUS}0.0076, {MINUS}0.0055]", '3.51e' + MINUS + '07', '10/10 negative'), ('FALL', 'CONTINUES_RISING', '+0.0040 [+0.0010, +0.0069]', '0.0133', '9/10 positive'), ('RISE', 'RISES', '+0.0275 [+0.0269, +0.0280]', '5.74e' + MINUS + '15', '10/10 positive')):
    pr = F['primaries'][k]; i = pr['interval']
    claim(f'N5 {k} label', pr['label'], lab); claim(f'N5 {k}', est(i), shown); claim(f'N5 {k} rejected under Holm', pr['holm']['rejected'], True)
    a = pr['holm']['holm_adjusted_p']; claim(f'N5 {k} Holm-adjusted p', f'{a:.4f}' if a > 1e-3 else sci(a), adj)
    claim(f'N5 {k} draws', f"{max(i['negative'], i['positive'])}/{i['n']} " + ('negative' if i['negative'] > i['positive'] else 'positive'), draws)
    for who in ('memorization_only', 'jane_street'): claim(f'N5 {k} {who} predicts', F['predictions'][who][k], dict(M=dict(memorization_only='NOT_DETECTED', jane_street='not fixed by the pattern'), FALL=dict(memorization_only='CONTINUES_RISING or INCONCLUSIVE', jane_street='TURNS_DOWN'), RISE=dict(memorization_only='RISES', jane_street='RISES'))[k][who])
s5 = F['shift']; claim('N5 shift', f"{s5['label']} {est(s5['interval'])}", 'MOVES_LARGER +0.0237 [+0.0117, +0.0357]'); claim('N5 shift draws', f"{s5['interval']['positive']}/{s5['interval']['n']}", '10/10')
claim('N5 no location at a ladder end', sum(s5['locations_at_768'].values()) + sum(s5['locations_at_64'].values()), 0)
claim('N5 panel argmax 512 at all readouts', sorted({F['by_readout'][e]['argmax_width'] for e in F['by_readout']}), [512])
claim('N5 per-draw argmax 512 at all readouts', sorted({v for e in F['by_readout'] for v in F['by_readout'][e]['per_draw_argmax'].values()}), [512])
claim('N5 FALL by readout', '; '.join(f"{e} {est(F['by_readout'][e]['fall'])}" for e in ('E0.25', 'E0.5', 'E1', 'E2', 'E3')), f"E0.25 {MINUS}0.0017 [{MINUS}0.0030, {MINUS}0.0004]; E0.5 {MINUS}0.0031 [{MINUS}0.0042, {MINUS}0.0020]; E1 {MINUS}0.0018 [{MINUS}0.0028, {MINUS}0.0009]; E2 +0.0016 [{MINUS}0.0004, +0.0035]; E3 +0.0040 [+0.0010, +0.0069]")
P5 = points('N5p'); claim('N5 points', len(P5), 50)
claim('N5 768 below 512 in all points', sum(float(r['p_512']) > float(r['p_768']) for r in P5), 50)
claim('N5 smallest 512 minus 768', f(min(float(r['p_512']) - float(r['p_768']) for r in P5), 4), '+0.0037')
wi = {w: F['widths'].index(w) for w in (384, 512, 768)}; cur = F['by_readout']['E3']['curve']
claim('N5 panel p* at E3', ', '.join(f'{cur[wi[w]]:.4f}' for w in (384, 512, 768)) + ' in N5', '0.0979, 0.1175, 0.1038 in N5')
for name, reading in (('regime', F['readings'][0]), ('FALL', F['readings'][3])): quoted(f'N5 reading {name}', TEXT, reading)
claim('N5 M reading, quoted to the end of its parenthesis', F['readings'][2].split(' The gap includes')[0] in TEXT, True)
r5 = result('N5r'); source_has('N5 identical sets', r5, 'Identical-text sets across groups: 10'); source_has('N5 shared sequences', r5, 'mean 0.74% of a group over the eleven groups, largest 1.89% (d04)'); source_has('N5 64-token runs', r5, 'mean 1.00%, largest 2.21% (d04)')
source_has('N5 tie limit', r5, 'allows at most n / 1,024 tied values, which is 16 here')

# ------------------------------------------------------------------ N6: the peak confirmation
K = J['N6']; C = K['contrasts']; READ = ('E0.25', 'E0.5', 'E1', 'E2', 'E3'); ARMS = ('384|lr3e-04', '512|lr3e-04', '512|lr1e-04', '768|lr3e-04', '768|lr1e-04')
claim('N6 check', J['N6c']['status'], 'PASS'); claim('N6 mismatches', J['N6c']['mismatches'], []); claim('N6 input differences', J['N6c']['input_differences'], [])
claim('N6 decision', K['decision'], dict(primary='INTERIOR_PEAK', control='RATE_DEPENDENT')); claim('N6 note on the pull request edits', J['N6n']['verdict'], 'PASS')
claim('N6 fit bounds', K['fit_bounds'], dict(upper=0, lower=0, undefined=0))
for k, shown, draws in (('D1', '+0.0192 [+0.0179, +0.0204]', '6/6 positive'), ('D2', '+0.0158 [+0.0131, +0.0185]', '6/6 positive'), ('D4', f"{MINUS}0.0050 [{MINUS}0.0090, {MINUS}0.0010]", '6/6 negative'), ('D3', '+0.0111 [+0.0072, +0.0150]', '6/6 positive')):
    i = C[k]['interval']; claim(f'N6 {k}', est(i), shown); claim(f'N6 {k} draws', f"{max(i['negative'], i['positive'])}/{i['n']} " + ('negative' if i['negative'] > i['positive'] else 'positive'), draws); claim(f'N6 {k} none flagged', C[k]['flagged'], [])
claim('N6 D4 p', f"{C['D4']['interval']['p']:.4f}", '0.0232'); claim('N6 D4 sd', f"{C['D4']['interval']['sd']:.4f}", '0.0038')
no = K['not_overfit']; claim('N6 all arms NOT_OVERFIT', [no['arms'][a]['label'] for a in ARMS], ['NOT_OVERFIT'] * 5); claim('N6 every arm 6/6 below 0', [no['arms'][a]['interval']['negative'] for a in ARMS], [6] * 5)
means = [no['arms'][a]['interval']['mean'] for a in ARMS]; claim('N6 range of mean delta', f"{f(min(means), 4)} to {f(max(means), 4)}", f"{MINUS}0.0814 to {MINUS}0.0539")
re6 = K['rate_effects']
for w, q, shown, sides in (('512', 'p', f"{MINUS}0.0161 [{MINUS}0.0170, {MINUS}0.0153]", (6, 0)), ('512', 'validation', '+0.0181 [+0.0120, +0.0241]', (0, 6)), ('768', 'p', '+0.0047 [+0.0015, +0.0079]', (0, 6)), ('768', 'validation', f"{MINUS}0.0166 [{MINUS}0.0321, {MINUS}0.0011]", (5, 1))):
    i = re6[w][q]['interval']; claim(f'N6 rate effect {q} at {w}', est(i), shown); claim(f'N6 rate effect {q} at {w} draws', (i['negative'], i['positive']), sides)
BY = {e: K['by_readout'][e] for e in READ}
for e in READ: claim(f'N6 by readout row {e}', f"| {e} | {est(BY[e]['contrasts']['D1']['interval'])} | {est(BY[e]['contrasts']['D2']['interval'])} | {est(BY[e]['contrasts']['D4']['interval'])} |", next(l for l in TEXT.replace(chr(13), '').split(chr(10)) if l.startswith(f'| {e} | ') and '[' in l))
claim('N6 per-draw argmax at 3e-4', sorted({v for e in READ for v in BY[e]['per_draw_argmax_at_3e-4'].values()}), [512])
fa = BY['E3']['fall_at_3e-4']['interval']; claim('N6 FALL at E3', est(fa), '+0.0014 [' + MINUS + '0.0013, +0.0041]'); claim('N6 FALL at E3 draws', f"{fa['positive']}/{fa['n']}", '4/6')
mi = K['matched_gap']['interval']; claim('N6 M', est(mi), f"{MINUS}0.0078 [{MINUS}0.0102, {MINUS}0.0053]"); claim('N6 M draws', f"{mi['negative']}/{mi['n']}", '6/6'); quoted('N6 M note', TEXT, K['matched_gap']['note'])
pan = BY['E3']['panel']; claim('N6 panel p* at E3', ', '.join(f"{pan[a]['p']:.4f}" for a in ARMS[:2] + ARMS[3:4]) + ' in N6', '0.0979, 0.1171, 0.1013 in N6')
claim('N6 mean gap at E3 behind the caveat', f"{pan['512|lr3e-04']['gap']:.4f} at 512 at 3e-4 and {pan['768|lr1e-04']['gap']:.4f} at 768 at 1e-4", '0.5823 at 512 at 3e-4 and 0.5430 at 768 at 1e-4')
claim('N6 lowest mean validation NLL at E3 in all arms', [min(READ, key=lambda e: BY[e]['panel'][a]['validation']) for a in ARMS], ['E3'] * 5)
for i, name in ((1, 'primary'), (2, 'control'), (3, 'D3')): quoted(f'N6 reading {name}', TEXT, K['readings'][i])
P6 = points('N6p'); P = {(r['draw'], float(r['epoch']), int(r['width']), r['tag']): r for r in P6}; DR = sorted({r['draw'] for r in P6})
def above(e, tag, key): return sum(float(P[(d, e, 512, tag)][key]) > float(P[(d, e, 768, tag)][key]) for d in DR)
for label, e in zip(READ, (0.25, 0.5, 1.0, 2.0, 3.0)): claim(f'N6 tally {label}', f"| {label} | {above(e, 'lr3e-04', 'p')} | {above(e, 'lr3e-04', 'gap')} | {above(e, 'lr1e-04', 'p')} | {above(e, 'lr1e-04', 'gap')} |", dict(zip(READ, ('| E0.25 | 6 | 0 | 6 | 0 |', '| E0.5 | 6 | 0 | 6 | 0 |', '| E1 | 6 | 0 | 6 | 0 |', '| E2 | 6 | 2 | 3 | 0 |', '| E3 | 6 | 6 | 0 | 0 |')))[label])
r6 = result('N6r'); source_has('N6 articles left', r6, '16,451 are left over'); source_has('N6 identical sets', r6, '0 sets across the fresh groups'); source_has('N6 runs in another fresh group', r6, '64-token runs recurring in another fresh group: mean 0.15%, largest 0.19%'); source_has('N6 runs in t00-d10', r6, 'Recurring in the sequences t00–d10 used: mean 0.26%, largest 0.35%')
source_has('N6 public timing', r6, 'about 22.0 minutes after Run C2 ended'); source_has('N6 tie limit', r6, 'allows at most n / 1,024 tied values, which is 16 here'); source_has('N6 V at 768 on t00', r6, 'minus 3e-4, was −0.0357')
for shown in ('16,451', '0.15%', '0.19%', '0.26%', '0.35%', '0.74%', '1.89% (d04)', '1.00%', '2.21%', 'about 22.0 minutes after Run C2 ended', '0.0357'): claim(f'chain text has {shown}', shown, shown)

# ------------------------------------------------------------------ compare
STRUCTURAL = (list, dict, bool, int, tuple)
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
