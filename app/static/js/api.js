/* 统一封装 CSRF 与错误，页面只处理业务数据。 */
let csrf = '';
export class APIError extends Error { constructor(message, status, code) { super(message); this.status=status; this.code=code; } }
export async function api(path, options={}) {
  const {json, ...rest}=options;
  const headers = new Headers(rest.headers || {});
  if (rest.method && rest.method !== 'GET') headers.set('X-CSRF-Token',csrf);
  if (json !== undefined) { headers.set('Content-Type','application/json'); rest.body=JSON.stringify(json); }
  let response;
  try { response=await fetch(`/api/v1${path}`,{...rest,headers,credentials:'same-origin',cache:'no-store'}); }
  catch { throw new APIError('连接暂时中断。请检查网络后重试，未保存的编辑内容仍在当前页面。',0,'network_error'); }
  const result=await response.json().catch(()=>({}));
  if (!response.ok) throw new APIError(result.error?.message || '请求未完成，请稍后重试。', response.status, result.error?.code);
  if (result.data?.csrfToken) csrf=result.data.csrfToken;
  return result.data;
}
export const getSession = () => api('/auth/session');
/* 下载保持同源和不缓存，服务器错误在下载前明确反馈。 */
export async function downloadFile(path,filename){
  const response=await fetch('/api/v1'+path,{credentials:'same-origin',cache:'no-store'});
  if(!response.ok){const value=await response.json().catch(()=>({}));throw new Error(value.error?.message||'下载未完成，请稍后重试。');}
  const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
