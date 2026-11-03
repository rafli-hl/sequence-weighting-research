# Windows-side power checks for the one-rate ladder, revision 02 (owner ruling 20261030-03). Dot-sourced by
# ONERATE_OWNER_RUN.ps1 after gpu_check.ps1 (revision 05, unchanged) and its source hash checks; the native fixtures
# dot-source it and then a stand-in Get-PowerSample. Attempt 1 failed when the charger was unplugged during d06 (the
# ASUS power scheme then switched from Turbo to Silent, and the closed lid put the laptop into Modern Standby).
# - Get-PowerSample: one reading of the power line (AC, BATTERY or UNKNOWN), the battery percent and the active scheme.
# - Invoke-PowerGpuGate: before a draw, revision 05's GPU check followed by a power reading; a check is IDLE only if the
#   GPU check is IDLE and the power is AC (off AC it reads ON_BATTERY or POWER_UNVERIFIED; on AC, the GPU check's own
#   BUSY or UNVERIFIED). Not IDLE is rechecked every
#   recheck_interval_seconds until busy_window_seconds (30 minutes) after the first check, then BUSY_TIMEOUT, exactly as
#   revision 05's Invoke-GpuGate; every check, with its power reading, is kept in the verdict.
# - Wait-WorkerWithPowerGates: revision 05's Wait-WorkerWithGates with these gates, plus a power reading every
#   IntervalSeconds outside the before-draw checks (whose own readings are in the gate records) appended as one JSON line
#   to the power log; failed log writes are counted; every change of power source or scheme also goes to the progress
#   log, and a reading whose scheme could not be read is counted and is not taken as a change of scheme (a change of
#   power source at that reading is still recorded; confirmation of the revision 02 review, N3). Nothing is written to the console while the worker runs. powercfg runs as a redirected process with a 5 s
#   timeout, as revision 05 runs nvidia-smi (review of revision 02, findings 2 and 3).

function Get-PowerSample {
    $line = 'UNKNOWN'; $pct = $null; $guid = $null; $name = $null; $err = $null
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        $ps = [System.Windows.Forms.SystemInformation]::PowerStatus
        $line = switch ([string]$ps.PowerLineStatus) { 'Online' { 'AC' } 'Offline' { 'BATTERY' } default { 'UNKNOWN' } }
        $pct = [Math]::Round(100 * [double]$ps.BatteryLifePercent, 1)
    } catch { $err = 'power status: ' + $_.Exception.Message }
    try {
        $info = [Diagnostics.ProcessStartInfo]::new(); $info.FileName = "$env:SystemRoot\System32\powercfg.exe"; $info.Arguments = '/getactivescheme'
        $info.UseShellExecute = $false; $info.CreateNoWindow = $true; $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
        $proc = [Diagnostics.Process]::new(); $proc.StartInfo = $info
        if (-not $proc.Start()) { throw 'powercfg did not start' }
        $outTask = $proc.StandardOutput.ReadToEndAsync(); $errTask = $proc.StandardError.ReadToEndAsync()
        if (-not $proc.WaitForExit(5000)) { try { $proc.Kill() } catch {}; throw 'powercfg timed out' }
        $s = if ($outTask.Wait(2000)) { $outTask.Result } else { '' }
        if ($s -match '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s+\(([^)]*)\)') { $guid = $Matches[1].ToLowerInvariant(); $name = $Matches[2] }
        else { throw 'powercfg output not parsed' }
    } catch { if (-not $err) { $err = 'power scheme: ' + $_.Exception.Message } }
    return [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); power = $line; battery_percent = $pct; scheme_guid = $guid; scheme_name = $name; error = $err }
}

function Format-PowerSample($Sample) {
    return ('power ' + $Sample.power + ', battery ' + $Sample.battery_percent + '%, plan ' + $Sample.scheme_name)
}

function Format-PowerGpuCheck($Check) {
    # The GPU part formatted by revision 05's Format-GpuCheck on the GPU's own verdict, then the power reading.
    $g = [ordered]@{}; foreach ($k in $Check.Keys) { $g[$k] = $Check[$k] }; $g.verdict = $Check.gpu_verdict
    return ('GPU ' + (Format-GpuCheck $g) + '; ' + (Format-PowerSample $Check.power))
}

function Invoke-PowerGpuCheck($Config, [string]$Exe, [string[]]$Prefix) {
    $c = Invoke-GpuCheck $Config 'boundary' $Exe $Prefix
    $p = Get-PowerSample
    $c.power = $p; $c.gpu_verdict = $c.verdict
    if ($p.power -eq 'BATTERY') { $c.verdict = 'ON_BATTERY' } elseif ($p.power -ne 'AC') { $c.verdict = 'POWER_UNVERIFIED' }
    return $c
}

