import asyncio
import uvloop
from aiohttp import web
import aiohttp_jinja2
import jinja2

from lib import requests

import configparser


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
config = configparser.ConfigParser()
config.read('crosstheaisle.conf')


async def hello(request):
    return web.Response(text="Hello, world")


@aiohttp_jinja2.template('facebook_login.jinja2')
def login(request):
    return {'config': config}

async def facebook_login(request):
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
    access_token_response = await requests.get_json(requests.build_url(access_token_url,
                                                                 token_request_params))
    print(access_token_response)

    return web.Response(text=("code: {code}, granted_scores: "
                              "{granted_scopes}").format(**params))


if __name__ == "__main__":
    app = web.Application()
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('./template/')
    )

    app.router.add_static('/static', './static/')
    app.router.add_get('/login', login)
    app.router.add_get('/facebook/login', facebook_login)

    web.run_app(app, port=int(config['server']['port']))
