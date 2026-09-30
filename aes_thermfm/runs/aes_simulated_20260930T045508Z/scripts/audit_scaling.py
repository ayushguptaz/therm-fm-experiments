"""Audit saved AES artifacts; no new model predictions or thermal ground truth.

Requires only NumPy. Extracts the existing raster() function through AST to
benchmark its exact implementation without running build_inputs.py's CLI or
requiring h5py. Does not modify the original input/output artifacts.
"""
import argparse
import ast
import csv
import hashlib
import json
import platform
import re
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / 'outputs/scaling_audit'
    out.mkdir(parents=True, exist_ok=True)
    geom = json.loads((root / 'outputs/geometry.json').read_text())
    x0, y0, x1, y1 = geom['die_um']
    with (root / 'outputs/cells_0.10.csv').open() as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in row.keys() - {'name', 'master'}:
            row[key] = float(row[key])
    powered = [row for row in rows if row['total_W'] > 0]
    source = root / 'scripts/build_inputs.py'
    tree = ast.parse(source.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'raster')
    namespace = dict(np=np, x0=x0, y0=y0, x1=x1, y1=y1)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    original = np.load(root / 'inputs/thermfm/conservation_arrays.npz')
    grids = []
    for mode, width, height, original_index in [
        ('native_die', x1-x0, y1-y0, 1),
        ('benchmark_1mm_embedding', 1000., 1000., 5),
    ]:
        for size in [101, 201, 401, 1001]:
            namespace['a'] = SimpleNamespace(size=size, thickness_um=200.)
            start = time.perf_counter()
            density, watts, volumes, xn, yn, total, integrated = namespace['raster'](rows, width, height)
            elapsed = time.perf_counter() - start
            if size == 101:
                assert np.allclose(watts, original['power_W'][original_index], rtol=1e-12, atol=1e-18)
            assert np.isfinite(density).all()
            assert abs(integrated-total) < 1e-12
            grids.append(dict(
                mode=mode, size=size, pitch_um=[width/(size-1), height/(size-1)],
                powered_bins=int(np.count_nonzero(watts)),
                raster_seconds=elapsed, total_W=total, conservation_error_W=abs(integrated-total),
                max_density_W_m3=float(density.max()), largest_bin_power_fraction=float(watts.max()/total),
                aes_die_intervals_xy=[(x1-x0)/(width/(size-1)), (y1-y0)/(height/(size-1))],
                float32_input_plus_output_MiB=10*size*size*4/2**20,
                ten_thousand_float32_pairs_GiB=10000*10*size*size*4/2**30,
                ten_thousand_current_float64_inputs_GiB=10000*8*size*size*8/2**30,
            ))
            print(json.dumps(grids[-1]), flush=True)
    pred = np.load(root / 'outputs/aes_inference/temperature_K.npy')
    response = []
    for mode, start in [('native_die', 0), ('benchmark_1mm_embedding', 4)]:
        zero = pred[start+3]
        for i in range(start, start+3):
            delta = pred[i] - zero
            response.append(dict(
                mode=mode, case_index=i, mean_delta_K=float(delta.mean()),
                min_delta_K=float(delta.min()), max_delta_K=float(delta.max()),
                fraction_delta_below_minus_1mK=float(np.mean(delta < -0.001)),
                peak_delta_K=float(pred[i].max()-zero.max()),
                rms_delta_K=float(np.sqrt(np.mean(delta**2))),
            ))
    stages = []
    for path in sorted((root / 'flow/logs/nangate45/aes/base').glob('*.log')):
        matches = re.findall(r'Elapsed time: ([\d:.]+)\[h:\]min:sec\. .*?Peak memory: (\d+)KB', path.read_text())
        if matches:
            duration, mem = matches[-1]
            seconds = 0.
            for part in duration.split(':'):
                seconds = seconds*60 + float(part)
            stages.append(dict(log=path.name, elapsed_seconds=seconds, peak_memory_MiB=int(mem)/1024))
    report = dict(
        scope='New local raster benchmarks and analysis of saved outputs; no new OpenROAD/model/thermal-solver runs.',
        platform=platform.platform(), numpy=np.__version__,
        raster_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        timing_caveat='One measurement per grid, no warm-up; raster only, excludes CSV reads/tensor assembly/HDF5 writes; not GPU timings.',
        storage_caveat='Arithmetic for uncompressed arrays; excludes coordinates deduplication, compression, intermediate activations, optimizer, references and layout files.',
        physical_instances=len(rows), positive_power_instances=len(powered),
        powered_cell_median_width_um=float(np.median([r['x1_um']-r['x0_um'] for r in powered])),
        powered_cell_median_height_um=float(np.median([r['y1_um']-r['y0_um'] for r in powered])),
        grid_benchmarks=grids, saved_prediction_response=response,
        baseline_101_maps_match_saved_artifacts=True,
        reported_flow_stages=sorted(stages, key=lambda r:r['elapsed_seconds'], reverse=True),
        sum_reported_elapsed_seconds=sum(s['elapsed_seconds'] for s in stages),
    )
    (out / 'audit.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
