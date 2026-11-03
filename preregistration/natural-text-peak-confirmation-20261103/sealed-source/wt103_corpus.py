"""A3: the WikiText-103 corpus with the frozen natural-text tokenizer (WSL; tokenizers 0.21.4), and the corpus rules the
few-epoch study reads (stdlib). Owner-run after A2, under the same approval.

  <WSL venv python> -I -B wt103_corpus.py --approval-id <ID> --expected-subject <SUBJECT>

Order of work (every refusal comes before anything is written):
1. A2's record, bound to A1's, the same approval and source; the rows file re-hashed.
2. The natural-text corpus manifest (pinned) and its frozen tokenizer (pinned); no tokenizer is trained.
3. Reproduction: the frozen tokenizer, loaded from its file, re-encodes the pinned WikiText-2 rows of every split into the
   natural-text corpus's train, validation and test files byte for byte (the sealed text_data segmentation and chunking).
4. The WikiText-103 training rows (1,801,350) are split into articles (text_data.articles), each encoded separately and
   chunked into non-overlapping 129-token sequences (remainder dropped).
5. Exclusions: a WikiText-103 training article is excluded if its title row or its full text equals that of any WikiText-2
   article (train, validation or test). Every one of WikiText-2's 600 training articles must be found by full text, or the
   step stops.
6. The corpus folder: tokenizer.json (a copy), train.u16, validation.u16 and test.u16 (copies of the natural-text corpus's
   files, which equal WikiText-103's validation and test splits), and CORPUS_MANIFEST.json, written last into <folder>.part,
   which is renamed into place only when complete; a part folder left by an interrupted attempt is kept as
   <folder>.failed-<k>, recorded in the manifest, and the step proceeds (review 1, finding 4, and its confirmation, N1).
Fixture mode (tests only) needs a FIXTURE id, targets outside the project root, a stand-in encoder and a fixture corpus.
"""
import argparse, json, os, platform, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import acquire_plan as ap
import acquire_common as ac
import text_plan as plan
import text_data

CODE_FILES = ('wt103_corpus.py', 'acquire_plan.py', 'acquire_common.py', 'a1_download.py', 'a2_rows.py', 'text_plan.py', 'text_data.py')
KIND = 'WikiText-103 raw training split with the frozen natural-text tokenizer'
sha = ac.sha


def hf_encoder(tokenizer_bytes):
    """The frozen tokenizer from its file (tokenizers 0.21.4, the pre-registered version); encode without special tokens."""
    import tokenizers
    if tokenizers.__version__ != plan.TOKENIZER['library_version']: raise SystemExit('tokenizers version differs from the pre-registered one')
    tok = tokenizers.Tokenizer.from_str(tokenizer_bytes.decode('utf-8'))
    if tok.get_vocab_size() != plan.VOCAB: raise SystemExit('Frozen tokenizer vocabulary differs')
    return lambda text: tok.encode(text, add_special_tokens=False).ids


def title_of(article): return article.split('\n', 1)[0].strip()


