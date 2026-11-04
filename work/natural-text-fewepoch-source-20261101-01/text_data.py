"""Pure data rules for the natural-text ladder (stdlib; no framework, no losses, no outcomes).

Used by prepare_corpus.py (segmentation and chunking), the activation builder (partition) and the worker (which
re-derives the partition and the shared selections from the frozen corpus manifest and refuses any difference).
"""
import random, re
import text_plan as plan

_HEAD = re.compile(plan.ARTICLE_HEAD)


def is_head(texts, i):
    """A level-1 heading row with an empty row directly before and after it (table and formula rows can match the
    pattern alone; owner decision of 28 Oct 2026)."""
    if not _HEAD.match(texts[i]): return False
    if not plan.HEAD_NEEDS_BLANK_ROWS: return True
    return i > 0 and texts[i - 1] == '' and i + 1 < len(texts) and texts[i + 1] == ''


def articles(texts):
    """Split WikiText rows into articles: a heading row (is_head) starts a new article; rows before the first head
    are dropped. Returns a list of article strings (row texts concatenated unchanged)."""
    out, current = [], None
    for i, t in enumerate(texts):
        if is_head(texts, i):
            if current is not None: out.append(''.join(current))
            current = [t]
        elif current is not None:
            current.append(t)
    if current is not None: out.append(''.join(current))
    return out


def chunk(ids, n=plan.SEQ_TOKENS):
    """Non-overlapping windows of n tokens from the start of one article; the remainder is dropped."""
    return [list(ids[i:i + n]) for i in range(0, len(ids) - n + 1, n)]


def stride(total, k):
    """k indices spread evenly over range(total) (all of them if total <= k)."""
    if total <= k: return list(range(total))
    return [i * total // k for i in range(k)]


def validation_indices(manifest): return stride(manifest['splits']['validation']['sequences'], plan.N_VALIDATION)
def pool_indices(manifest): return stride(manifest['splits']['test']['sequences'], plan.POOL_MAX)


def _fill(order, counts, n, groups):
    filled, current, have = [], [], 0
    for a in order:
        if len(filled) == groups: break
        current.append(a); have += counts[a]
        if have >= n: filled.append(current); current, have = [], 0
    return filled if len(filled) == groups else None


CODE_FILES = ('prepare_corpus.py', 'text_plan.py', 'text_data.py')


def validate_manifest(manifest, code_hashes):
    """The corpus manifest must match the pre-registration: tokenizer settings, vocabulary, sequence length, text
    hashes, the code that produced it (sealed source hashes), the article counts and contiguous article offsets.
    Python, platform and TOKENIZERS_PARALLELISM are recorded, not checked. Raises ValueError."""
    if json_norm(manifest['tokenizer']['settings']) != json_norm(plan.TOKENIZER): raise ValueError('Tokenizer settings differ from the plan')
    if manifest['tokenizer']['library_version'] != plan.TOKENIZER['library_version']: raise ValueError('Tokenizer library version')
    if manifest['vocab'] != plan.VOCAB or manifest['seq_tokens'] != plan.SEQ_TOKENS: raise ValueError('Vocabulary or sequence length')
    if manifest['text_assets'] != {s: dict(path=r, sha256=h) for s, (r, h) in plan.TEXT_ASSETS.items()}: raise ValueError('Text assets differ from the plan')
    if manifest.get('code_sha256') != {f: code_hashes[f] for f in CODE_FILES}: raise ValueError('Corpus was not produced by the sealed code')
    if manifest.get('tokenizer_trained_twice_identical') is not True: raise ValueError('Tokenizer determinism not recorded')
    if {s: len(m['articles']) for s, m in manifest['splits'].items()} != plan.ARTICLE_COUNTS: raise ValueError('Article counts differ from the pre-registered 600/60/60')
    for split, m in manifest['splits'].items():
        first = 0
        for a in m['articles']:
            if a['first'] != first or a['sequences'] < 0: raise ValueError('Article offsets are not contiguous: ' + split)
            first += a['sequences']
        if first != m['sequences'] or m['bytes'] != 2 * plan.SEQ_TOKENS * m['sequences']: raise ValueError('Article counts do not add up: ' + split)
    return manifest


def json_norm(x):
    import json
    return json.loads(json.dumps(x, sort_keys=True))


def partition(manifest, partition_seed):
    """Pre-registered article partition into the eleven groups (t00 first, then d01..d10).

    Articles are shuffled with random.Random(partition_seed) and assigned in that order to the current group until it
    holds at least N sequences; then the next group starts. Each group uses its first N sequences in assignment order.
    N is N_TRAIN, or, if eleven groups cannot be filled, the largest multiple of N_STEP (>= N_FLOOR) that fills them.
    Depends only on per-article sequence counts (outcome-blind)."""
    arts = manifest['splits']['train']['articles']
    counts = {a['index']: a['sequences'] for a in arts}; first = {a['index']: a['first'] for a in arts}
    order = sorted(counts); random.Random(partition_seed).shuffle(order)
    n = plan.N_TRAIN
    while n >= plan.N_FLOOR:
        filled = _fill(order, counts, n, len(plan.GROUPS))
        if filled is not None: break
        n -= plan.N_STEP
    else:
        raise ValueError('Corpus cannot fill eleven groups at the floor N')
    groups = {}
    for name, arts_in in zip(plan.GROUPS, filled):
        seqs = [first[a] + k for a in arts_in for k in range(counts[a])][:n]
        groups[name] = dict(articles=arts_in, sequences=seqs)
    return dict(n=n, fallback=n != plan.N_TRAIN, groups=groups, unused_articles=len(order) - sum(len(g['articles']) for g in groups.values()))
