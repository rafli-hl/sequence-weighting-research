"""Frozen partition of the few-epoch study (stdlib; no framework, no losses, no outcomes). Sealed with the registry tool
and the seed policy before any seed exists (reports/natural-text-fewepoch-seed-registry-20261101-01/SEED_REGISTRY_POLICY.md).

The eligible WikiText-103 training articles (those the corpus manifest does not exclude) are sorted, shuffled with
random.Random(partition_seed) and assigned whole, in that order, to t00, d01, ..., d10, each group until it holds at least
N_FILL sequences (text_data._fill). Each group records its first N_FILL sequences in assignment order; a run uses the first N.
Depends only on per-article sequence counts and the partition seed (outcome-blind).
"""
import random
import text_data
import wt103_corpus
import fewepoch_plan as fp


def partition(manifest, partition_seed):
    arts = wt103_corpus.eligible_articles(manifest)
    counts = {a['index']: a['sequences'] for a in arts}; first = {a['index']: a['first'] for a in arts}
    order = sorted(counts); random.Random(partition_seed).shuffle(order)
    filled = text_data._fill(order, counts, fp.N_FILL, len(fp.GROUPS))
    if filled is None: raise ValueError('The eligible articles cannot fill eleven groups at N_FILL')
    groups = {}
    for name, arts_in in zip(fp.GROUPS, filled):
        groups[name] = dict(articles=arts_in, sequences=[first[a] + k for a in arts_in for k in range(counts[a])][:fp.N_FILL])
    assigned = sum(len(g['articles']) for g in groups.values())
    return dict(n_fill=fp.N_FILL, groups=groups, eligible_articles=len(order), unused_articles=len(order) - assigned)


def sequences(partition, group, n):
    if n > partition['n_fill']: raise ValueError('N exceeds the filled group size')
    return partition['groups'][group]['sequences'][:n]


def disjoint(partition, manifest):
    """By article: the eleven groups are disjoint, use no excluded article, and each holds exactly N_FILL distinct
    sequences, every one inside its own group's articles. Raises PermissionError."""
    if sorted(partition['groups']) != sorted(fp.GROUPS) or partition['n_fill'] != fp.N_FILL: raise PermissionError('Partition groups or size differ from the plan')
    arts = [a for g in fp.GROUPS for a in partition['groups'][g]['articles']]
    if len(arts) != len(set(arts)): raise PermissionError('Groups share an article')
    if set(arts) & set(manifest['exclusions']['articles']): raise PermissionError('A group uses an excluded article')
    offsets = {a['index']: (a['first'], a['sequences']) for a in manifest['splits']['train']['articles']}
    for g in fp.GROUPS:
        seqs = partition['groups'][g]['sequences']
        if len(seqs) != fp.N_FILL or len(set(seqs)) != len(seqs): raise PermissionError('Group size: ' + g)
        own = {offsets[a][0] + k for a in partition['groups'][g]['articles'] for k in range(offsets[a][1])}
        if not set(seqs) <= own: raise PermissionError("A sequence lies outside its group's articles: " + g)
    return dict(articles=len(arts), groups=len(fp.GROUPS), n_fill=fp.N_FILL)
