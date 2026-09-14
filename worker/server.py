"""Authenticated, persistent single-GPU job service. Start with python server.py."""
from __future__ import annotations
import argparse, hmac, json, os, re, sqlite3, threading, uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from engine import extract_frames,reconstruct,health,Cancelled

UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
class Service:
 def __init__(self,root:Path,repo:Path,token:str):
  if len(token)<24:raise ValueError('WOLFWORLD_TOKEN must contain at least 24 characters')
  self.root=root.resolve();self.root.mkdir(parents=True,exist_ok=True);self.repo=repo.resolve();self.token=token
  self.db=sqlite3.connect(self.root/'jobs.sqlite',check_same_thread=False);self.lock=threading.RLock();self.pool=ThreadPoolExecutor(max_workers=1);self.processes={};self.receiving=set();self.health_cache=None
  self.db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,data TEXT NOT NULL)');self.db.commit()
  for row in self.db.execute('SELECT id,data FROM jobs').fetchall():
   job=json.loads(row[1])
   if job['status'] in ('running','queued'):self.update(job['id'],status='failed',stage='Worker restarted',error='Worker restart interrupted the job; start a new reconstruction in the web app')
 def get(self,id):
  with self.lock:
   row=self.db.execute('SELECT data FROM jobs WHERE id=?',(id,)).fetchone()
   return json.loads(row[0]) if row else None
 def update(self,id,**changes):
  with self.lock:
   data=self.get(id);data.update(changes);self.db.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(data,ensure_ascii=False),id));self.db.commit();return data
 def create(self,b):
  if not UUID.fullmatch(str(b.get('id',''))):raise ValueError('Invalid job ID')
  if b.get('frames') not in (24,48,96) or b.get('resolution') not in (518,700,952):raise ValueError('Unsupported model configuration')
  items=b.get('inputs');
  if not isinstance(items,list) or not 1<=len(items)<=12:raise ValueError('Select 1–12 videos')
  seen=set()
  for i in items:
   if not UUID.fullmatch(str(i.get('id',''))) or i['id'] in seen:raise ValueError('Invalid or duplicate video ID')
   if not isinstance(i.get('size'),int) or not 0<i['size']<=2*1024**3:raise ValueError('Invalid video size')
   if not isinstance(i.get('name'),str) or Path(i['name']).suffix.lower() not in ('.mp4','.mov','.m4v','.webm'):raise ValueError('Invalid video format')
   seen.add(i['id'])
  with self.lock:
   previous=self.get(b['id'])
   if previous:
    if any(previous[k]!=b[k] for k in ('inputs','frames','resolution')):raise ValueError('The existing job ID has different inputs or settings')
    return previous
   active=sum(json.loads(v[0])['status'] in ('uploading','queued','running') for v in self.db.execute('SELECT data FROM jobs'))
   if active>=5:raise ValueError('Worker queue is full; at most 5 active jobs are allowed')
   data={k:b[k] for k in ('id','inputs','frames','resolution')};data.update(status='uploading',stage='Waiting for videos',progress=5,error=None,received=[])
   (self.root/b['id']/'inputs').mkdir(parents=True,exist_ok=True)
   self.db.execute('INSERT INTO jobs VALUES(?,?)',(b['id'],json.dumps(data)));self.db.commit();return data
 def start(self,id):
  with self.lock:
   j=self.get(id)
   if not j:raise KeyError('Job not found')
   if j['status'] in ('queued','running','complete'):return j
   if j['status']!='uploading':raise ValueError('Job has ended; create a new job')
   if set(j['received'])!={i['id'] for i in j['inputs']}:raise ValueError('Video transfer is incomplete')
   j=self.update(id,status='queued',stage='Waiting for GPU',progress=25);self.pool.submit(self.run,id);return j
 def cancel(self,id):
  with self.lock:
   j=self.get(id)
   if not j:raise KeyError('Job not found')
   if j['status']=='complete':raise ValueError('Job is already complete')
   return self.update(id,status='cancelled',stage='Cancelled',error='Job cancelled by user')
 def run(self,id):
  def cancelled():return self.get(id)['status']=='cancelled'
  def progress(p,s):
   with self.lock:
    if not cancelled():self.update(id,progress=p,stage=s)
  if cancelled():return
  j=self.update(id,status='running',stage='Extracting keyframes',progress=25);directory=self.root/id
  try:
   inputs=[{**i,'path':str(directory/'inputs'/(i['id']+Path(i['name']).suffix.lower()))} for i in j['inputs']]
   report=extract_frames(inputs,directory,j['frames'],progress,cancelled)
   if cancelled():raise Cancelled('Job cancelled')
   path,count=reconstruct(self.repo,directory,j['resolution'],progress,cancelled)
   if cancelled():raise Cancelled('Job cancelled')
   report['gaussians']=count;report['output_bytes']=path.stat().st_size
   self.update(id,status='complete',stage='Reconstruction complete',progress=100,report=report)
  except Cancelled:pass
  except Exception as exc:
   if not cancelled():self.update(id,status='failed',stage='Reconstruction failed',error=str(exc)[:500])
 def get_health(self):
  # Importing a foundation model repeatedly is expensive; cache dependency diagnostics.
  with self.lock:
   if self.health_cache is None:self.health_cache=health(self.repo)
   return self.health_cache

