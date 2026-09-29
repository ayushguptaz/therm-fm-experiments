import argparse
import csv
import json
from pathlib import Path
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('--root',required=True)
a=p.parse_args()
root=Path(a.root)
out=root/'outputs/aes_inference'
cases=json.loads((root/'inputs/thermfm/cases.json').read_text())
report=json.loads((out/'inference_report.json').read_text())
y=np.load(out/'temperature_K.npy')
with h5py.File(root/'inputs/thermfm/input.mat') as f: x=f['data'][:]
assert len(cases)==len(y)==8
rows=[]
for c,r,field in zip(cases,report['samples'],y):
    zero_i=3 if c['index']<4 else 7
    delta=field-y[zero_i]
    rows.append({'case':c['case'],'power_mW':1000*c['total_power_W'],'min_K':r['min_K'],'max_K':r['max_K'],'mean_K':r['mean_K'],'mean_delta_from_zero_K':float(delta.mean()),'max_abs_delta_from_zero_K':float(np.abs(delta).max()),'fraction_cooler_than_zero':float(np.mean(delta < -1e-4))})
with (out/'case_summary.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
for row,i in enumerate([1,5]):
    c=cases[i]; dw,dh=c['domain_size_um'];extent=[-dw/2,dw/2,-dh/2,dh/2]
    maps=[x[i,0,0],y[i,0],y[i,1]]
    titles=['Power density (W/m³)','Therm-FM layer 0 (K)','Therm-FM layer 1 (K)']
    for col,(z,title) in enumerate(zip(maps,titles)):
        vmin=float(y[[1,5]].min()) if col else 0
        vmax=float(y[[1,5]].max()) if col else None
        im=ax[row,col].imshow(z,origin='lower',extent=extent,cmap='inferno' if col==0 else 'magma',vmin=vmin,vmax=vmax)
        ax[row,col].set_title(title)
        ax[row,col].set_xlabel('x (µm)');ax[row,col].set_ylabel('y (µm)')
        fig.colorbar(im,ax=ax[row,col],shrink=.80)
    ax[row,0].text(.02,.98,c['coordinate_mode']+'\nactivity 0.10',transform=ax[row,0].transAxes,ha='left',va='top',color='white',bbox={'facecolor':'black','alpha':.6,'edgecolor':'none'})
fig.suptitle('AES → OpenROAD → Therm-FM\nExploratory predictions; no AES thermal ground truth',fontsize=16)
fig.savefig(out/'aes_temperature_maps.png',dpi=160)
plt.close(fig)

fig,ax=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
for mode,start,color in [('Native die',0,'#126782'),('1 mm embedding',4,'#c45723')]:
    inds=[start+3,start,start+1,start+2]
    powers=[rows[i]['power_mW'] for i in inds]
    ax[0].plot(powers,[rows[i]['mean_K'] for i in inds],'o-',label=mode,color=color)
    ax[1].plot(powers,[rows[i]['max_K'] for i in inds],'o-',label=mode,color=color)
for aa,title in zip(ax,['Mean predicted temperature','Maximum predicted temperature']):
    aa.set_title(title);aa.set_xlabel('Total applied heat source (mW)');aa.set_ylabel('Temperature (K)');aa.grid(alpha=.2);aa.legend()
fig.suptitle('Power-response check (0 mW is a synthetic zero-source input)',fontsize=13)
fig.savefig(out/'power_response.png',dpi=160)
plt.close(fig)

diagnostics={'cases':rows,'caveat':'Temperature summaries are predictions, not measured accuracy. Monotonicity is a diagnostic of the fixed linear-conduction assumption, not proof of correctness.','power_integral_max_absolute_error_W':max(abs(c['total_power_W']-c['integrated_density_power_W']) for c in cases),'median_forward_seconds':float(np.median(report['forward_seconds_per_sample'])),'max_forward_seconds':max(report['forward_seconds_per_sample'])}
(out/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
print(json.dumps(diagnostics,indent=2))
