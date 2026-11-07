/* 在同一网络环境启动合成服务和浏览器；所有子进程结束后释放内存库。 */
const {spawn}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs/promises');
const root=path.resolve(__dirname,'..');
const python=process.env.TEST_PYTHON||path.join(root,'.venv','Scripts','python.exe');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const children=new Set();
function start(command,args,env=process.env){
 const child=spawn(command,args,{cwd:root,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
 children.add(child);child.on('exit',()=>children.delete(child));return child;
}
function check(script,base){
 return new Promise((resolve,reject)=>{
  const child=start(process.execPath,[path.join('tools',script)],{...process.env,TEST_BASE_URL:base});
  child.stdout.pipe(process.stdout);child.stderr.pipe(process.stderr);
  child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(new Error(script+' exited '+code)));
 });
}
async function withServer(script,port,checks){
 const base='http://127.0.0.1:'+port;
 // 避免连接到本次启动前已经存在的服务，合成管理员仅由此进程建立。
 try{await fetch(base+'/health',{signal:AbortSignal.timeout(500)});throw new Error('端口已被占用：'+port);}catch(error){if(error.message.startsWith('端口'))throw error;}
 const server=start(python,[path.join('tools',script)]);let logs='';let launchError;
 server.on('error',error=>{launchError=error;});
 for(const stream of [server.stdout,server.stderr])stream.on('data',chunk=>{logs=(logs+chunk).slice(-6000);});
 try{
  let ready=false;
  for(let i=0;i<60;i++){
   if(launchError)throw launchError;
   if(server.exitCode!==null)throw new Error(logs);
   try{const health=await(await fetch(base+'/health',{signal:AbortSignal.timeout(500)})).json();if(health.database==='sqlite'){ready=true;break;}}catch{}
   await delay(250);
  }
  if(!ready)throw new Error('合成服务启动失败：'+logs);
  for(const checkFile of checks)await check(checkFile,base);
 }finally{server.kill();}
}
async function main(){
 const temporary=path.join(root,'test-results','browser-tmp');await fs.mkdir(temporary,{recursive:true});
 process.env.TEMP=temporary;process.env.TMP=temporary;
 await withServer('run-check-server.py',5003,['browser-check.cjs','i18n-browser-check.cjs']);
 await withServer('workflows-check-server.py',5004,['workflows-browser-check.cjs']);
}
function cleanup(){for(const child of children)child.kill();}
process.on('SIGINT',()=>{cleanup();process.exit(130);});
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(cleanup);
