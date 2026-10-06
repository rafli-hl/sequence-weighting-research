"""Frozen outcome-independent checks; run only in approved pretrain phase."""
import math
import torch
from common import require, utc
from optimizer import NormMatchedAdamW

def run_fixtures(guard):
    # Import at call time: torch is already defined before decorator-bearing worker.
    import experiment as candidate
    candidate.imports(); candidate.runtime()
    comparisons=0; maxima={}
    def close(a,b,label,absolute=2e-7,relative=2e-6):
        nonlocal comparisons
        a=torch.as_tensor(a,dtype=torch.float64); b=torch.as_tensor(b,dtype=torch.float64)
        require(a.shape==b.shape and torch.isfinite(a).all().item() and torch.isfinite(b).all().item(),label+' shape/finite')
        err=(a-b).abs(); tol=absolute+relative*b.abs()
        fraction=float((err/tol).max())
        maxima[label]=max(maxima.get(label,0.),fraction); comparisons+=1
        require(fraction<=1.,'Locked AdamW fixture failed: '+label)
    for device in ('cpu','cuda'):
        for wd in (0.,.1):
            base=torch.tensor([-.8,-.1,0.,.3,.9],device=device,dtype=torch.float32)
            ours=torch.nn.Parameter(base.clone()); ref=torch.nn.Parameter(base.clone())
            opt=NormMatchedAdamW([('theta',ours)],'adam',weight_decay=wd)
            locked=torch.optim.AdamW([ref],lr=1e-4,betas=(.9,.999),eps=1e-8,weight_decay=wd,
                                    foreach=False,fused=False,amsgrad=False,capturable=False,maximize=False)
            for step in range(1,161):
                guard.check()
                gradient=torch.tensor([1.,-2.,.0,.1,-.4],device=device)*((step%7-3)/4)
                if step%9==0: gradient=gradient.flip(0)
                ours.grad=gradient.clone(); ref.grad=gradient.clone()
                scalar=opt.step(); locked.step()
                if step in (1,2,6,160):
                    state=locked.state[ref]
                    close(ours,ref,'native_theta_'+device)
                    close(opt.m[0],state['exp_avg'],'native_m_'+device)
                    close(opt.v[0],state['exp_avg_sq'],'native_v_'+device)
                    require(opt.t==int(state['step']),'Native step counter')
                    require(scalar['norm_matching_abs_error']<=1e-8+2e-6*scalar['adaptive_counterfactual_norm'],
                            'Native direction norm')
    # Explicit synthetic moment history includes positive, negative, zero and
    # anisotropic coordinates, nonzero decay and bias correction beyond step1.
    for mode in ('adam','isotropic'):
        p=torch.nn.Parameter(torch.tensor([.7,-.4,0.],dtype=torch.float64))
        opt=NormMatchedAdamW([('theta',p)],mode)
        m=torch.zeros_like(p); v=torch.zeros_like(p)
        for step,g in enumerate((torch.tensor([1.,-3.,0.],dtype=torch.float64),
                                 torch.tensor([-2.,.5,4.],dtype=torch.float64)),1):
            previous=p.detach().clone(); p.grad=g.clone()
            m=.9*m+.1*g; v=.999*v+.001*g.square()
            mh=m/(1-.9**step); a=mh/((v/(1-.999**step)).sqrt()+1e-8)
            direction=a if mode=='adam' else mh*(float(a.norm())/float(mh.norm()))
            reference=previous*(1-1e-4*.1)-1e-4*direction
            scalar=opt.step()
            close(p,reference,'analytic_update_'+mode,1e-12,1e-12)
            close(scalar['direction_norm'],float(a.norm()),'analytic_global_norm_'+mode,1e-12,1e-12)
        zero=torch.nn.Parameter(torch.tensor([1.,-2.],dtype=torch.float64))
        guarded=NormMatchedAdamW([('theta',zero)],mode); zero.grad=torch.zeros_like(zero)
        result=guarded.step()
        require(result['exact_zero_update'] and result['direction_norm']==0.,'Exact-zero adaptive guard')
        close(zero,torch.tensor([1.,-2.],dtype=torch.float64)*(1-1e-5),'zero_decay_only',1e-12,1e-12)
        zero_parameter=torch.nn.Parameter(torch.zeros(2,dtype=torch.float64))
        zero_parameter.grad=torch.ones_like(zero_parameter)
        relative=NormMatchedAdamW([('theta',zero_parameter)],mode).step()
        require(relative['relative_step_l2'] is None and relative['relative_guard']=='parameter_norm_le_1e-12',
                'Undefined relative parameter-step guard')
        tiny=torch.nn.Parameter(torch.ones(2,dtype=torch.float64)); tiny.grad=torch.full_like(tiny,1e-20)
        try: NormMatchedAdamW([('theta',tiny)],mode).step()
        except RuntimeError as error: require('near-zero' in str(error),'Wrong near-zero rejection')
        else: raise RuntimeError('Near-zero update was accepted')
        bad=torch.nn.Parameter(torch.ones(2)); bad.grad=torch.tensor([float('nan'),0.])
        try: NormMatchedAdamW([('theta',bad)],mode).step()
        except RuntimeError: pass
        else: raise RuntimeError('Nonfinite update accepted')
    left=torch.nn.Parameter(torch.tensor([.2,-.3],dtype=torch.float64))
    right=torch.nn.Parameter(torch.tensor([.5,.7,-.1],dtype=torch.float64))
    global_opt=NormMatchedAdamW([('left',left),('right',right)],'isotropic')
    left.grad=torch.tensor([.01,10.],dtype=torch.float64)
    right.grad=torch.tensor([-.2,.8,3.],dtype=torch.float64)
    theta=torch.cat((left.detach(),right.detach())); g=torch.cat((left.grad,right.grad))
    a=g/(g.abs()+1e-8); scale=float(a.norm())/float(g.norm())
    expected=theta*(1-1e-5)-1e-4*g*scale
    global_opt.step()
    close(torch.cat((left.detach(),right.detach())),expected,'global_not_per_tensor_norm',1e-12,1e-12)
    class FixedLogits(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.logits=torch.nn.Parameter(torch.linspace(-.8,.8,2*40*84,dtype=torch.float64).reshape(2,40,84))
        def forward(self,x): return self.logits
    holder=FixedLogits(); tokens=torch.arange(82).reshape(2,41)%84
    kinds=torch.full((2,40),-1,dtype=torch.long)
    for j in range(12): kinds[:,j*3+4]=j%3
    for mask in (torch.ones(2,3),torch.tensor([[1.,1.,.3],[1.,1.,1.7]])):
        actual,_,_=candidate.component_objective(holder,tokens,kinds,mask)
        logp=holder.logits.log_softmax(-1); nll=-logp.gather(-1,tokens[:,1:,None]).squeeze(-1)
        reference=sum(nll[row,kinds[row]==k].mean()*mask[row,k] for row in range(2) for k in range(3))/6
        close(actual.detach(),reference.detach(),'component_objective',1e-12,1e-12)
        ga=torch.autograd.grad(actual,holder.logits,retain_graph=True)[0]
        gb=torch.autograd.grad(reference,holder.logits)[0]
        close(ga,gb,'component_gradient',1e-12,1e-12)
        require((ga[kinds<0]==0).all().item(),'Ignored context gradient')
    guard.check(disk=True)
    return dict(status='PASS_PRETRAINING_FIXTURES',utc=utc(),comparisons=comparisons,
                maximum_tolerance_fraction=maxima,locked_torch='2.7.0+cu126',
                native_flags=dict(foreach=False,fused=False,amsgrad=False,capturable=False,maximize=False),
                native_fixture_steps=[1,2,6,160],native_devices=['cpu','cuda'],
                tolerance_native=dict(absolute=2e-7,relative=2e-6),
                analytic_absolute=1e-12,analytic_relative=1e-12,
                exact_zero=True,near_zero_rejected=True,nonfinite_rejected=True,
                global_not_per_tensor_norm=True,undefined_relative_parameter_step=True,
                component_and_gradient_scaling=True,ignored_context=True)
