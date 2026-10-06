# Why the next intervention should tie group rules

30 September 2026. Source-grounded design rationale; no new model training,
generator draw, model metric or numerical fit was run to prepare this document.
The accompanying [protocol](NEXT_PROTOCOL_DRAFT.md) is proposed and not frozen.

## The scientific gap

The primary U/R/random policy did not show repeatable useful adaptation at the
middle capacity in Stage 6, and the largest capacity selected epoch 0 in three
of four tuning panels. Numerical agreement in Stages 9–10 does not explain this
failure. A useful next experiment should test a feature of the learning problem
that can change held-out learning while preserving a controlled connection to
sequence weighting.

This is not a claim that the entire task cannot support learning. All four
Stage 6 M/R and M/J panels passed the global utility criterion. M starts with
much larger nonshared losses, so its large gains can include improving poor
initial predictions. U's initial losses make that source of improvement much
smaller. The question concerns this specified U setting and its pattern
structure, not the impossibility of useful synthetic adaptation.

Sources: [Stage 4 report](../sequence-weighting-stage4/results-baseline-v05-20260929-01-r2/REPORT.md),
[Stage 5 report](../sequence-weighting-stage5/results-utility-v06-20260929-01-r1/REPORT.md),
[Stage 6 report](../sequence-weighting-stage6/results-stability-v07-20260929-01/REPORT.md),
and [Stage 4–10 synthesis](../sequence-weighting-stage10/SYNTHESIS_STAGE4_10.md).

## What the generator actually makes learnable

The following are properties of saved source, not explanations established by
the past model outcomes.

| Source fact | Consequence and limitation |
| --- | --- |
| `core.py:50–75` draws 16 permutations once per corpus, uses `group=i%16`, and splits the resulting sequence list afterward. | Train, validation and test share the same group mappings and contain all 16 groups. Existing held-out evaluation is not extrapolation to unseen groups. |
| Each mixed example has four group queries sampled among 16 distinct query values, and the 512 training examples give 32 examples per group. | A particular group/query association has expected training support `32*4/16=8`. Some finite-corpus counts may be smaller or zero; they must be reported rather than assumed away. |
| Shared answers are always `(x+1)%16`. | This rule is identical across corpora and pretraining; U already has high shared accuracy, although there can still be NLL improvement. |
| Instance answers are fresh `rng.randrange(16)` draws, independently generated for each query in each sequence. | At unseen example keys there is no population predictive signal from the key, group, query, or earlier answers. Conditional population entropy is log(16), before accounting for the model's probability mass outside answer tokens. Training memorization can reduce empirical train loss without reducing expected held-out instance loss. A finite held-out sample can fluctuate. |
| `engine.py:61–79` rewrites example keys into disjoint phase/split namespaces without changing group/query mappings. | This prevents direct example-key reuse. It does not make group mappings disjoint between train and held-out data. |
| `stage6.py:39–47` gives U shared hard-label CE plus uniform-target CE at group/instance positions, with separately normalized coefficient 1 and all 84 tokens in log-softmax. | U explicitly encourages nearly uniform answer probabilities for both nonshared types. Group answers can later become predictable; independent instance answers cannot acquire population signal merely through repeated training. |
| Pretraining and adaptation are generated from separate data seeds. | The pretraining group permutations are not the adaptation corpus's group rule. Accidental overlap is possible; no exact mapping transfer is guaranteed. U still sees hard group/instance answers as teacher-forced context. |

Source files: [generator](../sequence-weighting-stage6/core.py),
[split construction](../sequence-weighting-stage6/engine.py),
[pretraining objective](../sequence-weighting-stage6/stage6.py),
[model and answer loss](../sequence-weighting-stage6/model.py).

For U, the mixed population floor would be `(0+0+log(16))/3` if shared and group
rules were learned perfectly and instance predictions remained optimal. Thus
the existing task has genuine room for group generalization; its failure is
not a theorem following from one third random labels. Conversely, U's instance
loss near log(16) is not an unexplained lack of learnability. Adaptation must
learn the reusable group rule while limiting shared forgetting and instance
overconfidence. Which of optimization, representation, data support and
interference limits the observed U policy remains unresolved.

