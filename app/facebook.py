from aiohttp import web
from aiohttp_session import get_session

from lib import db
from lib import requests
from lib.utils import obscure_id


async def facebook_login(request):
    session = await get_session(request)
    config = request.app['config']
    params = request.url.query
    if 'error_reason' in params:
        return web.HTTPForbidden(text=("You denied us because: "
                                       "{error_description}").format(**params))
    token_request_params = {
        "client_id": config['facebook']['app_id'],
        "redirect_uri": config['facebook']['redirect_uri'],
        "client_secret": config['facebook']['app_secret'],
        "code": params['code'],
    }

    access_token_url = "https://graph.facebook.com/v2.8/oauth/access_token"
    url = requests.build_url(access_token_url, token_request_params)
    access_token = await requests.get_json(url)

    fb_url = ("https://graph.facebook.com/v2.8/me?fields=email,name"
              "&access_token={access_token}").format(**access_token)
    user_data = await requests.get_json(fb_url)
    user_data['id'] = obscure_id(int(user_data['id']),
                                 request.app['config']['server']['fernet_secret'],
                                 'facebook')

    try:
        userid = request.app['db'].new_user(user_data['name'],
                                            user_data['email'],
                                            user_data['id'],
                                            access_token['access_token'])
    except db.UserAlreadyExists:
        userid = user_data['id']
    finally:
        session['userid'] = userid
        session['name'] = user_data['name']

    return web.HTTPTemporaryRedirect('/login', body=b'Redirecting...')

