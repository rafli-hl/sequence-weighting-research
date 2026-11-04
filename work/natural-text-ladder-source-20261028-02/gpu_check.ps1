# Windows-side GPU checks for the natural-text ladder owner script (revision 05, owner ruling of 28 Oct 2026).
# Dot-sourced by TEXT_OWNER_RUN.ps1 after its source hash checks; the native fixtures dot-source it with a stand-in nvidia-smi.
# Every threshold and timing comes from the sealed GPU_CHECK.json, fixed from an idle baseline before the run.
# A check: settle, then samples_per_check nvidia-smi readings of memory used, memory total and utilization. BUSY if the
# mean utilization exceeds its threshold, or, before start only (prestart: no worker yet), if any reading's memory used
# exceeds the pre-start limit. Before a draw (boundary) the worker is alive and may hold GPU memory, so memory is recorded
# in every reading but not gated (owner change of 29 Oct 2026). UNVERIFIED (never IDLE) if any reading fails; before a
# draw it is rechecked like BUSY. While the worker runs, nothing is written to the console: a legacy console window stalls
# a console write while text is selected in it (review 4). Progress goes to OWNER_PROGRESS.log in the activation folder.

function Read-GpuConfig([string]$Path) {
    $c = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($k in @('nvidia_smi', 'samples_per_check', 'sample_interval_seconds', 'settle_seconds', 'smi_timeout_seconds', 'utilization_mean_max_percent',
                     'prestart_memory_used_max_mib', 'recheck_interval_seconds', 'busy_window_seconds')) {
        if ($null -eq $c.$k) { throw ('GPU check configuration lacks ' + $k) }
    }
    if ([int]$c.samples_per_check -lt 1) { throw 'GPU check configuration needs at least one sample per check' }
    return $c
}

function Get-GpuSample([string]$Exe, [string[]]$Prefix, [double]$TimeoutSeconds) {
    # One nvidia-smi reading of the single GPU; $null if it fails, times out, reports more than one GPU or does not parse.
    $argv = @($Prefix) + @('--query-gpu=memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits')
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Exe
    $info.Arguments = (($argv | Where-Object { $_ } | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
    $info.UseShellExecute = $false; $info.CreateNoWindow = $true; $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
    $p = [Diagnostics.Process]::new(); $p.StartInfo = $info
    try { if (-not $p.Start()) { return $null } } catch { return $null }
    $outTask = $p.StandardOutput.ReadToEndAsync(); $errTask = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit([int](1000 * $TimeoutSeconds))) { try { $p.Kill() } catch {}; return $null }
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) { return $null }
    $lines = @($outTask.Result -split "`r?`n" | Where-Object { $_.Trim() })
    if ($lines.Count -ne 1) { return $null }
    $fields = @($lines[0] -split ',')
    if ($fields.Count -ne 3) { return $null }
    $v = @()
    foreach ($x in $fields) { $n = 0; if (-not [int]::TryParse($x.Trim(), [ref]$n)) { return $null }; $v += $n }
    return [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); memory_used_mib = $v[0]; memory_total_mib = $v[1]; utilization_percent = $v[2] }
}

function Invoke-GpuCheck($Config, [string]$Context, [string]$Exe, [string[]]$Prefix) {
    if ($Context -ne 'prestart' -and $Context -ne 'boundary') { throw 'Invalid GPU check context' }
    $memMax = if ($Context -eq 'prestart') { [int]$Config.prestart_memory_used_max_mib } else { $null }     # before a draw: recorded, not gated
    $check = [ordered]@{ started_utc = [DateTime]::UtcNow.ToString('o'); context = $Context; utilization_mean_max_percent = [double]$Config.utilization_mean_max_percent; memory_used_max_mib = $memMax }
    Start-Sleep -Milliseconds ([int](1000 * [double]$Config.settle_seconds))
    $samples = @(); $failed = 0
    for ($i = 0; $i -lt [int]$Config.samples_per_check; $i++) {
        if ($i -gt 0) { Start-Sleep -Milliseconds ([int](1000 * [double]$Config.sample_interval_seconds)) }
        $s = Get-GpuSample $Exe $Prefix ([double]$Config.smi_timeout_seconds)
        if ($null -eq $s) { $failed++ } else { $samples += ,$s }
    }
    $check.samples = $samples; $check.failed_samples = $failed
    if ($failed -gt 0 -or $samples.Count -eq 0) { $check.mean_utilization_percent = $null; $check.max_memory_used_mib = $null; $check.verdict = 'UNVERIFIED'; return $check }
    $sum = 0.0; $maxMem = 0
    foreach ($s in $samples) { $sum += [double]$s.utilization_percent; if ($s.memory_used_mib -gt $maxMem) { $maxMem = $s.memory_used_mib } }
    $mean = $sum / $samples.Count
    $check.mean_utilization_percent = [Math]::Round($mean, 2); $check.max_memory_used_mib = $maxMem
    $check.verdict = if ($mean -gt $check.utilization_mean_max_percent -or ($null -ne $memMax -and $maxMem -gt $memMax)) { 'BUSY' } else { 'IDLE' }
    return $check
}

