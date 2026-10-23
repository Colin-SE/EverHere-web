import {t,h,m,locale} from './i18n.js';
/* 草稿写入串行化：同一会话不乱序，版本冲突保留表单输入。 */
import {api} from './api.js';
export class DraftSession {
  constructor(kind,read,status){this.kind=kind;this.read=read;this.status=status;this.current=null;this.queue=Promise.resolve();this.timer=null;this.saved='';this.pending=0;}
  async open(options={}) {
    clearTimeout(this.timer);await this.queue.catch(()=>{});
    this.current=options.draftId?await api('/drafts/'+encodeURIComponent(options.draftId)):await api('/drafts',{method:'POST',json:{kind:this.kind,...options}});
    return this.current;
  }
  ready(){this.saved=JSON.stringify(this.read());this.status(t('已保存在本机'));}
  get dirty(){return this.pending>0||JSON.stringify(this.read())!==this.saved;}
  changed(){if(!this.current)return;clearTimeout(this.timer);this.status(t('尚未落盘'));this.timer=setTimeout(()=>this.store().catch(()=>{}),600);}
  async store(){
    clearTimeout(this.timer);const draft=this.current;if(!draft)return;
    const values=this.read(),snapshot=JSON.stringify(values);this.pending++;this.status(t('正在保存草稿…'));
    const task=this.queue.catch(()=>{}).then(async()=>{
      const result=await api('/drafts/'+encodeURIComponent(draft.id),{method:'PUT',json:{version:draft.version,values}});
      draft.version=result.version;draft.values=result.values;
      if(this.current===draft){this.saved=snapshot;this.status(JSON.stringify(this.read())===snapshot?t('已保存在本机'):t('尚未落盘'));}
      return result;
    }).catch(error=>{if(this.current===draft)this.status(t('草稿未保存：')+error.message);throw error;}).finally(()=>{this.pending--;});
    this.queue=task;return task;
  }
  async commit(extra={}){await this.store();const result=await api('/drafts/'+encodeURIComponent(this.current.id)+'/commit',{method:'POST',json:{version:this.current.version,...extra}});this.current=null;return result;}
  async discard(){clearTimeout(this.timer);await this.queue.catch(()=>{});if(this.current)await api('/drafts/'+encodeURIComponent(this.current.id),{method:'DELETE',json:{version:this.current.version}});this.current=null;}
  detach(){clearTimeout(this.timer);this.current=null;}
}
