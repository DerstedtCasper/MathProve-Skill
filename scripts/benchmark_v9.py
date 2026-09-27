#!/usr/bin/env python3
"""Microbenchmark controller/hook overhead only; NOT mathematical research speed."""
from pathlib import Path
import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skill'))
from runtime_v9.core import Store

def main():
    p=argparse.ArgumentParser();p.add_argument('--samples',type=int,default=30);a=p.parse_args()
    if not 5<=a.samples<=1000:p.error('samples must be 5..1000')
    script=Path(__file__).resolve().parents[1]/'skill/scripts/mathprove_hook.py'
    with tempfile.TemporaryDirectory(prefix='mathprove bench ') as d:
        root=Path(d);s=Store(root,create=True);s.create_run('bench',{'mode':'research','statement':'Elementary timing fixture','assumptions':[],'symbols':{}})
        times={}
        for event in ('PreToolUse','PostToolUse','SessionStart','Stop'):
            values=[]
            for i in range(a.samples):
                payload={'session_id':'benchmark','cwd':d,'hook_event_name':event,'tool_name':'Bash','tool_input':{'command':'echo fixture'},'tool_response':{'exit_code':0},'tool_use_id':str(i)}
                start=time.perf_counter();r=subprocess.run([sys.executable,str(script),'--root',d,'--event',event],input=json.dumps(payload),text=True,capture_output=True,timeout=10)
                elapsed=(time.perf_counter()-start)*1000
                if r.returncode:raise RuntimeError('Hook process failed')
                json.loads(r.stdout);values.append(elapsed)
            ordered=sorted(values);times[event]={'median_ms':round(statistics.median(values),3),'p95_ms':round(ordered[min(len(ordered)-1,int(.95*len(ordered)))],3)}
        print(json.dumps({'samples_per_event':a.samples,'python':sys.version.split()[0],'platform':sys.platform,'measurements':times,'scope':'Local synthetic subprocess overhead. Not a comparison with Pi, CoMath, research outcomes, or model-token spending.'},indent=2))
if __name__=='__main__':main()