def encode_articles(articles, encode, extra=False):
    """prepare_corpus's encoding of one split: each article encoded separately and chunked. Returns (bytes, rows)."""
    buf = array('H'); rows = []; tokens = dropped = 0
    for i, article in enumerate(articles):
        ids = encode(article)
        if any(not 0 <= t < plan.VOCAB for t in ids): raise SystemExit('Token id outside the vocabulary')
        windows = text_data.chunk(ids)
        row = dict(index=i, first=len(buf) // plan.SEQ_TOKENS, sequences=len(windows), tokens=len(ids))
        if extra: row.update(title_sha256=sha(title_of(article).encode('utf-8')), text_sha256=sha(article.encode('utf-8')))
        rows.append(row)
        for w in windows: buf.extend(w)
        tokens += len(ids); dropped += len(ids) - len(windows) * plan.SEQ_TOKENS
    if sys.byteorder != 'little': buf.byteswap()
    return buf.tobytes(), rows, tokens, dropped


def wt2_articles(root):
    """Every WikiText-2 article of each split, from the pinned rows files (text_data segmentation)."""
    out = {}
    for split, (rel, pin) in plan.TEXT_ASSETS.items():
        raw = (Path(root) / rel).read_bytes()
        if sha(raw) != pin: raise SystemExit('WikiText-2 rows file differs from its pin: ' + rel)
        out[split] = text_data.articles([r['text'] for r in json.loads(raw)])
    return out


def exclusions(rows103, wt2):
    """Per WikiText-103 training article, the reasons it is excluded (title row or full text equal to a WikiText-2
    article's), and the WikiText-2 training articles found by full text."""
    ident = {s: (set(sha(title_of(a).encode('utf-8')) for a in arts), set(sha(a.encode('utf-8')) for a in arts)) for s, arts in wt2.items()}
    reasons = {}
    for r in rows103:
        why = [f'wikitext2_{s}_{kind}' for s, (titles, texts) in ident.items() for kind, hit in (('title', r['title_sha256'] in titles), ('text', r['text_sha256'] in texts)) if hit]
        if why: reasons[str(r['index'])] = why
    texts103 = {r['text_sha256']: r['index'] for r in rows103}
    found = {k: texts103.get(sha(a.encode('utf-8'))) for k, a in enumerate(wt2['train'])}
    return reasons, found


def build(approval_id, expected_subject, fixture=False, assets=None, out=None, root=ac.ROOT, make_encoder=hf_encoder, wt2_corpus=None, wt2_manifest_sha256=None,
          tokenizer_sha256=None, expected_rows=ap.TRAIN_ROWS, here=HERE):
    ac.check_approval(approval_id, fixture)
    if not fixture and any(x is not None for x in (wt2_corpus, wt2_manifest_sha256, tokenizer_sha256)): raise SystemExit('Real mode binds the plan pins only')
    ac.check_source(here, expected_subject)
    assets = ac.place(fixture, assets, ap.ASSETS, root); out = ac.place(fixture, out, ap.CORPUS, root)
    wt2_corpus = Path(wt2_corpus) if wt2_corpus is not None else Path(root) / ap.WT2_CORPUS
    wt2_manifest_sha256 = wt2_manifest_sha256 or ap.WT2_MANIFEST_SHA256; tokenizer_sha256 = tokenizer_sha256 or ap.TOKENIZER_SHA256
    a2, a2_sha = ac.read_record(assets / 'A2_RECORD.json', 'A2', approval_id, expected_subject)
    a1, a1_sha = ac.read_record(assets / 'A1_RECORD.json', 'A1', approval_id, expected_subject)
    if a2['a1_record_sha256'] != a1_sha: raise SystemExit('A2 was not made from this A1 record')
    h, n = ac.sha_file(assets / ap.ROWS_FILE)
    if (h, n) != (a2['rows_file']['sha256'], a2['rows_file']['bytes']) or a2['rows'] != expected_rows: raise SystemExit('Rows file differs from A2 record')
    if out.exists(): raise SystemExit('Corpus folder exists; one-use step')
    man_raw = (wt2_corpus / 'CORPUS_MANIFEST.json').read_bytes()
    if sha(man_raw) != wt2_manifest_sha256: raise SystemExit('Natural-text corpus manifest differs from its pin')
    wt2_man = json.loads(man_raw); tok_raw = (wt2_corpus / 'tokenizer.json').read_bytes()
    if sha(tok_raw) != tokenizer_sha256 or sha(tok_raw) != wt2_man['tokenizer']['sha256']: raise SystemExit('Frozen tokenizer differs from its pin')
    encode = make_encoder(tok_raw)
    # 3. The frozen tokenizer reproduces the natural-text corpus, split by split.
    wt2 = wt2_articles(root); shared = {}
    for split in ('train', 'validation', 'test'):
        data, rows, _, _ = encode_articles(wt2[split], encode); m = wt2_man['splits'][split]
        if sha(data) != m['sha256'] or len(data) != m['bytes'] or rows != m['articles']: raise SystemExit('The frozen tokenizer does not reproduce the natural-text corpus: ' + split)
        b = (wt2_corpus / m['file']).read_bytes()
        if b != data: raise SystemExit('Natural-text corpus file differs from its manifest: ' + split)
        shared[split] = b
    # 4. WikiText-103 training articles.
    import a2_rows
    texts = a2_rows.read_rows(assets / ap.ROWS_FILE)
    if len(texts) != expected_rows: raise SystemExit('Rows file row count differs')
    arts = text_data.articles(texts); del texts
    data, rows103, tokens, dropped = encode_articles(arts, encode, extra=True)
    # 5. Exclusions and the containment check.
    reasons, found = exclusions(rows103, wt2); del arts
    missing = [k for k, v in found.items() if v is None]
    if missing: raise SystemExit(f'{len(missing)} of the {len(found)} WikiText-2 training articles are not in WikiText-103 by full text (first: {missing[:5]}); stopped, nothing written')
    excluded = sorted(int(k) for k in reasons); eligible = [r for r in rows103 if str(r['index']) not in reasons]
    part = out.with_name(out.name + '.part')
    kept = f'{out.name}.failed-{1 + sum(1 for _ in out.parent.glob(out.name + ".failed-*"))}' if part.exists() else None
    manifest = dict(schema=3, kind=KIND, seq_tokens=plan.SEQ_TOKENS, vocab=plan.VOCAB, approval_id=approval_id, fixture=bool(fixture), source_subject_sha256=expected_subject,
                    tokenizer=dict(file='tokenizer.json', sha256=sha(tok_raw), library_version=plan.TOKENIZER['library_version'], settings=plan.TOKENIZER,
                                   source=dict(corpus=ap.WT2_CORPUS, manifest_sha256=sha(man_raw)), retrained=False),
                    sources=dict(dataset=ap.DATASET, config=ap.CONFIG, revision=ap.REVISION, license=ap.LICENSE, a1_record_sha256=a1_sha, a2_record_sha256=a2_sha,
                                 rows=dict(path=ap.ROWS_FILE, sha256=a2['rows_file']['sha256'], rows=expected_rows),
                                 validation_and_test='the natural-text corpus files (WikiText-103 validation and test parquet files equal WikiText-2\'s at the pinned revision)'),
                    code_sha256={f: sha((Path(here) / f).read_bytes()) for f in CODE_FILES},
                    environment=dict(python=platform.python_version(), platform=platform.platform(), TOKENIZERS_PARALLELISM=os.environ.get('TOKENIZERS_PARALLELISM')),
                    splits=dict(train=dict(file='train.u16', bytes=len(data), sha256=sha(data), articles=rows103, sequences=len(data) // (2 * plan.SEQ_TOKENS),
                                           tokens=tokens, tokens_dropped_as_remainders=dropped),
                                validation=wt2_man['splits']['validation'], test=wt2_man['splits']['test']),
                    wikitext2=dict(train_articles=len(found), train_articles_found_by_text=len(found) - len(missing), found_at={str(k): v for k, v in found.items()}),
                    exclusions=dict(rule='excluded if the title row or the full text equals that of any WikiText-2 article (train, validation or test)',
                                    articles=excluded, reasons=reasons, count=len(excluded)),
                    checks=dict(tokenizer_reproduces_natural_text_corpus=True, eligible_articles=len(eligible), eligible_sequences=sum(r['sequences'] for r in eligible)),
                    interrupted_attempt_kept=kept)
    validate_manifest(manifest, manifest['code_sha256'], sha(man_raw), sha(tok_raw), wt2_man)
    raw = (json.dumps(manifest, sort_keys=True, indent=1) + '\n').encode('utf-8')
    if kept is not None: os.replace(part, out.with_name(kept))
    part.mkdir(parents=False)
    (part / 'tokenizer.json').write_bytes(tok_raw); (part / 'train.u16').write_bytes(data)
    (part / 'validation.u16').write_bytes(shared['validation']); (part / 'test.u16').write_bytes(shared['test'])
    (part / 'CORPUS_MANIFEST.json').write_bytes(raw)
    os.replace(part, out)
    return manifest, sha(raw)


def validate_manifest(manifest, code_hashes, wt2_manifest_sha256=None, tokenizer_sha256=None, wt2_manifest=None):
    """The WikiText-103 corpus manifest matches its pre-registration: kind, frozen tokenizer, vocabulary and sequence
    length, the sealed code, contiguous article offsets, the validation and test entries of the natural-text corpus, all
    600 WikiText-2 training articles found and excluded, and exclusions consistent with their reasons. The pins default to
    the plan's, read at call time. Raises ValueError."""
    wt2_manifest_sha256 = wt2_manifest_sha256 or ap.WT2_MANIFEST_SHA256; tokenizer_sha256 = tokenizer_sha256 or ap.TOKENIZER_SHA256
    if manifest.get('schema') != 3 or manifest.get('kind') != KIND: raise ValueError('Not a WikiText-103 corpus manifest')
    t = manifest['tokenizer']
    if t['sha256'] != tokenizer_sha256 or t['retrained'] is not False or t['source']['manifest_sha256'] != wt2_manifest_sha256: raise ValueError('Tokenizer is not the frozen one')
    if json.loads(json.dumps(t['settings'], sort_keys=True)) != json.loads(json.dumps(plan.TOKENIZER, sort_keys=True)) or t['library_version'] != plan.TOKENIZER['library_version']: raise ValueError('Tokenizer settings')
    if manifest['vocab'] != plan.VOCAB or manifest['seq_tokens'] != plan.SEQ_TOKENS: raise ValueError('Vocabulary or sequence length')
    if manifest.get('code_sha256') != {f: code_hashes[f] for f in CODE_FILES}: raise ValueError('Corpus was not produced by the sealed code')
    if (manifest['sources']['dataset'], manifest['sources']['config'], manifest['sources']['revision']) != (ap.DATASET, ap.CONFIG, ap.REVISION): raise ValueError('Dataset source')
    for split, m in manifest['splits'].items():
        first = 0
        for a in m['articles']:
            if a['first'] != first or a['sequences'] < 0: raise ValueError('Article offsets are not contiguous: ' + split)
            first += a['sequences']
        if first != m['sequences'] or m['bytes'] != 2 * plan.SEQ_TOKENS * m['sequences']: raise ValueError('Article counts do not add up: ' + split)
    if [a['index'] for a in manifest['splits']['train']['articles']] != list(range(len(manifest['splits']['train']['articles']))): raise ValueError('Article indices')
    if wt2_manifest is not None and any(manifest['splits'][s] != wt2_manifest['splits'][s] for s in ('validation', 'test')): raise ValueError('Validation or test split differs from the natural-text corpus')
    if any(manifest['splits'][s]['sha256'] != ap.WT2_SPLIT_SHA256[s] for s in ('validation', 'test')): raise ValueError('Validation or test split differs from the natural-text corpus pins')
    w = manifest['wikitext2']; ex = manifest['exclusions']
    if w['train_articles'] != ap.WT2_TRAIN_ARTICLES or w['train_articles_found_by_text'] != ap.WT2_TRAIN_ARTICLES: raise ValueError('Not every WikiText-2 training article was found')
    if any(str(v) not in ex['reasons'] for v in w['found_at'].values()): raise ValueError('A WikiText-2 training article is not excluded')
    if ex['articles'] != sorted(int(k) for k in ex['reasons']) or ex['count'] != len(ex['articles']) or any(not v for v in ex['reasons'].values()): raise ValueError('Exclusions differ from their reasons')
    return manifest


def eligible_articles(manifest):
    """Training articles not excluded, in index order, with their sequence counts and offsets."""
    ex = set(manifest['exclusions']['articles'])
    return [a for a in manifest['splits']['train']['articles'] if a['index'] not in ex]


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--approval-id', required=True); p.add_argument('--expected-subject', required=True)
    a = p.parse_args()
    manifest, digest = build(a.approval_id, a.expected_subject)
    print(json.dumps(dict(manifest_sha256=digest, sequences={s: v['sequences'] for s, v in manifest['splits'].items()}, excluded=manifest['exclusions']['count'],
                          checks=manifest['checks']), indent=1))
