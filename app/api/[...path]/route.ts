import { env } from 'cloudflare:workers';
import {handleApi} from '@/lib/core';
export const dynamic='force-dynamic';
async function route(req:Request){
 if(!env.DB||!env.BUCKET)return Response.json({error:'Scene storage is temporarily unavailable. Please try again.'},{status:503});
 const owner=req.headers.get('oai-authenticated-user-id');
 return handleApi(req,owner,{db:env.DB,bucket:env.BUCKET});
}
export {route as GET,route as POST,route as PUT,route as DELETE};
