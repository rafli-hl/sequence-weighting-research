"""Inspect failed diagnostic identities without changing training or primary fits."""
import argparse
import json
import math
import sys
from decimal import Decimal,localcontext
sys.dont_write_bytecode=True
import torch
from engine import ROOT,HERE,read,write,utc


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-id',required=True); args=ap.parse_args()
    root=ROOT/'work/runs'/args.run_id
    torch.set_num_threads(4)
    failed=[]; max_identity=0.; max_gram=0.; max_relative=0.; checked=0
    for path in sorted((root/'runs').glob('confirm-*/sequence_losses.pt')):
        rec=torch.load(path,weights_only=True); w=rec['weights']; initial=rec['checkpoints'][0]['train']
        if float(w.max()-w.min())<1e-12: continue
        for cp in rec['checkpoints'][1:]:
            primary=initial['loss']-cp['train']['loss']
            cg=initial['component_loss'].double()-cp['train']['component_loss'].double()
            identity=float((cg.mean(1)-primary.double()).abs().max()); max_identity=max(max_identity,identity)
            total=float(cg.sum())
            if total<=3e-10: continue
            cg=cg[w.argsort()]; n=len(w); q0=torch.arange(1,n+1,dtype=torch.float64)/n
            mass=cg.sum(0)/total; cumulative=cg.cumsum(0)/total
            centered=cumulative-q0[:,None]*mass[None,:]; q=cg.sum(1).cumsum(0)/total
            gram=centered.T@centered/n; objective=float(((q-q0)**2).mean())
            e1=float((cumulative.sum(1)-q).abs().max())
            e2=float((centered.sum(1)-(q-q0)).abs().max())
            e3=abs(float(gram.sum())-objective)
            scale=max(1.,float(gram.abs().sum()),abs(objective))
            max_gram=max(max_gram,e3); max_relative=max(max_relative,e3/scale); checked+=1
            if identity>=2e-6 or e1>1e-12 or e2>1e-12 or e3>=1e-12:
                # Independent high-precision arithmetic on the saved float64 contributions.
                with localcontext() as ctx:
                    ctx.prec=70
                    cc=[[Decimal.from_float(x) for x in row] for row in centered.tolist()]
                    direct=sum(sum(row)**2 for row in cc)/Decimal(n)
                    gd=[[sum(row[i]*row[j] for row in cc)/Decimal(n) for j in range(3)] for i in range(3)]
                    expanded=sum(sum(row) for row in gd)
                    decimal_identity=float(abs(direct-expanded))
                    torch_gram_vs_decimal=float(abs(Decimal.from_float(float(gram.sum()))-expanded))
                    objective_vs_decimal=float(abs(Decimal.from_float(objective)-direct))
                failed.append(dict(name=path.parent.name,epoch=cp['epoch'],component_total_gain=total,
                    primary_total_gain=float(primary.double().sum()),gain_identity_error=identity,
                    cumulative_error=e1,centered_error=e2,gram_error=e3,gram_abs_sum=float(gram.abs().sum()),
                    objective=objective,scale_normalized_gram_error=e3/scale,
                    decimal_identity_error=decimal_identity,torch_gram_vs_decimal=torch_gram_vs_decimal,
                    objective_vs_decimal=objective_vs_decimal))
    output=dict(utc=utc(),checked_random_positive_component_gain=checked,strict_failures=failed,
        max_gain_identity_error=max_identity,max_gram_error=max_gram,max_scale_normalized_gram_error=max_relative,
        note='Strict frozen identity failures retained. Primary estimator and all trained records untouched.')
    write(HERE/f'roundoff-probe-{args.run_id}.json',output)
    print(json.dumps(output),flush=True)


if __name__=='__main__': main()
