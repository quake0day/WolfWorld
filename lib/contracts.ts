export const CHUNK_BYTES=8*1024*1024;
export const MAX_VIDEO_BYTES=2*1024*1024*1024;
export const MAX_SCENE_BYTES=256*1024*1024;
export const PRESETS={preview:{label:'Quick preview',frames:24,resolution:518},balanced:{label:'Balanced',frames:48,resolution:700},detail:{label:'High detail',frames:96,resolution:952}} as const;
export type Preset=keyof typeof PRESETS;
export type Media={id:string;name:string;kind:'video'|'splat';size:number;mime:string;status:string;created:number};
export type Job={id:string;name:string;media:string[];status:'queued'|'transferring'|'running'|'complete'|'failed'|'cancelled';stage:string;progress:number;preset:Preset;result:string|null;error:string|null;created:number;updated:number;report:Record<string,unknown>|null};
export type WorkerConfig={url:string;configured:boolean;tokenConfigured:boolean};
export type WorkerHealth={service:string;model_ready:boolean;gpu_available:boolean;model_installed:boolean;ffmpeg:boolean;message:string};
export function formatBytes(n:number){if(n<1024*1024)return `${(n/1024).toFixed(0)} KB`;if(n<1024*1024*1024)return `${(n/1024/1024).toFixed(1)} MB`;return `${(n/1024/1024/1024).toFixed(2)} GB`}
