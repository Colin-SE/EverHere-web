import {t,h,m,locale} from './i18n.js';
/* 统一封装 CSRF 与错误，页面只处理业务数据。 */
let csrf = '', space = '';
export class APIError extends Error { constructor(message, status, code) { super(message); this.status=status; this.code=code; } }
export async function api(path, options={}) {
  const {json, timeout=15000, ...rest}=options;
  const headers = new Headers(rest.headers || {});
  headers.set('X-Everhere-Language',locale());
  if (rest.method && rest.method !== 'GET') {
    headers.set('X-CSRF-Token',csrf);
    if(space)headers.set('X-Everhere-Space',space);
  }
  if (json !== undefined) { headers.set('Content-Type','application/json'); rest.body=JSON.stringify(json); }
  const deadline=AbortSignal.timeout(timeout);
  const signal=rest.signal?AbortSignal.any([deadline,rest.signal]):deadline;
  let response,result;
  try {
    response=await fetch(`/api/v1${path}`,{...rest,signal,headers,credentials:'same-origin',cache:'no-store'});
    result=await response.json().catch(error=>{if(signal.aborted)throw error;return {};});
  }catch(error){
    if(rest.signal?.aborted)throw error;
    if(deadline.aborted)throw new APIError(t('暂时未收到结果，请检查原操作后重试。'),0,'timeout');
    throw new APIError(t('连接暂时中断。请检查网络后重试，未保存的编辑内容仍在当前页面。'),0,'network_error');
  }
  if (!response.ok) {
    const error=new APIError(result.error?.message || t('请求未完成，请稍后重试。'), response.status, result.error?.code);
    if(result.error?.reference)error.message+=' '+t('问题编号：{id}',{id:result.error.reference});
    if(error.code==='csrf_error')error.message+=' '+t('请确认当前账号后重新提交。');
    throw error;
  }
  if(path==='/accounts/logout')space='';
  if (result.data?.csrfToken) csrf=result.data.csrfToken;
  if (result.data?.spaceId) space=result.data.spaceId;
  return result.data;
}
export const getSession = () => api('/auth/session');

function showNetworkStatus(){
  document.querySelectorAll('[data-network-status]').forEach(element=>{element.hidden=navigator.onLine;});
}
if(typeof window!=='undefined'){
  window.addEventListener('online',showNetworkStatus);
  window.addEventListener('offline',showNetworkStatus);
  showNetworkStatus();
}

export function uploadPhotos(path, body, progress) {
  return new Promise((resolve,reject)=>{
    const request=new XMLHttpRequest();
    const unavailable=()=>new APIError(t('暂时未收到上传结果，可重试同一批照片。'),0,'network_error');
    request.open('POST','/api/v1'+path);
    request.setRequestHeader('X-Everhere-Language',locale());
    request.setRequestHeader('X-CSRF-Token',csrf);
    if(space)request.setRequestHeader('X-Everhere-Space',space);
    request.timeout=120000;
    request.responseType='json';
    request.upload.onprogress=event=>progress(event.lengthComputable?Math.floor(100*event.loaded/event.total):null);
    request.onload=()=>{
      const value=request.response;
      if(request.status>=200&&request.status<300&&value?.data)resolve(value.data);
      else reject(new APIError(value?.error?.message||t('请求未完成，请稍后重试。'),request.status,value?.error?.code));
    };
    request.onerror=request.ontimeout=()=>reject(unavailable());
    request.send(body);
  });
}
