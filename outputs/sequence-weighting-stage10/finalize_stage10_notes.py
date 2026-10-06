"""Administrative handoff update from final audited saved results; no new fits."""
import json
from pathlib import Path
from datetime import datetime, timezone
import hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN='search-v011-20260930-01'
RAW=ROOT/'work/runs'/RUN
OUT=HERE/f'results-{RUN}'

def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,text): path.write_text(text,encoding='utf-8')

def main():
    reviewpath=HERE/f'FINAL_REVIEW-{RUN}.json'
    review=read(reviewpath); end=read(RAW/'END.json'); audit=read(RAW/'AUDIT.json')
    freeze=read(RAW/'FREEZE.json'); summary=read(OUT/'summaries.json')
    u=summary['unique_inputs']; aliases=summary['policy_references']; flags=u['classification']
    assert review['status']==audit['status']=='PASS' and end['status']=='COMPLETE'
    assert u['total']==186 and aliases['total']==324 and len(summary['cells'])==36
    synthesis=HERE/'SYNTHESIS_STAGE4_10.md'
    assert 'pending final audited' not in synthesis.read_text(encoding='utf-8').lower()
    assert 'result is pending' not in synthesis.read_text(encoding='utf-8').lower()
    def rate(name):
        x=flags[name]; return f"{x['true']}/{x['available']}"
    counts=u['status_counts']
    report=OUT.relative_to(ROOT).as_posix()+'/REPORT.md'
    reviewname=reviewpath.relative_to(ROOT).as_posix()
    synthname=synthesis.relative_to(ROOT).as_posix()
    facts=(f"All 186 inputs / 207 native checkpoints / 324 policy references were retained. "
           f"There are {counts['compared']} compared, {counts['guard']} guard, {counts['unresolved']} unresolved and {counts['not_run']} unrun inputs. "
           f"Primary/reference objective agreement: {rate('search_objective_agreement')}; parameter agreement: {rate('parameter_agreement')}. "
           f"Original/reference objective agreement: {rate('original_objective_agreement')}; parameter agreement: {rate('original_parameter_agreement')}. "
           f"{flags['original_parameter_agreement']['false']} original p values exceed the separate 1e-6 parameter tolerance; their objectives still meet the frozen objective tolerance. "
           f"Arithmetic convergence: {rate('precision_converged')}. All counts use explicitly available comparisons; guards remain undefined.")
    scope=('This is bounded search agreement, without a global-optimality certificate. '
           'Original p*, K, validation selections and utility/peak verdicts are unchanged. '
           'The Stage 6 primary middle-capacity utility gate still fails in all four fresh panels. '
           'Numerical agreement does not establish recovery, fit quality or usefulness.')
    nextstep=('The next work is a bounded research-note draft using the Stage 4–10 synthesis and existing evidence, '
              'with a refreshed primary-literature review before novelty claims. Identify a specific remaining scientific gap '
              'before proposing another experiment. No further training, numerical audit, cloud job or publication is launched automatically.')
    prefix=f'''# Stage 10 — complete and independently verified

Completed locally on 30 September 2026: `{RUN}`. All 13 sources,
protocol, fixtures, review and copied inputs froze at {freeze['utc']} before
the new comparisons. The shared numerical phase completed in
{end['elapsed_seconds']:.2f} seconds ({end['elapsed_seconds']/60:.2f} minutes), within its 3,600-second ceiling.

{facts}

{scope}

Final report: `{report}`.
Independent final review: `{reviewname}`.
Bounded synthesis: `{synthname}`.
All three figures were visually reviewed; archive SHA256/CRC and saved-record
trace/classification/summary checks passed. Stage 4's 54 absent initial test
measurements and gains remain null; all 324 selected test measurements remain.
No process remains active. Do not duplicate this run or edit its frozen sources.

## Next recommendation — evidence-based paper draft

{nextstep}

The completed recommendations below are historical context.

'''
    path=ROOT/'NEXT_EXPERIMENT.md'; old=path.read_text(encoding='utf-8')
    old=old[old.index('# Stage 9 '):]
    old=old.replace('This recommendation is now authorized as Stage 10; current preparation status is recorded above.',
                    'This recommendation is complete as Stage 10 above.')
    save(path,prefix+old)
    section=f'''## 18. Stage 10 continuous-search agreement (v0.11) — complete

Run `{RUN}`. Source `outputs/sequence-weighting-stage10/`; raw
`work/runs/{RUN}/`. The freeze preceded the numerical clock, which started
at {read(RAW/'START.json')['utc']}. Numerical elapsed {end['elapsed_seconds']:.2f} seconds;
peak RSS {end['peak_rss_mib']:.2f} MiB. Preparation took {read(RAW/'runtime.json')['preparation_elapsed_seconds']:.2f} seconds.
No model training, inference, retuning or GPU use occurred.

### Design and provenance

The complete Stage 9 cohort was copied without outcome-based selection. Independent
provenance reconstructed 324 references, 207 native checkpoints and 186 exact
weight/gain inputs, including 945 full split-pairing checks across nine datasets.
The original float32 loss subtraction precedes promotion; gains stay signed.
There are 1,681 original source files and 1,644 historical raw-manifest bindings.
The new historical manifest protects 801 prior output/raw/source files; it does
not claim a fresh hash pass over every model binary.

All 13 experiment/analysis source files, protocol, config, fixtures and independent
design review were source-bound before the freeze. Preflight fixtures exposed and
fixed report tick serialization and all-zero-axis scaling before measured data.
The old Python-summation fixture was replaced with a threshold-rounding guard
fixture appropriate to this runtime. These were prefreeze synthetic checks;
historical or frozen scientific outputs were not overwritten.

Decimal80 scans 513 j/64 points, retains every derivative sign change and bisects
all brackets. Independent Decimal110 scans 1,025 j/128 points and refines every
declared mesh minimum using golden section. Both include endpoints and every
mesh candidate, with exact J then p ties. Refinement width is 1e-12 (40/80
iterations). Original p is evaluated separately and never enters candidates.
All full meshes, derivative/bracket traces, candidates and signed comparisons
are retained. The shared 3,600-second budget includes verification and caches.

Arithmetic tolerance is 1e-50*max(1,abs(J110)). Objective agreement tolerances
are 1e-18*S between new searches and 1e-12*S for saved original p, with
S=max(1,reference mesh J span); parameter tolerance is 1e-6. The fixed ±.001
neighborhood is a diagnostic and never enters candidate selection.

### Results and limits

{facts}

The independent final audit verified {review['saved_point_checks_verified']:,} saved arithmetic checks,
all stored bracket decisions, classifications, 36 cell summaries and exact
historical context. {flags['weak_neighborhood']['true']} eligible inputs met the frozen weak-neighborhood rule;
{flags['original_better_than_search']['true']} original points were better beyond tolerance.
Selected test losses are available for all 324 policy references. All 54 Stage 4
initial-test/test-gain values remain null. No imputation or retrospective selection.

{scope}

### Artifacts and continuation

- Report: `{report}`.
- Synthesis: `{synthname}`.
- Independent final verification: `{reviewname}`.
- Visual review: `outputs/sequence-weighting-stage10/VISUAL_REVIEW-{RUN}.json`.
- Archive: `outputs/sequence-weighting-stage10/results-{RUN}/run-records.zip`.
- Archive bytes: {review['archive_bytes']:,}; SHA256 `{review['archive_sha256']}`; ZIP CRC PASS.
- Raw files independently verified: {review['raw_files_verified']:,}; all three final figures passed visual review.

{nextstep}

No process remains active. Only scripts were executed, not the historical notebook.
'''
    path=ROOT/'HANDOFF.md'; old=path.read_text(encoding='utf-8')
    assert '## 18. Stage 10' not in old
    start=old.index('**Latest continuation status:**'); stop=old.index('**Previous completed status:**',start)
    latest=f'**Latest continuation status:** Stage 10 is complete and independently verified (30 September 2026), run `{RUN}`. Section 18 records the full retained cohort, search agreement, limitations, final report and archive. No process remains active. Preserve frozen sources and every original outcome.\n\n'
    old=old[:start]+latest+old[stop:]
    old=old.replace('Sections 10–17 supersede','Sections 10–18 supersede').replace('Section 17 is the latest continuation.','Section 18 is the latest continuation.')
    save(path,old.rstrip()+'\n\n'+section)
    path=ROOT/'RUNBOOK.md'; old=path.read_text(encoding='utf-8')
    start=old.index('### Stage 10 '); stop=old.index('### Stage 9 ',start)
    block=f'''### Stage 10 v0.11 complete and independently verified

Run `{RUN}` is complete. {facts}

The shared numerical phase took {end['elapsed_seconds']:.2f} seconds. All source/input,
saved-trace, classification, summary, archive and visual checks passed. Preserve
the frozen 13 sources and raw directory; do not relaunch. Final report:
`{report}`. Final verification: `{reviewname}`.
See HANDOFF section 18 and `{synthname}` for interpretation.
No process remains active. {scope}

'''
    save(path,old[:start]+block+old[stop:])
    path=ROOT/'CODEX_START.md'; old=path.read_text(encoding='utf-8'); stop=old.index('## Historical migration prompt')
    save(path,f'''# Current continuation point — 30 September 2026

Stages 2–10 are complete. Read AGENTS.md, HANDOFF.md (latest Section 18),
NEXT_EXPERIMENT.md, RUNBOOK.md and the Stage 1 report before extending research.
Stage 10 `{RUN}` is complete and independently verified. No process is active.
{facts}

{scope}

Final report: `{report}`.
Synthesis: `{synthname}`.
{nextstep}
Preserve every historical estimate and frozen source. Do not restart prior stages.

'''+old[stop:])
    path=ROOT/'RESEARCH_STATE.json'; state=read(path)
    if 'stage10-v011' not in state['completed']: state['completed'].append('stage10-v011')
    state.update(next='bounded research-note draft from Stage4–10 synthesis; refresh primary literature before novelty claims',
        next_status='recommended; no new experiment automatically authorized',latest_completed_stage=10,
        latest_run_id=RUN,latest_status='complete and independently verified; full retained cohort and all original outcomes preserved',
        active_experiment=None,latest_report=report,latest_completion_record=reviewname,updated_date='2026-09-30')
    save(path,json.dumps(state,indent=2,ensure_ascii=False)+'\n')
    completion=dict(status='COMPLETE',utc=datetime.now(timezone.utc).isoformat(),run_id=RUN,
        final_review_sha256=sha(reviewpath),report_sha256=sha(OUT/'REPORT.md'),synthesis_sha256=sha(synthesis),
        archive_sha256=review['archive_sha256'],archive_crc='PASS',raw_files_verified=review['raw_files_verified'],
        numerical_elapsed_seconds=end['elapsed_seconds'],status_counts=counts,original_outcomes_unchanged=True,
        active_processes=False,notes_updater_sha256=sha(Path(__file__)))
    target=HERE/f'COMPLETION-{RUN}.json'
    with target.open('x',encoding='utf-8') as stream: json.dump(completion,stream,indent=2); stream.write('\n')
    print(json.dumps(completion))

if __name__=='__main__': main()
