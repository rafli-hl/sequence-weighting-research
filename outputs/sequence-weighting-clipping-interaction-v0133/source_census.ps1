$ErrorActionPreference = 'Stop'
$repoRoot = 'D:\codex\sequence-weighting-research'
$stageRoot = Join-Path $PSScriptRoot 'bundle'
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
$candidateSeeds = @(91420101,91420102,91420103,91420104,91420105,91430101,91430102,91430103,91430104,91430105,91440101,91440151,91440201,91440251,91440301,91440351,91440401,91440451,91440501,91440551)
$derivedSeeds = @($candidateSeeds[0..9] | ForEach-Object { $_ + 77 })
$derivedSeeds += @($candidateSeeds[10..19] | ForEach-Object { $modelSeed = $_; 1..10 | ForEach-Object { $modelSeed + 999 + $_ } })
$pattern = '(?<![0-9])(?:' + (($candidateSeeds+$derivedSeeds | Sort-Object -Unique) -join '|') + ')(?![0-9])'
$matcher = [regex]::new($pattern,[System.Text.RegularExpressions.RegexOptions]::Compiled)
$extensions = @('.json','.jsonl','.py','.md','.txt','.csv','.ps1','.sh')
$scanRoots = @((Join-Path $repoRoot 'outputs'),(Join-Path $repoRoot 'work\runs'),(Join-Path $repoRoot 'context'),(Join-Path $repoRoot 'migration'))
$historicalFiles = @($scanRoots | ForEach-Object { Get-ChildItem -LiteralPath $_ -Recurse -Force -File } | Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() })
$historicalFiles += @(Get-ChildItem -LiteralPath $repoRoot -File -Force | Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() })
$historicalFiles += @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'work') -File -Force | Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() })
$records = [System.Collections.Generic.List[object]]::new()
$hits = [System.Collections.Generic.List[object]]::new()
foreach ($historicalFile in ($historicalFiles | Sort-Object FullName -Unique)) {
    $contents = [System.IO.File]::ReadAllText($historicalFile.FullName)
    foreach ($match in $matcher.Matches($contents)) {
        $hits.Add(@{ path=$historicalFile.FullName; candidate=[long]$match.Value })
    }
    $records.Add(@{ path=$historicalFile.FullName.Substring($repoRoot.Length+1).Replace('\','/'); bytes=$historicalFile.Length; sha256=(Get-FileHash -LiteralPath $historicalFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant() })
}
if ($hits.Count -gt 0) { throw ('Candidate historical matches: ' + ($hits | ConvertTo-Json -Compress)) }
$result = [ordered]@{
    status='CANDIDATE_ABSENCE_IN_READABLE_HISTORICAL_TEXT'; utc=[DateTime]::UtcNow.ToString('o');
    candidates=$candidateSeeds; derived_candidates=$derivedSeeds; file_count=$records.Count; candidate_matches=@();
    method='Conservative exact decimal numeric-token absence scan, Windows read-only. Does not execute code, decode binary tensors, or prove absence of undocumented/dynamic seeds.';
    exclusions='Binary datasets/checkpoints, virtual environment, wheels, text assets, .git; no missing readable files accepted.';
    records=$records
}
[System.IO.File]::WriteAllText((Join-Path $stageRoot 'SEED_CENSUS.json'),($result | ConvertTo-Json -Depth 6),[System.Text.UTF8Encoding]::new($false))
foreach ($name in @('core.py','model.py','engine.py')) {
    $vendorRoot = Join-Path $stageRoot 'vendor'
    New-Item -ItemType Directory -Path $vendorRoot -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repoRoot ('outputs\sequence-weighting-stage11-v0128\'+$name)) -Destination (Join-Path $vendorRoot $name)
}
$anchorPaths = @('AGENTS.md','HANDOFF.md','NEXT_EXPERIMENT.md','RUNBOOK.md','outputs/sequence-weighting-stage11-v0128/config.py','outputs/sequence-weighting-stage11-v0128/stage11.py','outputs/sequence-weighting-weighting-contrast-v0131/results-fixed-policy-v0131-20261003-01/SYNTHESIS_AND_DECISION.md','outputs/sequence-weighting-pilot/results-mechanism-v02/REPORT.md')
$anchors = @($anchorPaths | ForEach-Object { @{ path=$_; sha256=(Get-FileHash -LiteralPath (Join-Path $repoRoot $_) -Algorithm SHA256).Hash.ToLowerInvariant() } })
[System.IO.File]::WriteAllText((Join-Path $stageRoot 'BACKGROUND_ANCHORS.json'),($anchors | ConvertTo-Json -Depth 3),[System.Text.UTF8Encoding]::new($false))
Write-Output ('Inventory files: '+$records.Count+'; no candidate matches; vendor copies prepared.')
