# Existing-data exploratory analysis only. No Python, Torch, models, WSL or data generation.
param(
 [string]$RunRoot='D:\codex\sequence-weighting-research\work\runs\compensation-calibration-v0136-20261005-01',
 [string]$BundleRoot='D:\codex\sequence-weighting-research\outputs\sequence-weighting-compensation-calibration-v0136',
 [string]$OutputDir=(Join-Path $PSScriptRoot 'derived')
)
$ErrorActionPreference='Stop'
[System.Globalization.CultureInfo]::CurrentCulture=[System.Globalization.CultureInfo]::InvariantCulture
$clock=[System.Diagnostics.Stopwatch]::StartNew()
$startUtc=[datetime]::UtcNow.ToString('o')
if(Test-Path -LiteralPath $OutputDir) { throw 'Output directory exists; refuse overwrite' }
New-Item -ItemType Directory -Path $OutputDir -ErrorAction Stop | Out-Null
Add-Type -Path (Join-Path $PSScriptRoot 'SavedLossReader.cs')
$script:inputs=[System.Collections.Generic.Dictionary[string,object]]::new()
$script:maximumMetricDifference=0.0
function Require($ok,[string]$reason) { if(!$ok) { throw $reason } }
function TimeGuard { Require ($clock.Elapsed.TotalSeconds -lt 120) '120-second lightweight analysis allowance exceeded' }
function InputHash([string]$path,[string]$expected='') {
 TimeGuard
 $item=Get-Item -LiteralPath $path
 $hash=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
 if($expected) { Require ($hash -eq $expected) ('Saved input binding failed: '+$path) }
 if(!$script:inputs.ContainsKey($path)) { $script:inputs.Add($path,[pscustomobject]@{path=$path;bytes=$item.Length;sha256=$hash}) }
 return $hash
}
function JsonInput([string]$path,[string]$expected='') { [void](InputHash $path $expected); return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json }
function MeanRows($rows,[string]$property) {
 [double[]]$values=@($rows | ForEach-Object { [double]$_.PSObject.Properties[$property].Value })
 return [ComponentArithmetic]::Mean($values)
}
function CloseMetric([double]$a,[double]$b,[string]$label) {
 $difference=[Math]::Abs($a-$b)
 $script:maximumMetricDifference=[Math]::Max($script:maximumMetricDifference,$difference)
 Require ($difference -le 2e-6) ('Decoded saved metric mismatch: '+$label)
}
$sourceManifest=JsonInput (Join-Path $BundleRoot 'SOURCE_MANIFEST.json') '6bc67e09f61bbeb78ad38f26778408b2b051671a8e26d4f657e62f6e7b2f7865'
$audit=JsonInput (Join-Path $BundleRoot 'results-fresh-compensation-calibration-v0136-20261005-01/AUDIT.json') '8f72f522dc2100729a3fe6f846af1fcdbfa655629de24a1238d01a5ba6888dbf'
Require ($audit.status -eq 'PASS_CALIBRATION_NUMERICAL_AUDIT') 'Parent numerical evidence not accepted'
[void](InputHash (Join-Path $BundleRoot 'results-fresh-compensation-calibration-v0136-20261005-01/CALIBRATION_DECISION.json') '777fd45feaf04e1fe7b7462fe12faf56857667d8d4702302461a062608ebde60')
$prepare=JsonInput (Join-Path $RunRoot 'PREPARE_COMPLETE.json')
$pretrain=JsonInput (Join-Path $RunRoot 'PRETRAIN_COMPLETE.json')
$adapt=JsonInput (Join-Path $RunRoot 'ADAPT_COMPLETE.json')
$fitComplete=JsonInput (Join-Path $RunRoot 'FIT_COMPLETE.json')
$baselineManifest=JsonInput (Join-Path $RunRoot 'BASELINE_MANIFEST.json') $pretrain.baseline_manifest_sha256
$trajectoryManifest=JsonInput (Join-Path $RunRoot 'TRAJECTORY_MANIFEST.json') $adapt.trajectory_manifest_sha256
$fitManifest=JsonInput (Join-Path $RunRoot 'FIT_MANIFEST.json') $fitComplete.fit_manifest_sha256
$lossRows=[System.Collections.Generic.List[object]]::new()
$responseRows=[System.Collections.Generic.List[object]]::new()
$quartileRows=[System.Collections.Generic.List[object]]::new()
$sequenceRows=[System.Collections.Generic.List[object]]::new()
$components=@('shared','group','instance')
$identities=@('d91620101-s91640101','d91620101-s91640151','d91620102-s91640201','d91620102-s91640251','d91620103-s91640301','d91620103-s91640351')
foreach($identity in $identities) {
 TimeGuard
 $fit=JsonInput (Join-Path $RunRoot ('fits/'+$identity+'.json')) $fitManifest.PSObject.Properties[($identity+'.json')].Value
 [double[]]$q=$fit.q; Require ($q.Length -eq 512) 'Training q count'
 Require ([Math]::Abs([ComponentArithmetic]::Mean($q)-1) -lt 2e-7) 'Global q mean'
 [double[]]$x=@($q | ForEach-Object { [Math]::Log($_) })
 [int[]]$order=@(0..511 | Sort-Object @{Expression={$q[$_]}},@{Expression={$_}})
 Require (($order -join ',') -eq ($fit.allocation.R.train.ascending_q_indices -join ',')) 'q/index sort mismatch'
 $qHash=[SavedLossReader]::QHash($q)
 $baseRelative=$identity+'/record.json'
 $base=JsonInput (Join-Path $RunRoot ('baselines/'+$baseRelative)) $baselineManifest.PSObject.Properties[$baseRelative].Value
 $initialPath=Join-Path $RunRoot ('baselines/'+$identity+'/initial-arrays.pt')
 [void](InputHash $initialPath $baselineManifest.PSObject.Properties[($identity+'/initial-arrays.pt')].Value)
 $initial=[SavedLossReader]::Read($initialPath)
 $final=@{};$records=@{}
 foreach($arm in @('U','R')) {
  $relative=$identity+'-'+$arm+'/record.json'
  $record=JsonInput (Join-Path $RunRoot ('trajectories/'+$relative)) $trajectoryManifest.PSObject.Properties[$relative].Value
  Require ($record.data_seed -eq $fit.data_seed -and $record.seed -eq $fit.seed -and $record.arm -eq $arm) 'Paired identity'
  Require ($record.initial_checkpoint_sha256 -eq $base.checkpoint_sha256) 'Shared initial checkpoint'
  Require ($record.order_sha256 -and $record.q_sha256 -eq $qHash -and $record.whole_sequence_weighting -eq $true) 'Saved target or objective identity'
  Require ($record.epoch -eq 10 -and $record.clip -eq 1 -and $record.coefficients.Count -eq 3 -and @($record.coefficients | Where-Object { [double]$_ -ne (1.0/3.0) }).Count -eq 0) 'Canonical endpoint/scaling'
  $arrayRelative=$identity+'-'+$arm+'/F10-arrays.pt'
  $arrayPath=Join-Path $RunRoot ('trajectories/'+$arrayRelative)
  [void](InputHash $arrayPath $trajectoryManifest.PSObject.Properties[$arrayRelative].Value)
  $final[$arm]=[SavedLossReader]::Read($arrayPath);$records[$arm]=$record
 }
 Require ($records.U.order_sha256 -eq $records.R.order_sha256) 'Paired epoch orders'
 foreach($split in @('train','validation','test')) {
  Require ($records.U.data_sha256.PSObject.Properties[$split].Value -eq $records.R.data_sha256.PSObject.Properties[$split].Value) 'Paired token/label hash'
  CloseMetric ([ComponentArithmetic]::Mean($initial[$split].Total)) $base.initial_metrics.PSObject.Properties[$split].Value.loss ($identity+' initial total '+$split)
  foreach($arm in @('U','R')) {CloseMetric ([ComponentArithmetic]::Mean($final[$arm][$split].Total)) $records[$arm].metrics.PSObject.Properties[$split].Value.loss ($identity+' '+$arm+' total '+$split)}
  for($k=0;$k -lt 3;$k++) {
   $component=$components[$k]
   [double[]]$a=[ComponentArithmetic]::Column($initial[$split].Components,$k)
   [double[]]$u=[ComponentArithmetic]::Column($final.U[$split].Components,$k)
   [double[]]$r=[ComponentArithmetic]::Column($final.R[$split].Components,$k)
   [double[]]$gu=[ComponentArithmetic]::Difference($a,$u)
   [double[]]$gr=[ComponentArithmetic]::Difference($a,$r)
   [double[]]$delta=[ComponentArithmetic]::Difference($u,$r)
   CloseMetric ([ComponentArithmetic]::Mean($a)) $base.initial_metrics.PSObject.Properties[$split].Value.PSObject.Properties[$component].Value.loss ($identity+' initial '+$component+' '+$split)
   foreach($arm in @('U','R')) {
    $vector=if($arm -eq 'U') {$u} else {$r}
    CloseMetric ([ComponentArithmetic]::Mean($vector)) $records[$arm].metrics.PSObject.Properties[$split].Value.PSObject.Properties[$component].Value.loss ($identity+' '+$arm+' '+$component+' '+$split)
   }
   $lossRows.Add([pscustomobject]@{identity=$identity;corpus=$fit.data_seed;seed=$fit.seed;split=$split;component=$component;
    initial_mean=[ComponentArithmetic]::Mean($a);U_final_mean=[ComponentArithmetic]::Mean($u);R_final_mean=[ComponentArithmetic]::Mean($r);
    U_mean_gain=[ComponentArithmetic]::Mean($gu);R_mean_gain=[ComponentArithmetic]::Mean($gr);R_minus_U_gain=[ComponentArithmetic]::Mean($delta);
    U_negative_gain_count=[ComponentArithmetic]::NegativeCount($gu);R_negative_gain_count=[ComponentArithmetic]::NegativeCount($gr);n=$gr.Length})
   if($split -eq 'train') {
    [double[]]$sequenceGainU=$gu;[double[]]$sequenceGainR=$gr
    for($quartile=0;$quartile -lt 4;$quartile++) {
     [int[]]$indices=$order[($quartile*128)..($quartile*128+127)]
     $quartileRows.Add([pscustomobject]@{identity=$identity;corpus=$fit.data_seed;seed=$fit.seed;component=$component;quartile=$quartile+1;n=128;
      mean_q=[ComponentArithmetic]::MeanIndices($q,$indices);
      U_mean_gain=[ComponentArithmetic]::MeanIndices($gu,$indices);R_mean_gain=[ComponentArithmetic]::MeanIndices($gr,$indices);R_minus_U_gain=[ComponentArithmetic]::MeanIndices($delta,$indices)})
    }
    [int[]]$low=$order[0..127];[int[]]$high=$order[384..511]
    $responseRows.Add([pscustomobject]@{identity=$identity;corpus=$fit.data_seed;seed=$fit.seed;component=$component;
     U_mean_gain=[ComponentArithmetic]::Mean($gu);R_mean_gain=[ComponentArithmetic]::Mean($gr);R_minus_U_gain=[ComponentArithmetic]::Mean($delta);
     slope_U_gain_per_logq=[ComponentArithmetic]::Slope($x,$gu);slope_R_gain_per_logq=[ComponentArithmetic]::Slope($x,$gr);slope_paired_delta_per_logq=[ComponentArithmetic]::Slope($x,$delta);
     R_high_minus_low=[ComponentArithmetic]::MeanIndices($gr,$high)-[ComponentArithmetic]::MeanIndices($gr,$low);
     U_high_minus_low=[ComponentArithmetic]::MeanIndices($gu,$high)-[ComponentArithmetic]::MeanIndices($gu,$low);
     paired_delta_high_minus_low=[ComponentArithmetic]::MeanIndices($delta,$high)-[ComponentArithmetic]::MeanIndices($delta,$low)})
    for($j=0;$j -lt 512;$j++) {
     $sequenceRows.Add([pscustomobject]@{identity=$identity;corpus=$fit.data_seed;seed=$fit.seed;sequence_index=$j;q=$q[$j];log_q=$x[$j];component=$component;
       initial_loss=$a[$j];U_final_loss=$u[$j];R_final_loss=$r[$j];U_gain=$gu[$j];R_gain=$gr[$j];paired_delta_gain=$delta[$j]})
    }
   }
  }
 }
}
# First average two nested seeds within each corpus, then three corpus means equally.
$corpusLoss=[System.Collections.Generic.List[object]]::new()
foreach($group in ($lossRows | Group-Object corpus,split,component)) {
 Require ($group.Count -eq 2) 'Nested loss group count'
 $first=$group.Group[0]
 $corpusLoss.Add([pscustomobject]@{corpus=$first.corpus;split=$first.split;component=$first.component;nested_seeds=2;
  initial_mean=(MeanRows $group.Group 'initial_mean');U_final_mean=(MeanRows $group.Group 'U_final_mean');R_final_mean=(MeanRows $group.Group 'R_final_mean');
  U_mean_gain=(MeanRows $group.Group 'U_mean_gain');R_mean_gain=(MeanRows $group.Group 'R_mean_gain');R_minus_U_gain=(MeanRows $group.Group 'R_minus_U_gain')})
}
$corpusResponse=[System.Collections.Generic.List[object]]::new()
$responseProperties=@('U_mean_gain','R_mean_gain','R_minus_U_gain','slope_U_gain_per_logq','slope_R_gain_per_logq','slope_paired_delta_per_logq','R_high_minus_low','U_high_minus_low','paired_delta_high_minus_low')
foreach($group in ($responseRows | Group-Object corpus,component)) {
 Require ($group.Count -eq 2) 'Nested response group count'
 $row=[ordered]@{corpus=$group.Group[0].corpus;component=$group.Group[0].component;nested_seeds=2}
 foreach($property in $responseProperties) { $row[$property]=MeanRows $group.Group $property }
 $corpusResponse.Add([pscustomobject]$row)
}
$corpusQuartiles=[System.Collections.Generic.List[object]]::new()
foreach($group in ($quartileRows | Group-Object corpus,component,quartile)) {
 Require ($group.Count -eq 2) 'Nested quartile group count'
 $corpusQuartiles.Add([pscustomobject]@{corpus=$group.Group[0].corpus;component=$group.Group[0].component;quartile=$group.Group[0].quartile;nested_seeds=2;
  mean_q=(MeanRows $group.Group 'mean_q');U_mean_gain=(MeanRows $group.Group 'U_mean_gain');R_mean_gain=(MeanRows $group.Group 'R_mean_gain');R_minus_U_gain=(MeanRows $group.Group 'R_minus_U_gain')})
}
$summary=[System.Collections.Generic.List[object]]::new()
foreach($component in $components) {
 $group=@($corpusResponse | Where-Object {$_.component -eq $component})
 Require ($group.Count -eq 3) 'Three independent corpora'
 $row=[ordered]@{component=$component;independent_corpora=3;nested_seeds_per_corpus=2}
 foreach($property in $responseProperties) {$row[$property]=MeanRows $group $property}
 $summary.Add([pscustomobject]$row)
}
$tables=@{'SEED_COMPONENT_LOSSES.csv'=$lossRows;'CORPUS_COMPONENT_LOSSES.csv'=$corpusLoss;'SEED_RESPONSE.csv'=$responseRows;
 'CORPUS_RESPONSE.csv'=$corpusResponse;'SEED_Q_QUARTILES.csv'=$quartileRows;'CORPUS_Q_QUARTILES.csv'=$corpusQuartiles;
 'TRAIN_SEQUENCE_GAINS.csv'=$sequenceRows;'SUMMARY_COMPONENT_RESPONSE.csv'=$summary}
