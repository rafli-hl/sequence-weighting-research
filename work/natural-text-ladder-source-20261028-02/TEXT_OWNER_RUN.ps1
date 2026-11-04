param([Parameter(Mandatory=$true)][string]$ExpectedSubject)
# One-use owner entry for the natural-text ladder, revision 05 (Run B, or B1 or B2 after its start-up fallback, from
# AUTHORIZATION.json). Runs only from its activation. Revision 05 (owner ruling of 28 Oct 2026) adds Windows-side GPU
# checks with nvidia-smi (gpu_check.ps1, GPU_CHECK.json): before start, a busy GPU refuses the run before anything is
# claimed; before every draw, a busy GPU is rechecked for up to 30 minutes, then the run stops with a clear status.
$originQpc=[Diagnostics.Stopwatch]::GetTimestamp();$frequency=[Diagnostics.Stopwatch]::Frequency
$ErrorActionPreference='Stop'
function Owner-Elapsed { return ([Diagnostics.Stopwatch]::GetTimestamp()-$originQpc)/[double]$frequency }
$root=$PSScriptRoot
$auth=Get-Content -LiteralPath (Join-Path $root 'AUTHORIZATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($auth.enabled -ne $true -or $auth.execution_ready -ne $true) {throw 'DISABLED: no natural-text ladder approval'}
# Mode A is not run in revision 05: Run A is reused from revision 04.
$paths=@{B=@('D:\sequence-weighting-research\work\natural-text-ladder-activation-b-20261028-02','D:\sequence-weighting-research\work\runs\natural-text-ladder-b-20261028-02','/mnt/d/sequence-weighting-research/work/natural-text-ladder-activation-b-20261028-02');
         B1=@('D:\sequence-weighting-research\work\natural-text-ladder-activation-b1-20261028-02','D:\sequence-weighting-research\work\runs\natural-text-ladder-b1-20261028-02','/mnt/d/sequence-weighting-research/work/natural-text-ladder-activation-b1-20261028-02');
         B2=@('D:\sequence-weighting-research\work\natural-text-ladder-activation-b2-20261028-02','D:\sequence-weighting-research\work\runs\natural-text-ladder-b2-20261028-02','/mnt/d/sequence-weighting-research/work/natural-text-ladder-activation-b2-20261028-02')}
if (-not $paths.ContainsKey([string]$auth.mode)) {throw 'Invalid activation mode'}
$expected=$paths[[string]$auth.mode][0];$out=$paths[[string]$auth.mode][1];$wslRoot=$paths[[string]$auth.mode][2]
if ($root -ne $expected -or $auth.one_use -ne $true -or -not $auth.approval_id) {throw 'Invalid activation'}
if ($auth.source_subject_sha256 -ne $ExpectedSubject -or (Get-FileHash -LiteralPath (Join-Path $root 'SOURCE_SUBJECT.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedSubject) {throw 'Source pin mismatch'}
foreach($row in (Get-Content -LiteralPath (Join-Path $root 'SOURCE_SUBJECT.json') -Raw -Encoding UTF8 | ConvertFrom-Json).files) {
    $p=Join-Path $root $row.path
    if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256 -or (Get-Item -LiteralPath $p).Length -ne $row.bytes) {throw 'Changed source'}
}
$bound=@(@('REGISTRY.json',$auth.registry_sha256),@('EXCLUSIONS.json',$auth.exclusions_sha256),@('DRAW.json',$auth.draw_sha256),@('PARTITION.json',$auth.partition_sha256),@('APPROVAL_RECORD.json',$auth.approval_record_sha256))
if ($auth.mode -ne 'A') {$bound+=,@('LR_SELECTION.json',$auth.lr_selection_sha256)}
foreach($pair in $bound) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $pair[0]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pair[1]) {throw ('Binding mismatch: '+$pair[0])}
}
$claim=Join-Path $root 'OWNER_CLAIM.json';$receipt=Join-Path $root 'OWNER_EXIT_RECEIPT.json';$gateDir=Join-Path $root 'gpu-checks'
if ((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $claim) -or (Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath (Join-Path $gateDir 'PRESTART.json'))) {throw 'One-use attempt consumed; no retry'}
if ((Get-PSDrive D).Free -lt 4GB) {throw 'Admission requires at least 4 GiB free on D:'}
# Revision 05: the GPU check module and its sealed thresholds (both hash-checked above as source files).
. (Join-Path $root 'gpu_check.ps1')
$gpu=Read-GpuConfig (Join-Path $root 'GPU_CHECK.json');$smi=[string]$gpu.nvidia_smi
if (-not (Test-Path -LiteralPath $smi)) {throw ('nvidia-smi not found at '+$smi+'; nothing was claimed or started')}
$pre=Invoke-GpuCheck $gpu 'prestart' $smi @()
if ($pre.verdict -ne 'IDLE') {
    $k=1;while(Test-Path -LiteralPath (Join-Path $gateDir ('PRESTART-REFUSED-'+$k+'.json'))){$k++}
    Write-GateRecord $gateDir ('PRESTART-REFUSED-'+$k+'.json') ([ordered]@{schema=1;stage='PRESTART';verdict='REFUSED';checks=@($pre)})
    throw ('GPU not idle before start ('+(Format-GpuCheck $pre)+'). Nothing was claimed or started. If BUSY: close games and other GPU apps; if UNVERIFIED: nvidia-smi failed, check that it runs. Then run the same command again.')
}
$progress=Join-Path $root 'OWNER_PROGRESS.log'
Write-Host ('GPU check before start: '+(Format-GpuCheck $pre))
Write-Host ('Starting. Until the run ends nothing more is printed here; progress, including every GPU check, goes to '+$progress+'. Do not close this window or press Ctrl+C.')
[IO.File]::WriteAllText($claim,(@{origin_qpc=$originQpc;qpc_frequency=$frequency;subject=$ExpectedSubject;approval_id=$auth.approval_id;mode=$auth.mode;one_use=$true}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-GateRecord $gateDir 'PRESTART.json' ([ordered]@{schema=1;stage='PRESTART';verdict='IDLE';checks=@($pre)})
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName='wsl.exe'
$info.Arguments=('-d Ubuntu --exec /mnt/d/sequence-weighting-research/work/.venv-wsl/bin/python -I -B '+$wslRoot+'/text_worker.py run')
$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$proc=[Diagnostics.Process]::new();$proc.StartInfo=$info
if(-not $proc.Start()){throw 'WSL client did not start'}
$stdoutTask=$proc.StandardOutput.ReadToEndAsync();$stderrTask=$proc.StandardError.ReadToEndAsync()
# Overall 21,600 s worker deadline plus 300 s for its own terminal publication. No kill on timeout. GPU checks before each draw.
$draws=@('d01','d02','d03','d04','d05','d06','d07','d08','d09','d10')
$wait=Wait-WorkerWithGates $proc $out $root $gpu $smi @() 21900 {Owner-Elapsed} $draws $progress
$observed=$wait.observed
$rc=$null;if($observed){$proc.WaitForExit();$rc=$proc.ExitCode}
$cap=65536
$stdout=if($stdoutTask.Wait(5000)){$stdoutTask.Result}else{'<stdout incomplete>'};$stderr=if($stderrTask.Wait(5000)){$stderrTask.Result}else{'<stderr incomplete>'}
if($stdout.Length -gt $cap){$stdout=$stdout.Substring($stdout.Length-$cap)};if($stderr.Length -gt $cap){$stderr=$stderr.Substring($stderr.Length-$cap)}
[IO.File]::WriteAllText((Join-Path $root 'WORKER_STDOUT.log'),$stdout,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $root 'WORKER_STDERR.log'),$stderr,[Text.UTF8Encoding]::new($false))
$terminalPath=Join-Path $out 'TERMINAL.json';$terminal=$null;$terminalHash=$null
if(Test-Path -LiteralPath $terminalPath){$terminal=Get-Content -LiteralPath $terminalPath -Raw -Encoding UTF8|ConvertFrom-Json;$terminalHash=(Get-FileHash -LiteralPath $terminalPath -Algorithm SHA256).Hash.ToLowerInvariant()}
$status=if($observed -and $rc -eq 0 -and $terminal.status -eq 'COMPLETE'){'COMPLETE'}elseif($observed -and $rc -eq 0 -and $auth.mode -eq 'B' -and $terminal.status -eq 'FALLBACK_TO_SPLIT'){'FALLBACK_TO_SPLIT'}elseif(-not $observed){'EXIT_UNOBSERVED_NO_KILL'}else{'FAILED'}
$gpuStop=($null -ne $terminal -and $null -ne $terminal.error -and $terminal.error.type -eq 'GpuBusyError')
$gateFiles=@(Get-ChildItem -LiteralPath $gateDir -File | Sort-Object Name | ForEach-Object {[ordered]@{name=$_.Name;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}})
$value=[ordered]@{status=$status;mode=$auth.mode;subject=$ExpectedSubject;exit_observed=$observed;exit_code=$rc;elapsed_seconds=(Owner-Elapsed);terminal_status=$terminal.status;terminal_sha256=$terminalHash;
                 stop_reason=$(if($gpuStop){'GPU_NOT_IDLE_30_MIN'}else{$null});gpu_prestart=[ordered]@{verdict=$pre.verdict;mean_utilization_percent=$pre.mean_utilization_percent;max_memory_used_mib=$pre.max_memory_used_mib};
                 gpu_gates=$wait.gates;gpu_check_files=$gateFiles;retry=$false;note='Native exit does not prove Linux process absence. Preserve every directory; do not rerun.'}
[IO.File]::WriteAllText($receipt,($value|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$value|ConvertTo-Json -Depth 6
if($status -eq 'FALLBACK_TO_SPLIT'){Write-Output 'Run B stopped before any training: its own benchmark puts ten draws over 6 h and five within it. The pre-registered split B1 and B2 applies; preserve this run, no retry.'}
elseif($gpuStop){throw ('STOPPED: '+$terminal.error.message+'. Under the owner ruling of 28 Oct 2026 this final attempt has failed and the natural-text ladder closes as UNAVAILABLE. Preserve every folder; no retry.')}
elseif($status -ne 'COMPLETE'){throw 'Natural-text ladder run failed or incomplete; preserve evidence, no retry'}
