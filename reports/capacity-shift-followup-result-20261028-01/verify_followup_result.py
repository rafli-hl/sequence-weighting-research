"""Read-only verification of the capacity-shift follow-up run (protocol revision 02; owner run of 27-28 Oct 2026).

  python -I -B verify_followup_result.py

Reads the activation, the run, the sealed source, the registry, the owner's analysis output and the re-run of the
sealed analysis in analysis-rerun/ (made beforehand from the activation copy of shift_analysis.py). Writes only
VERIFICATION.json next to this script. Tree hashes before and after show that nothing read was changed.
"""
import hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(r'D:\sequence-weighting-research'); HERE = Path(__file__).resolve().parent
ACT = ROOT / 'work/capacity-shift-followup-activation-20261027-01'; RUN = ROOT / 'work/runs/capacity-shift-followup-20261027-01'
SRC = ROOT / 'work/capacity-shift-followup-source-20261027-01'; REG = ROOT / 'reports/capacity-shift-followup-seed-registry-20261027-01'
PREP = ROOT / 'reports/capacity-shift-followup-preparation-20261027-01'; ANA = ROOT / 'reports/capacity-shift-followup-analysis-20261027-01'
RERUN = HERE / 'analysis-rerun'
PIN = 'd93eee952d3dc0a6518fd44d95ab27bf1eb11139752731967d301ab420e88c9c'; BUILDER = 'ad0480cb2e87dc77dce45ec7084174662bb9989fb6746ed6e78076e8748bd70b'
APPROVAL_ID = 'OWNER-20261027-FOLLOWUP-01'
OWNER_TEXT = ('I approve (i) the frozen capacity-shift follow-up protocol revision 02, source subject d93eee952d3dc0a6518fd44d95ab27bf1eb11139752731967d301ab420e88c9c, '
              'builder ad0480cb2e87dc77dce45ec7084174662bb9989fb6746ed6e78076e8748bd70b and the seed policy, and (ii) one outcome-blind registry draw followed by one '
              'owner-run follow-up attempt within its sealed limits (at most 6 hours, at most 3 GiB, 5 GiB free at admission), with no retry, and then the frozen offline analysis. '
              'I will run the commands myself.')
LIMITS = dict(overall_seconds=21600, stage_cap_max=1425, storage_bytes=3 * 2 ** 30, total_files=1000, stage_storage_bytes=2 ** 28, stage_files=128,
              gpu_sampled_bytes=2 * 2 ** 30, worker_peak_rss_bytes=4032 * 2 ** 20)
FILES = ('ANALYSIS.json', 'POINTS.csv', 'SECONDARIES.csv', 'CLIPPING.csv')
checks = []
def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''): h.update(chunk)
    return h.hexdigest()
def load(p): return json.loads(Path(p).read_bytes())
def check(name, ok, **detail): checks.append(dict(check=name, ok=bool(ok), **detail))
def tree(root):
    h = hashlib.sha256(); n = 0; size = 0
    for p in sorted(Path(root).rglob('*')):
        h.update(p.relative_to(root).as_posix().encode() + (b'/' if p.is_dir() else b''))
        if p.is_file(): h.update(fsha(p).encode()); n += 1; size += p.stat().st_size
    return dict(sha256=h.hexdigest(), files=n, bytes=size)
TREES = dict(activation=ACT, run=RUN, source=SRC, registry=REG, analysis=ANA, preparation=PREP, rerun=RERUN)
before = {k: tree(v) for k, v in TREES.items()}

# ------------------------------------------------------------------ sources, approval, authorization, registry
for label, root in (('activation', ACT), ('source', SRC)):
    raw = (root / 'SOURCE_SUBJECT.json').read_bytes(); bad = [r['path'] for r in json.loads(raw)['files'] if (root / r['path']).stat().st_size != r['bytes'] or fsha(root / r['path']) != r['sha256']]
    check(f'{label} subject pin and every bound file', sha(raw) == PIN and not bad, changed=bad)