## Chosen intervention

Construct paired adaptation corpora with the original 4/4/4 composition:

- **G16:** the original 16 independent group-specific permutations.
- **G1:** use the first of those sampled permutations for every group ID.

Generate the original complete corpus once, then replace only group-answer
tokens in the G1 copy. Keep the query values/order, type masks, example keys,
group IDs, shared answers and instance answers unchanged. Pretraining is
unchanged U and uses one identical checkpoint in both conditions.

G1 makes the group-type rule reusable across groups. A query's expected support
for its single mapping is `512*4/16=128`, compared with 8 per mapping in G16.
Both use bijections on the same 16 answers. This preserves the intended
population answer marginal but does not promise exactly equal empirical answer
counts. The contrast deliberately changes both number of functions and support
per function; it estimates the effect of **tying group rules**, not a pure
effect of sample count or an abstract notion of pattern complexity.

Changing group answers changes later teacher-forced input context. Full input
equality therefore holds across weighting/optimizer arms *within* a condition,
not across G1/G16. The cross-condition audit must verify that every difference
is an intended group-answer token and that all common skeleton fields match.
The intervention can alter shared/instance outcomes through these contexts and
through parameter updates, so all three components must remain in the report.
The intervention changes the training and held-out task jointly. Its primary
contrast compares within-task learning gains; it is not a comparison of two
trained models scored on identical held-out targets.

## Alternatives considered

| Route | What it would answer | Decision |
| --- | --- | --- |
| More optimizer panels on unchanged U data | Further selection stability within a bounded optimizer family | Stage 6 already exposed the weakness. It would not directly manipulate a proposed mechanism. |
| Replace random instance labels with another learnable rule | Whether removing an irreducible component improves useful learning | Plausible later, but changes the meaning of the instance-memorization component and removes the existing noise control. |
| Increase the corpus size only | Whether greater sample support helps adaptation | Also changes total tokens and optimizer updates at fixed epochs; requires additional matching to separate these effects. |
| Add several pretrained public-text model sizes | Whether the phenomenon occurs in a closer language-model setting | Scientifically valuable, but the current local budget and a single historical 70M text check do not support a credible broad scaling experiment now. |
| Tie group rules, keeping the independent instance component | Whether greater cross-example reusability helps learning under the same mixed task and U baseline | Chosen as the smallest direct intervention on reusable versus more specific patterns. |

## Predictions and what would change the research direction

The primary mechanistic prediction is that at matched optimizer and epoch 10,
G1 produces larger held-out group-component gain than G16. The practical
prediction is that validation-selected G1 adaptation improves total held-out
NLL over its own epoch-0 baseline, especially at the previously fragile middle
capacity. Both can fail. The precise descriptive go/stop criteria are fixed in
the proposed protocol, independently of p*.

A lower group-component p* in G1 than G16 at the matched checkpoint is a
secondary directional prediction about weight sensitivity. It is not guaranteed
by the construction or necessary for useful learning. Undefined estimates,
poor fits, boundary values and contrary directions remain in every denominator.
All selected-policy comparisons are distinguished from the matched-epoch
intervention. Three capacities still cannot identify movement between two
interior peaks.

The connection to [Jane Street's question](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/)
is a controlled test of broadly reusable versus more specific patterns and
their weighting sensitivity. Success would justify a more informative mechanism
study in this toy setting; it would not prove Jane Street's large-model
explanation, improve their weighting method, or establish novelty. Failure
would strengthen the negative boundary-condition account without triggering
another automatic grid or a task change chosen to obtain a peak.

## Decision status

This proposal follows the existing evidence and source structure. No claim is
made that its runtime, manipulation, usefulness, exponent direction or capacity
pattern has been measured. The next executable milestone is a new versioned
implementation with outcome-independent fixtures, resource feasibility evidence,
independent review, and a source/input/protocol freeze before model outcomes.
