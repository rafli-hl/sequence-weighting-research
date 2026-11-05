"""Frozen fresh-draw partition of the peak confirmation (owner decision 20261103-03). Stdlib only; no framework, no losses,
no outcomes. Sealed with peak_registry.py and the seed policy before any seed of this study exists; the study source uses a
byte copy (reports/natural-text-peak-seed-registry-20261103-01/SEED_REGISTRY_POLICY.md).

The six fresh groups c01-c06 come from the eligible WikiText-103 training articles (those the corpus manifest does not
exclude), less:
- every article the few-epoch partition assigned to a group, re-derived with the sealed fewepoch_data.partition from the
  few-epoch registry's partition_seed; the re-derivation must equal the few-epoch study's PARTITION_SHA256;
- every remaining article whose full text equals that of an assigned article;
- every copy of any text that occurs more than once among what remains.
The fresh indices are sorted, shuffled with random.Random(partition_seed) (this registry's seed) and assigned whole, in that
order, to c01, ..., c06, each group until it holds at least N sequences (text_data._fill); each group uses its first N
sequences in assignment order. Depends only on per-article sequence counts, text hashes and the two partition seeds
(outcome-blind).
"""
import collections, hashlib, json, random
import fewepoch_data
import fewepoch_plan as fp
import text_data
import wt103_corpus

GROUPS = tuple(f'c{i:02d}' for i in range(1, 7))
N_TRAIN = 16384


def encoded(x): return (json.dumps(x, sort_keys=True, indent=2) + '\n').encode('utf-8')


def assigned_articles(manifest, fewepoch_partition_seed, pin=None):
    """The articles of the few-epoch partition, re-derived with the sealed function. Raises ValueError if it differs from the pin."""
    part = fewepoch_data.partition(manifest, fewepoch_partition_seed)
    if hashlib.sha256(encoded(part)).hexdigest() != (pin or fp.PARTITION_SHA256): raise ValueError('The few-epoch partition differs from its pin')
    return {a for g in part['groups'].values() for a in g['articles']}


def fresh_pool(manifest, assigned):
    """The fresh articles (sorted indices) and what each rule removed."""
    arts = wt103_corpus.eligible_articles(manifest); rows = {a['index']: a for a in manifest['splits']['train']['articles']}
    if not set(assigned) <= {a['index'] for a in arts}: raise ValueError('An assigned article is not eligible')
    unused = [a for a in arts if a['index'] not in assigned]
    assigned_text = {rows[i]['text_sha256'] for i in assigned}
    rest = [a for a in unused if a['text_sha256'] not in assigned_text]
    copies = collections.Counter(a['text_sha256'] for a in rest)
    fresh = [a for a in rest if copies[a['text_sha256']] == 1]
    return dict(articles=sorted(a['index'] for a in fresh), eligible_articles=len(arts), assigned_articles=len(assigned), unused_articles=len(unused),
                removed_text_duplicates_of_assigned=len(unused) - len(rest), removed_repeats_inside_the_pool=len(rest) - len(fresh),
                sets_of_repeats_inside_the_pool=sum(1 for v in copies.values() if v > 1), fresh_articles=len(fresh), fresh_sequences=sum(a['sequences'] for a in fresh))


def partition(manifest, assigned, partition_seed):
    """c01-c06 from the fresh articles. Raises ValueError if they cannot fill six groups at N."""
    pool = fresh_pool(manifest, assigned); rows = {a['index']: a for a in manifest['splits']['train']['articles']}
    counts = {i: rows[i]['sequences'] for i in pool['articles']}; first = {i: rows[i]['first'] for i in pool['articles']}
    order = list(pool['articles']); random.Random(partition_seed).shuffle(order)
    filled = text_data._fill(order, counts, N_TRAIN, len(GROUPS))
    if filled is None: raise ValueError('The fresh articles cannot fill six groups at N')
    groups = {name: dict(articles=arts_in, sequences=[first[a] + k for a in arts_in for k in range(counts[a])][:N_TRAIN]) for name, arts_in in zip(GROUPS, filled)}
    return dict(n=N_TRAIN, groups=groups, pool={k: v for k, v in pool.items() if k != 'articles'}, left_over_articles=len(order) - sum(len(g['articles']) for g in groups.values()))


def disjoint(part, manifest, assigned):
    """By article and by full text: the six groups are disjoint, hold exactly N distinct sequences inside their own articles,
    and touch no excluded article, no assigned article and no text of an assigned article. Raises PermissionError."""
    if sorted(part['groups']) != sorted(GROUPS) or part['n'] != N_TRAIN: raise PermissionError('Partition groups or size differ from the plan')
    rows = {a['index']: a for a in manifest['splits']['train']['articles']}; arts = [a for g in GROUPS for a in part['groups'][g]['articles']]
    if len(arts) != len(set(arts)): raise PermissionError('Groups share an article')
    if set(arts) & set(manifest['exclusions']['articles']): raise PermissionError('A group uses an excluded article')
    if set(arts) & set(assigned): raise PermissionError('A group uses an assigned article')
    texts = [rows[a]['text_sha256'] for a in arts]
    if len(texts) != len(set(texts)): raise PermissionError('Groups share a full text')
    if set(texts) & {rows[a]['text_sha256'] for a in assigned}: raise PermissionError('A group uses the text of an assigned article')
    for g in GROUPS:
        seqs = part['groups'][g]['sequences']
        if len(seqs) != N_TRAIN or len(set(seqs)) != N_TRAIN: raise PermissionError('Group size: ' + g)
        own = {rows[a]['first'] + k for a in part['groups'][g]['articles'] for k in range(rows[a]['sequences'])}
        if not set(seqs) <= own: raise PermissionError("A sequence lies outside its group's articles: " + g)
    return dict(articles=len(arts), groups=len(GROUPS), n=N_TRAIN)
