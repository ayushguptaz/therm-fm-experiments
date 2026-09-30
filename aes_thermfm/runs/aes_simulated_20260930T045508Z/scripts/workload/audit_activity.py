"""Check simulated activity provenance, waveform values and annotation coverage."""
import argparse, hashlib, json, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();root=Path(a.root)
reports={}
for workload in ('busy','gapped'):
    path=root/f'outputs/workload/{workload}.vcd'
    digest=hashlib.sha256(); declarations=0; widths={}; initial={}; unknown=0; events=0; times=[];scope=[];clock_code=None;clock_edges=0;clock_value=None
    with path.open('rb') as f:
        for raw in f:
            digest.update(raw);s=raw.decode().strip()
            if s.startswith('$scope'):scope.append(s.split()[2])
            elif s.startswith('$upscope'):scope.pop()
            elif s.startswith('$var'):
                parts=s.split();widths[parts[3]]=int(parts[2]);declarations+=1
                if '/'.join(scope)=='aes_workload_tb/dut' and parts[4]=='clk':clock_code=parts[3]
            elif s.startswith('#'):times.append(int(s[1:]))
            elif s and s[0] in '01xXzZbB':
                if s[0] in 'bB':value,code=s[1:].split()
                else:value,code=s[0],s[1:]
                initial.setdefault(code,value);events+=1
                if any(v in value.lower() for v in 'xz'):unknown+=1
                if code==clock_code:
                    if clock_value is not None and value!=clock_value:clock_edges+=1
                    clock_value=value
    assert times and events and clock_code and clock_edges>0
    assert unknown==0,f'{workload}: {unknown} X/Z value records'
    simlog=(root/f'logs/simulation_{workload}.log').read_text()
    m=re.search(r'PASS blocks=272 warmup=16 measured=256 gap_cycles=(\d+) start_ps=(\d+) end_ps=(\d+) duration_ps=(\d+)',simlog)
    assert m,simlog
    gap,start,end,duration=map(int,m.groups())
    # Icarus emits a 1ps VCD time base for this testbench. Confirm before using timestamps.
    header=path.open().read(512)
    assert re.search(r'\$timescale\s+1ps\s+\$end',header),header
    assert times[0]==0 and times[-1]==duration and end-start==duration
    assert abs(clock_edges-duration/1000)<=1,(clock_edges,duration)
    annotation=(root/f'outputs/activity_{workload}.rpt').read_text()
    vcd_match=re.search(r'^vcd\s+(\d+)\s*$',annotation,re.M)
    unannotated_match=re.search(r'^unannotated\s+(\d+)\s*$',annotation,re.M)
    assert vcd_match and int(vcd_match.group(1))>0,annotation
    assert unannotated_match and int(unannotated_match.group(1))==0,annotation
    powerlog=(root/f'logs/power_{workload}.log').read_text()
    reports[workload]={'vcd_sha256':digest.hexdigest(),'bytes':path.stat().st_size,'declarations':declarations,'unique_signal_codes':len(widths),'initialized_codes':len(initial),'value_records':events,'unknown_value_records':unknown,'clock_transitions':clock_edges,'start_ps':start,'end_ps':end,'duration_ps':duration,'gap_cycles':gap,'ciphertexts_checked':272,'measured_blocks':256,'annotation_report':annotation,'warnings':[s for s in powerlog.splitlines() if 'WARN' in s or 'Error' in s]}
(root/'outputs/workload/activity_audit.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
