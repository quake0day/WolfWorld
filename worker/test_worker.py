import json, os, subprocess, tempfile, threading, unittest, urllib.request, urllib.error, uuid
from pathlib import Path
from engine import extract_frames,probe,validate_gaussian,model_command,health
from server import Service,create_server

class WorkerTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def video(self,name='room.mp4',offset=0):
  path=self.root/name
  subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i',f'testsrc2=size=320x240:rate=12:duration=3','-vf',f'hue=h={offset}','-c:v','mpeg4','-y',str(path)],check=True,capture_output=True)
  return path
 def test_real_ffmpeg_multivideo_preprocessing(self):
  paths=[self.video('one.mp4'),self.video('two.mp4',60)];inputs=[{'id':str(uuid.uuid4()),'name':p.name,'path':str(p)} for p in paths]
  progress=[];report=extract_frames(inputs,self.root/'job',24,lambda p,s:progress.append(p));self.assertEqual(report['videos'],2);self.assertGreaterEqual(report['selected_frames'],4);self.assertLessEqual(report['selected_frames'],24);self.assertEqual(len({f['video_id'] for f in report['frames']}),2);self.assertEqual(progress[-1],50);self.assertFalse(report['generated_unobserved_regions']);self.assertEqual(probe(paths[0])['width'],320)
 def test_corrupt_video_rejected(self):
  p=self.root/'bad.mp4';p.write_bytes(b'not a video')
  with self.assertRaises(subprocess.CalledProcessError):probe(p)
 def test_stationary_duplicate_video_rejected(self):
  p=self.root/'flat.mp4';subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=blue:size=320x240:duration=2','-c:v','mpeg4',str(p)],check=True)
  with self.assertRaisesRegex(ValueError,'distinct frames'):extract_frames([{'id':'a','name':p.name,'path':str(p)}],self.root/'job',24)
 def test_adapter_command_and_gaussian_validation(self):
  cmd=model_command(self.root,self.root/'frames',self.root/'output',518);self.assertIn('--strict_output_path',cmd);self.assertIn('--no_interactive',cmd);self.assertIn('--enable_bf16',cmd)
  p=self.root/'pointcloud.ply';p.write_text('ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nend_header\n0\n')
  with self.assertRaisesRegex(ValueError,'Gaussian'):validate_gaussian(p)
 def test_service_auth_upload_queue_cancellation_and_persistence(self):
  token='test-only-token-'+('x'*24);svc=Service(self.root/'data',self.root/'missing-repo',token);httpd=create_server(svc,'127.0.0.1',0);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{httpd.server_port}'
  def request(path,method='GET',data=None,auth=True):
   headers={'Authorization':f'Bearer {token}'} if auth else {};b=json.dumps(data).encode() if isinstance(data,dict) else data
   req=urllib.request.Request(base+path,data=b,headers=headers,method=method)
   with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
  try:
   with self.assertRaises(urllib.error.HTTPError) as ctx:request('/health',auth=False)
   self.assertEqual(ctx.exception.code,401);self.assertFalse(request('/health')['model_ready'])
   v=self.video();vid=str(uuid.uuid4());jid=str(uuid.uuid4());b={'id':jid,'frames':24,'resolution':518,'inputs':[{'id':vid,'name':'room.mp4','size':v.stat().st_size}]}
   self.assertEqual(request('/jobs','POST',b)['id'],jid);self.assertEqual(request('/jobs','POST',b)['id'],jid)
   with self.assertRaises(urllib.error.HTTPError):request(f'/jobs/{jid}/start','POST')
   self.assertEqual(request(f'/jobs/{jid}/inputs/{vid}/parts/1','PUT',v.read_bytes())['part'],1);self.assertTrue(request(f'/jobs/{jid}/inputs/{vid}/complete','POST')['received']);self.assertTrue(request(f'/jobs/{jid}/inputs/{vid}/complete','POST')['received']);self.assertEqual(request(f'/jobs/{jid}')['received'],[vid]);request(f'/jobs/{jid}/cancel','POST');self.assertEqual(request(f'/jobs/{jid}')['status'],'cancelled')
   other=Service(self.root/'data',self.root/'missing-repo',token);self.assertEqual(other.get(jid)['status'],'cancelled');other.pool.shutdown();other.db.close()
  finally:httpd.shutdown();httpd.server_close();svc.pool.shutdown();svc.db.close()
 def test_restart_marks_interrupted_jobs_failed(self):
  svc=Service(self.root/'data',self.root,'x'*32);jid=str(uuid.uuid4());svc.create({'id':jid,'frames':24,'resolution':518,'inputs':[{'id':str(uuid.uuid4()),'name':'a.mp4','size':10}]});svc.update(jid,status='running');svc.pool.shutdown();svc.db.close();svc=Service(self.root/'data',self.root,'x'*32);self.assertEqual(svc.get(jid)['status'],'failed');svc.pool.shutdown();svc.db.close()

if __name__=='__main__':unittest.main(verbosity=2)