appr_raw = (ACT / 'APPROVAL_RECORD.json').read_bytes(); appr = json.loads(appr_raw); auth = load(ACT / 'AUTHORIZATION.json')
check('builder file is the approved builder', fsha(PREP / 'build_followup_activation.py') == BUILDER, builder_sha256=fsha(PREP / 'build_followup_activation.py'))
check('approval text and id equal the owner approval; id is not a fixture id', appr['user_text'] == OWNER_TEXT and appr['user_message_id'] == auth['approval_id'] == APPROVAL_ID
      and not APPROVAL_ID.upper().startswith('FIXTURE') and appr['retries'] is False and appr['assistant_must_not_launch'] is True)
check('preparation evidence bound in the approval record equals the current files (6 pins)', len(appr['preparation_evidence']) == 6
      and all(fsha(ROOT / e['path']) == e['sha256'] and (ROOT / e['path']).stat().st_size == e['bytes'] for e in appr['preparation_evidence']))
reg_raw, ex_raw, draw_raw = ((ACT / n).read_bytes() for n in ('REGISTRY.json', 'EXCLUSIONS.json', 'DRAW.json'))
check('authorization enabled, one use, binds approval record, subject, registry, exclusions and draw', auth['enabled'] is True and auth['execution_ready'] is True and auth['one_use'] is True
      and auth['approval_record_sha256'] == sha(appr_raw) and auth['source_subject_sha256'] == PIN and auth['registry_sha256'] == sha(reg_raw) == appr['registry_sha256']
      and auth['exclusions_sha256'] == sha(ex_raw) and auth['draw_sha256'] == sha(draw_raw) == appr['draw_sha256'], registry_sha256=sha(reg_raw), draw_sha256=sha(draw_raw))
check('activation registry, exclusions and draw are byte copies of the drawn registry directory; claim present; no stop record',
      reg_raw == (REG / 'REGISTRY.json').read_bytes() and ex_raw == (REG / 'EXCLUSIONS.json').read_bytes() and draw_raw == (REG / 'DRAW.json').read_bytes()
      and (REG / 'DRAW_CLAIM.json').is_file() and not (REG / 'REGISTRY_STOPPED.json').exists())
sys.path.insert(0, str(SRC)); import ladder_registry, ladder_plan as plan
try: registry = ladder_registry.validate(json.loads(reg_raw), ex_raw, draw_raw); rederived = True
except ValueError as e: registry, rederived = None, str(e)
reg = json.loads(reg_raw); draw = json.loads(draw_raw)
accepted = rejected = 0
for d in reg['decisions']:
    if accepted == 61: break
    if d['accepted']: accepted += 1
    else: rejected += 1
check('registry re-derives from its draw under the frozen policy and exclusions; 12 corpora, 61 values from 256 candidates',
      rederived is True and reg['policy_sha256'] == load(SRC / 'SOURCE_SUBJECT.json')['seed_policy_sha256'] == fsha(REG / 'SEED_REGISTRY_POLICY.md')
      and [r['corpus_slot'] for r in reg['corpus_pairs']] == list(plan.CORPORA) and draw['bytes'] == 1024 and len(reg['decisions']) == 256,
      detail=rederived, accepted=sum(d['accepted'] for d in reg['decisions']), rejected_before_61st_acceptance=rejected,
      exclusion_values=len(json.loads(ex_raw)['values']))
man = load(PREP / 'ACTIVATION_MANIFEST.json')
late = {'OWNER_CLAIM.json', 'OWNER_EXIT_RECEIPT.json', 'WORKER_STDOUT.log', 'WORKER_STDERR.log'}
built = {f['path']: f['sha256'] for f in man['files']}
now = {p.relative_to(ACT).as_posix(): fsha(p) for p in ACT.rglob('*') if p.is_file()}
check('activation manifest ARMED_UNUSED at build; every built file unchanged; only the owner claim, receipt and logs were added later',
      man['status'] == 'ARMED_UNUSED' and man['source_subject_sha256'] == PIN and all(now.get(k) == v for k, v in built.items()) and set(now) - set(built) == late,
      added=sorted(set(now) - set(built)))

