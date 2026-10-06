# Stage 11: paired group-rule sharing

Descriptive results from five corpus draws, with two nested model/weight seeds.
Fixed F10 group-learning contrasts and validation-selected R utility answer different questions.
No significance, large-LM replication, superior weighting method or peak-shift claim is implied.

## Prespecified readiness checks

| Check | Result |
| --- | --- |
| relative_response_positive | None |
| absolute_G1_group_gain_positive | None |
| selected_G1_middle_utility | None |
| mechanism_ready | None |
| G1_global_utility | None |
| capacity_ready | None |
| relative_response_direction | unavailable |
| automatic_next_run | False |
| uses_p_or_fit_for_decision | False |

Missing or undefined observations remain in the denominators. Passing a planning criterion does not launch another experiment.

## Selected-policy held-out learning

| Condition | Arm | Width | Epoch | Test gain (corpus mean) | Utility | p* (corpus mean) |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| G16 | random | 64 | 10 | undefined / unavailable | None | undefined / unavailable |
| G16 | random | 128 | 10 | undefined / unavailable | None | undefined / unavailable |
| G16 | random | 256 | 10 | undefined / unavailable | None | undefined / unavailable |
| G16 | uniform | 64 | 10 | undefined / unavailable | None | undefined / unavailable |
| G16 | uniform | 128 | 10 | undefined / unavailable | None | undefined / unavailable |
| G16 | uniform | 256 | 10 | undefined / unavailable | None | undefined / unavailable |
| G1 | random | 64 | 10 | undefined / unavailable | None | undefined / unavailable |
| G1 | random | 128 | 10 | undefined / unavailable | None | undefined / unavailable |
| G1 | random | 256 | 10 | undefined / unavailable | None | undefined / unavailable |
| G1 | uniform | 64 | 10 | undefined / unavailable | None | undefined / unavailable |
| G1 | uniform | 128 | 10 | undefined / unavailable | None | undefined / unavailable |
| G1 | uniform | 256 | 10 | undefined / unavailable | None | undefined / unavailable |

## Availability and limits

{'confirmation_corpora': 5, 'nested_seeds_per_corpus': 2, 'planned_native_checkpoints': 780, 'observed_native_checkpoints': 0, 'policy_references': 840, 'status_counts': {'not_run': 780}}

See summaries.json for all component losses, memorization, clipping, fit objectives, boundaries, signed gains, initial losses, all corpus/seed values and missing records.
G1/G16 alter both target rules and subsequent teacher-forced context. Comparisons use each condition’s own baseline.
The fixed intervention changes rule complexity and support together. Three capacities cannot show a shift between two interior peaks.
This generated report requires independent raw-array, selected-checkpoint and figure review before final acceptance. Only scripts were executed.
