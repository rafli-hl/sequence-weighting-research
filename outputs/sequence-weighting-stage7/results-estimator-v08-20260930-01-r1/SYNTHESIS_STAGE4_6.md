# Stages 4–6: baseline, selection and exponent interpretability

30 September 2026. Retrospective synthesis of completed experiments; no new
training, model selection or estimator filtering. Numerical claims refer to the
final reports listed below. K = p*middle − max(p*small, p*large).

## Baseline intervention and arithmetic reference

Stage 4 paired M/U pretraining tokens, cold states and orders. M optimized
shared-answer loss; U added uniform-target loss on group/instance answers.
U improved both initial nonshared validation losses in all nine capacity/corpus
cells, retaining 100% shared accuracy. This manipulation also changes learned
representations and adaptation dynamics; it does not isolate a scalar baseline
effect or demonstrate complete probability calibration. (S4, §§1–2.)

At fixed LR1e-4, WD.1, clip1 and epoch30, U had nine positive K values,
mean 4.561708, versus M −.038544. However, 2/9 middle-capacity U estimates reached
p*=8; mean fit objective was 2.600139 versus M .000177. Keeping U's trained
trajectory but substituting M's initial losses changed mean K to −.000385.
The reverse substitution made every K undefined. These reference swaps expose
arithmetic sensitivity; they are not trained interventions or causal mediation.
Undefined terms cannot be omitted to obtain a finite decomposition. (S4, §§1,4.)

## Duration, optimizer and selection change the question

With the same fixed optimizer at epoch60, U's mean K became −.533549 and all
three corpus means were negative; M retained nine positive K values. Joint-arm
validation tuning changed both optimizer and capacity-specific stopping times.
Selected U had an undefined K aggregate and failed the combined generalization
criterion. Thus matched adaptation, selected duration and selected-policy
comparisons have different estimands. (S4, §§1,3,5.)

Stage 5 admitted canonical epoch0, used a smaller-LR grid and 30-epoch horizon,
and made random-arm validation selection R primary; joint-arm J remained
secondary. All nonzero selections nevertheless used LR1e-4. U/R chose epochs
10/3/0. Mean test improvements against own initialization were
.030936/.001879/0: small and middle capacities passed utility, but largest
abstention made global utility false. Utility required updates, positive mean
test improvement in every corpus, and validation no worse than initialization
in every corpus. Scaling passed separately. The middle benefit included one
negative test pair and three negative validation pairs among nine. (S5, §§1–3.)

## Fresh panels qualify the middle benefit

Stage 6 preserved Stage 5's procedure across four fresh two-pair tuning panels.
U/R largest-capacity abstention occurred in 3/4 panels; middle abstention in
2/4. Small utility passed 4/4, middle and global utility 0/4. Positive overall
middle test gains in the two adapting panels did not satisfy the corpus-level
test/validation conditions. Panel P4 selected LR1e-5 for middle and large
capacities, so Stage 5's absence of smaller-LR selections did not recur.
M/R and M/J passed utility/scaling throughout, with mixed peak verdicts.
(S6, §§1–4.)

These four panels share three confirmation corpora and reuse identical selected
checkpoints. Twelve panel/corpus cells are not twelve independent datasets;
model/weight seeds are nested. Panel variation includes tuning data, model/weight
seeds and pretraining data together. The 0/4 middle result qualifies Stage 5's
success without identifying which source of variation caused the difference.
(S6, §§1–3.)

## Undefined outcomes and estimator limits

Every primary K in Stage 5 and every primary panel-level K aggregate in Stage 6
was undefined, not a demonstrated peak disappearance. Stage 6 P1–P3 included
abstention; P4 adapted every capacity but had one undefined large-capacity p*.
Its middle fit reached p*=8 once. Mean middle cancellation ratios were .345061
in Stage 5 and .303125/.346585 for Stage 6's adapting primary panels, versus
1 for M/R. Signed cancellation, fit objective, bounds and undefined reasons
must accompany p*, alongside memorization, losses and clipping. No diagnostic
was used to exclude results or select policies. (S5, §§3–4; S6, §4.)

The supported scope is sensitivity within one bounded synthetic task. Three
capacities cannot establish an interior-to-interior peak shift. Estimator
recovery with known simulated gains can study interpretability separately;
it cannot establish model generalization or retrospectively validate/filter
these outcomes. No exact large-LM replication, novelty or publication claim follows.

## Sources: exact paths relative to the project root

- **S4:** `outputs/sequence-weighting-stage4/results-baseline-v05-20260929-01-r2/REPORT.md`
- **S5:** `outputs/sequence-weighting-stage5/results-utility-v06-20260929-01-r1/REPORT.md`
- **S6:** `outputs/sequence-weighting-stage6/results-stability-v07-20260929-01/REPORT.md`
