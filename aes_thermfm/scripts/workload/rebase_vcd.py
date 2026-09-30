"""Rebase the post-warm-up recording to zero without altering signal values."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('dest');a=p.parse_args()
first=None;last=None;h=hashlib.sha256()
with open(a.source,'rb') as src,open(a.dest,'wb') as dst:
    for line in src:
        h.update(line)
        if line.startswith(b'#'):
            stamp=int(line[1:]);first=stamp if first is None else first;last=stamp
            line=f'#{stamp-first}\n'.encode()
        dst.write(line)
assert first is not None and last>first
Path(a.dest+'.time_origin.json').write_text(json.dumps({'source_sha256':h.hexdigest(),'source_start_ps':first,'source_end_ps':last,'duration_ps':last-first,'change':'Only timestamp origin shifted; all signal value records preserved.'},indent=2)+'\n')
