"""Global norm-matched AdamW adapter. Fixtures must pass before research training."""
import math
import torch
from common import require, EPS_NORM

def norm(values):
    vector=torch.cat([value.reshape(-1) for value in values])
    result=float(torch.linalg.vector_norm(vector,dtype=torch.float64))
    require(math.isfinite(result),'Nonfinite global norm')
    return result

class NormMatchedAdamW:
    def __init__(self,named,mode,lr=1e-4,weight_decay=.1,betas=(.9,.999),eps=1e-8):
        self.named=tuple(sorted(named,key=lambda item:item[0]))
        require(mode in ('adam','isotropic'),'Unknown optimizer mode')
        self.mode=mode; self.lr=lr; self.wd=weight_decay; self.betas=betas; self.eps=eps; self.t=0
        require(self.named and all(p.dtype in (torch.float32,torch.float64) for _,p in self.named),'Parameter dtype')
        self.m=[torch.zeros_like(p) for _,p in self.named]
        self.v=[torch.zeros_like(p) for _,p in self.named]
        self.names=[dict(name=n,shape=list(p.shape),numel=p.numel()) for n,p in self.named]

    def zero_grad(self):
        for _,p in self.named: p.grad=None

    def capture(self,gradient=False):
        result=dict(step=self.t,names=self.names,
                    theta=[p.detach().cpu().clone() for _,p in self.named],
                    m=[x.detach().cpu().clone() for x in self.m],
                    v=[x.detach().cpu().clone() for x in self.v])
        if gradient: result['gradient']=[p.grad.detach().cpu().clone() for _,p in self.named]
        return result

    @torch.no_grad()
    def step(self):
        require(all(p.grad is not None and not p.grad.is_sparse for _,p in self.named),'Missing/sparse gradient')
        require(torch.stack([torch.isfinite(p.grad).all() for _,p in self.named]).all().item(),'Nonfinite gradient')
        before=[p.detach().clone() for _,p in self.named]
        gradients=[p.grad for _,p in self.named]; b1,b2=self.betas; self.t+=1
        for m,v,g in zip(self.m,self.v,gradients):
            m.lerp_(g,1-b1); v.mul_(b2).addcmul_(g,g,value=1-b2)
        require(torch.stack([torch.isfinite(x).all() for x in self.m+self.v]).all().item(),'Nonfinite optimizer moment')
        mh=[m/(1-b1**self.t) for m in self.m]
        vh=[v/(1-b2**self.t) for v in self.v]
        a=[m/(v.sqrt()+self.eps) for m,v in zip(mh,vh)]
        mn=norm(mh); an=norm(a); exact_zero=mn==0. and an==0.
        if exact_zero: scale=0.; d=[torch.zeros_like(p) for _,p in self.named]
        else:
            require(mn>EPS_NORM and an>EPS_NORM,'Guarded near-zero moment/adaptive norm')
            scale=an/mn; require(math.isfinite(scale),'Nonfinite isotropic scale')
            d=a if self.mode=='adam' else [m*scale for m in mh]
        dn=norm(d); error=abs(dn-an)
        require(error<=1e-8+2e-6*an,'Same-state adaptive norm matching failed')
        for (_,p),direction in zip(self.named,d):
            p.mul_(1-self.lr*self.wd); p.add_(direction,alpha=-self.lr)
        require(torch.stack([torch.isfinite(p).all() for _,p in self.named]).all().item(),'Nonfinite optimizer parameter')
        actual=[p.detach()-q for (_,p),q in zip(self.named,before)]
        theta_norm=norm(before); step_norm=norm(actual)
        return dict(optimizer_step=self.t,mode=self.mode,gradient_norm=norm(gradients),
                    first_moment_norm=norm(self.m),second_moment_norm=norm(self.v),
                    mhat_norm=mn,adaptive_counterfactual_norm=an,direction_norm=dn,
                    isotropic_scale=scale,norm_matching_abs_error=error,exact_zero_update=exact_zero,
                    parameter_step_l2=step_norm,parameter_norm_before=theta_norm,
                    relative_step_l2=None if theta_norm<=EPS_NORM else step_norm/theta_norm,
                    relative_guard='parameter_norm_le_1e-12' if theta_norm<=EPS_NORM else None)
