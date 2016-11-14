import asyncio
import uvloop
from aiohttp import web
import aiohttp_jinja2
import jinja2

from lib import requests
from lib import db 

import configparser


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@aiohttp_jinja2.template('facebook_login.jinja2')
def login(request):
    return {'config': request.app['config']}

async def facebook_login(request):
    config = request.app['config']
    params = request.url.query
    if 'error_reason' in params:
        return web.Response(text=("You denied us because: "
                                  "{error_description}").format(**params))
    token_request_params = {
        "client_id": config['facebook']['app_id'],
        "redirect_uri": config['facebook']['redirect_uri'],
        "client_secret": config['facebook']['app_secret'],
        "code": params['code'],
    }

    access_token_url = "https://graph.facebook.com/v2.8/oauth/access_token"
    url = requests.build_url(access_token_url, token_request_params)
    access_token_response = await requests.get_json(url)

    print(access_token_response)
    fb_url = ("https://graph.facebook.com/v2.8/me?fields=email,name"
              "&access_token={access_token}").format(**access_token_response)
    user_data = await requests.get_json(fb_url)

    try:
        uid = request.app['db'].new_user(user_data['name'], user_data['email'],
                                         user_data['id'],
                                         access_token_response['access_token'])
    except db.UserAlreadyExists:
        uid = user_data['id']

    return web.Response(text=("uid: {}").format(uid))


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('crosstheaisle.conf')

    app = web.Application()
    app['config'] = config
    app['db'] = db.Database()

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('./template/')
    )

    app.router.add_static('/static', './static/')
    app.router.add_get('/login', login)
    app.router.add_get('/facebook/login', facebook_login)

    web.run_app(app, port=int(config['server']['port']))
