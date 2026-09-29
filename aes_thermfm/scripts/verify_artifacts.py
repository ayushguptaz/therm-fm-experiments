import argparse
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args()
root=Path(a.root)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
checks={}
r=json.loads((root/'outputs/aes_inference/inference_report.json').read_text())
for name,path,key in [('weights','vendor/checkpoint_IND8C_GWL2_T/pytorch_model.bin','weights_sha256'),('stats','vendor/checkpoint_IND8C_GWL2_T/normalization_constants.json','stats_sha256'),('input','inputs/thermfm/input.mat','input_sha256')]:
    assert digest(root/path)==r[key]
    checks[name+'_hash_matches_executed_run']=True
with h5py.File(root/'inputs/thermfm/input.mat') as f: x=f['data'][:]
y=np.load(root/'outputs/aes_inference/temperature_K.npy')
replay=np.load(root/'outputs/replay_check/temperature_K.npy')
assert x.shape==(8,4,2,101,101) and y.shape==(8,2,101,101)
assert np.isfinite(x).all() and np.isfinite(y).all()
assert np.array_equal(y,replay), float(np.max(np.abs(y-replay)))
checks['archived_source_and_weights_replay_bitwise_equal']=True
checks['all_shapes_and_finite_checks_passed']=True
with h5py.File(root/'outputs/aes_inference/predictions.mat') as f:
    assert np.array_equal(y,f['data'][:])
checks['npy_and_hdf5_predictions_equal']=True
cases=json.loads((root/'inputs/thermfm/cases.json').read_text())
vol=np.load(root/'inputs/thermfm/conservation_arrays.npz')
for i,c in enumerate(cases):
    integrated=float((x[i,0,0]*vol['control_volume_m3'][i]).sum())
    assert np.isclose(integrated,c['total_power_W'],rtol=1e-9,atol=1e-12)
    assert np.all(x[i,0,1]==0)
checks['serialized_tensor_power_conservation_passed']=True
base=root/'flow/results/nangate45/aes/base'
for ext in ['def','gds','odb','sdc','spef','v']:
    f=base/f'6_final.{ext}';assert f.is_file() and f.stat().st_size>0
checks['final_physical_design_files_present']=True
with h5py.File(root/'inputs/source_sanity/input.mat') as f:
    assert f['data'].shape==(1,4,2,101,101)
    assert f.attrs['source_sample_index']==999
checks['real_source_sanity_pair_archived']=True
report={'checks':checks,'count':len(checks),'status':'PASS','scope':'file/data/inference integrity; not AES thermal accuracy, timing closure, or foundry sign-off'}
(root/'outputs/verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
