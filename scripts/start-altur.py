#!/usr/bin/env python3
"""Foreground, loopback-only launch with checkout-local state and runtime."""
import argparse,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8793);p.add_argument('--agent-dir',type=Path);args=p.parse_args()
base=root/'.trial';home=base/'agent-home';state=base/'state'
for d in [home,state,base/'workspace']:d.mkdir(parents=True,exist_ok=True)
agent=(args.agent_dir or root/'.runtime/hermes-agent').resolve()
if not (agent/'run_agent.py').is_file():
 p.error('Isolated agent source is missing. Run scripts/setup-altur.py first.')
settings=state/'settings.json'
if not settings.exists():
 settings.write_text(json.dumps({'show_claude_code_sessions':False,'default_workspace':str(base/'workspace')}))
# Seed only a new instance's supported identity file; preserve custom SOUL.md.
b=json.loads((root/'branding/brand.json').read_text())
soul=home/'SOUL.md'
if not soul.exists():
 soul.write_text(b['assistant']['identity_instruction'].format(product=b['product']['display_name'],publisher=b['organization']['display_name'])+'\n')
# Drop inherited provider credentials, profile selectors, discovery overrides.
env={k:v for k,v in os.environ.items() if not (k.startswith(('HERMES_','OPENAI_','ANTHROPIC_','OPENROUTER_')) or k.endswith('_API_KEY'))}
env.update(HERMES_HOME=str(home),HERMES_BASE_HOME=str(home),HERMES_CONFIG_PATH=str(home/'config.yaml'),HERMES_WEBUI_STATE_DIR=str(state),HERMES_WEBUI_AGENT_DIR=str(agent),HERMES_WEBUI_PYTHON=sys.executable,HERMES_WEBUI_DEFAULT_WORKSPACE=str(base/'workspace'),HERMES_WEBUI_HOST='127.0.0.1',HERMES_WEBUI_PORT=str(args.port),ALTUR_WEBUI_ISOLATED='1')
os.chdir(root);os.execve(sys.executable,[sys.executable,str(root/'server.py')],env)
