$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskStage = Join-Path $taskRoot 'outputs/sequence-weighting-stage11'
$taskRunId = 'rule-tying-v012-20260930-01'
$taskRun = Join-Path $taskRoot ('work/runs/' + $taskRunId)
$taskPackage = Join-Path $taskStage 'preparation-20260930-01'
if (Test-Path -LiteralPath $taskPackage) { throw 'Preparation package already exists' }
$taskFreeze = Get-Content -Raw -Encoding UTF8 (Join-Path $taskRun 'FREEZE.json') | ConvertFrom-Json
if ($taskFreeze.status -ne 'frozen_before_research_outcomes') { throw 'Freeze incomplete' }
if (Test-Path -LiteralPath (Join-Path $taskRun 'RUN_STARTED.json')) { throw 'Research already started' }
$taskResource = Get-Content -Raw -Encoding UTF8 (Join-Path $taskStage 'RESOURCE_ACCEPTANCE.json') | ConvertFrom-Json
$taskUtf8 = [System.Text.UTF8Encoding]::new($false)
function Write-TaskText([string]$path,[string]$value) { [System.IO.File]::WriteAllText($path,$value,$taskUtf8) }
function Write-TaskJson([string]$path,$value) { Write-TaskText $path ($value | ConvertTo-Json -Depth 30) }
function Read-TaskText([string]$path) { [System.IO.File]::ReadAllText($path) }
function Bind-TaskFile([string]$path) {
    [ordered]@{path=$path.Substring($taskRoot.Length+1).Replace('\','/');bytes=(Get-Item -LiteralPath $path).Length;sha256=(Get-FileHash -LiteralPath $path).Hash.ToLower()}
}
New-Item -ItemType Directory -Path (Join-Path $taskPackage 'context_before') | Out-Null
$taskRoots=@('HANDOFF.md','NEXT_EXPERIMENT.md','RUNBOOK.md','CODEX_START.md','RESEARCH_STATE.json','RESEARCH_GOAL.md')
foreach($name in $taskRoots) { Copy-Item -LiteralPath (Join-Path $taskRoot $name) -Destination (Join-Path $taskPackage ('context_before/'+$name)) }
$taskNow=[DateTime]::UtcNow.ToString('o')
$taskStatus='Stage 11 v0.12 implementation and preparation are complete. Run rule-tying-v012-20260930-01 is frozen before research outcomes; research training has not started. See HANDOFF section 20.'
$taskHandoff=Read-TaskText (Join-Path $taskRoot 'HANDOFF.md')
$taskHandoff=[regex]::Replace($taskHandoff,'\*\*Latest continuation status:\*\*[^\r\n]+',('**Latest continuation status:** '+$taskStatus),1)
$taskHandoff += @'


## 20. Stage 11 implementation prepared and frozen — 30 September 2026

The reviewed G1/G16 experiment now has new v0.12 data/training, validation-only
selection, analysis, reporting, fixtures and resource guards under
`outputs/sequence-weighting-stage11/`. No historical source or measured outcome
was replaced. `core.py` and `model.py` are exact Stage 6 copies; derived functions
and the reviewed proposal have parent hashes in `PARENT_SOURCES.json`.

Run `rule-tying-v012-20260930-01` has a source/input/environment freeze in
`work/runs/rule-tying-v012-20260930-01/FREEZE.json`. There is no RUN_STARTED record,
pretrained research model or research outcome. Only unrelated engineering
fixtures, synthetic metric checks and a local GPU resource benchmark were run.

Seed inventory checked 13,617 historical text files. Original proposed seeds
1501/1502 had cross-role derived-RNG identifier collisions; revision 1 uses
tuning model seeds 140101/140201 and confirmation seeds 150101/150201. This is
not a claim that prior corpora overlapped. Data/pretraining seeds and all
scientific outcomes, grids, counting units and go/stop criteria remain as designed.

Data/loss-gradient/guard fixtures, ten analysis-fixture groups, runner integration,
complete/missing/preselection-failure reports and six final fixture figures passed.
Independent implementation review binds the final sources, evidence and the
clock-only runner correction. Two failed fixtures and every intervening version
remain preserved. Preparation timing includes a disclosed conservative allowance
for uninstrumented launch/fixture time; see PREPARATION_ATTEMPTS and FREEZE.

Resource projection: 3,160.25 seconds (~52.7 minutes), including a 25% multiplier;
raw plus reserved compact archive 4,097,524,554 bytes (~3.82 GiB), below 4 GiB.
Worst-capacity peak CUDA allocated memory was 150.49 MiB. These are estimates
from fixtures, not model research results. Enforce the 5,400-second whole-training
ceiling, 4 GiB storage bound and 2 GiB free-space reserve during execution.

Next: launch the existing frozen run locally with `stage11.py run --run-id
rule-tying-v012-20260930-01`, then audit selection, actual full data/weight/order
pairing, saved gains and retained model binaries, report every failed/undefined
outcome, verify the compact archive and visually review real-result figures.
Do not create a duplicate run, change frozen top-level source, or resume silently.
Later independent audit code must use a separate versioned subdirectory so it
does not alter the frozen source manifest. No cloud, upload or publication.

The experiment has not answered its scientific question yet. Stage 10 remains
the latest completed measured experiment. Preparation package:
`outputs/sequence-weighting-stage11/preparation-20260930-01/REPORT.md`.
'@
Write-TaskText (Join-Path $taskRoot 'HANDOFF.md') $taskHandoff
$taskNext=@'
# Current next task — execute the frozen Stage 11 run

Stage 11 implementation/readiness is complete, independently reviewed and frozen.
Read HANDOFF section 20 and `outputs/sequence-weighting-stage11/PROTOCOL_STAGE11.md`.
Frozen run: `work/runs/rule-tying-v012-20260930-01/`. Research training has not begun.

From PowerShell in this D: project:

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage11/stage11.py run --run-id rule-tying-v012-20260930-01
```

The runner verifies source/input/environment bindings, then performs tuning,
freezes validation-only selections and confirmation schedule, and confirms the
matched F and selected R policies. No p*, fit or test score selects a model.
There are 72 tuning trajectories and 120–240 confirmation trajectories, with
36 shared U pretrained models. All confirm trajectories reach epoch 30.

Enforce 90 minutes for the complete training stage and 4 GiB raw plus compact
archive, with a 2 GiB free reserve. The fixture projection is ~53 minutes and
3.82 GiB; it is not a guarantee. Failures stop execution and retain partial rows.
Audit and report all results afterward; preserve every earlier stage and guard.
No silent resume, source edit, duplicate run or automatic expansion.

## Historical continuation points

Everything below records earlier tasks, superseded by the current next task.

'@
Write-TaskText (Join-Path $taskRoot 'NEXT_EXPERIMENT.md') ($taskNext+(Read-TaskText (Join-Path $taskRoot 'NEXT_EXPERIMENT.md')))
$taskStart="# Current continuation point - Stage 11 frozen, research not run`n`n$taskStatus`n`nRead AGENTS.md, HANDOFF.md section 20, NEXT_EXPERIMENT.md, RUNBOOK.md and the Stage 1 report. The next task is the frozen local Stage 11 run, then full independent audit and reporting. Preserve all historical results and use the existing WSL Python/GPU. Do not edit frozen top-level Stage 11 source or restart old experiments.`n`n## Historical continuation prompts`n`n"
Write-TaskText (Join-Path $taskRoot 'CODEX_START.md') ($taskStart+(Read-TaskText (Join-Path $taskRoot 'CODEX_START.md')))
$taskRunbook=Read-TaskText (Join-Path $taskRoot 'RUNBOOK.md')
$taskRunbook=$taskRunbook.Replace('## Start new research',"## Start new research`n`n### Current: Stage 11 frozen; next task is local execution`n`n$taskStatus`nUse the exact launch command in NEXT_EXPERIMENT.md. Resource projection: ~53 minutes and 3.82 GiB; enforce 90 minutes /4 GiB plus2 GiB free reserve. No research training has begun. The older continuation entries below are historical.`n")
Write-TaskText (Join-Path $taskRoot 'RUNBOOK.md') $taskRunbook
$taskState=Get-Content -Raw -Encoding UTF8 (Join-Path $taskRoot 'RESEARCH_STATE.json')|ConvertFrom-Json
$taskState.completed += 'stage11-v012-implementation-readiness'
$taskState.next='execute frozen Stage11 rule-tying-v012-20260930-01 locally, then independently audit and report'
$taskState.next_status='source/input/environment frozen; research training not started'
$taskState.latest_completed_milestone='stage11-v012-implementation-readiness'
$taskState.latest_milestone_completion='outputs/sequence-weighting-stage11/preparation-20260930-01/COMPLETION.json'
$taskState.next_protocol_draft='outputs/sequence-weighting-stage11/PROTOCOL_STAGE11.md'
$taskState.next_protocol_status='implemented_reviewed_frozen_not_executed'
$taskState.updated_utc=$taskNow
$taskState|Add-Member -NotePropertyName prepared_run_id -NotePropertyValue $taskRunId -Force
$taskState|Add-Member -NotePropertyName prepared_freeze -NotePropertyValue 'work/runs/rule-tying-v012-20260930-01/FREEZE.json' -Force
Write-TaskJson (Join-Path $taskRoot 'RESEARCH_STATE.json') $taskState
$taskGoal=Read-TaskText (Join-Path $taskRoot 'RESEARCH_GOAL.md')
$taskGoal += "`n`n## Operational continuation after implementation readiness`n`nStage 11 is now implemented, independently reviewed and frozen before research outcomes. The next task is local execution of rule-tying-v012-20260930-01, followed by independent audit and reporting. The earlier writing-tool goal is complete; this update records research direction without claiming the empirical mechanism is resolved.`n"
Write-TaskText (Join-Path $taskRoot 'RESEARCH_GOAL.md') $taskGoal
$taskReport=@"
# Stage 11 implementation readiness

Completed $taskNow. **Frozen; research training not started.**

- New versioned G1/G16 runner, validation-only policies, component analysis and report code.
- Engine, analysis, orchestration and report fixtures PASS; final six fixture figures reviewed.
- Independent implementation acceptance and source/input/environment freeze recorded.
- Fresh seed revision documented; 13,617 historical text files inventoried.
- Resource estimate: 3,160.25 seconds with25% margin; 4,097,524,554 bytes including archive reserve.
- Combined accounted preparation time at freeze: $($taskFreeze.combined_preparation_seconds) seconds, including the disclosed conservative timing allowance.

The frozen run is work/runs/$taskRunId. No research model checkpoint or outcome
has been generated. Failed fixture attempts, original proposal and every prior
measured result remain preserved. Resource projections are engineering estimates;
runtime guards remain binding. No new empirical advance is claimed.

Next: execute this frozen run locally, independently audit its real results,
retain undefined and failed outcomes, and verify all figures and archive records.
The numerical stages are complete; a fresh generic numerical audit is not the
current scientific task.
"@
Write-TaskText (Join-Path $taskPackage 'REPORT.md') $taskReport
$taskEvidence=@('RESOURCE_ACCEPTANCE.json','RESOURCE_BENCHMARK-r1.json','PREPARATION_ATTEMPTS.json','PARENT_SOURCES.json','CLOCK_DELTA_REVIEW.json','ENGINE_CHECKS-r1.json','ANALYSIS_CHECKS-r2.json','RUNNER_CHECKS-r3.json','INDEPENDENT_SEED_REVIEW-r2.json')
$taskFiles=@(foreach($name in $taskEvidence){Bind-TaskFile (Join-Path $taskStage $name)})
$taskFiles += @(foreach($name in $taskRoots){Bind-TaskFile (Join-Path $taskRoot $name)})
$taskFiles += @(Bind-TaskFile (Join-Path $taskRun 'FREEZE.json');Bind-TaskFile (Join-Path $taskRun 'INPUT_MANIFEST.json');Bind-TaskFile (Join-Path $taskPackage 'REPORT.md'))
$taskFiles += @(Get-ChildItem -LiteralPath (Join-Path $taskPackage 'context_before') -File | ForEach-Object {Bind-TaskFile $_.FullName})
Write-TaskJson (Join-Path $taskPackage 'MANIFEST.json') ([ordered]@{created_utc=$taskNow;files=$taskFiles;source_manifest=$taskFreeze.source_sha256;independent_review=$taskFreeze.review})
Write-TaskJson (Join-Path $taskPackage 'COMPLETION.json') ([ordered]@{status='implementation_prepared_reviewed_frozen_not_executed';completed_utc=$taskNow;run_id=$taskRunId;freeze=(Bind-TaskFile (Join-Path $taskRun 'FREEZE.json'));manifest=(Bind-TaskFile (Join-Path $taskPackage 'MANIFEST.json'));research_training_started=$false;research_outcomes_generated=$false;engineering_fixtures_only=$true;resource_estimate=$taskResource;combined_preparation_seconds=$taskFreeze.combined_preparation_seconds;goal='Prepare the reviewed next experiment while preserving Jane Street alignment and scientific constraints'})
'PASS: readiness handoff and completion records saved'
