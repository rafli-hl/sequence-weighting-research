# Matched-progress confirmation: disclosure figures on the real draws

**Owner decision:** 20261104-02, item 1. Outcome-blind: from the corpus manifest and the seeds only. **Measured** on m01–m06 at N = 16,384. Carried by hand into the results report.

| Group | Articles | Sequences used | Tied weights, before / after division by numpy's mean (limit 16) |
|---|---|---|---|
| m01 | 407 | 16,384 | 3 / 3 |
| m02 | 388 | 16,384 | 3 / 4 |
| m03 | 376 | 16,384 | 0 / 0 |
| m04 | 425 | 16,384 | 1 / 1 |
| m05 | 421 | 16,384 | 1 / 1 |
| m06 | 395 | 16,384 | 1 / 1 |

## Identical full text

- **Sets across the fresh groups:** 0.
- **Fresh texts equal to an assigned article's:** 0.
- **Repeated inside a group:** 0.

The rule removes these, so zero is what it should give.

## Titles, which the rule does not remove

- **Fresh articles sharing a title with an article of N5 or N6, with a different text:** 0.
- **Titles shared across the fresh groups:** 0.

## Not measured

**Exact token sequences and 64-token runs,** which N6's disclosure measured. They would read the corpus's split files, and this step may open only the manifest. So how far token runs recur across m01–m06, N5, N6, the validation set and the pool is not known here. For scale, N6's groups had 64-token runs recurring in another fresh group at a mean of 0.15%. That is N6's figure and not a measurement of these draws.

**Shared by design:** every draw shares the validation set, the pool and the tokenizer with each other and with the earlier natural-text studies.

**Tied weights:** from the stdlib draw and the IEEE cast, without Torch. The weights used are after division, by Torch's mean, so the counts from real Torch can differ by one or so.

**Limit.** Draws are treated as independent in every interval. These figures do not measure how far that is true.
