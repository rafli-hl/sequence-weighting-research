"""Independent frozen snapshot audit; does not import the candidate optimizer."""
import math
import torch
from common import require, SNAPSHOT_PAIR, SNAPSHOT_STEPS, ARM_POLICY, PARAMETERS

def audit_snapshots(target,record,base_state,final_state,obj,ds,assignment,guard,sha,load):
    selected=(record['data_seed'],record['seed'])==SNAPSHOT_PAIR
    expected={f'step-{t:03d}.pt' for t in SNAPSHOT_STEPS} if selected else set()
    require(set(record['snapshot_bindings'])==expected,'Fixed snapshot selection mismatch')
    if not selected: return []
    reports=[]
    for t in SNAPSHOT_STEPS:
        guard.check(disk=True)
        name=f'step-{t:03d}.pt'; path=target/name
        require(sha(path)==record['snapshot_bindings'][name],'Snapshot hash mismatch')
        snap=load(path); before=snap['before']; after=snap['after']; arm=record['arm']
        require(snap['data_seed']==SNAPSHOT_PAIR[0] and snap['seed']==SNAPSHOT_PAIR[1] and
                snap['arm']==arm and snap['mode']==ARM_POLICY[arm][1],'Snapshot identity')
        require(before['step']==t-1 and after['step']==t,'Snapshot step identity')
        require(snap['lr']==1e-4 and snap['weight_decay']==.1 and snap['betas']==[.9,.999] and
                snap['eps']==1e-8,'Snapshot hyperparameters')
        named=tuple(sorted(obj.named_parameters()))
        layout=[dict(name=n,shape=list(p.shape),numel=p.numel()) for n,p in named]
        require(before['names']==layout and after['names']==layout and
                sum(p.numel() for _,p in named)==PARAMETERS,'Snapshot layout')
        for payload,fields in ((before,('theta','m','v','gradient')),(after,('theta','m','v'))):
            for field in fields:
                require(len(payload[field])==len(layout),'Snapshot tensor count')
                for value,row in zip(payload[field],layout):
                    require(value.dtype==torch.float32 and list(value.shape)==row['shape'] and
                            torch.isfinite(value).all().item(),'Snapshot tensor dtype/shape/finite')
        if t==1:
            require(all(torch.count_nonzero(v).item()==0 for v in before['m']+before['v']),
                    'Fresh optimizer moments not zero')
            require(all(torch.equal(x,base_state[row['name']]) for x,row in zip(before['theta'],layout)),
                    'First snapshot differs from shared checkpoint')
        if t==160:
            require(all(torch.equal(x,final_state[row['name']]) for x,row in zip(after['theta'],layout)),
                    'Last snapshot differs from F10 checkpoint')
        checks=0; maxima={}
        def close(a,b,label,atol=2e-7,rtol=2e-6):
            nonlocal checks
            a=torch.as_tensor(a,dtype=torch.float64).detach().cpu()
            b=torch.as_tensor(b,dtype=torch.float64).detach().cpu()
            require(a.shape==b.shape and torch.isfinite(a).all().item() and torch.isfinite(b).all().item(),
                    'Snapshot comparison nonfinite/shape '+label)
            fraction=float(((a-b).abs()/(atol+rtol*b.abs())).max())
            maxima[label]=max(maxima.get(label,0.),fraction); checks+=1
            require(fraction<=1.,'Independent optimizer audit failed '+label)
        flat=lambda values:torch.cat([x.detach().reshape(-1).double().cpu() for x in values])
        th=flat(before['theta']); old_m=flat(before['m']); old_v=flat(before['v']); grad=flat(before['gradient'])
        # Independent float64 closed-form moments and directions.
        m=.9*old_m+.1*grad; v=.999*old_v+.001*grad.square()
        close(flat(after['m']),m,'first_moment')
        close(flat(after['v']),v,'second_moment')
        mh=m/(1-.9**t); adaptive=mh/((v/(1-.999**t)).sqrt()+1e-8)
        mn=float(mh.norm()); an=float(adaptive.norm())
        if mn==0. and an==0.: direction=torch.zeros_like(mh); scale=0.; exact_zero=True
        else:
            require(mn>1e-12 and an>1e-12,'Snapshot near-zero guard')
            scale=an/mn; exact_zero=False
            direction=adaptive if ARM_POLICY[arm][1]=='adam' else mh*scale
        close(float(direction.norm()),an,'same_state_global_norm',1e-8,2e-6)
        prediction=(1-1e-4*.1)*th-1e-4*direction
        observed=flat(after['theta'])
        close(observed,prediction,'analytic_theta',4e-8,2e-6)
        rounding=4e-8+4*torch.finfo(torch.float32).eps*th.abs()
        close(observed-th,prediction-th,'analytic_actual_step',rounding,2e-4)
        scalar=snap['scalar']; require(scalar['optimizer_step']==t and scalar['mode']==ARM_POLICY[arm][1] and
                                      scalar['exact_zero_update']==exact_zero,'Snapshot scalar identity')
        scalar_reference=dict(gradient_norm=float(grad.norm()),first_moment_norm=float(flat(after['m']).norm()),
            second_moment_norm=float(flat(after['v']).norm()),mhat_norm=mn,
            adaptive_counterfactual_norm=an,direction_norm=float(direction.norm()),isotropic_scale=scale,
            parameter_norm_before=float(th.norm()),parameter_step_l2=float((observed-th).norm()))
        for key,value in scalar_reference.items(): close(scalar[key],value,'scalar_'+key,2e-6,2e-4)
        require(scalar['norm_matching_abs_error']<=1e-8+2e-6*scalar['adaptive_counterfactual_norm'],
                'Saved norm matching error')
        # Native branch alone is also replayed through locked PyTorch AdamW on
        # CPU32 using saved same-state moments; never initialize from another arm.
        if ARM_POLICY[arm][1]=='adam':
            ps=[torch.nn.Parameter(x.clone()) for x in before['theta']]
            native=torch.optim.AdamW(ps,lr=1e-4,weight_decay=.1,betas=(.9,.999),eps=1e-8,
                foreach=False,fused=False,amsgrad=False,capturable=False,maximize=False)
            for p,g,om,ov in zip(ps,before['gradient'],before['m'],before['v']):
                p.grad=g.clone()
                native.state[p]=dict(step=torch.tensor(float(t-1)),exp_avg=om.clone(),exp_avg_sq=ov.clone())
            native.step()
            close(flat(ps),observed,'locked_native_theta')
            close(flat([native.state[p]['exp_avg'] for p in ps]),flat(after['m']),'locked_native_m')
            close(flat([native.state[p]['exp_avg_sq'] for p in ps]),flat(after['v']),'locked_native_v')
            del native,ps
        # Recompute saved training gradient from saved pre-step state, full tokens
        # and direct token coefficients; no candidate loss or optimizer imported.
        with torch.no_grad():
            for (_,p),value in zip(named,before['theta']): p.copy_(value.to(p.device))
        obj.train(); obj.zero_grad(set_to_none=True)
        epoch,index=divmod(t-1,16); ids=assignment['orders'][epoch][index*32:(index+1)*32]
        require(snap['epoch']==epoch+1 and snap['batch_index']==index,'Snapshot batch position')
        from hashlib import sha256
        h=sha256(); h.update(str((tuple(ids.shape),str(ids.dtype))).encode()); h.update(ids.numpy().tobytes())
        require(snap['ids_sha256']==h.hexdigest(),'Snapshot applied order hash')
        x,kinds=(values[ids].cuda() for values in ds['train'])
        logits=obj(x[:,:-1]); nll=-logits.log_softmax(-1).gather(-1,x[:,1:,None]).squeeze(-1)
        require(all((kinds.eq(k).sum(1)==4).all().item() for k in range(3)),'Snapshot component counts')
        w=assignment['arm_weights'][arm][ids].cuda()
        objective=sum((nll.masked_select(kinds==k).reshape(32,4).sum(1)*w[:,k]).sum()
                      for k in range(3))/(32*12)
        recomputed=torch.autograd.grad(objective,[p for _,p in named])
        close(flat(recomputed),grad,'independent_gradient',2e-6,2e-4)
        require(all(p.grad is None for _,p in named),'Audit autograd contaminated parameters')
        reports.append(dict(arm=arm,step=t,checks=checks,maximum_tolerance_fraction=maxima,
            snapshot_sha256=sha(path),first_step_zero_moments=t==1,last_step_checkpoint_bound=t==160,
            total_step_norm=float((observed-th).norm()),adaptive_direction_norm=an,
            scope='Independent eight prescribed step snapshots, not replay of every intermediate update'))
        del snap,before,after,th,old_m,old_v,grad,m,v,mh,adaptive,direction,prediction,observed,recomputed
        guard.check()
    return reports
