"""Deterministic AES-128 workload with an independent OpenSSL reference."""
import argparse, hashlib, json, random, subprocess
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--root',required=True); a=p.parse_args()
out=Path(a.root)/'inputs/workload';out.mkdir(parents=True,exist_ok=True)
key='000102030405060708090a0b0c0d0e0f'
rng=random.Random(20260930)
blocks=[bytes.fromhex('00112233445566778899aabbccddeeff')]
blocks += [rng.getrandbits(128).to_bytes(16,'big') for _ in range(271)]
plain=b''.join(blocks)
ref=subprocess.run(['openssl','enc','-aes-128-ecb','-K',key,'-nopad'],input=plain,capture_output=True,check=True).stdout
assert len(ref)==len(plain) and ref[:16].hex()=='69c4e0d86a7b0430d8cdb78070b4c55a'
(out/'plaintext.hex').write_text(''.join(b.hex()+'\n' for b in blocks))
(out/'ciphertext.hex').write_text(''.join(ref[i:i+16].hex()+'\n' for i in range(0,len(ref),16)))
metadata={'seed':20260930,'key_hex':key,'total_blocks':272,'warmup_blocks':16,'measured_blocks':256,'clock_period_ns':2.0,'workloads':{'busy':{'gap_cycles':0},'gapped':{'gap_cycles':16}},'reference':'OpenSSL AES-128-ECB without padding; first vector independently checked against the standard AES example','openssl_version':subprocess.check_output(['openssl','version'],text=True).strip(),'plaintext_sha256':hashlib.sha256(plain).hexdigest(),'reference_sha256':hashlib.sha256(ref).hexdigest(),'scope':'Synthetic reproducible transaction workloads, not captured application traffic; fixed key; no timing-delay annotation in gate simulation.'}
(out/'workload.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata,indent=2))
