"""Local OpenAI-compatible fixture. Never a real AI provider."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,time,argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port',type=int,default=8794)
parser.add_argument('--capture',type=Path,help='Optional local request capture for prompt inspection')
parser.add_argument('--capture-log',type=Path,help='Append every dummy fixture request as JSONL for prompt-boundary inspection')
args=parser.parse_args()
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  raw=json.dumps({'object':'list','data':[{'id':'altur-fixture','object':'model','owned_by':'local-fixture'}]}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
 def do_POST(self):
  d=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
  if args.capture:
   args.capture.parent.mkdir(parents=True,exist_ok=True);args.capture.write_text(json.dumps(d,indent=2))
  if args.capture_log:
   args.capture_log.parent.mkdir(parents=True,exist_ok=True)
   with args.capture_log.open('a') as output:output.write(json.dumps(d)+'\n')
  user=next((str(m.get('content','')) for m in reversed(d.get('messages',[])) if m.get('role')=='user'),'')
  text='[LOCAL FIXTURE] I am Altur-Agent. This response verifies the WebUI transport and branding; no real AI provider was called.'
  if 'preserve' in user.lower():text+=' User text preserved: Hermes, NousResearch, nesquena.'
  if 'slow' in user.lower():text+=' Slow streaming cancellation fixture. '*120
  self.send_response(200)
  if d.get('stream'):
   self.send_header('Content-Type','text/event-stream');self.end_headers()
   try:
    for i in range(0,len(text),12):
     payload={'id':'fixture','object':'chat.completion.chunk','model':'altur-fixture','choices':[{'index':0,'delta':{'content':text[i:i+12]},'finish_reason':None}]}
     self.wfile.write(('data: '+json.dumps(payload)+'\n\n').encode());self.wfile.flush();time.sleep(.06 if 'slow' not in user else .15)
    self.wfile.write(('data: '+json.dumps({'id':'fixture','object':'chat.completion.chunk','model':'altur-fixture','choices':[{'index':0,'delta':{},'finish_reason':'stop'}]})+'\n\n').encode())
    self.wfile.write(b'data: [DONE]\n\n')
   except BrokenPipeError:pass
  else:
   self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'id':'fixture','object':'chat.completion','model':'altur-fixture','choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':30,'total_tokens':130}}).encode())
ThreadingHTTPServer(('127.0.0.1',args.port),H).serve_forever()
