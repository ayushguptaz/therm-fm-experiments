import argparse, hashlib, json, tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();root=Path(a.root)
assert (root/'outputs/workload/pipeline_status.txt').read_text().strip()=='PASS'
files=[]
for folder in ('inputs','outputs','logs','scripts','flow/logs','flow/reports'):
 for f in (root/folder).rglob('*'):
  if not f.is_file() or f.is_symlink():continue
  if '__pycache__' in f.parts or f.name.startswith('._') or f.suffix in ('.pyc','.vcd','.vvp') or f.name.endswith('.vcd.gz'):continue
  files.append(f)
files.extend((root/'flow/results/nangate45/aes/base').glob('6_final.*'))
files.append(root/'vendor/ORFS_LICENSE')
files=sorted(set(files))
manifest=root/'REVIEW_MANIFEST.sha256'
manifest.write_text(''.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(root)}\n' for f in files))
with tarfile.open(root.parent/(root.name+'_review.tar.gz'),'w:gz') as tar:
 for f in files+[manifest]:tar.add(f,arcname=str(f.relative_to(root)),recursive=False)
print(json.dumps({'files':len(files),'bytes':sum(f.stat().st_size for f in files),'archive':str(root.parent/(root.name+'_review.tar.gz')),'large_waveforms':'Retained on execution host; excluded from compact review archive.'},indent=2))
