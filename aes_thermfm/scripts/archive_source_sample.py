"""Preserve a real held-out source pair for independent inference verification."""
import argparse
from pathlib import Path
import h5py

p=argparse.ArgumentParser()
p.add_argument('--dataset',required=True)
p.add_argument('--destination',required=True)
p.add_argument('--index',type=int,default=999)
a=p.parse_args()
out=Path(a.destination);out.mkdir(parents=True,exist_ok=True)
for name in ['input.mat','output.mat']:
    with h5py.File(Path(a.dataset)/name) as src, h5py.File(out/name,'w') as dst:
        dst.create_dataset('data',data=src['data'][a.index:a.index+1],compression='gzip')
        dst.attrs['source_dataset']='IND_8C'
        dst.attrs['source_sample_index']=a.index
        dst.attrs['purpose']='actual source-benchmark sample; not AES labels'
