"""Conservative placed-cell power rasterization and Therm-FM tensor creation."""
import argparse
import csv
import json
from pathlib import Path
import h5py
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--root',required=True)
p.add_argument('--size',type=int,default=101)
p.add_argument('--thickness-um',type=float,default=200.)
a=p.parse_args()
root=Path(a.root)
geometry=json.loads((root/'outputs/geometry.json').read_text())
x0,y0,x1,y1=geometry['die_um']
width,height=x1-x0,y1-y0
assert a.thickness_um>0 and a.size>1

def load_cells(activity):
    with (root/f'outputs/cells_{activity}.csv').open() as f:
        rows=list(csv.DictReader(f))
    seen=set()
    for r in rows:
        assert r['name'] not in seen, 'Duplicate physical instance'
        seen.add(r['name'])
        for k in r:
            if k not in ['name','master']: r[k]=float(r[k])
        assert np.isfinite([v for v in r.values() if isinstance(v,float)]).all()
        assert r['total_W']>=0
        assert np.isclose(r['total_W'],sum(r[k] for k in ['internal_W','switching_W','leakage_W']),rtol=1e-5,atol=1e-12)
    summary=dict(line.split('=',1) for line in (root/f'outputs/power_summary_{activity}.txt').read_text().splitlines())
    design_total=float(summary['design_power_components_W'].split()[3])
    cell_total=sum(r['total_W'] for r in rows)
    assert np.isclose(cell_total,design_total,rtol=1e-4,atol=1e-9), (cell_total,design_total)
    return rows

def raster(rows,domain_w,domain_h):
    xn=np.linspace(-domain_w/2,domain_w/2,a.size)
    yn=np.linspace(-domain_h/2,domain_h/2,a.size)
    xe=np.r_[xn[0],(xn[:-1]+xn[1:])/2,xn[-1]]
    ye=np.r_[yn[0],(yn[:-1]+yn[1:])/2,yn[-1]]
    watts=np.zeros((a.size,a.size),dtype=np.float64)
    for r in rows:
        power=r['total_W']
        if power==0: continue
        lo_x=r['x0_um']-(x0+x1)/2
        hi_x=r['x1_um']-(x0+x1)/2
        lo_y=r['y0_um']-(y0+y1)/2
        hi_y=r['y1_um']-(y0+y1)/2
        assert lo_x>=xe[0]-1e-6 and hi_x<=xe[-1]+1e-6
        assert lo_y>=ye[0]-1e-6 and hi_y<=ye[-1]+1e-6
        area=(hi_x-lo_x)*(hi_y-lo_y)
        assert area>0
        ix=np.flatnonzero((xe[:-1]<hi_x)&(xe[1:]>lo_x))
        iy=np.flatnonzero((ye[:-1]<hi_y)&(ye[1:]>lo_y))
        dx=np.maximum(0,np.minimum(xe[ix+1],hi_x)-np.maximum(xe[ix],lo_x))
        dy=np.maximum(0,np.minimum(ye[iy+1],hi_y)-np.maximum(ye[iy],lo_y))
        weights=dy[:,None]*dx[None,:]/area
        assert np.isclose(weights.sum(),1,rtol=1e-7,atol=1e-10)
        watts[np.ix_(iy,ix)]+=power*weights
    volumes_m3=np.diff(ye)[:,None]*np.diff(xe)[None,:]*a.thickness_um*1e-18
    density=watts/volumes_m3
    total=sum(r['total_W'] for r in rows)
    recovered=float((density*volumes_m3).sum())
    assert np.isclose(recovered,total,rtol=1e-9,atol=1e-12)
    return density,watts,volumes_m3,xn,yn,total,recovered

samples=[]
manifest=[]
power_maps=[]
volume_maps=[]
for mode,dw,dh in [('native_die',width,height),('benchmark_1mm_embedding',1000.,1000.)]:
    assert dw>=width and dh>=height
    for activity in ['0.02','0.10','0.20','zero_source']:
        rows=load_cells(activity) if activity!='zero_source' else []
        density,watts,volume,xn,yn,total,recovered=raster(rows,dw,dh)
        inp=np.zeros((4,2,a.size,a.size),dtype=np.float64)
        inp[0,0]=density
        xx,yy=np.meshgrid(xn/1000.,yn/1000.)
        inp[1]=xx
        inp[2]=yy
        inp[3,0]=1.
        inp[3,1]=2.
        samples.append(inp)
        power_maps.append(watts)
        volume_maps.append(volume)
        manifest.append({'index':len(samples)-1,'case':f'{mode}_activity_{activity}','coordinate_mode':mode,'activity':activity,'domain_size_um':[dw,dh],'heat_source_thickness_um':a.thickness_um,'source_layer':0,'passive_zero_source_layer':1,'cell_count':len(rows),'total_power_W':total,'integrated_density_power_W':recovered,'max_density_W_m3':float(density.max()),'mean_density_W_m3':float(density.mean()),'assumptions':'x/y in mm; z=1,2 are layer IDs; source treated as W/m^3; checkpoint package retained implicitly; no physical accuracy established'})
x=np.stack(samples)
assert x.shape==(8,4,2,a.size,a.size)
assert np.isfinite(x).all()
out=root/'inputs/thermfm'
out.mkdir(parents=True,exist_ok=True)
with h5py.File(out/'input.mat','w') as f:
    f.create_dataset('data',data=x,compression='gzip')
    f.attrs['axis_order']='sample, physical_channel, layer, y, x'
    f.attrs['physical_channels']='power_density_W_m3, x_mm, y_mm, layer_identifier'
    f.attrs['note']='HDF5 with Therm-FM key/shape contract; not a MATLAB v7.3 header implementation. No ground-truth temperatures.'
np.savez_compressed(out/'conservation_arrays.npz',power_W=np.stack(power_maps),control_volume_m3=np.stack(volume_maps))
(out/'cases.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
