"""Real video preprocessing and WorldMirror 2.0 adapter. No simulated model output."""
from __future__ import annotations
import json, math, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np
from PIL import Image

class Cancelled(Exception): pass

def probe(path:Path)->dict:
    result=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True,timeout=30)
    info=json.loads(result.stdout)
    video=next((s for s in info.get('streams',[]) if s.get('codec_type')=='video'),None)
    if not video: raise ValueError('The uploaded file has no decodable video stream')
    duration=float(info.get('format',{}).get('duration',video.get('duration',0)))
    if not math.isfinite(duration) or not 0<duration<=1800: raise ValueError('Each video must be longer than 0 seconds and no longer than 30 minutes')
    return {'duration':duration,'width':video['width'],'height':video['height'],'codec':video['codec_name']}

def frame_stats(path:Path):
    with Image.open(path) as image:
        gray=np.asarray(image.convert('L').resize((96,96)),dtype=np.float32)
    lap=-4*gray[1:-1,1:-1]+gray[:-2,1:-1]+gray[2:,1:-1]+gray[1:-1,:-2]+gray[1:-1,2:]
    return float(lap.var()),gray

def extract_frames(inputs:list[dict],directory:Path,budget:int,progress=lambda *_:None,cancel=lambda:False)->dict:
    if not 1<=len(inputs)<=12 or budget<len(inputs)*2: raise ValueError('The video count does not fit the keyframe budget')
    frames=directory/'frames';frames.mkdir(parents=True,exist_ok=True)
    records=[];warnings=[];base,extra=divmod(budget,len(inputs))
    for i,source in enumerate(inputs):
        if cancel():raise Cancelled('Job cancelled')
        src=Path(source['path']);info=probe(src);quota=base+(i<extra)
        candidates=directory/f'candidates_{i:02}';candidates.mkdir(exist_ok=True)
        rate=min(5,(quota*3)/info['duration'])
        command=['ffmpeg','-nostdin','-v','error','-i',str(src),'-an','-vf',f'fps={rate},scale=min(1280\\,iw):-2','-frames:v',str(quota*3),'-q:v','2',str(candidates/'%06d.jpg')]
        subprocess.run(command,check=True,capture_output=True,timeout=600)
        images=sorted(candidates.glob('*.jpg'));scores=[];previous=None
        for image in images:
            score,gray=frame_stats(image)
            difference=999. if previous is None else float(np.abs(gray-previous).mean())
            if difference>=1.5:scores.append((image,score));previous=gray
        sharp=[v for v in scores if v[1]>=8]
        if len(sharp)>=min(2,quota):scores=sharp
        else:warnings.append(f"{source['name']} has few sharp or visually distinct frames; consider recording more footage")
        if len(scores)<2:raise ValueError(f"{source['name']} has too few distinct frames; record again while moving the phone slowly")
        # Even temporal coverage is more useful than selecting only the sharpest adjacent frames.
        picks=np.linspace(0,len(scores)-1,min(quota,len(scores))).round().astype(int)
        for k in picks:
            image,score=scores[int(k)];dest=frames/f'clip_{i:02}_{image.name}';shutil.copyfile(image,dest)
            records.append({'file':dest.name,'video_id':source['id'],'source_frame':image.name,'sharpness':round(score,2)})
        shutil.rmtree(candidates)
        progress(25+round(25*(i+1)/len(inputs)),f'Extracting keyframes {i+1}/{len(inputs)}')
    report={'selected_frames':len(records),'videos':len(inputs),'frames':records,'warnings':warnings,'engine':'worldmirror-2.0','generated_unobserved_regions':False}
    (directory/'frames.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def model_command(repo:Path,frames:Path,output:Path,resolution:int)->list[str]:
    if resolution not in (518,700,952):raise ValueError('Unsupported reconstruction resolution')
    return [sys.executable,'-m','hyworld2.worldrecon.pipeline','--input_path',str(frames.resolve()),'--strict_output_path',str(output.resolve()),'--target_size',str(resolution),'--enable_bf16','--compress_gs_max_points','1000000','--save_conf','--no_interactive']

def validate_gaussian(path:Path)->int:
    if not path.exists() or not 0<path.stat().st_size<=256*1024*1024:raise ValueError('Reconstruction output is empty or exceeds 256 MiB')
    with path.open('rb') as f:head=f.read(16384).split(b'end_header')[0]
    if not head.startswith(b'ply\n') or any(k not in head for k in [b'opacity',b'scale_0',b'rot_0',b'f_dc_0']):raise ValueError('Worker output is not a valid Gaussian PLY')
    for line in head.splitlines():
        if line.startswith(b'element vertex '):
            n=int(line.split()[-1])
            if n>0:return n
    raise ValueError('Gaussian PLY has no valid vertices')

def reconstruct(repo:Path,directory:Path,resolution:int,progress,cancel,process_hook=lambda p:None):
    output=directory/'output';output.mkdir(exist_ok=True)
    progress(55,'WorldMirror reconstruction (progress is reported by stage)')
    command=model_command(repo,directory/'frames',output,resolution)
    with (directory/'model.log').open('w') as log:
        process=subprocess.Popen(command,cwd=repo,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUNBUFFERED':'1'})
        process_hook(process)
        started=time.monotonic()
        try:
            while process.poll() is None:
                if cancel() or time.monotonic()-started>7200:
                    process.terminate()
                    try:process.wait(15)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                    if cancel():raise Cancelled('Job cancelled')
                    raise RuntimeError('Reconstruction exceeded 2 hours; lower the resolution or frame count')
                time.sleep(.5)
            if process.returncode:
                text=(directory/'model.log').read_text(errors='replace')[-4000:]
                if 'out of memory' in text.lower():raise RuntimeError('GPU memory exhausted; choose Quick Preview or use fewer videos')
                raise RuntimeError('WorldMirror inference failed; inspect model.log on the worker and check dependencies, model weights, and GPU configuration')
        finally:process_hook(None)
    count=validate_gaussian(output/'gaussians.ply');progress(95,'Saving the 3D scene')
    return output/'gaussians.ply',count

def health(repo:Path)->dict:
    gpu=False
    try:gpu=subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],capture_output=True,timeout=10).returncode==0
    except (FileNotFoundError,subprocess.SubprocessError):pass
    installed=(repo/'hyworld2/worldrecon/pipeline.py').is_file();ffmpeg=bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
    torch_ready=False
    if gpu and installed:
        try:
            check=subprocess.run([sys.executable,'-c','import torch; import hyworld2.worldrecon.pipeline; assert torch.cuda.is_available()'],cwd=repo,capture_output=True,timeout=90)
            torch_ready=check.returncode==0
        except subprocess.SubprocessError:pass
    ready=gpu and installed and ffmpeg and torch_ready
    message='GPU and model dependencies are ready; the first inference will download or load weights.' if ready else 'NVIDIA GPU, WorldMirror dependencies, and FFmpeg are required; see the worker setup guide.'
    return {'service':'wolfworld-worker','gpu_available':gpu,'model_installed':installed,'ffmpeg':ffmpeg,'model_ready':ready,'message':message,'version':'1.0.0'}
