param([Parameter(Mandatory=$true)][string]$ExpectedSubject)
# One-use owner entry for a run of the matched-progress confirmation (N7; owner instruction of 4 Nov 2026): Run M1 (m01-m03) or Run M2
# (m04-m06), from the activation's AUTHORIZATION.json mode. Derived from the peak confirmation's owner script,
# with its power gate and power log (power_gate.ps1): before its claim it refuses to start on battery; before every stage
# its check covers the GPU and AC power; while the worker runs it logs the power source and plan every 5 s to
# POWER_LOG.jsonl. Runs only from its activation. Before its claim it checks the activation (a real approval id, fixture
# false), every source file, the bound records of its mode, the corpus manifest, every corpus file and the tokenizer, the
# free space and the Windows nvidia-smi pre-start check (gpu_check.ps1); a refusal claims nothing. While the worker runs, it
# answers the worker's check request before every stage and writes nothing to the console; progress goes to
# OWNER_PROGRESS.log in the activation folder.
$originQpc=[Diagnostics.Stopwatch]::GetTimestamp();$frequency=[Diagnostics.Stopwatch]::Frequency
$ErrorActionPreference='Stop'
function Owner-Elapsed { return ([Diagnostics.Stopwatch]::GetTimestamp()-$originQpc)/[double]$frequency }
$root=$PSScriptRoot
$modes=@{
    'M1'=@{activation='D:\sequence-weighting-research\work\natural-text-matched-activation-m1-20261104-01';out='D:\sequence-weighting-research\work\runs\natural-text-matched-m1-20261104-01';stages=@('m01','m02','m03');records=@();hours='about 2.6'};
    'M2'=@{activation='D:\sequence-weighting-research\work\natural-text-matched-activation-m2-20261104-01';out='D:\sequence-weighting-research\work\runs\natural-text-matched-m2-20261104-01';stages=@('m04','m05','m06');records=@(,@('RUN_M1_TERMINAL.json','run_m1_terminal_sha256'));hours='about 2.6'}
}
$corpus='D:\sequence-weighting-research\work\runs\natural-text-corpus-wt103-20261101-01'
$auth=Get-Content -LiteralPath (Join-Path $root 'AUTHORIZATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($auth.enabled -ne $true -or $auth.execution_ready -ne $true) {throw 'DISABLED: no matched-progress confirmation approval'}
$mode=[string]$auth.mode
if (-not $modes.ContainsKey($mode)) {throw 'Invalid activation'}
$m=$modes[$mode];$expected=$m.activation;$out=$m.out
if ($root -ne $expected -or $auth.one_use -ne $true -or -not $auth.approval_id -or $auth.fixture -ne $false -or ([string]$auth.approval_id).ToUpperInvariant().StartsWith('FIXTURE')) {throw 'Invalid activation'}
if ($auth.source_subject_sha256 -ne $ExpectedSubject -or (Get-FileHash -LiteralPath (Join-Path $root 'SOURCE_SUBJECT.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedSubject) {throw 'Source pin mismatch'}
foreach($row in (Get-Content -LiteralPath (Join-Path $root 'SOURCE_SUBJECT.json') -Raw -Encoding UTF8 | ConvertFrom-Json).files) {
    $p=Join-Path $root $row.path
    if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256 -or (Get-Item -LiteralPath $p).Length -ne $row.bytes) {throw 'Changed source'}
}
$bound=@(@('REGISTRY.json','registry_sha256'),@('EXCLUSIONS.json','exclusions_sha256'),@('DRAW.json','draw_sha256'),@('PARTITION.json','partition_sha256'),@('FEWEPOCH_REGISTRY.json','fewepoch_registry_sha256'),@('PEAK_REGISTRY.json','peak_registry_sha256'),@('APPROVAL_RECORD.json','approval_record_sha256'))+$m.records
foreach($pair in $bound) {
    $h=$auth.($pair[1])
    if (-not $h -or (Get-FileHash -LiteralPath (Join-Path $root $pair[0]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $h) {throw ('Binding mismatch: '+$pair[0])}
}
# The run's inputs, checked before anything is claimed (the worker checks them again and re-derives the registry and the
# partition): the corpus manifest, every corpus file and the tokenizer.
if (-not $auth.corpus_manifest_sha256 -or (Get-FileHash -LiteralPath (Join-Path $corpus 'CORPUS_MANIFEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $auth.corpus_manifest_sha256) {throw ('Input pin mismatch: '+(Join-Path $corpus 'CORPUS_MANIFEST.json'))}
$manifest=Get-Content -LiteralPath (Join-Path $corpus 'CORPUS_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach($split in @('train','validation','test')) {
    $f=$manifest.splits.$split;$p=Join-Path $corpus $f.file
    if ((Get-Item -LiteralPath $p).Length -ne $f.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $f.sha256) {throw ('Corpus file differs from its manifest: '+$split)}
}
if ((Get-FileHash -LiteralPath (Join-Path $corpus 'tokenizer.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.tokenizer.sha256) {throw 'Tokenizer differs from its manifest'}
$claim=Join-Path $root 'OWNER_CLAIM.json';$receipt=Join-Path $root 'OWNER_EXIT_RECEIPT.json';$gateDir=Join-Path $root 'gpu-checks'
if ((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $claim) -or (Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath (Join-Path $gateDir 'PRESTART.json'))) {throw 'One-use attempt consumed; no retry'}
if ((Get-PSDrive D).Free -lt 3GB) {throw 'Admission requires at least 3 GiB free on D:'}
. (Join-Path $root 'gpu_check.ps1')
. (Join-Path $root 'power_gate.ps1')
$gpu=Read-GpuConfig (Join-Path $root 'GPU_CHECK.json');$smi=[string]$gpu.nvidia_smi
if (-not (Test-Path -LiteralPath $smi)) {throw ('nvidia-smi not found at '+$smi+'; nothing was claimed or started')}
$pre=Invoke-GpuCheck $gpu 'prestart' $smi @()
$power=Get-PowerSample
if ($pre.verdict -ne 'IDLE' -or $power.power -ne 'AC') {
    $k=1;while(Test-Path -LiteralPath (Join-Path $gateDir ('PRESTART-REFUSED-'+$k+'.json'))){$k++}
    Write-GateRecord $gateDir ('PRESTART-REFUSED-'+$k+'.json') ([ordered]@{schema=1;stage='PRESTART';verdict='REFUSED';checks=@($pre);power=$power})
    if ($power.power -ne 'AC') {throw ('Not on AC power before start ('+(Format-PowerSample $power)+'). Nothing was claimed or started. Plug in the charger, keep the lid open, then run the same command again.')}
    throw ('GPU not idle before start ('+(Format-GpuCheck $pre)+'). Nothing was claimed or started. If BUSY: close games and other GPU apps; if UNVERIFIED: nvidia-smi failed, check that it runs. Then run the same command again.')
}
$progress=Join-Path $root 'OWNER_PROGRESS.log'
Write-Host ('GPU check before start: '+(Format-GpuCheck $pre)+'; '+(Format-PowerSample $power))
Write-Host ('Starting Run '+$mode+' ('+$m.hours+' hours; at most 6). Until the run ends nothing more is printed here; progress, including every GPU check, goes to '+$progress+'. Do not close this window or press Ctrl+C.')
[IO.File]::WriteAllText($claim,(@{origin_qpc=$originQpc;qpc_frequency=$frequency;subject=$ExpectedSubject;approval_id=$auth.approval_id;mode=$mode;one_use=$true}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-GateRecord $gateDir 'PRESTART.json' ([ordered]@{schema=1;stage='PRESTART';verdict='IDLE';checks=@($pre);power=$power})
$powerLog=Join-Path $root 'POWER_LOG.jsonl'
$wslRoot='/mnt/d/sequence-weighting-research/'+(($expected.Substring('D:\sequence-weighting-research\'.Length)) -replace '\\','/')
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName='wsl.exe'
$info.Arguments=('-d Ubuntu --exec /mnt/d/sequence-weighting-research/work/.venv-wsl/bin/python -I -B '+$wslRoot+'/matched_worker.py run')
$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$proc=[Diagnostics.Process]::new();$proc.StartInfo=$info
if(-not $proc.Start()){throw 'WSL client did not start'}
$stdoutTask=$proc.StandardOutput.ReadToEndAsync();$stderrTask=$proc.StandardError.ReadToEndAsync()
# Overall 21,600 s worker deadline plus 300 s for its own terminal publication. No kill on timeout. Checks before each stage.
$draws=[string[]]$m.stages
$wait=Wait-WorkerWithPowerGates $proc $out $root $gpu $smi @() 21900 {Owner-Elapsed} $draws $progress $powerLog 5
$observed=$wait.observed
$rc=$null;if($observed){$proc.WaitForExit();$rc=$proc.ExitCode}
$cap=65536
$stdout=if($stdoutTask.Wait(5000)){$stdoutTask.Result}else{'<stdout incomplete>'};$stderr=if($stderrTask.Wait(5000)){$stderrTask.Result}else{'<stderr incomplete>'}
if($stdout.Length -gt $cap){$stdout=$stdout.Substring($stdout.Length-$cap)};if($stderr.Length -gt $cap){$stderr=$stderr.Substring($stderr.Length-$cap)}
[IO.File]::WriteAllText((Join-Path $root 'WORKER_STDOUT.log'),$stdout,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $root 'WORKER_STDERR.log'),$stderr,[Text.UTF8Encoding]::new($false))
$terminalPath=Join-Path $out 'TERMINAL.json';$terminal=$null;$terminalHash=$null;$terminalUnreadable=$false
if(Test-Path -LiteralPath $terminalPath){
    try{$terminalHash=(Get-FileHash -LiteralPath $terminalPath -Algorithm SHA256).Hash.ToLowerInvariant()}catch{$terminalHash=$null;$terminalUnreadable=$true}
    try{$terminal=Get-Content -LiteralPath $terminalPath -Raw -Encoding UTF8|ConvertFrom-Json}catch{$terminal=$null;$terminalUnreadable=$true}
    if($terminal -isnot [System.Management.Automation.PSCustomObject]){$terminal=$null;$terminalUnreadable=$true}
}
$status=if($observed -and $rc -eq 0 -and $terminal.status -eq 'COMPLETE'){'COMPLETE'}elseif($observed -and $terminal.status -eq 'STOPPED_AT_STARTUP'){'STOPPED_AT_STARTUP'}elseif(-not $observed){'EXIT_UNOBSERVED_NO_KILL'}else{'FAILED'}
$gpuStop=($null -ne $terminal -and $null -ne $terminal.error -and $terminal.error.type -eq 'GpuBusyError')
$powerStop=($null -ne $terminal -and $null -ne $terminal.error -and $terminal.error.type -eq 'PowerGateError')
$stageFolders=@($draws | Where-Object { Test-Path -LiteralPath (Join-Path $out $_) -PathType Container })
$powerLogHash=if(Test-Path -LiteralPath $powerLog){(Get-FileHash -LiteralPath $powerLog -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null}
$gateFiles=@(Get-ChildItem -LiteralPath $gateDir -File | Sort-Object Name | ForEach-Object {[ordered]@{name=$_.Name;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}})
$value=[ordered]@{status=$status;mode=$mode;subject=$ExpectedSubject;exit_observed=$observed;exit_code=$rc;elapsed_seconds=(Owner-Elapsed);terminal_status=$terminal.status;terminal_sha256=$terminalHash;terminal_unreadable=$terminalUnreadable;
                 terminal_outside_ledger=($null -ne $terminal -and $null -ne $terminal.terminal_outside_ledger);
                 startup_decision=$terminal.startup.decision;startup_reason=$terminal.startup.reason;stop_reason=$(if($powerStop){'POWER_NOT_AC_30_MIN'}elseif($gpuStop){'GPU_NOT_IDLE_30_MIN'}else{$terminal.stop_reason});
                 stage_folders=$stageFolders;counted_as_attempt=($stageFolders.Count -gt 0);
                 gpu_prestart=[ordered]@{verdict=$pre.verdict;mean_utilization_percent=$pre.mean_utilization_percent;max_memory_used_mib=$pre.max_memory_used_mib};power_prestart=$power;
                 gpu_gates=$wait.gates;gpu_check_files=$gateFiles;power_during_run=$wait.power;power_log_sha256=$powerLogHash;retry=$false;note='Native exit does not prove Linux process absence. Preserve every directory; do not rerun.'}
[IO.File]::WriteAllText($receipt,($value|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$value|ConvertTo-Json -Depth 6
if(@($wait.power.changes).Count -gt 0 -or $wait.power.off_ac_samples -gt 0){Write-Output ('Note: the power changed during the run ('+$wait.power.off_ac_samples+' of '+$wait.power.samples+' readings off AC; see POWER_LOG.jsonl).')}
if($value.terminal_outside_ledger){Write-Output 'Note: TERMINAL.json was written outside the output ledger (terminal_outside_ledger); report it with the result.'}
$counted=if($stageFolders.Count -gt 0){' A stage folder exists, so under the counting rule this run was the only attempt of its stages: no retry or replacement draw. PROTOCOL.md section 12 says what is read next.'}else{' No stage folder exists, so under the counting rule this stop is not counted as the attempt; the next step is an owner decision.'}
if($status -eq 'STOPPED_AT_STARTUP'){throw ('STOPPED before any training: '+$terminal.stop_reason+'. Nothing was trained. Preserve every folder; no retry.'+$counted)}
elseif($powerStop -or $gpuStop){throw ('STOPPED: '+$terminal.error.message+'. Preserve every folder; no retry.'+$counted)}
elseif($status -ne 'COMPLETE'){throw ('Matched-progress Run '+$mode+' failed or incomplete; preserve evidence, no retry.'+$counted)}
Write-Output ('Start-up: '+$terminal.startup.decision+' ('+$terminal.startup.reason+'); Run '+$mode+' COMPLETE.')
