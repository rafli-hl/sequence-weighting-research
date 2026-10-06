"""Complete destination checks without changing historical research records."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
processes = subprocess.check_output(['ps', '-eo', 'pid,args'], text=True)
conflicts = [s for s in processes.splitlines() if any(x in s for x in
             ['-m pip install', 'mechanism.py calibrate', 'mechanism.py confirm', 'text_check.py --'])]
if conflicts:
    raise RuntimeError('Existing installation/training process: ' + '\n'.join(conflicts))
print('No competing installer or historical training process.', flush=True)
result = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True, check=True)
(ROOT/'migration/PACKAGE_CHECK.txt').write_text(result.stdout, encoding='utf-8')
lock = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
(ROOT/'migration/environment-lock-D.txt').write_text(lock, encoding='utf-8')
for script, args in [('outputs/sequence-weighting-pilot/check_runtime.py',
                      ['--output', str(ROOT/'migration/RUNTIME_CHECK_D.json')]),
                     ('migration/validate_models.py', [])]:
    subprocess.run([sys.executable, str(ROOT/script), *args], cwd=ROOT, check=True)
(ROOT/'migration/STATUS.md').write_text(
    '# Migration status\n\nRuntime verification completed from the D: project.\n'
    'PACKAGE_CHECK.txt, RUNTIME_CHECK_D.json and MODEL_CHECK_D.json pass.\n'
    'Research files retain the prior SHA256 migration verification.\n', encoding='utf-8')