foreach($name in $tables.Keys) { $tables[$name] | Export-Csv -LiteralPath (Join-Path $OutputDir $name) -NoTypeInformation -Encoding utf8 }
foreach($input in $inputs.Values) {Require ((Get-FileHash -LiteralPath $input.path).Hash.ToLowerInvariant() -eq $input.sha256) 'Input changed during arithmetic'}
$methods=[ordered]@{status='EXPLORATORY_EXISTING_DATA_PENDING_INDEPENDENT_REVIEW';start_utc=$startUtc;end_utc=[datetime]::UtcNow.ToString('o');
 elapsed_seconds=$clock.Elapsed.TotalSeconds;time_cap_seconds=120;array_archives_decoded=18;float32_metadata_sha256=[SavedLossReader]::MetadataHash;
 decoder='Native Windows/.NET ZIP reads; no pickle execution; exact inspected metadata hash and contiguous FloatStorage mapping';
 gain_operation='Promote saved FP32 component losses to FP64 before initial-minus-final subtraction; paired delta=U_final-R_final';
 scaling='Each component averages four answer-token losses. Whole-sequence mean is (shared+group+instance)/3. All reported response metrics are unscaled component-token nats.';
 q_reference='Saved 512 training q values from each manifest-bound fit record; exact FP32 q hash matches U/R records; log q predictor; stable (q,index) quartiles128 each';
 normalization='Unweighted means and slopes. No gain-mass normalization, absolute-value gains, exponent fitting or compensation. q was globally mean-one normalized during the completed run.';
 aggregation='Two nested seed statistics averaged within corpus, then three corpus means equally; no sequence/seed pseudo-replication';
 slope='OLS with intercept of signed gain or paired delta on log(q); covariance(logq,y)/variance(logq)';
 quartile_contrast='High128-minus-low128 signed gain and paired delta means, same q partition for both arms; all four quartiles retained';
 validation_test='U/R own-initial component loss comparison only; no q assignment exists on held-out sequences, so no held-out q regression';
 maximum_decoded_vs_record_mean_difference=$maximumMetricDifference;saved_record_mean_tolerance=2e-6;
 source_calibration_status_unchanged='CALIBRATION_FAILED';no_models_loaded=$true;no_python_or_wsl=$true;no_data_generation=$true;no_training_or_model_evaluation=$true;
 inputs=@($inputs.Values | Sort-Object path)}
[System.IO.File]::WriteAllText((Join-Path $OutputDir 'METHODS_AND_INPUTS.json'),($methods | ConvertTo-Json -Depth 10),[System.Text.UTF8Encoding]::new($false))
$totalBytes=[long]0;foreach($file in Get-ChildItem -LiteralPath $OutputDir -File){$totalBytes+=$file.Length}
Require ($totalBytes -lt 8*1048576) '8 MiB derived-output allowance exceeded'
TimeGuard
[pscustomobject]@{elapsed_seconds=$clock.Elapsed.TotalSeconds;input_files=$inputs.Count;decoded_record_max_difference=$maximumMetricDifference;derived_bytes=$totalBytes;
 component_summary=@($summary);corpus_response=@($corpusResponse);corpus_losses=@($corpusLoss)} | ConvertTo-Json -Depth 8