# ------------------------------------------------------------------ receipts, stages and limits
owner = load(ACT / 'OWNER_EXIT_RECEIPT.json'); claim = load(ACT / 'OWNER_CLAIM.json'); term_raw = (RUN / 'TERMINAL.json').read_bytes(); term = json.loads(term_raw); bench = load(RUN / 'BENCHMARK.json')
check('owner claim and receipt: COMPLETE, exit 0 observed, no retry; binds TERMINAL.json', claim['approval_id'] == APPROVAL_ID and claim['subject'] == PIN
      and owner['status'] == owner['terminal_status'] == term['status'] == 'COMPLETE' and owner['exit_observed'] and owner['exit_code'] == 0 and owner['retry'] is False
      and owner['terminal_sha256'] == sha(term_raw) and term['subject'] == PIN, terminal_sha256=sha(term_raw), owner_elapsed=owner['elapsed_seconds'], worker_elapsed=term['elapsed_seconds'])
receipts = [load(RUN / f'{c}-RECEIPT.json') for c in plan.CORPORA]
check('twelve stages c01..c12 COMPLETE with 16 trajectories each; receipts equal TERMINAL stage entries', [r['stage'] for r in receipts] == list(plan.CORPORA)
      and all(r['status'] == 'COMPLETE' and r['trajectories'] == 16 for r in receipts) and term['stages'] == receipts, stage_seconds=[round(r['seconds'], 1) for r in receipts])
caps = bench['caps']
check('benchmark cap feasible and at most 1,425 s; every stage within its cap; overall within 21,600 s', caps['feasible'] and caps['stage_work_cap_seconds'] <= LIMITS['stage_cap_max']
      and all(r['seconds'] <= caps['stage_work_cap_seconds'] for r in receipts) and term['elapsed_seconds'] <= LIMITS['overall_seconds'] and owner['elapsed_seconds'] <= LIMITS['overall_seconds'],
      cap=caps['stage_work_cap_seconds'], projected=caps['projected_stage_seconds'], benchmark_seconds=bench['benchmark']['overheads']['benchmark_seconds'],
      max_stage_seconds=max(r['seconds'] for r in receipts), sum_stage_seconds=sum(r['seconds'] for r in receipts))
check('storage within 3 GiB / 1,000 files by the terminal inventory and by the recomputed run tree', term['inventory']['bytes'] <= LIMITS['storage_bytes'] and term['inventory']['files'] <= LIMITS['total_files']
      and before['run']['bytes'] <= LIMITS['storage_bytes'] and before['run']['files'] <= LIMITS['total_files'], inventory=term['inventory'], tree=dict(bytes=before['run']['bytes'], files=before['run']['files']))
# Run 01 of this script required tree = inventory + TERMINAL.json exactly and failed: one 2,355-byte file had left cache/
# (the library TMPDIR) after the final inventory, as in the ladder verification (run-01-check-error/).
gone = term['inventory']['bytes'] + len(term_raw) - before['run']['bytes']; cache_now = list((RUN / 'cache').rglob('*'))
check('reconciliation: tree = final inventory + TERMINAL.json - one file no longer present; cache/ (library TMPDIR) now empty',
      before['run']['files'] == term['inventory']['files'] and 0 < gone < 2 ** 20 and cache_now == [], vanished_bytes=gone, terminal_json_bytes=len(term_raw), cache_entries_now=len(cache_now))
deltas = [r['closed_totals'][0] - (receipts[i - 1]['closed_totals'][0] if i else 0) for i, r in enumerate(receipts)]
stage_files = {c: sum(1 for p in (RUN / c).rglob('*') if p.is_file()) for c in plan.CORPORA}
check('each stage: 50 files and at most 256 MiB', all(v == 50 for v in stage_files.values()) and all(0 < d <= LIMITS['stage_storage_bytes'] for d in deltas), stage_bytes=deltas, stage_files=stage_files)
check('sampled peaks within limits (GPU 2 GiB, worker RSS 4,032 MiB), overall and in every stage receipt',
      all(p['device_used_sampled'] <= LIMITS['gpu_sampled_bytes'] and p['cuda_reserved'] <= LIMITS['gpu_sampled_bytes'] and p['worker_peak_rss'] <= LIMITS['worker_peak_rss_bytes'] for p in [term['peaks']] + [r['peaks'] for r in receipts]),
      peaks=term['peaks'])

