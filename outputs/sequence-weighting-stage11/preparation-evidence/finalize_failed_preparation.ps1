$ErrorActionPreference='Stop'
$taskRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskStage=Join-Path $taskRoot 'outputs/sequence-weighting-stage11'
$taskRun=Join-Path $taskRoot 'work/runs/rule-tying-v012-20260930-01'
$taskPackage=Join-Path $taskStage 'preparation-20260930-01'
if(Test-Path -LiteralPath $taskPackage){throw 'Package already exists'}
if(!(Test-Path -LiteralPath (Join-Path $taskRun 'PREPARATION_FAILURE.json'))){throw 'Failure record missing'}
foreach($name in @('FREEZE.json','RUN_STARTED.json','baselines','initial','runs')){if(Test-Path -LiteralPath (Join-Path $taskRun $name)){throw ('Unexpected research artifact '+$name)}}
$taskUtf8=[System.Text.UTF8Encoding]::new($false)
function Write-TaskText([string]$path,[string]$text){[System.IO.File]::WriteAllText($path,$text,$taskUtf8)}
function Write-TaskJson([string]$path,$value){Write-TaskText $path ($value|ConvertTo-Json -Depth 30)}
function Read-TaskText([string]$path){[System.IO.File]::ReadAllText($path)}
function Bind-TaskFile([string]$path){[ordered]@{path=$path.Substring($taskRoot.Length+1).Replace('\','/');bytes=(Get-Item -LiteralPath $path).Length;sha256=(Get-FileHash -LiteralPath $path).Hash.ToLower()}}
$taskReview=Get-Content -Raw -Encoding UTF8 (Join-Path $taskStage 'REVIEW_PREPARATION_FAILURE.json')|ConvertFrom-Json
if($taskReview.status -ne 'PASS_FAIL_CLOSED_PREPARATION_STOP'){throw 'Failure audit did not pass'}
New-Item -ItemType Directory -Path (Join-Path $taskPackage 'context_before')|Out-Null
$taskRoots=@('HANDOFF.md','NEXT_EXPERIMENT.md','RUNBOOK.md','CODEX_START.md','RESEARCH_STATE.json','RESEARCH_GOAL.md')
foreach($name in $taskRoots){Copy-Item -LiteralPath (Join-Path $taskRoot $name) -Destination (Join-Path $taskPackage ('context_before/'+$name))}
$taskStatus='Stage 11 implementation and resource checks passed review, but its preparation freeze failed the cumulative 300-second cap. No FREEZE or RUN_STARTED exists and no research training began. See section 20; preserve the failed attempt.'
$taskHandoff=Read-TaskText (Join-Path $taskRoot 'HANDOFF.md')
$taskHandoff=[regex]::Replace($taskHandoff,'\*\*Latest continuation status:\*\*[^\r\n]+',('**Latest continuation status:** '+$taskStatus),1)
$taskHandoff+=@'


## 20. Stage 11 implemented; preparation freeze stopped — 30 September 2026

New v0.12 source under `outputs/sequence-weighting-stage11/` implements the G1/G16
intervention, paired U pretraining, F/R policies, validation-only selection,
corpus-level analysis, reporting and runtime/storage guards. Core/model are exact
Stage 6 copies; all parent provenance is in PARENT_SOURCES.json. Historical
experiments and the reviewed paper-track proposal remain unchanged.

Engine fixtures, ten analysis fixture groups, trajectory orchestration and
complete/missing/preselection-failure reports passed. Six final fixture figures
were inspected. Independent implementation review binds 18 source files and
37 evidence files. Failed engine/report fixtures and subsequent repairs remain.
Seed inventory examined 13,617 historical text files. Original model seeds 1501/1502
collided with derived RNG identifiers in another role; fresh model/weight seeds
are 140101/140201 for tuning and 150101/150201 for confirmation. No corpus overlap
is inferred from the original cross-PRNG-role collision. Research data seeds,
sample counts, grids, estimands and scientific go/stop rules are unchanged.

The local RTX 3050 engineering benchmark passed: projection 3,160.25 seconds with
25% margin, and 4,097,524,554 bytes (~3.82 GiB) raw-plus-archive storage. Worst-capacity
peak CUDA allocation 150.49 MiB. These are fixture estimates, not research results.

### Recorded stop at the preparation limit

The independent review recorded 290.557594982 seconds of prior accounted preparation,
including a disclosed 60-second conservative allowance for uninstrumented fixture
and import/launch time. The allowance is not a measured duration or proved bound.
The subsequent freeze command exceeded the cumulative 300-second cap and stopped.
Exact freeze-process elapsed was not saved; the event-to-failure interval excludes
startup and must not be substituted for it. Do not claim the old cap was met.

Failed attempt: `work/runs/rule-tying-v012-20260930-01/`. Source copies, generated
data/assignments and INPUT_MANIFEST are preserved with PREPARATION_FAILURE.json.
FREEZE.json, RUN_STARTED.json, research baselines and training runs are absent.
Independent failure review checks these facts and the saved input/source hashes.
No research training, selection, confirmation or new empirical outcome occurred.

### Next narrowly scoped preparation task

Read `outputs/sequence-weighting-stage11/preparation-revision-v2/PROPOSED_FREEZE_PROTOCOL.md`.
It proposes new versioned preparation source and a unique run with a separate,
explicit 60-second freeze-process allowance. All old preparation costs and failures
remain recorded; the revision must be implemented and independently reviewed
before use. The proposal review additionally requires a separate finite allowance
for changed fixtures and rejection of every failed preparation by the launcher.
It must save complete timing on failure and fail closed after final
manifest writes. This proposal has not been executed. Do not resume the failed
directory or silently increase its allowance.

Research training remains bounded at 5,400 seconds, raw-plus-archive at 4 GiB, with
2 GiB free reserve. Seeds, corpus units, validation-only selection and all scientific
criteria remain unchanged. Stage 10 is still the latest completed measured
experiment; no major Jane Street advance or new mechanism finding is claimed.
Preparation report: `outputs/sequence-weighting-stage11/preparation-20260930-01/REPORT.md`.
'@
Write-TaskText (Join-Path $taskRoot 'HANDOFF.md') $taskHandoff
$taskNext=@'
# Current next task — preparation revision after the Stage 11 freeze stop

Stage 11 implementation, fixtures and local resource projection passed independent
review. The freeze attempt then exceeded its cumulative 300-second preparation
cap. **The run is not frozen and research training has not started.**

Read HANDOFF section 20 and:
`outputs/sequence-weighting-stage11/preparation-revision-v2/PROPOSED_FREEZE_PROTOCOL.md`.

Implement the narrow prospective revision in separate versioned source: explicit
60-second freeze-process ceiling, complete UTC/monotonic failure timing, validation
of unchanged fixture dependencies, and failure checks after final writes. Read
the companion INDEPENDENT_REVIEW_PLAN.json for the seven implementation gates,
including a separate bounded allowance for changed fixtures. Obtain
a source-bound independent review before a fresh preparation attempt with a new
run ID. Preserve every prior preparation cost and failure; do not claim the old
300-second cap passed, resume the old directory, or silently increase its budget.

Failed directory: `work/runs/rule-tying-v012-20260930-01/`. It has source/input
records and PREPARATION_FAILURE.json; FREEZE.json and RUN_STARTED.json are absent.
The runner therefore cannot start this directory. No research model was trained.

The proposed preparation change leaves scientific seeds, corpora, model capacities,
epochs, LR grid, F/R selection, estimands and go/stop rules unchanged. The 90-minute
training cap, 4 GiB raw-plus-archive cap and 2 GiB reserve remain. Resource projection
is ~53 minutes and 3.82 GiB; projections do not replace enforced limits.

## Historical continuation points

The following earlier tasks are superseded by the status above.

'@
Write-TaskText (Join-Path $taskRoot 'NEXT_EXPERIMENT.md') ($taskNext+(Read-TaskText (Join-Path $taskRoot 'NEXT_EXPERIMENT.md')))
Write-TaskText (Join-Path $taskRoot 'CODEX_START.md') ("# Current continuation - Stage11 freeze failed before research training`n`n$taskStatus`n`nRead AGENTS.md, HANDOFF section20, NEXT_EXPERIMENT.md, RUNBOOK.md and the Stage1 report. Next task is the explicit preparation revision in its own versioned source, followed by independent review. Do not run or resume the failed directory.`n`n## Historical prompts`n`n"+(Read-TaskText (Join-Path $taskRoot 'CODEX_START.md')))
$taskBook=Read-TaskText (Join-Path $taskRoot 'RUNBOOK.md')
$taskBook=$taskBook.Replace('## Start new research',"## Start new research`n`n### Current: Stage11 freeze stopped; preparation revision pending`n`n$taskStatus`nSee NEXT_EXPERIMENT.md for the narrow proposed preparation revision. Do not launch the failed directory. Training/storage scientific limits remain unchanged. Older entries below are historical.`n")
Write-TaskText (Join-Path $taskRoot 'RUNBOOK.md') $taskBook
$taskState=Get-Content -Raw -Encoding UTF8 (Join-Path $taskRoot 'RESEARCH_STATE.json')|ConvertFrom-Json
$taskState.next='implement and independently review proposed Stage11 preparation revision before a new freeze attempt'
$taskState.next_status='v1 preparation cap failed; v2 proposal not implemented or executed; research training not started'
$taskState.next_protocol_draft='outputs/sequence-weighting-stage11/preparation-revision-v2/PROPOSED_FREEZE_PROTOCOL.md'
$taskState.next_protocol_status='revision_proposed_after_preparation_failure'
$taskState.updated_utc=[DateTime]::UtcNow.ToString('o')
$taskState|Add-Member -NotePropertyName stage11_status -NotePropertyValue 'implementation_reviewed_preparation_failed_not_frozen_not_trained' -Force
$taskState|Add-Member -NotePropertyName stage11_preparation_record -NotePropertyValue 'outputs/sequence-weighting-stage11/preparation-20260930-01/COMPLETION.json' -Force
$taskState|Add-Member -NotePropertyName failed_preparation_run -NotePropertyValue 'rule-tying-v012-20260930-01' -Force
Write-TaskJson (Join-Path $taskRoot 'RESEARCH_STATE.json') $taskState
Write-TaskText (Join-Path $taskRoot 'RESEARCH_GOAL.md') ((Read-TaskText (Join-Path $taskRoot 'RESEARCH_GOAL.md'))+"`n`n## Operational status after Stage11 implementation`n`nImplementation and engineering checks passed. Freeze preparation exceeded its cumulative300second cap, so the failed attempt is preserved and no research training started. The next task is the narrow proposed preparation revision linked by NEXT_EXPERIMENT.md. The prior writing-tool goal is complete; the empirical mechanism remains unresolved.`n")
$taskReport=@'
# Stage 11 preparation outcome

**Implementation reviewed; freeze failed; research training not started.**

Completed: versioned runner/analysis/reporting, data and U-loss-gradient fixtures,
ten analysis fixture groups, orchestration checks, missing/partial failure reporting,
six final fixture figures, historical seed inventory and independent review.

| Engineering estimate | Value | Limit |
| --- | ---: | ---: |
| Whole research training time, including 25% margin | 3,160.25 s (~52.7 min) | 5,400 s |
| Raw plus reserved compact archive | 4,097,524,554 bytes (~3.82 GiB) | 4 GiB |
| Worst-capacity peak CUDA allocated | 150.49 MiB | existing local GPU |

These are fixture measurements/projections, not research outcomes. The original
proposal's seeds were revised before research results to avoid recorded cross-role
RNG identifier collisions. Corpus counts, scientific comparisons and criteria
were preserved. Engine/report fixture failures and exact repairs remain recorded.

The final freeze exceeded the 300-second cumulative preparation cap after prior
accounting of 290.557594982 s (including a disclosed 60 s timing allowance). Exact
freeze elapsed is unavailable; the failure guard establishes the cap was exceeded.
The attempt did not write FREEZE or RUN_STARTED and generated no research model.
Source/input files remain in work/runs/rule-tying-v012-20260930-01.

Next: implement and independently review preparation-revision-v2's prospective
separate 60-second freeze process, preserving all past costs and failure evidence.
The companion proposal review specifies additional implementation gates and a
separate bounded fixture allowance; it does not approve execution.
The revision is not implemented or executed. The 90-minute training and 4 GiB storage limits
remain unchanged. This outcome does not establish a new mechanism, useful weight
intervention or major advance over Jane Street.
'@
Write-TaskText (Join-Path $taskPackage 'REPORT.md') $taskReport
$taskFiles=@(Get-ChildItem -LiteralPath $taskStage -File|Where-Object {$_.Extension -in @('.py','.md','.json')}|ForEach-Object {Bind-TaskFile $_.FullName})
$taskFiles+=@(foreach($name in $taskRoots){Bind-TaskFile (Join-Path $taskRoot $name)})
$taskFiles+=@(Bind-TaskFile (Join-Path $taskRun 'PREPARATION_FAILURE.json');Bind-TaskFile (Join-Path $taskRun 'INPUT_MANIFEST.json');Bind-TaskFile (Join-Path $taskPackage 'REPORT.md');Bind-TaskFile (Join-Path $taskStage 'preparation-revision-v2/PROPOSED_FREEZE_PROTOCOL.md'))
$taskFiles+=@(Bind-TaskFile (Join-Path $taskStage 'preparation-revision-v2/INDEPENDENT_REVIEW_PLAN.json');Bind-TaskFile $PSCommandPath)
$taskFiles+=@(Get-ChildItem -LiteralPath (Join-Path $taskPackage 'context_before') -File|ForEach-Object {Bind-TaskFile $_.FullName})
Write-TaskJson (Join-Path $taskPackage 'MANIFEST.json') ([ordered]@{created_utc=[DateTime]::UtcNow.ToString('o');files=$taskFiles;scope='Implementation/preparation and context; input/source bindings separately audited in the failed run manifest'})
Write-TaskJson (Join-Path $taskPackage 'COMPLETION.json') ([ordered]@{status='implementation_reviewed_preparation_failed_no_research_training';recorded_utc=[DateTime]::UtcNow.ToString('o');failed_run_id='rule-tying-v012-20260930-01';failure=(Bind-TaskFile (Join-Path $taskRun 'PREPARATION_FAILURE.json'));manifest=(Bind-TaskFile (Join-Path $taskPackage 'MANIFEST.json'));research_training_started=$false;research_outcomes_generated=$false;freeze_completed=$false;next_revision_implemented=$false;interpretation='Honest preparation stop at existing cap; no empirical result'})
'Recorded Stage11 preparation failure and consistent next-task handoff'
