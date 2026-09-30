"""Controlled second-layer power intervention using archived AES inputs/model."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
out = root/'outputs/layer_coupling_20260930'
out.mkdir(parents=True, exist_ok=True)
with h5py.File(root/'inputs/thermfm/input.mat') as f:
    original = f['data'][:]
old_predictions = np.load(root/'outputs/aes_inference/temperature_K.npy')
original_cases = json.loads((root/'inputs/thermfm/cases.json').read_text())
samples, cases = [], []
for source_index in [1, 5]:
    base = original[source_index]
    for label, scale, flip in [('zero',0.,False),('half',.5,False),('equal',1.,False),('double',2.,False),('equal_flipped',1.,True),('zero_repeat',0.,False)]:
        x = base.copy()
        x[0,1] = scale * (np.flip(base[0,0], axis=1) if flip else base[0,0])
        assert np.array_equal(x[:,0],base[:,0])
        assert np.array_equal(x[1:,1],base[1:,1])
        samples.append(x)
        cases.append(dict(index=len(samples)-1, domain=original_cases[source_index]['coordinate_mode'],
                          original_index=source_index, second_layer_case=label, second_layer_scale=scale,
                          second_layer_power_mW=scale*original_cases[source_index]['total_power_W']*1000,
                          aes_power_mW=original_cases[source_index]['total_power_W']*1000))
x = np.stack(samples)
with h5py.File(out/'input.mat','w') as f:
    f.create_dataset('data',data=x,compression='gzip')
    f.attrs['purpose']='Only second-layer heat source changes; physical stack is not removed.'
(out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
with (out/'inference.log').open('w') as log:
    subprocess.run([sys.executable,str(root/'scripts/infer.py'),
                    '--repo',str(root/'vendor/Therm-FM'),
                    '--checkpoint',str(root/'vendor/checkpoint_IND8C_GWL2_T'),
                    '--input',str(out/'input.mat'),'--output-dir',str(out/'predictions')],
                   stdout=log,stderr=subprocess.STDOUT,check=True)
y = np.load(out/'predictions/temperature_K.npy')
assert y.shape==(12,2,101,101) and np.isfinite(y).all()
metrics=[]
for start,source_index in [(0,1),(6,5)]:
    assert np.array_equal(y[start],y[start+5]), 'Identical-input repeat mismatch'
    assert np.array_equal(y[start],old_predictions[source_index]), 'Archived baseline mismatch'
    for i in range(start,start+6):
        delta=y[i,0]-y[start,0]
        metrics.append(dict(**cases[i],aes_mean_change_K=float(delta.mean()),
                            aes_mean_absolute_change_K=float(np.abs(delta).mean()),
                            aes_max_absolute_change_K=float(np.abs(delta).max()),
                            aes_min_change_K=float(delta.min()),aes_max_change_K=float(delta.max()),
                            aes_peak_temperature_change_K=float(y[i,0].max()-y[start,0].max())))
pattern=[]
for start in [0,6]:
    delta=y[start+4,0]-y[start+2,0]
    pattern.append(dict(domain=cases[start]['domain'],
                        same_total_power_different_pattern_max_abs_change_K=float(np.abs(delta).max())))
report=dict(scope='Learned model dependence, not a thermal validation or a physical layer-removal experiment.',
            first_layer_all_fields_unchanged=True,second_layer_coordinates_unchanged=True,
            baseline_matches_archived_predictions_bitwise=True,identical_input_repeats_bitwise_equal=True,
            normalized_second_layer_zero_power=(0-25992669184.)/42735398912.,
            metrics=metrics,spatial_pattern_intervention=pattern)
(out/'coupling_report.json').write_text(json.dumps(report,indent=2)+'\n')

plt.rcParams.update({'font.size':10})
fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
for row,(start,source_index) in enumerate([(0,1),(6,5)]):
    width,height=original_cases[source_index]['domain_size_um']
    xn=np.linspace(-width/2,width/2,101);yn=np.linspace(-height/2,height/2,101)
    xe=np.r_[xn[0],(xn[1:]+xn[:-1])/2,xn[-1]]
    ye=np.r_[yn[0],(yn[1:]+yn[:-1])/2,yn[-1]]
    base=y[start,0]; changed=y[start+2,0];delta=changed-base
    lo=min(base.min(),changed.min());hi=max(base.max(),changed.max())
    for col,(field,title) in enumerate([(base,'AES temperature: second layer = 0 mW'),
                                      (changed,'AES temperature: second layer = 17.86 mW'),
                                      (delta,'Change in AES temperature')]):
        if col==2:
            limit=float(np.abs(delta).max())
            im=axes[row,col].pcolormesh(xe,ye,field,cmap='RdBu_r',vmin=-limit,vmax=limit)
        else:
            im=axes[row,col].pcolormesh(xe,ye,field,cmap='magma',vmin=lo,vmax=hi)
        axes[row,col].set(title=title,xlabel='x (µm)',ylabel='y (µm)',aspect='equal')
        fig.colorbar(im,ax=axes[row,col],shrink=.8,label='K' if col<2 else 'Temperature change (K)')
    axes[row,0].text(.02,.02,'Native die' if row==0 else '1 mm embedding',
                     transform=axes[row,0].transAxes,color='white',bbox=dict(facecolor='black',alpha=.6))
fig.suptitle('Does the other layer affect AES?\nAES input fixed at 17.86 mW; only second-layer power changes',fontsize=15)
fig.savefig(out/'aes_layer_coupling.png',dpi=160)
plt.close(fig)
lines=['# Controlled layer-coupling test','',
       'Date: 2026-09-30. Tests the saved checkpoint, not physical accuracy.', '',
       '## Intervention', '',
       'Held every AES-layer input and both layers\' coordinates fixed. Changed only second-layer power: zero, 0.5×, 1×, 2× the AES power map, plus a horizontally flipped 1× map. Repeated the zero case. Ran both original coordinate domains using archived model source, weights, statistics, and inference code.', '',
       '## Results', '',
       '| Domain | Second-layer power (mW) | AES mean temperature change (K) | Largest absolute local change (K) |',
       '|---|---:|---:|---:|']
for m in metrics:
    if m['second_layer_case'] in ['zero','half','equal','double']:
        lines.append(f"| {m['domain']} | {m['second_layer_power_mW']:.5f} | {m['aes_mean_change_K']:+.8f} | {m['aes_max_absolute_change_K']:.8f} |")
lines += ['', 'All changes are relative to the same-domain zero-power second layer. These are changes in model predictions, not errors relative to true temperatures.', '',
          'Both baseline predictions match the archived AES results bitwise; duplicate zero-input runs are also bitwise equal. All output values are finite. The recorded input assertions ensure the AES input and coordinate channels stayed unchanged.', '',
          '## Interpretation and limits', '',
          'A nonzero AES response to the second-layer intervention demonstrates that the two outputs are not independent of the other layer\'s power input in this checkpoint. It does not prove that the learned coupling is physically accurate.', '',
          'Zero heat generation does not remove a layer. After the saved normalization, raw zero power in slot 1 becomes approximately -0.60822, not a masked/missing channel. Geometry, materials and cooling also remain implicit in this adapted checkpoint.', '',
          'This test cannot quantify adding a passive layer versus having no second layer: those are different physical stacks. That comparison needs matched solver cases (with/without that layer under explicitly defined boundaries), followed by appropriately adapted models if using Therm-FM. The unchanged checkpoint requires eight channels.', '',
          'The equal/flipped cases additionally probe spatial dependence at the same total power. They are synthetic input interventions, not newly routed designs. Exact metrics and all model provenance are in coupling_report.json and predictions/inference_report.json.', '',
          '![Controlled comparison](../outputs/layer_coupling_20260930/aes_layer_coupling.png)', '',
          '## Reproduce', '', '```bash',
          'python scripts/check_layer_coupling.py --root /absolute/path/to/aes_thermfm','```', '',
          'Use the archived compatible inference environment; this needs Torch, Transformers, NumPy, h5py and Matplotlib. The script writes only its experiment directory and this generated report.']
(root/'docs/LAYER_COUPLING_TEST.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(report,indent=2))
