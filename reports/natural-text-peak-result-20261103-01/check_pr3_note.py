"""Checks NOTE_PUBLIC_REGISTRATION_EDITS.md against the saved GitHub responses and the local files. Reads only; writes PR3_NOTE_CHECK.json next to this script.
Network: none. The responses in pr3-gh-snapshot-20261104/ were saved by read-only gh calls on 4 Nov 2026.

  python -I -B check_pr3_note.py
"""
import datetime, hashlib, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent; R = HERE.parents[1]; SNAP = HERE / 'pr3-gh-snapshot-20261104'; APP = R / 'reports/natural-text-peak-analysis-approval-20261103-01'; SRC = R / 'work/natural-text-peak-source-20261103-01'
load = lambda p: json.loads(Path(p).read_bytes().decode('utf-8')); sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
stamp = lambda s: datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
pr = load(SNAP / 'pr.json'); edits = load(SNAP / 'edits.json')['data']['repository']['pullRequest']; comments = load(SNAP / 'comments.json'); inline = load(SNAP / 'review_comments.json'); timeline = load(SNAP / 'timeline.json')
owner = [c for c in comments if c['id'] == 6622066939][0]; pinned = load(APP / 'pinned-records/PUBLIC_PREREGISTRATION_CHECK.json'); result = (HERE / 'RESULT.md').read_text(encoding='utf-8'); note = (HERE / 'NOTE_PUBLIC_REGISTRATION_EDITS.md').read_text(encoding='utf-8')
section_7f = result.split('### 7f.')[1].split('## 8.')[0]; written = stamp(re.search(r'`ANALYSIS\.json` was written at (\S+Z)\.', result).group(1)); nodes = edits['userContentEdits']['nodes']
headings = re.findall(r'^## \d+\. (.+)$', result, re.M)
order = [('NOT_OVERFIT per arm', 'NOT_OVERFIT per arm'), ('the primary', 'The primary'), ('the control', 'The control'), ('D3 with its gap caveat', 'D3, with its gap caveat'), ('the sealed readings', 'The sealed readings'), ('other secondaries', 'Other secondaries'), ('disclosures', 'Disclosures'), ('operations', 'Operations'), ('limitations', 'Limitations'), ('how the numbers were checked', 'How these numbers were checked')]
listed = owner['body'].split('Its section order is:')[1].split('. The analysis itself')[0]
cases = {
    'the description was last edited at 2026-11-04T03:52:23Z, by rafli-hl': edits['lastEditedAt'] == '2026-11-04T03:52:23Z' and edits['editor']['login'] == 'rafli-hl',
    'the description now gives the narrower reading': 'It speaks only to the two rates tested (3e-4 and 1e-4)' in pr['body'],
    'the description no longer has the looser words': 'learning-rate artifact' not in pr['body'],
    'the description now gives the timing': 'about 22 minutes **after** Run C2 ended' in pr['body'],
    'the edit history keeps the looser words, in the version before the last edit': 'whether the drop at 768 is a learning-rate artifact' in nodes[1]['diff'] and 'whether the drop at 768 is a learning-rate artifact' in nodes[2]['diff'] and 'learning-rate artifact' not in nodes[0]['diff'],
    'the addendum comment is by rafli-hl, at 2026-11-04T03:52:24Z, not edited since': owner['user']['login'] == 'rafli-hl' and owner['created_at'] == owner['updated_at'] == '2026-11-04T03:52:24Z',
    'the comment names the layout by the hash of the local file': sha(APP / 'make_results_report.py') in owner['body'],
    'the comment names the analysis by the hash of the local file': sha(SRC / 'peak_analysis.py') in owner['body'],
    'the section order in the comment equals the headings of RESULT.md': len(headings) == len(order) and all(c in listed and h.startswith(r) or (c in listed and r in h) for (c, r), h in zip(order, headings)) and [listed.index(c) for c, _ in order] == sorted(listed.index(c) for c, _ in order),
    'the edit and the comment came before ANALYSIS.json was written': stamp(edits['lastEditedAt']) < written and stamp(owner['created_at']) < written,
    'ANALYSIS.json came 288 s after the comment': (written - stamp(owner['created_at'])).total_seconds() == 288,
    'the pull request head and merge time are those of the pinned check': pr['head_sha'] == pinned['head_sha'] if 'head_sha' in pinned else pr['head_sha'] in json.dumps(pinned),
    'no commit was added after the merge': [e.get('sha') for e in timeline if e.get('event') == 'committed'][-1] == pr['head_sha'] and stamp(pr['merged_at']) < stamp(owner['created_at']),
    'section 7f has the sentence on the layout': '**This layout is not in it.**' in section_7f,
    'section 7f has the sentence on the looser wording': '**The wording there is looser than the protocol' in section_7f,
    'section 7f mentions neither the edit nor the comment': '6622066939' not in section_7f and 'edited' not in section_7f and '03:52' not in section_7f,
    'two inline comments from the review bot, at the two places quoted': sorted((c['user']['login'], c['path'].rsplit('/', 1)[1], c.get('line')) for c in inline) == [('chatgpt-codex-connector[bot]', 'README.md', 25), ('chatgpt-codex-connector[bot]', 'peak_analysis.py', 59)],
    'the report refuses unless both terminals are the approved ones': 'ANALYSIS.json does not bind the real terminals of Runs C1 and C2' in (APP / 'make_results_report.py').read_text(encoding='utf-8'),
    'the sealed README says what the bot quotes': 'no activation or run of this study exists' in (SRC / 'README.md').read_text(encoding='utf-8'),
    'the note names the hash of RESULT.md': sha(HERE / 'RESULT.md') in note,
}
out = dict(schema=1, purpose='The note on the pull request edits, checked against the saved responses and the local files', result_md_sha256=sha(HERE / 'RESULT.md'), snapshot={p.name: sha(p) for p in sorted(SNAP.iterdir())}, cases=cases, passed=sum(cases.values()), total=len(cases), verdict='PASS' if all(cases.values()) else 'FAIL')
(HERE / 'PR3_NOTE_CHECK.json').write_bytes((json.dumps(out, indent=1) + '\n').encode('utf-8'))
for k, v in cases.items(): print('PASS' if v else 'FAIL', k)
print(out['verdict'], out['passed'], 'of', out['total'])