function Format-GpuCheck($Check) {
    if ($Check.verdict -eq 'UNVERIFIED') { return ('UNVERIFIED (' + $Check.failed_samples + ' failed nvidia-smi readings)') }
    $limit = if ($null -eq $Check.memory_used_max_mib) { 'recorded, not gated' } else { 'limit ' + $Check.memory_used_max_mib + ' MiB' }
    return ($Check.verdict + ': mean utilization ' + $Check.mean_utilization_percent + '% (limit ' + $Check.utilization_mean_max_percent + '%), max memory used ' + $Check.max_memory_used_mib + ' MiB (' + $limit + ')')
}

function Write-OwnerProgress([string]$Log, [string]$Line) {
    # One timestamped line appended to the progress log (UTF-8, no BOM); never throws, never writes to the console.
    if (-not $Log) { return }
    try { [IO.File]::AppendAllText($Log, ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss') + '  ' + $Line + "`r`n"), [Text.UTF8Encoding]::new($false)) } catch {}
}

function Invoke-GpuGate($Config, [string]$Stage, [string]$Exe, [string[]]$Prefix, [string]$Log = '') {
    # Before a draw: check; while not IDLE, recheck every recheck_interval_seconds until busy_window_seconds after the
    # start of the first check, then BUSY_TIMEOUT. Every check is kept in the verdict.
    $clock = [Diagnostics.Stopwatch]::StartNew(); $checks = @()
    while ($true) {
        $at = [Math]::Round($clock.Elapsed.TotalSeconds, 1)
        $c = Invoke-GpuCheck $Config 'boundary' $Exe $Prefix; $c.since_first_check_seconds = $at
        $checks += ,$c
        if ($c.verdict -eq 'IDLE') { return [ordered]@{ schema = 1; stage = $Stage; verdict = 'IDLE'; checks = $checks } }
        $left = [double]$Config.busy_window_seconds - $clock.Elapsed.TotalSeconds
        if ($left -le 0) { return [ordered]@{ schema = 1; stage = $Stage; verdict = 'BUSY_TIMEOUT'; checks = $checks } }
        Write-OwnerProgress $Log ('GPU check before ' + $Stage + ': ' + (Format-GpuCheck $c) + '. Waiting; ' + [Math]::Ceiling($left / 60) + ' min left before the run stops. Close GPU apps.')
        Start-Sleep -Milliseconds ([int](1000 * [Math]::Min([double]$Config.recheck_interval_seconds, $left)))
    }
}

function Write-GateRecord([string]$Directory, [string]$Name, $Value) {
    # Atomic, immutable write (temporary name, then rename), UTF-8 without BOM.
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $final = Join-Path $Directory $Name; $temp = $final + '.part'
    if ((Test-Path -LiteralPath $final) -or (Test-Path -LiteralPath $temp)) { throw ('GPU check record exists: ' + $Name) }
    [IO.File]::WriteAllText($temp, ($Value | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temp, $final)
}

function Wait-WorkerWithGates($Process, [string]$RunRoot, [string]$ActivationRoot, $Config, [string]$Exe, [string[]]$Prefix, [double]$DeadlineSeconds, [scriptblock]$Elapsed, [string[]]$Stages, [string]$Log = '') {
    # Wait for the worker to exit (or the owner deadline), answering each draw's GPU check request: the request is in the
    # run folder (written by the worker), the verdict goes to the activation folder (read and recorded by the worker).
    $handled = @{}; $gates = @()
    while ($true) {
        if ($Process.WaitForExit(1000)) { return [ordered]@{ observed = $true; gates = $gates } }
        if ((& $Elapsed) -ge $DeadlineSeconds) { return [ordered]@{ observed = $false; gates = $gates } }
        $dir = Join-Path $RunRoot 'gpu-checks'
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        foreach ($stage in $Stages) {
            if ($handled.ContainsKey($stage) -or -not (Test-Path -LiteralPath (Join-Path $dir ($stage + '-REQUEST.json')))) { continue }
            $gate = Invoke-GpuGate $Config $stage $Exe $Prefix $Log
            Write-GateRecord (Join-Path $ActivationRoot 'gpu-checks') ($stage + '-RESPONSE.json') $gate
            $handled[$stage] = $true; $gates += ,([ordered]@{ stage = $stage; verdict = $gate.verdict; checks = @($gate.checks).Count })
            Write-OwnerProgress $Log ('GPU check before ' + $stage + ': ' + $gate.verdict + ' (' + (Format-GpuCheck $gate.checks[-1]) + ')')
        }
    }
}
