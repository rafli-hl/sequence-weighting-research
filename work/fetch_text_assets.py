import concurrent.futures as cf
import hashlib,json,subprocess
from pathlib import Path
root=Path('work/text-assets'); (root/'model').mkdir(exist_ok=True); (root/'dataset').mkdir(exist_ok=True)
model=json.loads((root/'model-metadata.json').read_text())
dataset=json.loads((root/'dataset-metadata.json').read_text())
files=[]
for f in model['siblings']:
 if f['rfilename'] in ['config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','model.safetensors']:
  files.append(('model',f,f'https://huggingface.co/EleutherAI/pythia-70m/resolve/{model["sha"]}/{f["rfilename"]}'))
for f in dataset['siblings']:
 if f['rfilename'].startswith('wikitext-2-raw-v1/'):
  files.append(('dataset',f,f'https://huggingface.co/datasets/Salesforce/wikitext/resolve/{dataset["sha"]}/{f["rfilename"]}'))
def fetch(item):
 kind,f,url=item; p=root/kind/Path(f['rfilename']).name
 for attempt in range(10):
  if p.exists() and p.stat().st_size==f['size']: break
  r=subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--max-time','120','--continue-at','-','--output',str(p),url])
  if r.returncode==0: break
 else: raise RuntimeError('Download failed: '+p.name)
 b=p.read_bytes(); sha=hashlib.sha256(b).hexdigest()
 if 'lfs' in f: assert sha==f['lfs']['sha256'],p
 else: assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==f['blobId'],p
 print('Verified',p.name,len(b),flush=True)
 return {'kind':kind,'filename':f['rfilename'],'url':url,'sha256':sha,'bytes':len(b)}
with cf.ThreadPoolExecutor(max_workers=4) as pool: manifest=list(pool.map(fetch,files))
(root/'provenance.json').write_text(json.dumps({'model':'EleutherAI/pythia-70m','model_revision':model['sha'],'dataset':'Salesforce/wikitext','dataset_config':'wikitext-2-raw-v1','dataset_revision':dataset['sha'],'files':manifest,'source':'Official repository files, pinned by commit, file hashes verified','model_license':'Apache-2.0','dataset_license':'CC-BY-SA-3.0'},indent=2))
