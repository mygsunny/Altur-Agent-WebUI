#!/usr/bin/env python3
"""Install a pinned runtime only within this checkout. Never invoke global bootstrap."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];b=json.loads((root/'branding/brand.json').read_text());dest=root/'.runtime/hermes-agent'
def run(*a):subprocess.run(a,check=True,cwd=root)
dest.parent.mkdir(exist_ok=True)
if not dest.exists():run('git','clone',b['runtime']['repository'],str(dest))
else:
 if subprocess.check_output(['git','-C',str(dest),'status','--porcelain'],text=True).strip():raise SystemExit('Runtime has local edits; refusing checkout')
run('git','-C',str(dest),'checkout','--detach',b['runtime']['commit'])
# Use the runtime's declared overrides, matching the upstream Docker installer.
import tomllib
project=tomllib.loads((dest/'pyproject.toml').read_text())
overrides=root/'.runtime/overrides.txt'
overrides.write_text('\n'.join(project.get('tool',{}).get('uv',{}).get('override-dependencies',[]))+'\n')
run(sys.executable,'-m','pip','install','uv==0.13.6')
run(sys.executable,'-m','uv','pip','install','--python',sys.executable,'--overrides',str(overrides),'-e',str(dest),'-r',str(root/'requirements.txt'))
print('Runtime installed. Start with this interpreter and scripts/start-altur.py.')