# ------------------------------------------------------------------ records, inputs and counts
records, bad_records, val_blocks, bindings = [], [], 0, 0
for c in plan.CORPORA:
    inputs = load(RUN / c / 'INPUTS.json'); row = next(r for r in reg['corpus_pairs'] if r['corpus_slot'] == c)
    if inputs['seeds'] != {k: v for k, v in row.items() if k != 'corpus_slot'}: bad_records.append(f'{c}: seeds differ from the registry')
    for (cond, arm, w, l) in plan.trajectories():
        base = RUN / c / f'{w}x{l}' / f'{cond}-{arm}'; rec = load(base / 'record.json'); raw = (base / 'arrays.f32').read_bytes(); records.append(rec)
        vb = rec['layout']['validation_blocks']; val_blocks += vb
        ok = (len(rec['checks']) == 49 and rec['layout']['train_blocks'] == 49 and len(rec['epochs']) == 40 and rec['checks'][-1]['update'] == 640
              and len(raw) == 4 * 7 * (49 * 512 + vb * 256) == rec['arrays']['bytes'] and sha(raw) == rec['arrays']['sha256'])
        fixed = {16 * e for e in plan.FIXED_EPOCHS}
        ok = ok and fixed <= {ch['update'] for ch in rec['checks'] if 'validation' in ch}
        bindings += 1
        if not ok: bad_records.append(f'{c}/{w}x{l}/{cond}-{arm}')
check('192 records: 49 checks to update 640, 40 epochs, every fixed epoch validated, array sizes and SHA-256 bindings; stage inputs carry the registry seeds',
      len(records) == 192 and not bad_records, bad=bad_records[:10], validation_blocks=val_blocks)
check('no landmark states saved', not list(RUN.rglob('landmark-*.pt')))
expected_eval = 12 * 8 * (72 + 24) + 192 * 49 * 16 + val_blocks * 8
c = term['counts']
check('counts: 147,456 updates, 288 models, 96 pretrained states; evaluation batches equal the recomputation from the records; terminal equals the c12 receipt',
      c == receipts[-1]['counts'] and c['updates'] == 147456 and c['models'] == 288 and c['pretrained_states'] == 96 and c['eval_batches'] == expected_eval,
      counts=c, expected_eval_batches=expected_eval, landmark_validations=val_blocks - 192 * len(plan.FIXED_EPOCHS))
check('worker logs empty', (ACT / 'WORKER_STDOUT.log').read_bytes() == b'' and (ACT / 'WORKER_STDERR.log').read_bytes() == b'')

# ------------------------------------------------------------------ analysis
same = {n: (RERUN / n).is_file() and fsha(RERUN / n) == fsha(ANA / n) for n in FILES}
check('sealed shift_analysis.py re-run (activation copy) reproduces ANALYSIS.json, POINTS.csv, SECONDARIES.csv and CLIPPING.csv byte for byte',
      all(same.values()) and set(p.name for p in ANA.iterdir()) == set(FILES), files=same, sha256={n: fsha(ANA / n) for n in FILES})
a = load(ANA / 'ANALYSIS.json')
labels = {k: v['label'] for k, v in a['slope_tests'].items()}
check('frozen decision MOVES_SMALLER (G16, R); all twelve corpora available', a['status'] == 'COMPLETE' and a['corpora_available'] == list(plan.CORPORA)
      and a['decision']['label'] == 'MOVES_SMALLER' and labels == {'primary|R': 'MOVES_SMALLER', 'primary|S_batch': 'MOVES_SMALLER', 'E15-E30|R': 'MOVES_SMALLER', 'E15-E30|S_batch': 'MOVES_SMALLER'},
      decision=a['decision']['label'], labels=labels)

after = {k: tree(v) for k, v in TREES.items()}
check('read-only: activation, run, source, registry, preparation, owner analysis and re-run unchanged by this verification', before == after,
      trees={k: dict(sha256=v['sha256'], files=v['files'], bytes=v['bytes']) for k, v in after.items()})
value = dict(status='PASS' if all(x['ok'] for x in checks) else 'FAIL', checks=len(checks), failed=[x['check'] for x in checks if not x['ok']], python=sys.version,
             script_sha256=fsha(Path(__file__)), results=checks)
(HERE / 'VERIFICATION.json').write_bytes((json.dumps(value, indent=2) + '\n').encode('utf-8'))
print(json.dumps(dict(status=value['status'], checks=len(checks), failed=value['failed']), indent=1))
