"""共同账户 BFF：凭证不交给浏览器，登录绝不读取或上传人生资料。"""
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import Blueprint, current_app, g

from ..extensions import db, limiter
from ..models import CloudConnection, new_id
from ..security import APIError, body, local_required

bp=Blueprint('cloud',__name__,url_prefix='/api/v1/cloud')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        # Bearer 凭证不能跟随重定向到另一个主机。
        return None


def remote(path, data=None, token=None):
    base=current_app.config.get('CLOUD_API_URL','').rstrip('/')
    region=current_app.config.get('CLOUD_REGION','cn')
    parsed=urlsplit(base)
    if not base:
        raise APIError('共同云服务尚未配置，资料继续保存在本机。',503,'cloud_not_configured')
    if region not in ('cn','global') or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1','::1'))):
        raise APIError('云服务配置无效：需要同区 HTTPS 地址；本机联调可用回环地址。',503,'cloud_configuration_error')
    payload=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
    headers={'Content-Type':'application/json','X-Everhere-Region':region,'Accept':'application/json'}
    if token:
        headers['Authorization']='Bearer '+token
    try:
        with build_opener(NoRedirect()).open(Request(base+path,data=payload,headers=headers),timeout=10) as response:
            raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:
                raise ValueError()
            value=json.loads(raw.decode('utf-8'))
            if not isinstance(value,dict):
                raise ValueError()
            return value
    except HTTPError as error:
        if error.code==404:
            raise APIError('共同服务尚未提供所需的权益或范围许可接口，云同步保持关闭。',503,'cloud_capability_unavailable') from None
        if error.code==401:
            raise APIError('云账号会话已失效，请重新登录。',401,'cloud_unauthorized') from None
        raise APIError('共同云服务拒绝了请求，请核对账号、区域或稍后重试。',502,'cloud_request_failed') from None
    except (URLError,ValueError,UnicodeError,TimeoutError,OSError):
        raise APIError('暂时无法校验共同云服务；本机资料仍可使用。',503,'cloud_unavailable') from None


def connection():
    value=db.session.get(CloudConnection,g.owner.id)
    if not value:
        raise APIError('请先登录同一区域的云账号。',401,'cloud_login_required')
    if value.region!=current_app.config.get('CLOUD_REGION','cn'):
        raise APIError('云账号区域与本机配置不符，请重新登录。',403,'region_mismatch')
    return value


def verified_access(value):
    # 现有 Android PG008 后端还没有权益接口；404 必须拒绝，不能用本机 enabled 代替权益。
    rights=remote('/v1/entitlements',token=value.token)
    entitlement=rights.get('cloudSync',{})
    if not isinstance(entitlement,dict):
        raise APIError('权益响应格式无效。',502,'cloud_response_invalid')
    try:
        expires=datetime.fromisoformat(entitlement['expiresAt'].replace('Z','+00:00'))
        valid=entitlement.get('active') is True and expires>datetime.now(timezone.utc)
    except (KeyError,TypeError,ValueError):
        valid=False
    if rights.get('region')!=value.region or rights.get('userId')!=value.account_id:
        raise APIError('权益响应与当前账户不匹配。',403,'cloud_identity_mismatch')
    return {'active':valid,'expiresAt':entitlement.get('expiresAt')}


@bp.get('/status')
@local_required
def status():
    value=db.session.get(CloudConnection,g.owner.id)
    data={'configured':bool(current_app.config.get('CLOUD_API_URL')),'region':current_app.config.get('CLOUD_REGION','cn'),'loggedIn':bool(value),'enabled':False,'localOnly':True}
    if value:
        data['account']={'id':value.account_id,'email':value.email}
        try:
            data['entitlement']=verified_access(connection())
        except APIError as error:
            data['reason']=error.message
            data['code']=error.code
    return {'data':data}


@bp.post('/login')
@local_required
@limiter.limit('10 per minute')
def login():
    data=body(); email=data.get('email'); password=data.get('password')
    if not isinstance(email,str) or len(email)>254 or not isinstance(password,str) or not 1<=len(password)<=128:
        raise APIError('请填写云账号邮箱与密码。')
    device=new_id()
    value=remote('/v1/auth/login',{'email':email,'password':password,'installationId':device,'deviceName':'Everhere Web 本机服务'})
    region=current_app.config.get('CLOUD_REGION','cn')
    if value.get('region')!=region or not all(isinstance(value.get(k),str) and value[k] for k in ('userId','email','accessToken')):
        raise APIError('云账号响应格式或区域无效。',502,'cloud_response_invalid')
    from uuid import UUID
    try:
        UUID(value['userId'])
    except ValueError:
        raise APIError('云账号标识无效。',502,'cloud_response_invalid') from None
    prior=db.session.get(CloudConnection,g.owner.id)
    if prior:
        db.session.delete(prior);db.session.flush()
    db.session.add(CloudConnection(id=g.owner.id,account_id=value['userId'],email=value['email'],token=value['accessToken'],region=region,device_id=device,enabled=False))
    db.session.commit()
    # 不保存 refreshToken；到期重新登录。没有任何记录/照片请求。
    return {'data':{'loggedIn':True,'enabled':False,'localOnly':True}}


@bp.post('/logout')
@local_required
def logout():
    value=connection()
    remote('/v1/auth/logout',{},value.token)
    db.session.delete(value);db.session.commit()
    return {'data':{'loggedIn':False,'enabled':False,'localDataRetained':True}}


@bp.post('/consent')
@local_required
def consent():
    value=connection(); data=body()
    if data.get('enabled') is False:
        value.enabled=False;db.session.commit()
        return {'data':{'enabled':False}}
    if data.get('enabled') is not True:
        raise APIError('请明确选择是否开启云同步。')
    rights=verified_access(value)
    if not rights['active']:
        raise APIError('没有有效云同步权益，本机资料不受影响。',403,'entitlement_required')
    # PG008 尚缺方向/范围许可，不能仅凭权益开放全库 push/pull。
    raise APIError('共同服务尚未实现用户选择方向和资料范围的确认许可，云同步暂不能开启。',503,'scoped_sync_unavailable')
