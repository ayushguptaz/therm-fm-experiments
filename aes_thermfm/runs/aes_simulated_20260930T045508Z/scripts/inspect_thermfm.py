import json
from pathlib import Path
import h5py
import numpy as np

root = Path('/home/ubuntu/Therm-FM')
report = {}
for case in ['HS_SC_refine1', 'IND_8C', 'IND_32C']:
    d = root / 'data/thermal_steady' / case
    with h5py.File(d/'input.mat') as f:
        ds = f['data']
        x = ds[0]
        entry = {'input_shape': list(ds.shape), 'channels': []}
        for p in range(x.shape[0]):
            for l in range(x.shape[1]):
                a = x[p,l]
                entry['channels'].append({'p':p,'layer':l,'min':float(a.min()),'max':float(a.max()),'mean':float(a.mean()),'unique':int(np.unique(a).size),'row_start':a[0,:5].tolist(),'col_start':a[:5,0].tolist(), 'changes_next_sample':bool(np.any(a != ds[1,p,l]))})
    with h5py.File(d/'output.mat') as f:
        entry['output_shape'] = list(f['data'].shape)
        y=f['data'][0]
        entry['output_range']=[float(y.min()),float(y.max())]
    report[case]=entry
print(json.dumps(report,indent=2))
