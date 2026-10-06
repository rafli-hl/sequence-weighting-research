# Current research synthesis: completed v0132

4 October 2026 UTC. This new synthesis supplements preserved historical records;
it does not replace their conclusions or restart completed studies. The latest
bounded experiment is documented in
[RESULT_AND_DECISION_20261004.md](RESULT_AND_DECISION_20261004.md).

The completed v0131 reanalysis found an adverse random-versus-uniform held-out
tradeoff and preferential high-weight instance allocation on five already seen
corpora. Its training associations and arithmetic loss decomposition did not
identify a mechanism. The completed v0130 no-clip diagnostic failed its frozen
width-128 validation criterion on those historical corpora; clip 1 remained the
canonical fixed control. Both studies stay closed and unchanged.

The new v0132 factorial contributes fresh paired intervention evidence: five
new corpus draws, two nested seeds per corpus, four component-weight arms,
G1/width 128/F10 and the fixed canonical optimizer policy. The instance-weight
factor increased unweighted group-token test NLL by **+0.035304929 nats**, with
corpus SD **0.004915780** and **5/5 positive corpus means**. The penalty also
appeared with uniform shared/group losses (I−U **+0.033297779**). Fresh R−U
total/group test penalties were **+0.041261750 / +0.053229730 nats** in their
respective answer-token units. The independent numerical audit and Astra result
review passed; the bounded study is complete.

The evidence now supports a narrow causal statement: changing instance-loss
weights worsened held-out group NLL under the tested training algorithm and
teacher-forced synthetic setup. It does not prove how that happened. Material
clipping-rate differences, AdamW update dynamics, near-ceiling group accuracy,
and worsened overall instance training loss restrict the interpretation.
Preferential high-weight training allocation remains supporting evidence rather
than proof of mediation, capacity competition or greater overall memorization.
No universal weighting disadvantage, p* peak, scaling curve or large-LM mechanism
is established. Five corpora remain the replication units.

Preserve all validated numerical evidence and its mechanistic uncertainty. A
future clipping/update-policy study is only a proposal; neither v0130's result
nor this record authorizes new execution, search, tuning or adaptive seed growth.

Historical reference: `../../sequence-weighting-weighting-contrast-v0131/results-fixed-policy-v0131-20261003-01/SYNTHESIS_AND_DECISION.md`.
The new decision record supplies source/result hashes, receipt timings, audit
limits and independent review provenance. No historical record or executable
source was modified to produce this synthesis.
