"""Frozen plan of the WikiText-103 acquisition (owner decisions 20261101-01 and -02, D6). Pure constants.

Three owner-run steps, under one owner approval:
- A1 (native Windows, stdlib): download the two WikiText-103 raw training parquet files from the project's pinned dataset
  revision, each checked against its pinned size and SHA-256 before it is renamed into place;
- A2 (native Windows, pyarrow): read their `text` column in file order and write the rows as gzip JSON lines; the same
  extraction is first checked on the local WikiText-2 parquet files against the pinned WikiText-2 rows files;
- A3 (WSL, tokenizers 0.21.4): encode with the frozen 4,096-token tokenizer of the natural-text corpus (no retraining), after
  checking that it reproduces that corpus byte for byte; segment and chunk with the sealed text_data rules; exclude every
  article equal by title row or full text to a WikiText-2 article; write the corpus and its manifest.
WikiText-103's validation and test files are byte-identical to WikiText-2's (same LFS SHA-256 at the pinned revision), so they
are not downloaded: the corpus reuses the natural-text corpus's validation and test sequences, unchanged.
Importing this module reads nothing and launches nothing.
"""
EXECUTION_ENABLED = False

DATASET = 'Salesforce/wikitext'
CONFIG = 'wikitext-103-raw-v1'
REVISION = 'b08601e04326c79dfdd32d625aee71d232d685c3'        # the project's WikiText-2 pin (work/text-assets/provenance.json)
LICENSE = 'CC-BY-SA-3.0 (GFDL also listed on the dataset card)'
METADATA = ('work/text-assets/dataset-metadata.json', 'fa98cee7e9bdeb3b4bd1572ca64ffb69bddbe87d383dcafcafb253e823f46bf8')   # saved 28 Sep 2026; sizes and LFS pins below
DOWNLOADS = (
    dict(name='train-00000-of-00002.parquet', bytes=156987808, sha256='74da360f23826045b3e6ac6375411fdb15f003030aa74f2596ed08b857cb9212'),
    dict(name='train-00001-of-00002.parquet', bytes=157088770, sha256='ba090ac30dbf5461e8dcbdd1a1b8e6f3cf9c2c756d64f0c1220450acd514f720'))
URL = 'https://huggingface.co/datasets/{dataset}/resolve/{revision}/{config}/{name}'
TRAIN_ROWS = 1801350                                          # wikitext-103-raw-v1 train num_examples (saved dataset metadata)
# WikiText-103's validation and test parquet files equal WikiText-2's at the pinned revision (the same LFS SHA-256), and the
# local WikiText-2 copies have these hashes (work/text-assets/provenance.json).
SHARED_SPLITS = dict(validation='204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c', test='5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91')
# The local WikiText-2 parquet files (the A2 method check reads them) and the WikiText-2 rows files they must reproduce.
WT2_PARQUET = dict(train=('work/text-assets/dataset/train-00000-of-00001.parquet', 'e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7'),
                   validation=('work/text-assets/dataset/validation-00000-of-00001.parquet', '204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c'),
                   test=('work/text-assets/dataset/test-00000-of-00001.parquet', '5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91'))
# The natural-text corpus (WikiText-2, 28 Oct 2026): its manifest, the frozen tokenizer, and its three sequence files.
WT2_CORPUS = 'work/runs/natural-text-corpus-20261028-01'
WT2_MANIFEST_SHA256 = '72daa1e174caa346494fb9a6cd0ded4ed192038a8918e4569a2a4ddb67a0834f'
TOKENIZER_SHA256 = 'cd642ca2b78a76e880adf07efb425bd2db741248cbf537aed0538c9421cca146'
WT2_SPLIT_SHA256 = dict(validation='bbbfdbc09a6b32730d2230716e396fd9e4860e1e80d17932f202458655017521', test='ceaf9d691dd53cd3322bbec431703161672b77e966b9d76c2489fb961846c5cb')   # its validation.u16 and test.u16
WT2_TRAIN_ARTICLES = 600

# Outputs (each must not exist before its step).
ASSETS = 'work/text-assets-wt103'                             # A1: dataset/ and A1_RECORD.json; A2: train-rows.jsonl.gz and A2_RECORD.json
ROWS_FILE = 'train-rows.jsonl.gz'
CORPUS = 'work/runs/natural-text-corpus-wt103-20261101-01'    # A3
SOURCE = 'work/natural-text-wt103-acquisition-source-20261101-01'
APPROVAL_PATTERN = r'^OWNER-[0-9]{8}-[A-Z0-9-]{2,60}$'
GZIP_LEVEL = 6
