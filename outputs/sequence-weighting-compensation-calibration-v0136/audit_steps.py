"""Independent four real-step checks: direct gradients and locked native AdamW replay."""
import torch
from common import require,sha,read
def audit_steps(target,ds,weights,orders,guard):
    from model import Model
    rows=[]
    def close(a,b,absolute=2e-7,relative=2e-6):
        a=a.detach().cpu().double(); b=b.detach().cpu().double()
        require(a.shape==b.shape and torch.isfinite(a).all().item() and torch.isfinite(b).all().item(),'Snapshot finite/shape')
        require(((a-b).abs()<=absolute+relative*b.abs()).all().item(),'Snapshot comparison')
    for number in (1,160):
        guard.check(disk=True)
        snapshot=torch.load(target/f'step-{number:03d}.pt',map_location='cpu',weights_only=True)
        e,j=divmod(number-1,16); ids=orders[e][j*32:(j+1)*32]
        require(torch.equal(snapshot['ids'],ids) and torch.equal(snapshot['weights'],weights[ids]),'Snapshot inputs')
        before,after=snapshot['before'],snapshot['after']
        require(before['step']==number-1 and after['step']==number,'Snapshot step identity')
        obj=Model(128,3,40).cuda(); obj.load_state_dict(before['theta']); obj.train()
        tokens,kinds=(v[ids].cuda() for v in ds['train'])
        logits=obj(tokens[:,:-1]); losses=-logits.log_softmax(-1).gather(-1,tokens[:,1:].unsqueeze(-1)).squeeze(-1)
        seq=losses.masked_fill(kinds<0,0).sum(1)/12
        objective=(seq*weights[ids,0].cuda()).mean(); obj.zero_grad(); objective.backward()
        for n,p in obj.named_parameters(): close(p.grad,before['gradient'][n])
        # Clip the saved pre-clip gradients, then replay native CPU FP32 update.
        cpu=Model(128,3,40); cpu.load_state_dict(before['theta'])
        opt=torch.optim.AdamW(cpu.parameters(),lr=1e-4,weight_decay=.1,betas=(.9,.999),
                             eps=1e-8,foreach=False,fused=False)
        for n,p in cpu.named_parameters():
            p.grad=before['gradient'][n].clone()
            if number==1:
                require(torch.count_nonzero(before['m'][n])==0 and torch.count_nonzero(before['v'][n])==0,'Initial zero moments')
            opt.state[p]={'step':torch.tensor(float(number-1)), 'exp_avg':before['m'][n].clone(),
                          'exp_avg_sq':before['v'][n].clone()}
        pre=float(torch.nn.utils.clip_grad_norm_(cpu.parameters(),1.,error_if_nonfinite=True))
        post=float(torch.sqrt(sum(p.grad.double().square().sum() for p in cpu.parameters())))
        require(abs(pre-snapshot['pre_clip_norm'])<=2e-5+2e-6*pre,'Clip pre-norm')
        require(abs(post-snapshot['post_clip_norm'])<=2e-5+2e-6*post,'Clip post-norm')
        opt.step()
        for n,p in cpu.named_parameters():
            close(p,after['theta'][n]); close(opt.state[p]['exp_avg'],after['m'][n]); close(opt.state[p]['exp_avg_sq'],after['v'][n])
        if number==1:
            baseline=target.parent.parent/'baselines'/target.name.rsplit('-',1)[0]/'pretrained.pt'
            state=torch.load(baseline,map_location='cpu',weights_only=True)
            require(all(torch.equal(state[n],before['theta'][n]) for n in state),'First step initial binding')
        else:
            final=torch.load(target/'F10.pt',map_location='cpu',weights_only=True)
            require(all(torch.equal(final[n],after['theta'][n]) for n in final),'Last step endpoint binding')
        rows.append(dict(arm=snapshot['arm'],step=number,snapshot_sha256=sha(target/f'step-{number:03d}.pt'),
            gradient_absolute=2e-7,gradient_relative=2e-6,update_absolute=2e-7,update_relative=2e-6,
            scope='First/last real update; does not replay intermediate trajectories'))
        del obj,cpu,opt; torch.cuda.empty_cache(); guard.check()
    return rows
