"""Frozen fresh-draw partition for the late-turn confirmation (owner decisions 20261031-02, item 1). Stdlib only; no
framework, no losses, no outcomes. Sealed with lateturn_registry.py before any seed of the confirmation exists; the
study source uses a byte copy.

The four fresh groups f01-f04 are cut from the WikiText-2 training articles that the natural-text ladder's partition
(t00, d01-d10) does not use:
- the used articles are re-derived with the sealed text_data.partition from the ladder registry's partition_seed and the
  frozen corpus manifest (they must equal the seen partition, PARTITION.json 5f9f2646...);
- the unused article indices are sorted, shuffled with random.Random(partition_seed) (this registry's seed), and assigned
  in that order to f01, f02, f03, f04 until each holds at least N sequences; each group uses its first N sequences in
  assignment order; articles left after f04 stay unused;
- N is 1536, or, if four groups cannot be filled, the largest multiple of 16 (>= 512) that fills them.
Depends only on per-article sequence counts and the two partition seeds (outcome-blind).
"""
import random
import text_plan as plan
import text_data

FRESH_GROUPS = ('f01', 'f02', 'f03', 'f04')
N_TRAIN, N_STEP, N_FLOOR = plan.N_TRAIN, plan.N_STEP, plan.N_FLOOR      # 1536, 16, 512: the seen partition's rule


def seen_partition(manifest, seen_partition_seed):
    """The natural-text ladder's partition (t00, d01-d10), re-derived with the sealed function."""
    return text_data.partition(manifest, seen_partition_seed)


def used_articles(seen):
    return {a for g in seen['groups'].values() for a in g['articles']}


def fresh_partition(manifest, used, partition_seed):
    """f01-f04 from the training articles not in `used`. Returns n, step_down, groups (articles in assignment order and
    their first n sequences), and the counts of unused and left-over articles. Raises ValueError below the floor."""
    arts = manifest['splits']['train']['articles']
    counts = {a['index']: a['sequences'] for a in arts}; first = {a['index']: a['first'] for a in arts}
    if not set(used) <= set(counts): raise ValueError('Used articles are not training articles')
    order = sorted(set(counts) - set(used)); random.Random(partition_seed).shuffle(order)
    n = N_TRAIN
    while n >= N_FLOOR:
        filled = text_data._fill(order, counts, n, len(FRESH_GROUPS))
        if filled is not None: break
        n -= N_STEP
    else:
        raise ValueError('The unused articles cannot fill four groups at the floor N')
    groups = {}
    for name, arts_in in zip(FRESH_GROUPS, filled):
        seqs = [first[a] + k for a in arts_in for k in range(counts[a])][:n]
        groups[name] = dict(articles=arts_in, sequences=seqs)
    assigned = sum(len(g['articles']) for g in groups.values())
    return dict(n=n, step_down=n != N_TRAIN, groups=groups, unused_articles=len(order), unused_sequences=sum(counts[a] for a in order),
                left_over_articles=len(order) - assigned)
