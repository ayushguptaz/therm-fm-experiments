"""Save verified power/temperature summaries and readable maps for VCD runs."""
import argparse, csv, json
from pathlib import Path
import h5py, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();root=Path(a.root)
cases=json.loads((root/'inputs/thermfm/cases.json').read_text())
with h5py.File(root/'inputs/thermfm/input.mat') as f:x=f['data'][:]
y=np.load(root/'outputs/aes_inference/temperature_K.npy')
vol=np.load(root/'inputs/thermfm/conservation_arrays.npz')['control_volume_m3']
assert x.shape==(6,4,2,101,101) and y.shape==(6,2,101,101)
assert np.isfinite(x).all() and np.isfinite(y).all()
rows=[]
for i,c in enumerate(cases):
    watts=float((x[i,0,0]*vol[i]).sum())
    assert np.isclose(watts,c['total_power_W'],atol=1e-12,rtol=1e-9)
    assert np.count_nonzero(x[i,0,1])==0
    baseline=next(j for j,b in enumerate(cases) if b['coordinate_mode']==c['coordinate_mode'] and b['workload']=='zero_source')
    rows.append({'case':c['case'],'domain':c['coordinate_mode'],'workload':c['workload'],'power_mW':1000*c['total_power_W'],'conservation_error_W':watts-c['total_power_W'],'AES_mean_K':float(y[i,0].mean()),'AES_peak_K':float(y[i,0].max()),'AES_mean_change_from_zero_K':float((y[i,0]-y[baseline,0]).mean()),'second_slot_mean_K':float(y[i,1].mean()),'second_slot_peak_K':float(y[i,1].max())})
with (root/'outputs/aes_inference/workload_summary.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(root/'outputs/aes_inference/workload_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
for workload in ('busy','gapped'):
    fig,axs=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    ids=[i for i,c in enumerate(cases) if c['workload']==workload]
    tmin=float(y[ids].min());tmax=float(y[ids].max())
    for row,i in enumerate(ids):
        c=cases[i];dw,dh=c['domain_size_um'];extent=[-dw/2,dw/2,-dh/2,dh/2]
        for col,(arr,title,unit) in enumerate([(x[i,0,0],'AES power density','W/m³'),(y[i,0],'AES slot temperature','K'),(y[i,1],'Synthetic second slot temperature','K')]):
            ax=axs[row,col];kw={} if col==0 else {'vmin':tmin,'vmax':tmax}
            im=ax.imshow(arr,origin='lower',extent=extent,cmap='inferno',**kw);fig.colorbar(im,ax=ax,label=unit,shrink=.8)
            ax.set(title=f"{title}\n{c['coordinate_mode']}",xlabel='x (µm)',ylabel='y (µm)')
    fig.suptitle(f"AES {workload}: simulated gate activity, {cases[ids[0]]['total_power_W']*1000:.3f} mW\nExploratory Therm-FM prediction; thermal stack and temperature accuracy unvalidated",fontsize=13)
    fig.savefig(root/f'outputs/aes_inference/{workload}_power_temperature.png',dpi=160);plt.close(fig)
metrics=json.loads((root/'flow/logs/nangate45/aes/base/6_report.json').read_text())
assert metrics['finish__timing__setup__ws']>=0 and metrics['finish__timing__hold__ws']>=0
assert metrics['finish__timing__drv__setup_violation_count']==0
assert metrics['finish__timing__drv__hold_violation_count']==0
route=json.loads((root/'flow/logs/nangate45/aes/base/5_2_route.json').read_text())
assert route['detailedroute__route__drc_errors']==0
checks={'static_setup_and_hold_pass':True,'router_drc_zero':True,'power_conservation':True,'finite_inputs_outputs':True,'synthetic_second_slot_zero_power':True,'shape_checks':True,'timing_metrics':{k:v for k,v in metrics.items() if any(t in k for t in ('setup__ws','hold__ws','setup_violation_count','hold_violation_count','drc'))},'scope':'Integrity checks, not thermal accuracy. Gate simulation is functional without SDF delays.'}
(root/'outputs/workload/verification.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(rows,indent=2));print(json.dumps(checks,indent=2))
