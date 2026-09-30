"""Label-free inference with actual Therm-FM weights; no fabricated output.mat."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import h5py
import numpy as np
import torch

parser=argparse.ArgumentParser()
parser.add_argument('--repo', required=True)
parser.add_argument('--checkpoint', required=True)
parser.add_argument('--input', required=True)
parser.add_argument('--output-dir', required=True)
parser.add_argument('--reference')
parser.add_argument('--sample', type=int)
args=parser.parse_args()
sys.path.insert(0,args.repo)
from scOT.model import ScOT

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()

torch.manual_seed(0)
torch.set_num_threads(2)
checkpoint=Path(args.checkpoint)
out=Path(args.output_dir)
out.mkdir(parents=True,exist_ok=True)
stats=json.loads((checkpoint/'normalization_constants.json').read_text())
with h5py.File(args.input) as f:
    x=f['data'][args.sample:args.sample+1] if args.sample is not None else f['data'][:]
assert x.ndim==5 and np.isfinite(x).all(), x.shape
n,p,l,h,w=x.shape
raw=x.transpose(0,2,1,3,4).reshape(n,p*l,h,w)
mu=np.asarray(stats['input']['mean']).reshape(1,-1,1,1)
sd=np.asarray(stats['input']['std']).reshape(1,-1,1,1)
assert (sd>0).all()
norm=((raw-mu)/sd).astype('float32')
assert np.isfinite(norm).all()
device='cuda' if torch.cuda.is_available() else 'cpu'
start=time.perf_counter()
model,loading=ScOT.from_pretrained(checkpoint,output_loading_info=True)
assert not any(loading.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']), loading
assert model.config.num_channels==p*l
assert model.config.image_size==h==w
assert all(torch.isfinite(v).all() for v in model.state_dict().values())
model=model.to(device).eval()
load_seconds=time.perf_counter()-start
if device=='cuda': torch.cuda.reset_peak_memory_stats()
pred=[]
times=[]
with torch.inference_mode():
    warm=torch.as_tensor(norm[:1],device=device)
    model(pixel_values=warm)
    if device=='cuda': torch.cuda.synchronize()
    for i in range(n):
        tensor=torch.as_tensor(norm[i:i+1],device=device)
        if device=='cuda': torch.cuda.synchronize()
        t=time.perf_counter()
        y=model(pixel_values=tensor).output
        if device=='cuda': torch.cuda.synchronize()
        times.append(time.perf_counter()-t)
        pred.append(y.cpu().numpy())
yn=np.concatenate(pred)
ymu=np.asarray(stats['output']['mean']).reshape(1,-1,1,1)
ysd=np.asarray(stats['output']['std']).reshape(1,-1,1,1)
y=yn*ysd+ymu
assert np.isfinite(y).all()
np.save(out/'temperature_K.npy',y)
with h5py.File(out/'predictions.mat','w') as f:
    f.create_dataset('data',data=y)
    f.attrs['units']='K; interpreted from source benchmark, not validated on AES'
    f.attrs['axis_order']='sample, output_layer, y, x'
report={'device':device,'torch_version':torch.__version__,'checkpoint':str(checkpoint),'weights_sha256':sha256(checkpoint/'pytorch_model.bin'),'stats_sha256':sha256(checkpoint/'normalization_constants.json'),'input_sha256':sha256(args.input),'input_shape':list(x.shape),'output_shape':list(y.shape),'loading_info':loading,'model_load_seconds':load_seconds,'forward_seconds_per_sample':times,'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated() if device=='cuda' else None,'normalized_input_channel_ranges':[{'min':float(norm[:,c].min()),'max':float(norm[:,c].max())} for c in range(p*l)],'samples':[{'min_K':float(a.min()),'max_K':float(a.max()),'mean_K':float(a.mean()),'layers':[{'min_K':float(b.min()),'max_K':float(b.max()),'mean_K':float(b.mean()),'argmax_yx':list(map(int,np.unravel_index(b.argmax(),b.shape)))} for b in a]} for a in y]}
if args.reference:
    with h5py.File(args.reference) as f:
        ref=f['data'][args.sample:args.sample+1] if args.sample is not None else f['data'][:]
    assert ref.shape==y.shape
    err=y-ref
    report['reference_metrics']={'MAE_K':float(np.abs(err).mean()),'RMSE_K':float(np.sqrt(np.square(err).mean())),'global_max_error_K':float(np.abs(err).max()),'purpose':'held-out source-benchmark plumbing check, not AES validation'}
(out/'inference_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
