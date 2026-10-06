"""Shared input/schema/parameter guards, not loss or gradient calculations."""
import hashlib
import os
import platform
import sys
import torch
from common import HERE, ROOT, require
sys.path.insert(0,str(HERE/'vendor'))
from model import Model

def environment():
    torch.set_num_threads(4)
    require(platform.python_version()=='3.12.3' and torch.__version__=='2.7.0+cu126' and
            torch.version.cuda=='12.6','Unreviewed Python/torch/CUDA environment')
    require(torch.cuda.is_available() and torch.cuda.get_device_name(0)=='NVIDIA GeForce RTX 3050 Laptop GPU',
            'Required existing GPU unavailable')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') is None,'Inherited CUBLAS policy changed')
    torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(False)
    return dict(python=platform.python_version(),torch=torch.__version__,cuda=torch.version.cuda,
                gpu=torch.cuda.get_device_name(0),precision='float32',threads=4,tf32=False,
                deterministic_algorithms=False,no_strict_determinism_claim=True)

def tensor_hash(*items):
    digest=hashlib.sha256()
    for item in items:
        value=item.detach().cpu().contiguous()
        digest.update(str((tuple(value.shape),str(value.dtype))).encode('utf-8'))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()

def state_binding(obj): return {name:tensor_hash(value) for name,value in obj.state_dict().items()}

def load_pair(row):
    require(row['training_order_epoch_index']==0 and row['training_batch_size']==32,'Frozen first-epoch partition')
    raw=torch.load(ROOT/row['corpus_path'],map_location='cpu',weights_only=True)
    require(set(raw)=={'train','validation','test'},'Parent corpus schema')
    # Do not access/evaluate the carried test tensors. Restrict the research view.
    data={name:raw[name] for name in ('train','validation')}; del raw
    for name,size in (('train',512),('validation',256)):
        tokens,kinds=data[name]
        require(tokens.dtype==torch.long and kinds.dtype==torch.long and
                tuple(tokens.shape)==(size,41) and tuple(kinds.shape)==(size,40),'Corpus tensor shape/dtype')
        require(((tokens>=0)&(tokens<84)).all().item(),'Invalid token')
        require(((kinds>=-1)&(kinds<=2)).all().item(),'Invalid component label')
        for component in range(3): require(((kinds==component).sum(1)==4).all().item(),'Four answers per component')
        require(tensor_hash(tokens,kinds)==row['data_tensor_sha256'][name],'Parent full token/label binding')
    assignment=torch.load(ROOT/row['assignment_path'],map_location='cpu',weights_only=True)
    require(set(assignment)=={'random_weights','orders','pretrain_orders','arm_weights'},'Assignment schema')
    weights=assignment['random_weights']; orders=assignment['orders']
    require(weights.dtype==torch.float32 and tuple(weights.shape)==(512,) and
            torch.isfinite(weights).all().item() and (weights>0).all().item(),'Saved random weights')
    require(abs(float(weights.mean())-1.)<=2e-7,'Saved weight global mean changed')
    require(orders.dtype==torch.long and tuple(orders.shape)==(10,512),'Saved order shape/dtype')
    require(tensor_hash(weights)==row['random_weights_sha256'] and tensor_hash(orders)==row['order_sha256'],
            'Saved weights/order tensor binding')
    for order in orders: require(torch.equal(order.sort().values,torch.arange(512)),'Saved order permutation')
    matrices=assignment['arm_weights']
    require(set(matrices)=={'Uclip','Iclip','Unoclip','Inoclip'},'Saved arm set')
    for arm in ('Uclip','Unoclip'):
        require(tuple(matrices[arm].shape)==(512,3) and torch.equal(matrices[arm],torch.ones(512,3)),
                'Uniform saved mask')
    for arm in ('Iclip','Inoclip'):
        value=matrices[arm]
        require(tuple(value.shape)==(512,3) and torch.equal(value[:,:2],torch.ones(512,2)) and
                torch.equal(value[:,2],weights),'Instance-only saved mask')
    return data,weights,orders[0].clone()

def load_model(row):
    torch.manual_seed(0)  # Constructor only; every parameter is overwritten by the saved state.
    obj=Model(128,3,40).cuda()
    state=torch.load(ROOT/row['checkpoint_path'],map_location='cpu',weights_only=True)
    require(all(isinstance(v,torch.Tensor) and v.dtype==torch.float32 and torch.isfinite(v).all().item()
                for v in state.values()),'Finite fp32 parameter-only checkpoint required')
    obj.load_state_dict(state,strict=True); obj.eval(); obj.zero_grad(set_to_none=True)
    named=tuple(sorted(obj.named_parameters(),key=lambda item:item[0]))
    require(sum(p.numel() for _,p in named)==621696 and all(p.requires_grad for _,p in named),
            'Fixed architecture/gradient parameter layout')
    if row['expected_tensor_sha256'] is not None:
        require(state_binding(obj)==row['expected_tensor_sha256'],'Initial state tensor binding')
    return obj,named