function Invoke-PowerGpuGate($Config, [string]$Stage, [string]$Exe, [string[]]$Prefix, [string]$Log = '') {
    $clock = [Diagnostics.Stopwatch]::StartNew(); $checks = @()
    while ($true) {
        $at = [Math]::Round($clock.Elapsed.TotalSeconds, 1)
        $c = Invoke-PowerGpuCheck $Config $Exe $Prefix; $c.since_first_check_seconds = $at
        $checks += ,$c
        if ($c.verdict -eq 'IDLE') { return [ordered]@{ schema = 1; stage = $Stage; verdict = 'IDLE'; checks = $checks } }
        $left = [double]$Config.busy_window_seconds - $clock.Elapsed.TotalSeconds
        if ($left -le 0) { return [ordered]@{ schema = 1; stage = $Stage; verdict = 'BUSY_TIMEOUT'; checks = $checks } }
        $hint = @(); if ($c.power.power -ne 'AC') { $hint += 'Plug in the charger.' }; if ($c.gpu_verdict -ne 'IDLE') { $hint += 'Close GPU apps.' }
        Write-OwnerProgress $Log ('Check before ' + $Stage + ': ' + $c.verdict + ' (' + (Format-PowerGpuCheck $c) + '). Waiting; ' + [Math]::Ceiling($left / 60) + ' min left before the run stops. ' + ($hint -join ' '))
        Start-Sleep -Milliseconds ([int](1000 * [Math]::Min([double]$Config.recheck_interval_seconds, $left)))
    }
}

function Wait-WorkerWithPowerGates($Process, [string]$RunRoot, [string]$ActivationRoot, $Config, [string]$Exe, [string[]]$Prefix, [double]$DeadlineSeconds, [scriptblock]$Elapsed, [string[]]$Stages,
                                   [string]$Log, [string]$PowerLog, [double]$IntervalSeconds) {
    $handled = @{}; $gates = @(); $n = 0; $nonAc = 0; $logFailed = 0; $schemeFailed = 0; $minPct = $null; $schemes = @{}; $changes = @(); $lastPower = $null; $lastGuid = $null; $next = 0.0
    while ($true) {
        if ($Process.WaitForExit(1000)) { $observed = $true; break }
        if ((& $Elapsed) -ge $DeadlineSeconds) { $observed = $false; break }
        if ((& $Elapsed) -ge $next) {
            $p = Get-PowerSample; $n++; $next = (& $Elapsed) + $IntervalSeconds
            try { [IO.File]::AppendAllText($PowerLog, (($p | ConvertTo-Json -Compress) + "`n"), [Text.UTF8Encoding]::new($false)) } catch { $logFailed++ }
            if ($p.power -ne 'AC') { $nonAc++ }
            if ($null -ne $p.battery_percent -and ($null -eq $minPct -or $p.battery_percent -lt $minPct)) { $minPct = $p.battery_percent }
            $changed = $null -ne $lastPower -and $p.power -ne $lastPower
            if ($null -eq $p.scheme_guid) { $schemeFailed++ }
            else {
                $schemes[[string]$p.scheme_name] = $true
                if ($null -ne $lastGuid -and $p.scheme_guid -ne $lastGuid) { $changed = $true }
                $lastGuid = $p.scheme_guid
            }
            if ($changed) {
                $changes += ,([ordered]@{ utc = $p.utc; power = $p.power; scheme_name = $p.scheme_name; battery_percent = $p.battery_percent })
                Write-OwnerProgress $Log ('Power changed during the run: ' + (Format-PowerSample $p) + '.')
            }
            $lastPower = $p.power
        }
        $dir = Join-Path $RunRoot 'gpu-checks'
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        foreach ($stage in $Stages) {
            if ($handled.ContainsKey($stage) -or -not (Test-Path -LiteralPath (Join-Path $dir ($stage + '-REQUEST.json')))) { continue }
            $gate = Invoke-PowerGpuGate $Config $stage $Exe $Prefix $Log
            Write-GateRecord (Join-Path $ActivationRoot 'gpu-checks') ($stage + '-RESPONSE.json') $gate
            $handled[$stage] = $true; $gates += ,([ordered]@{ stage = $stage; verdict = $gate.verdict; checks = @($gate.checks).Count; off_ac_checks = @($gate.checks | Where-Object { $_.power.power -ne 'AC' }).Count })
            Write-OwnerProgress $Log ('Check before ' + $stage + ': ' + $gate.verdict + ' (' + (Format-PowerGpuCheck $gate.checks[-1]) + ')')
        }
    }
    return [ordered]@{ observed = $observed; gates = $gates; power = [ordered]@{ samples = $n; log_write_failures = $logFailed; scheme_read_failures = $schemeFailed; off_ac_samples = $nonAc; min_battery_percent = $minPct; schemes = @($schemes.Keys | Sort-Object); changes = $changes } }
}
