import {t,h,m,locale} from './i18n.js';
/* 登录复用同一区域云账号；移除旧的本机注册与密码体系。 */
import {api,getSession} from './api.js';
const form=document.getElementById('auth-form'),error=document.getElementById('auth-error'),button=document.getElementById('auth-submit');
const ready=getSession().then(session=>{if(!session.cloudConfigured){error.textContent=t('共同云服务尚未配置；可直接返回本机档案继续记录。');button.disabled=true;}}).catch(value=>{error.textContent=value.message;button.disabled=true;});
form.addEventListener('submit',async event=>{event.preventDefault();button.disabled=true;error.textContent='';try{await ready;await api('/cloud/login',{method:'POST',json:Object.fromEntries(new FormData(form))});location.assign('/#view=mine');}catch(value){error.textContent=value.message;button.disabled=false;}});
