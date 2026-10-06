# Stage 11: paired group-rule sharing

Descriptive results from five corpus draws, with two nested model/weight seeds.
Fixed F10 group-learning contrasts and validation-selected R utility answer different questions.
No significance, large-LM replication, superior weighting method or peak-shift claim is implied.

## Prespecified readiness checks

| Check | Result |
| --- | --- |
| relative_response_positive | True |
| absolute_G1_group_gain_positive | True |
| selected_G1_middle_utility | True |
| mechanism_ready | True |
| G1_global_utility | True |
| capacity_ready | True |
| relative_response_direction | positive_in_all_corpora |
| automatic_next_run | False |
| uses_p_or_fit_for_decision | False |

Missing or undefined observations remain in the denominators. Passing a planning criterion does not launch another experiment.

## Selected-policy held-out learning

| Condition | Arm | Width | Epoch | Test gain (corpus mean) | Utility | p* (corpus mean) |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| G16 | random | 64 | 10 | 0.04360676 | True | 0.1889758 |
| G16 | random | 128 | 3 | 0.002176905 | False | 0.9649627 |
| G16 | random | 256 | 0 | 0 | False | undefined / unavailable |
| G16 | uniform | 64 | 10 | 0.07433754 | True | undefined / unavailable |
| G16 | uniform | 128 | 3 | 0.009022844 | True | undefined / unavailable |
| G16 | uniform | 256 | 0 | 0 | False | undefined / unavailable |
| G1 | random | 64 | 30 | 0.9234465 | True | 0.02226486 |
| G1 | random | 128 | 10 | 0.8718675 | True | 0.01774486 |
| G1 | random | 256 | 30 | 0.8715323 | True | 0.01910821 |
| G1 | uniform | 64 | 30 | 1.01112 | True | undefined / unavailable |
| G1 | uniform | 128 | 10 | 0.9141277 | True | undefined / unavailable |
| G1 | uniform | 256 | 30 | 0.9105275 | True | undefined / unavailable |

## Availability and limits

{'confirmation_corpora': 5, 'nested_seeds_per_corpus': 2, 'planned_native_checkpoints': 900, 'observed_native_checkpoints': 900, 'policy_references': 840, 'status_counts': {'complete': 900}}

See summaries.json for all component losses, memorization, clipping, fit objectives, boundaries, signed gains, initial losses, all corpus/seed values and missing records.
G1/G16 alter both target rules and subsequent teacher-forced context. Comparisons use each condition’s own baseline.
The fixed intervention changes rule complexity and support together. Three capacities cannot show a shift between two interior peaks.
This generated report requires independent raw-array, selected-checkpoint and figure review before final acceptance. Only scripts were executed.
