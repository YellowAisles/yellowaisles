from aiohttp import web
from aiohttp_session import get_session

from lib import db
from lib import requests
from lib.utils import obscure_id

from dateutil.parser import parse as date_parser
from datetime import datetime
from datetime import timedelta
from datetime import timezone


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

    fb_url = ("https://graph.facebook.com/v2.8/me?fields=email,name,"
              "verified,albums.order(reverse_chronological).limit(1)"
              "&access_token={access_token}").format(**access_token)
    user_data = await requests.get_json(fb_url)

    if not user_data['verified']:
        raise web.HTTPForbidden(text="facebook_not_verified")
    first_album_date = user_data['albums']['data'][0]["created_time"]
    min_account_age = timedelta(days=365.25 *
                                int(config['facebook']['min_account_years']))
    now = datetime.now(timezone.utc)
    if abs(date_parser(first_album_date) - now) < min_account_age:
        raise web.HTTPForbidden(text="facebook_account_not_old_enough")

    user_data['id'] = obscure_id(int(user_data['id']),
                                 config['server']['fernet_secret'],
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

