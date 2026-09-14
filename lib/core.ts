import {CHUNK_BYTES,MAX_VIDEO_BYTES,MAX_SCENE_BYTES,PRESETS} from './contracts.ts';
// Environment-free API core. Tests exercise the same handlers against SQLite and a bucket adapter.
type Dependencies={db:D1Database;bucket:R2Bucket;fetcher?:typeof fetch};
class ApiError extends Error{status:number;constructor(status:number,message:string){super(message);this.status=status}}
function check(ok:unknown,status:number,message:string):asserts ok{if(!ok)throw new ApiError(status,message)}
const json=(v:unknown,status=200)=>Response.json(v,{status,headers:{'Cache-Control':'no-store'}});
async function body(req:Request){check(Number(req.headers.get('content-length')||0)<32768,413,'Request is too large');const txt=await req.text();check(txt.length<32768,413,'Request is too large');try{return JSON.parse(txt)}catch{throw new ApiError(400,'Invalid JSON')}}
function validName(n:unknown){check(typeof n==='string'&&n.trim().length>0&&n.length<=160,400,'Name must contain 1–160 characters');return n.trim()}
function workerUrl(s:unknown){check(typeof s==='string',400,'Enter the HTTPS URL of your worker');let u:URL;try{u=new URL(s)}catch{throw new ApiError(400,'Invalid worker URL')}check(u.protocol==='https:'&&!u.username&&!u.password&&!u.search&&!u.hash,400,'Use an HTTPS URL without credentials or query parameters');const h=u.hostname.toLowerCase();check(!h.includes(':')&&!/^\d+\.\d+\.\d+\.\d+$/.test(h)&&h!=='localhost'&&!h.endsWith('.local')&&!h.endsWith('.internal'),400,'Use a reachable HTTPS hostname');return u.toString().replace(/\/$/,'')}
function exposeJob(j:any){return {...j,owner:undefined,lease:undefined,transferred:undefined,media:JSON.parse(j.media),report:j.report?JSON.parse(j.report):null,result:j.result?`/api/jobs/${j.id}/artifact`:null}}
export async function handleApi(req:Request,owner:string|null,deps:Dependencies):Promise<Response>{
 try{check(owner,401,'Sign in to access your scenes.');const {db,bucket}=deps;check(db&&bucket,503,'Scene storage is temporarily unavailable. Please try again.');
 const url=new URL(req.url),p=url.pathname.replace(/^\/api\/?/,'').split('/').filter(Boolean),method=req.method,now=Date.now();
 const first=(sql:string,...v:any[])=>db.prepare(sql).bind(...v).first<any>();
 const run=(sql:string,...v:any[])=>db.prepare(sql).bind(...v).run();
 const all=async(sql:string,...v:any[])=>(await db.prepare(sql).bind(...v).all<any>()).results;
 async function media(id:string){const x=await first('SELECT * FROM uploads WHERE id=? AND owner=?',id,owner);check(x,404,'File not found');return x}
 async function job(id:string){const x=await first('SELECT * FROM jobs WHERE id=? AND owner=?',id,owner);check(x,404,'Scene not found');return x}
 async function remote(cfg:any,path:string,init:RequestInit={}){const r=await(deps.fetcher||fetch)(cfg.url+path,{...init,redirect:'error',headers:{Authorization:`Bearer ${cfg.token}`,...init.headers},signal:AbortSignal.timeout(path.includes('/inputs/')?180000:path==='/health'?120000:20000)});if(!r.ok){let msg='';try{msg=(await r.json() as any).error||''}catch{}throw new ApiError(502,`Worker returned ${r.status}${msg?`: ${String(msg).slice(0,240)}`:''}`)}return r}
 if(p[0]==='config'){
  if(method==='GET'){const cfg=await first('SELECT * FROM settings WHERE owner=?',owner);return json({url:cfg?.url||'',configured:!!cfg,tokenConfigured:!!cfg?.token})}
  if(method==='POST'&&p[1]==='check'){const cfg=await first('SELECT * FROM settings WHERE owner=?',owner);check(cfg,409,'Save the worker connection first');const h=await(await remote(cfg,'/health')).json() as any;check(h.service==='wolfworld-worker',502,'This endpoint is not a WolfWorld worker');return json(h)}
  if(method==='PUT'){const b=await body(req),address=workerUrl(b.url);const prev=await first('SELECT * FROM settings WHERE owner=?',owner);const token=b.token||prev?.token;check(typeof token==='string'&&token.length>=24&&token.length<=256,400,'Worker token must contain 24–256 characters');await run('INSERT INTO settings(owner,url,token) VALUES(?,?,?) ON CONFLICT(owner) DO UPDATE SET url=excluded.url,token=excluded.token',owner,address,token);return json({url:address,configured:true,tokenConfigured:true})}
 }
 if(p[0]==='media'&&method==='GET')return json(await all('SELECT id,name,kind,size,mime,status,created FROM uploads WHERE owner=? AND status=? ORDER BY created DESC LIMIT 100',owner,'ready'));
 if(p[0]==='uploads'){
  if(p.length===1&&method==='POST'){const b=await body(req),name=validName(b.name),ext=name.split('.').pop()?.toLowerCase(),kind=b.kind==='splat'?'splat':'video',limit=kind==='video'?MAX_VIDEO_BYTES:MAX_SCENE_BYTES;check((kind==='video'?['mp4','mov','m4v','webm']:['ply','spz','splat','ksplat','sog']).includes(ext||''),400,'Unsupported file format');check(Number.isSafeInteger(b.size)&&b.size>0&&b.size<=limit,413,kind==='video'?'Each video must be 2 GB or smaller':'Scene files must be 256 MB or smaller');const id=crypto.randomUUID(),key=`${owner}/${id}/${name.replace(/[^a-zA-Z0-9._-]/g,'_')}`,mime=kind==='video'?(ext==='webm'?'video/webm':ext==='mov'?'video/quicktime':'video/mp4'):'application/octet-stream';const up=await bucket.createMultipartUpload(key,{httpMetadata:{contentType:mime}});try{await run('INSERT INTO uploads(id,owner,name,kind,size,mime,key,multipart,status,created) VALUES(?,?,?,?,?,?,?,?,?,?)',id,owner,name,kind,b.size,mime,key,up.uploadId,'uploading',now)}catch(e){await up.abort();throw e}return json({id,chunkBytes:CHUNK_BYTES},201)}
  const x=await media(p[1]);
  if(p[2]==='parts'&&method==='PUT'){
   check(x.status==='uploading',409,'File upload is already complete');const n=Number(p[3]),count=Math.ceil(x.size/CHUNK_BYTES);check(Number.isInteger(n)&&n>=1&&n<=count,400,'Invalid part number');const expected=Math.min(CHUNK_BYTES,x.size-(n-1)*CHUNK_BYTES);check(Number(req.headers.get('content-length'))===expected,400,'Part length does not match');const bytes=await req.arrayBuffer();check(bytes.byteLength===expected,400,'Part content is incomplete');const part=await bucket.resumeMultipartUpload(x.key,x.multipart).uploadPart(n,bytes);await run('INSERT INTO parts(id,upload,part,etag,size) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET etag=excluded.etag,size=excluded.size',`${x.id}:${n}`,x.id,n,part.etag,expected);return json({part:n})
  }
  if(p[2]==='complete'&&method==='POST'){
   if(x.status==='ready')return json({id:x.id,status:'ready'});check(x.status==='uploading',409,'Upload has been stopped');const pts=await all('SELECT part,etag,size FROM parts WHERE upload=? ORDER BY part',x.id);check(pts.length===Math.ceil(x.size/CHUNK_BYTES)&&pts.reduce((s:number,a:any)=>s+a.size,0)===x.size,409,'Some parts are missing. Please upload the file again.');const existing=await bucket.head(x.key);if(!existing)await bucket.resumeMultipartUpload(x.key,x.multipart).complete(pts.map((a:any)=>({partNumber:a.part,etag:a.etag})));await run('UPDATE uploads SET status=? WHERE id=?','ready',x.id);return json({id:x.id,status:'ready'})
  }
  if(method==='DELETE'){
   const linked=await all('SELECT media FROM jobs WHERE owner=?',owner);check(!linked.some((j:any)=>JSON.parse(j.media).includes(x.id)),409,'A scene references this file. Keep the source video.');if(x.status==='uploading')await bucket.resumeMultipartUpload(x.key,x.multipart).abort();else await bucket.delete(x.key);await db.batch([db.prepare('DELETE FROM parts WHERE upload=?').bind(x.id),db.prepare('DELETE FROM uploads WHERE id=?').bind(x.id)]);return json({deleted:true})
  }
  if(p[2]==='file'&&method==='GET'){check(x.status==='ready',409,'File upload is not complete');const obj=await bucket.get(x.key);check(obj,404,'File content not found');return new Response(obj.body as any,{headers:{'Content-Type':x.mime,'Content-Length':String(obj.size),'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Disposition':`inline; filename*=UTF-8''${encodeURIComponent(x.name)}`}})}
 }
 if(p[0]==='jobs'){
  if(p.length===1&&method==='GET')return json((await all('SELECT * FROM jobs WHERE owner=? ORDER BY created DESC LIMIT 100',owner)).map(exposeJob));
  if(p.length===1&&method==='POST'){
   const b=await body(req),name=validName(b.name);check(Array.isArray(b.media)&&b.media.length>=1&&b.media.length<=12&&new Set(b.media).size===b.media.length,400,'Select 1–12 videos');check(Object.hasOwn(PRESETS,b.preset),400,'Invalid reconstruction preset');for(const id of b.media){const x=await media(id);check(x.status==='ready'&&x.kind==='video',400,'Finish uploading the videos first')}
   const active=await first("SELECT COUNT(*) AS n FROM jobs WHERE owner=? AND status IN ('queued','running','transferring')",owner);check(active.n<5,409,'At most 5 active jobs are allowed');const id=crypto.randomUUID();await run('INSERT INTO jobs(id,owner,name,media,status,stage,progress,preset,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?)',id,owner,name,JSON.stringify(b.media),'queued','Waiting for worker',0,b.preset,now,now);return json(exposeJob(await job(id)),201)
  }
  const j=await job(p[1]);
  if(p[2]==='artifact'&&method==='GET'){check(j.status==='complete'&&j.result,409,'Reconstruction output is not ready');const obj=await bucket.get(j.result);check(obj,404,'Reconstruction file not found');return new Response(obj.body as any,{headers:{'Content-Type':'application/octet-stream','Content-Length':String(obj.size),'Cache-Control':'private, no-store','Content-Disposition':'attachment; filename="gaussians.ply"'}})}
  if(p[2]==='cancel'&&method==='POST'){check(!['complete','cancelled'].includes(j.status),409,'This job has already ended');const cfg=await first('SELECT * FROM settings WHERE owner=?',owner);if(cfg&&j.status!=='queued'){await remote(cfg,`/jobs/${j.id}/cancel`,{method:'POST'})}await run('UPDATE jobs SET status=?,stage=?,updated=? WHERE id=?','cancelled','Cancelled',now,j.id);return json(exposeJob(await job(j.id)))}
  if(p[2]==='retry'&&method==='POST'){check(['failed','cancelled'].includes(j.status),409,'This job does not need a retry');const id=crypto.randomUUID();await run('INSERT INTO jobs(id,owner,name,media,status,stage,progress,preset,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?)',id,owner,j.name,j.media,'queued','Waiting for worker',0,j.preset,now,now);return json(exposeJob(await job(id)),201)}
  if(p[2]==='sync'&&method==='POST'){
   if(['complete','failed','cancelled'].includes(j.status))return json(exposeJob(j));const cfg=await first('SELECT * FROM settings WHERE owner=?',owner);if(!cfg)return json(exposeJob(j));
   const lock=await run("UPDATE jobs SET lease=? WHERE id=? AND lease<? AND status IN ('queued','transferring','running')",now+240000,j.id,now);if(!lock.meta.changes)return json(exposeJob(j));
   try{
    const preset=PRESETS[j.preset as keyof typeof PRESETS];const ids:string[]=JSON.parse(j.media);const inputs=[];for(const id of ids)inputs.push(await media(id));
    if(j.status==='queued'){
     const health=await(await remote(cfg,'/health')).json() as any;check(health.service==='wolfworld-worker'&&health.model_ready,409,health.message||'The worker GPU or model is not ready');
     await remote(cfg,'/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:j.id,frames:preset.frames,resolution:preset.resolution,inputs:inputs.map((x:any)=>({id:x.id,name:x.name,size:x.size}))})});await run('UPDATE jobs SET status=?,stage=?,progress=?,error=NULL,updated=? WHERE id=? AND status<>?','transferring','Transferring source videos',5,Date.now(),j.id,'cancelled');
    }else if(j.status==='transferring'){
     const chunks=inputs.flatMap((x:any)=>Array.from({length:Math.ceil(x.size/CHUNK_BYTES)},(_,i)=>({x,part:i+1,offset:i*CHUNK_BYTES,length:Math.min(CHUNK_BYTES,x.size-i*CHUNK_BYTES),last:(i+1)*CHUNK_BYTES>=x.size})));
     if(j.transferred<chunks.length){const {x,part,offset,length,last}=chunks[j.transferred],obj=await bucket.get(x.key,{range:{offset,length}});check(obj,404,'Source video not found');await remote(cfg,`/jobs/${j.id}/inputs/${x.id}/parts/${part}`,{method:'PUT',headers:{'Content-Type':'application/octet-stream','Content-Length':String(length)},body:obj.body as any});if(last)await remote(cfg,`/jobs/${j.id}/inputs/${x.id}/complete`,{method:'POST'});await run('UPDATE jobs SET transferred=?,progress=?,updated=? WHERE id=? AND status<>?',j.transferred+1,Math.round(5+15*(j.transferred+1)/chunks.length),Date.now(),j.id,'cancelled')}
     else{await remote(cfg,`/jobs/${j.id}/start`,{method:'POST'});await run('UPDATE jobs SET status=?,stage=?,progress=?,updated=? WHERE id=? AND status<>?','running','Extracting keyframes',25,Date.now(),j.id,'cancelled')}
    }else{
     const r=await(await remote(cfg,`/jobs/${j.id}`)).json() as any;
     if(r.status==='complete'){
      const res=await remote(cfg,`/jobs/${j.id}/artifact`);check(res.body,502,'The worker did not return a scene file');const size=Number(res.headers.get('content-length'));check(size>0&&size<=MAX_SCENE_BYTES,413,'Output is empty or exceeds 256 MB. Try a lower quality preset.');const key=`${owner}/results/${j.id}/gaussians.ply`;await bucket.put(key,res.body as any,{httpMetadata:{contentType:'application/octet-stream'}});await run('UPDATE jobs SET status=?,stage=?,progress=?,result=?,report=?,error=NULL,updated=? WHERE id=? AND status<>?','complete','Reconstruction complete',100,key,JSON.stringify(r.report||{}),Date.now(),j.id,'cancelled');
     }else if(r.status==='failed'||r.status==='cancelled')await run('UPDATE jobs SET status=?,stage=?,error=?,updated=? WHERE id=? AND status<>?',r.status,r.status==='failed'?'Reconstruction failed':'Cancelled',String(r.error||'Worker stopped the job').slice(0,500),Date.now(),j.id,'cancelled');
     else await run('UPDATE jobs SET stage=?,progress=?,error=NULL,updated=? WHERE id=? AND status<>?',String(r.stage||'Reconstructing').slice(0,120),Math.min(95,Math.max(25,Number(r.progress)||25)),Date.now(),j.id,'cancelled');
    }
   }catch(e){const msg=e instanceof Error?e.message:'Worker is temporarily unreachable';await run('UPDATE jobs SET error=?,updated=? WHERE id=?',msg.slice(0,500),Date.now(),j.id);throw e}finally{await run('UPDATE jobs SET lease=0 WHERE id=?',j.id)}
   return json(exposeJob(await job(j.id)))
  }
  if(method==='GET')return json(exposeJob(j));
 }
 throw new ApiError(404,'Endpoint not found');
 }catch(e){if(e instanceof ApiError)return json({error:e.message},e.status);console.error('WolfWorld API',e instanceof Error?e.message:'unknown');return json({error:'The operation could not finish. Please retry; your jobs and source videos are preserved.'},503)}
}
