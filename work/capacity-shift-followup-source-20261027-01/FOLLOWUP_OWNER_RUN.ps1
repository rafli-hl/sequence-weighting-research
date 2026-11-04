param([Parameter(Mandatory=$true)][string]$ExpectedSubject)
# One-use owner entry for the capacity-shift follow-up. Runs only from its activation; never from the source directory.
$originQpc=[Diagnostics.Stopwatch]::GetTimestamp();$frequency=[Diagnostics.Stopwatch]::Frequency
$ErrorActionPreference='Stop'
function Owner-Elapsed { return ([Diagnostics.Stopwatch]::GetTimestamp()-$originQpc)/[double]$frequency }
$root=$PSScriptRoot
$expected='D:\sequence-weighting-research\work\capacity-shift-followup-activation-20261027-01'
$out='D:\sequence-weighting-research\work\runs\capacity-shift-followup-20261027-01'
$auth=Get-Content -LiteralPath (Join-Path $root 'AUTHORIZATION.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($auth.enabled -ne $true -or $auth.execution_ready -ne $true) {throw 'DISABLED: no capacity-shift follow-up approval'}
if ($root -ne $expected -or $auth.one_use -ne $true -or -not $auth.approval_id) {throw 'Invalid activation'}
if ($auth.source_subject_sha256 -ne $ExpectedSubject -or (Get-FileHash -LiteralPath (Join-Path $root 'SOURCE_SUBJECT.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedSubject) {throw 'Source pin mismatch'}
foreach($row in (Get-Content -LiteralPath (Join-Path $root 'SOURCE_SUBJECT.json') -Raw -Encoding UTF8 | ConvertFrom-Json).files) {
    $p=Join-Path $root $row.path
    if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256 -or (Get-Item -LiteralPath $p).Length -ne $row.bytes) {throw 'Changed source'}
}
foreach($pair in @(@('REGISTRY.json',$auth.registry_sha256),@('EXCLUSIONS.json',$auth.exclusions_sha256),@('DRAW.json',$auth.draw_sha256))) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $pair[0]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pair[1]) {throw 'Registry binding mismatch'}
}
$claim=Join-Path $root 'OWNER_CLAIM.json';$receipt=Join-Path $root 'OWNER_EXIT_RECEIPT.json'
if ((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $claim) -or (Test-Path -LiteralPath $receipt)) {throw 'One-use attempt consumed; no retry'}
if ((Get-PSDrive D).Free -lt 5GB) {throw 'Admission requires at least 5 GiB free on D:'}
[IO.File]::WriteAllText($claim,(@{origin_qpc=$originQpc;qpc_frequency=$frequency;subject=$ExpectedSubject;approval_id=$auth.approval_id;one_use=$true}|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName='wsl.exe'
$info.Arguments='-d Ubuntu --exec /mnt/d/sequence-weighting-research/work/.venv-wsl/bin/python -I -B /mnt/d/sequence-weighting-research/work/capacity-shift-followup-activation-20261027-01/ladder_worker.py run'
$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$proc=[Diagnostics.Process]::new();$proc.StartInfo=$info
if(-not $proc.Start()){throw 'WSL client did not start'}
$stdoutTask=$proc.StandardOutput.ReadToEndAsync();$stderrTask=$proc.StandardError.ReadToEndAsync()
# Overall 21,600 s worker deadline plus 300 s for its own terminal publication. No kill on timeout.
$observed=$proc.WaitForExit([int](1000*(21900-(Owner-Elapsed))))
$rc=$null;if($observed){$rc=$proc.ExitCode}
$cap=65536
$stdout=if($stdoutTask.Wait(5000)){$stdoutTask.Result}else{'<stdout incomplete>'};$stderr=if($stderrTask.Wait(5000)){$stderrTask.Result}else{'<stderr incomplete>'}
if($stdout.Length -gt $cap){$stdout=$stdout.Substring($stdout.Length-$cap)};if($stderr.Length -gt $cap){$stderr=$stderr.Substring($stderr.Length-$cap)}
[IO.File]::WriteAllText((Join-Path $root 'WORKER_STDOUT.log'),$stdout,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $root 'WORKER_STDERR.log'),$stderr,[Text.UTF8Encoding]::new($false))
$terminalPath=Join-Path $out 'TERMINAL.json';$terminal=$null;$terminalHash=$null
if(Test-Path -LiteralPath $terminalPath){$terminal=Get-Content -LiteralPath $terminalPath -Raw -Encoding UTF8|ConvertFrom-Json;$terminalHash=(Get-FileHash -LiteralPath $terminalPath -Algorithm SHA256).Hash.ToLowerInvariant()}
$status=if($observed -and $rc -eq 0 -and $terminal.status -eq 'COMPLETE'){'COMPLETE'}elseif(-not $observed){'EXIT_UNOBSERVED_NO_KILL'}else{'FAILED'}
$value=[ordered]@{status=$status;subject=$ExpectedSubject;exit_observed=$observed;exit_code=$rc;elapsed_seconds=(Owner-Elapsed);terminal_status=$terminal.status;terminal_sha256=$terminalHash;retry=$false;note='Native exit does not prove Linux process absence. Preserve every directory; do not rerun.'}
[IO.File]::WriteAllText($receipt,($value|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
$value|ConvertTo-Json -Depth 5
if($status -ne 'COMPLETE'){throw 'Capacity-shift follow-up failed or incomplete; preserve evidence, no retry'}
