"""Execute TEXT_PROTOCOL.md with already downloaded, pinned local assets."""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path
import torch
from torch.nn import functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM
from core import exponent


def write(path,obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


@torch.no_grad()
def evaluate(model,tokens):
    model.eval()
    result=[]
    for batch in tokens.split(4):
        batch=batch.cuda()
        logits=model(batch[:,:-1],use_cache=False).logits
        result.append(F.cross_entropy(logits.transpose(1,2),batch[:,1:],reduction='none').mean(1).cpu())
    return torch.cat(result)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--assets',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required')
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    args.output.mkdir(parents=True,exist_ok=False)
    tokenizer=AutoTokenizer.from_pretrained(args.assets/'model',local_files_only=True)
    data={}; source={}; seen=set()
    for split,count in [('train',512),('validation',128),('test',128)]:
        candidates=json.loads((args.assets/f'{split}-rows.json').read_text())
        tokens=[]; ids=[]
        for item in candidates:
            text=item['text']
            tok=tokenizer.encode(text,add_special_tokens=False,truncation=True,max_length=129)
            if len(tok)<129: continue
            tok=tok[:129]
            fingerprint=hashlib.sha256(json.dumps(tok).encode()).hexdigest()
            if fingerprint in seen: continue
            seen.add(fingerprint)
            tokens.append(tok)
            ids.append({'row_idx':item['row_idx'],'token_sha256':fingerprint,
                        'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
            if len(tokens)==count: break
        if len(tokens)!=count: raise RuntimeError(f'Insufficient eligible {split} rows: {len(tokens)}/{count}')
        data[split]=torch.tensor(tokens,dtype=torch.long)
        source[split]=ids
    write(args.output/'selected-rows.json',source)
    torch.save(data,args.output/'tokens.pt')
    provenance=json.loads((args.assets/'provenance.json').read_text())
    for weighting in ['random','uniform']:
        folder=args.output/weighting; folder.mkdir()
        torch.manual_seed(42); torch.cuda.manual_seed_all(42)
        model=AutoModelForCausalLM.from_pretrained(args.assets/'model',local_files_only=True,
                torch_dtype=torch.float32,attn_implementation='sdpa').cuda()
        model.config.use_cache=False
        optimizer=torch.optim.AdamW(model.parameters(),lr=.00003,weight_decay=.1)
        rng=random.Random(1042)
        weights=torch.tensor([math.exp(rng.uniform(math.log(.01),math.log(10))) for _ in range(512)])
        if weighting=='uniform': weights.fill_(1)
        weights/=weights.mean()
        initial=evaluate(model,data['train'])
        val=evaluate(model,data['validation'])
        history=[{'epoch':0,'train_nll':float(initial.mean()),'validation_nll':float(val.mean())}]
        seq=[initial]
        torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize(); start=time.perf_counter()
        for epoch in range(1,4):
            model.train()
            order=torch.randperm(512,generator=torch.Generator().manual_seed(999+42+epoch))
            norms=[]
            for group in order.split(32):
                optimizer.zero_grad(set_to_none=True)
                for ids in group.split(4):
                    tokens=data['train'][ids].cuda()
                    logits=model(tokens[:,:-1],use_cache=False).logits
                    perseq=F.cross_entropy(logits.transpose(1,2),tokens[:,1:],reduction='none').mean(1)
                    loss=(perseq*weights[ids].cuda()).sum()/len(group)
                    loss.backward()
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1)
                if not torch.isfinite(norm): raise RuntimeError('Nonfinite gradient')
                norms.append(float(norm)); optimizer.step()
            current=evaluate(model,data['train']); val=evaluate(model,data['validation'])
            gain=initial-current
            item={'epoch':epoch,'train_nll':float(current.mean()),'validation_nll':float(val.mean()),
                  'p_star':exponent(weights.tolist(),gain.tolist()),
                  'negative_gain_fraction':float((gain<0).float().mean()),
                  'gradient_clip_fraction':sum(v>1 for v in norms)/len(norms)}
            history.append(item); seq.append(current)
            write(folder/'history.json',history)
            print(weighting,json.dumps(item),flush=True)
        test=evaluate(model,data['test'])
        torch.cuda.synchronize()
        result={'weighting':weighting,'parameters':sum(p.numel() for p in model.parameters()),
                'history':history,'test_nll':float(test.mean()),'elapsed_seconds':time.perf_counter()-start,
                'peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20,
                'peak_reserved_mib':torch.cuda.max_memory_reserved()/2**20,
                'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),'provenance':provenance,
                'config':{'seed':42,'epochs':3,'learning_rate':.00003,'weight_decay':.1,'clip':1,
                          'microbatch':4,'effective_batch':32,'sequence_length':129,'precision':'float32',
                          'training':'full fine-tuning; all parameters','test_used_for_selection':False},
                'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'limitation':'One model/seed and selected paragraphs; no scaling-law or benchmark claim.'}
        write(folder/'result.json',result)
        torch.save({'weights':weights,'losses':torch.stack(seq)},folder/'sequence_losses.pt')
        model.save_pretrained(folder/'checkpoint',safe_serialization=True)
        del optimizer,model; torch.cuda.empty_cache()
    print('TEXT CHECK COMPLETE',flush=True)


if __name__=='__main__': main()
