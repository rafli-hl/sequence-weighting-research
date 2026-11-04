"""Corpus and tokenizer preparation for the natural-text ladder (one owner-approved step; outcome-blind).

  <WSL venv python> -I -B prepare_corpus.py <new output directory>

Verifies the pre-registered WikiText-2 rows files, trains the pre-registered 4,096-token byte-level BPE on the
training split's text (file order, unmodified) twice and requires byte-identical results, freezes it, encodes every article of every split separately, chunks
each article into non-overlapping 129-token windows (remainder dropped) and writes:
  tokenizer.json, {train,validation,test}.u16 (little-endian uint16 token ids, SEQ_TOKENS per sequence),
  CORPUS_MANIFEST.json (per-split article sequence counts and offsets, file hashes, tokenizer hash, versions).
No model, loss or fit is involved. The draws are cut later, from this frozen manifest, by text_data.partition.
"""
import hashlib, json, os, platform, sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import text_plan as plan
import text_data

ROOT = Path('/mnt/d/sequence-weighting-research') if os.name == 'posix' else Path(r'D:\sequence-weighting-research')
def sha(b): return hashlib.sha256(b).hexdigest()


def hf_tokenizer(train_texts):
    """The pre-registered tokenizer, trained with the locked `tokenizers` library. Returns (encode, tokenizer_json_bytes, version)."""
    import tokenizers
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    if tokenizers.__version__ != plan.TOKENIZER['library_version']: raise RuntimeError('tokenizers version differs from the pre-registered one')
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=plan.TOKENIZER['vocab_size'], min_frequency=plan.TOKENIZER['min_frequency'],
                                  special_tokens=list(plan.TOKENIZER['special_tokens']), initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
                                  show_progress=False)
    tok.train_from_iterator(train_texts, trainer=trainer, length=len(train_texts))
    if tok.get_vocab_size() != plan.VOCAB: raise RuntimeError(f'Tokenizer vocabulary is {tok.get_vocab_size()}, not {plan.VOCAB}')
    return (lambda text: tok.encode(text, add_special_tokens=False).ids), tok.to_str().encode('utf-8'), tokenizers.__version__


def prepare(out, root=ROOT, make_tokenizer=hf_tokenizer):
    out = Path(out)
    if out.exists(): raise FileExistsError('Output exists; one-use corpus step')
    texts = {}
    for split, (rel, pinned) in plan.TEXT_ASSETS.items():
        raw = (root / rel).read_bytes()
        if sha(raw) != pinned: raise RuntimeError(f'{rel} differs from its pre-registered SHA-256')
        texts[split] = [r['text'] for r in json.loads(raw)]
    encode, tok_bytes, version = make_tokenizer(texts['train'])
    _, tok_bytes_again, _ = make_tokenizer(texts['train'])          # determinism: the frozen tokenizer must be reproducible
    if tok_bytes_again != tok_bytes: raise RuntimeError('Tokenizer training is not deterministic (two trainings differ)')
    manifest = dict(schema=2, seq_tokens=plan.SEQ_TOKENS, vocab=plan.VOCAB, tokenizer=dict(file='tokenizer.json', sha256=sha(tok_bytes), library_version=version,
                    settings=plan.TOKENIZER), tokenizer_trained_twice_identical=True,
                    text_assets={s: dict(path=r, sha256=h) for s, (r, h) in plan.TEXT_ASSETS.items()},
                    code_sha256={f: sha((HERE / f).read_bytes()) for f in text_data.CODE_FILES},
                    environment=dict(python=platform.python_version(), platform=platform.platform(), TOKENIZERS_PARALLELISM=os.environ.get('TOKENIZERS_PARALLELISM')),
                    splits={})
    files = {'tokenizer.json': tok_bytes}
    for split in ('train', 'validation', 'test'):
        buf = array('H'); arts = []; tokens = dropped = 0
        for i, article in enumerate(text_data.articles(texts[split])):
            ids = encode(article)
            if any(not 0 <= t < plan.VOCAB for t in ids): raise RuntimeError('Token id outside the vocabulary')
            windows = text_data.chunk(ids)
            arts.append(dict(index=i, first=len(buf) // plan.SEQ_TOKENS, sequences=len(windows), tokens=len(ids)))
            for w in windows: buf.extend(w)
            tokens += len(ids); dropped += len(ids) - len(windows) * plan.SEQ_TOKENS
        if sys.byteorder != 'little': buf.byteswap()
        data = buf.tobytes(); files[f'{split}.u16'] = data
        manifest['splits'][split] = dict(file=f'{split}.u16', bytes=len(data), sha256=sha(data), articles=arts, sequences=len(data) // (2 * plan.SEQ_TOKENS),
                                         tokens=tokens, tokens_dropped_as_remainders=dropped)
    m = manifest['splits']
    manifest['checks'] = dict(validation_selected=len(text_data.validation_indices(manifest)), pool_selected=len(text_data.pool_indices(manifest)),
                              train_sequences=m['train']['sequences'], train_groups_possible_at_N=m['train']['sequences'] // plan.N_TRAIN)
    text_data.validate_manifest(manifest, manifest['code_sha256'])          # before anything is written
    raw = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode('utf-8')
    out.mkdir(parents=False)
    for name, data in files.items(): (out / name).write_bytes(data)
    (out / 'CORPUS_MANIFEST.json').write_bytes(raw)
    return manifest, sha(raw)


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('usage: prepare_corpus.py <new output directory>')
    manifest, digest = prepare(Path(sys.argv[1]))
    print(json.dumps(dict(manifest_sha256=digest, tokenizer_sha256=manifest['tokenizer']['sha256'],
                          sequences={s: v['sequences'] for s, v in manifest['splits'].items()}, checks=manifest['checks']), indent=1))