class Handler(BaseHTTPRequestHandler):
 server_version='WolfWorld/1.0'
 def log_message(self,fmt,*args):pass  # no URLs, bearer tokens or video names in HTTP logs
 def reply(self,data,status=200):
  b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def json_body(self):
  n=int(self.headers.get('Content-Length','0'))
  if not 0<n<32768:raise ValueError('JSON request is too large or empty')
  return json.loads(self.rfile.read(n))
 def handle_request(self):
  self.connection.settimeout(180)
  svc:Service=self.server.service
  if not hmac.compare_digest(self.headers.get('Authorization','').encode('utf-8'),f'Bearer {svc.token}'.encode('utf-8')):
   self.close_connection=True;return self.reply({'error':'Invalid access token'},401)
  p=urlsplit(self.path).path.strip('/').split('/')
  try:
   if p==['health'] and self.command=='GET':return self.reply(svc.get_health())
   if p==['jobs'] and self.command=='POST':return self.reply(svc.create(self.json_body()),201)
   if len(p)<2 or p[0]!='jobs' or not UUID.fullmatch(p[1]):raise KeyError('Endpoint not found')
   id=p[1];j=svc.get(id)
   if not j:raise KeyError('Job not found')
   if len(p)==2 and self.command=='GET':return self.reply(j)
   if p[2:] == ['start'] and self.command=='POST':return self.reply(svc.start(id))
   if p[2:] == ['cancel'] and self.command=='POST':return self.reply(svc.cancel(id))
   if len(p)>=5 and p[2]=='inputs':
    item=next((i for i in j['inputs'] if i['id']==p[3]),None)
    if not item:raise KeyError('Video not found')
    directory=svc.root/id/'inputs';path=directory/(item['id']+Path(item['name']).suffix.lower());chunk_size=8*1024*1024;count=(item['size']+chunk_size-1)//chunk_size
    if len(p)==6 and p[4]=='parts' and self.command=='PUT':
     n=int(p[5]);size=int(self.headers.get('Content-Length','0'))
     if not 1<=n<=count or size!=min(chunk_size,item['size']-(n-1)*chunk_size):raise ValueError('Incorrect part number or content length')
     key=(id,item['id'])
     with svc.lock:
      if svc.get(id)['status']!='uploading':raise ValueError('Job is not accepting new videos')
      if key in svc.receiving:raise ValueError('This video is being uploaded; retry later')
      svc.receiving.add(key)
     part=directory/f"{item['id']}.part{n:04}";temp=part.with_suffix('.partial')
     try:
      left=size
      with temp.open('wb') as f:
       while left:
        chunk=self.rfile.read(min(1024*1024,left))
        if not chunk:raise ValueError('Part upload interrupted')
        f.write(chunk);left-=len(chunk)
      temp.replace(part)
     finally:
      temp.unlink(missing_ok=True)
      with svc.lock:svc.receiving.discard(key)
     return self.reply({'part':n})
    if len(p)==5 and p[4]=='complete' and self.command=='POST':
     with svc.lock:
      if (id,item['id']) in svc.receiving:raise ValueError('Video upload is in progress')
      if svc.get(id)['status']!='uploading':raise ValueError('Job is not accepting new videos')
      parts=[directory/f"{item['id']}.part{n:04}" for n in range(1,count+1)]
      if not path.is_file() or path.stat().st_size!=item['size']:
       if any(not part.is_file() or part.stat().st_size!=min(chunk_size,item['size']-i*chunk_size) for i,part in enumerate(parts)):raise ValueError('Video parts are incomplete')
       temp=path.with_suffix('.assembling')
       with temp.open('wb') as out:
        for part in parts:
         with part.open('rb') as inp:
          while chunk:=inp.read(1024*1024):out.write(chunk)
       temp.replace(path)
      current=svc.get(id);svc.update(id,received=list(set(current['received']+[item['id']])))
      for part in parts:part.unlink(missing_ok=True)
     return self.reply({'received':True})
   if len(p)==4 and p[2]=='inputs' and self.command=='PUT':
    item=next((i for i in j['inputs'] if i['id']==p[3]),None)
    if not item:raise KeyError('Video not found')
    size=int(self.headers.get('Content-Length','0'))
    if size!=item['size']:raise ValueError('Video size mismatch; an exact Content-Length is required')
    key=(id,item['id'])
    with svc.lock:
     if j['status']!='uploading':raise ValueError('Job is not currently accepting new videos')
     if key in svc.receiving:raise ValueError('This video is being uploaded; retry later')
     svc.receiving.add(key)
    path=svc.root/id/'inputs'/(item['id']+Path(item['name']).suffix.lower());temp=path.with_suffix('.partial')
    try:
     left=size
     with temp.open('wb') as f:
      while left:
       chunk=self.rfile.read(min(1024*1024,left))
       if not chunk:raise ValueError('Video upload interrupted')
       f.write(chunk);left-=len(chunk)
     temp.replace(path)
     with svc.lock:
      current=svc.get(id);svc.update(id,received=list(set(current['received']+[item['id']])))
    finally:
     temp.unlink(missing_ok=True)
     with svc.lock:svc.receiving.discard(key)
    return self.reply({'received':True})
   if p[2:]==['artifact'] and self.command=='GET':
    if j['status']!='complete':raise ValueError('Reconstruction artifact is not ready')
    path=svc.root/id/'output'/'gaussians.ply'
    self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(path.stat().st_size));self.end_headers()
    with path.open('rb') as f:
     while b:=f.read(1024*1024):self.wfile.write(b)
    return
   raise KeyError('Endpoint not found')
  except KeyError as exc:self.reply({'error':str(exc)},404)
  except (ValueError,json.JSONDecodeError) as exc:self.close_connection=True;self.reply({'error':str(exc)},400)
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception:self.close_connection=True;self.reply({'error':'Worker error; check deployment configuration and available disk space'},500)
 do_GET=handle_request
 do_POST=handle_request
 do_PUT=handle_request

def create_server(svc:Service,host='0.0.0.0',port=8788):
 httpd=ThreadingHTTPServer((host,port),Handler);httpd.service=svc;return httpd

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--host',default='0.0.0.0');parser.add_argument('--port',type=int,default=8788);parser.add_argument('--data',default=os.environ.get('WOLFWORLD_DATA','./data'));parser.add_argument('--repo',default=os.environ.get('WORLDMIRROR_REPO','/opt/HY-World-2.0'));args=parser.parse_args()
 svc=Service(Path(args.data),Path(args.repo),os.environ.get('WOLFWORLD_TOKEN',''));httpd=create_server(svc,args.host,args.port)
 print(f'WolfWorld worker listening on {args.host}:{args.port}',flush=True)
 try:httpd.serve_forever()
 except KeyboardInterrupt:pass
 finally:httpd.server_close();svc.pool.shutdown(wait=False,cancel_futures=True)
if __name__=='__main__':main()
