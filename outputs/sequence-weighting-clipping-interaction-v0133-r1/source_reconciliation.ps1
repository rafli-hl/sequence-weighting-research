$ErrorActionPreference='Stop'
$repoRoot='D:\codex\sequence-weighting-research'
$stageRoot=Join-Path $PSScriptRoot 'bundle'
$census=Get-Content -LiteralPath (Join-Path $stageRoot 'SEED_CENSUS.json') -Raw | ConvertFrom-Json
$ledger=Get-Content -LiteralPath (Join-Path $repoRoot 'outputs\sequence-weighting-stage11\SEED_INVENTORY-20260930-r1.json') -Raw | ConvertFrom-Json
if(@($ledger.omissions).Count -gt 0) { throw 'Prior semantic inventory has omissions' }
$historicalSet=[System.Collections.Generic.HashSet[long]]::new()
foreach($row in $ledger.seed_records) { [void]$historicalSet.Add([long]$row.value) }
foreach($row in $ledger.derived_streams) { foreach($value in $row.values) { [void]$historicalSet.Add([long]$value) } }
$v0128=Get-Content -LiteralPath (Join-Path $repoRoot 'work\runs\rule-tying-v0128-20261001-01\design.json') -Raw | ConvertFrom-Json
foreach($row in @($v0128.tuning)+@($v0128.confirmation)) {
    foreach($value in $row) { [void]$historicalSet.Add([long]$value) }
    [void]$historicalSet.Add([long]$row[0]+77); [void]$historicalSet.Add([long]$row[2]+77)
    foreach($epoch in 1..30) { [void]$historicalSet.Add([long]$row[1]+999+$epoch) }
}
$v0132=Get-Content -LiteralPath (Join-Path $repoRoot 'work\runs\factorial-v0132-20261004-01\DESIGN_FREEZE.json') -Raw | ConvertFrom-Json
foreach($value in @($v0132.corpus_seeds)+@($v0132.pretraining_seeds)) { [void]$historicalSet.Add([long]$value); [void]$historicalSet.Add([long]$value+77) }
foreach($row in $v0132.model_weight_seeds) { foreach($value in $row) { [void]$historicalSet.Add([long]$value); foreach($epoch in 1..10) { [void]$historicalSet.Add([long]$value+999+$epoch) } } }
$collisions=@(@($census.candidates)+@($census.derived_candidates) | Where-Object { $historicalSet.Contains([long]$_) })
if($collisions.Count -gt 0) { throw ('Historical semantic seed collisions: '+($collisions -join ',')) }
$expressionForms=@($ledger.nonliteral_rng_expressions | ForEach-Object { $_.expression } | Sort-Object -Unique)
$anchors=@('outputs\sequence-weighting-stage11\SEED_INVENTORY-20260930-r1.json','work\runs\rule-tying-v0128-20261001-01\design.json','work\runs\factorial-v0132-20261004-01\DESIGN_FREEZE.json','outputs\sequence-weighting-factorial-v0132\reviews\SOURCE_REVIEW.json','outputs\sequence-weighting-factorial-v0132\SOURCE_MANIFEST.json','outputs\sequence-weighting-clipping-interaction-v0133-planning\PROPOSED_PROTOCOL.md') | ForEach-Object { @{path=$_.Replace('\','/');sha256=(Get-FileHash -LiteralPath (Join-Path $repoRoot $_) -Algorithm SHA256).Hash.ToLowerInvariant()} }
$result=[ordered]@{
    status='SOURCE_CANDIDATES_CLEAR_REQUIRES_INDEPENDENT_SEMANTIC_REVIEW';utc=[DateTime]::UtcNow.ToString('o');
    candidates=$census.candidates;derived_candidates=$census.derived_candidates;collisions=@();
    census_file_count=$census.file_count;census_sha256=(Get-FileHash -LiteralPath (Join-Path $stageRoot 'SEED_CENSUS.json') -Algorithm SHA256).Hash.ToLowerInvariant();
    prior_inventory_seed_records=@($ledger.seed_records).Count;prior_inventory_derived_streams=@($ledger.derived_streams).Count;prior_nonliteral_expressions=@($ledger.nonliteral_rng_expressions).Count;
    historical_semantic_seed_values=$historicalSet.Count;expression_forms=$expressionForms;anchors=@($anchors);
    reconciliation=@(
        'Prior inventory COLLISIONS concerns a rejected earlier proposal, not these selected v0133 identities. Saved seed records and all derived stream values were used; no omissions accepted.',
        'Saved v0128 tuning/confirmation triples were added with data+77 and model order/weight offsets for its full thirty-epoch plan, including four-epoch pretraining. v0130 reuses those corpora; v0131 produces no new corpora.',
        'Actual v0132 DESIGN_FREEZE identities were added with all fresh corpus/model identities and derived streams. The completed v0132 semantic source review is a bound historical anchor, not acceptance of v0133.',
        'The forty-three prior nonliteral expressions reduce to saved seed identities or +77, +1000 and +999+epoch derivations. Simulation weight/noise identities are covered by structured prior records. Frozen current source retains these documented derivations.',
        'Current historical numeric absence corroborates the semantic ledger; it is not used alone as semantic proof.',
        'Fixed namespace-pool seed 991 is intentionally shared. Within-pair Python weight and Torch first-order seed integers coincide in different PRNGs. Nested seeds differ by fifty so ten-epoch order ranges do not overlap.'
    );
    limitations=@('Unrecorded/deleted seeds and undocumented dynamic generation cannot be excluded. Binary archives/tensors were not decoded; expanded metadata and frozen source were inspected.','Independent review must confirm semantic coverage and accept this reconciliation. Numerical full-tensor equality/regeneration remain pending; no historical source executed.');
    no_python_tests_wsl_data_or_training=$true
}
[System.IO.File]::WriteAllText((Join-Path $stageRoot 'FRESHNESS_RECONCILIATION.json'),($result | ConvertTo-Json -Depth 7),[System.Text.UTF8Encoding]::new($false))
Write-Output ('Semantic historical values: '+$historicalSet.Count+'; collisions: '+$collisions.Count+'; census: '+$census.file_count)
$expressionForms | ConvertTo-Json
