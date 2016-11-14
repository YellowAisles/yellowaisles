import asyncio
import uvloop
from aiohttp import web
import aiohttp_session
from aiohttp_session import get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiohttp_jinja2
import jinja2

from lib import db
from app.facebook import facebook_login
from app.chat import chat_websocket
from app.chat import get_conversation

import configparser
import base64


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@aiohttp_jinja2.template('facebook_login.jinja2')
async def login(request):
    session = await get_session(request)
    return {'config': request.app['config'],
            'name': session.get('name', None)}


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('crosstheaisle.conf')

    app = web.Application()
    app['config'] = config
    app['db'] = db.Database()

    secret_key = base64.urlsafe_b64decode(config['server']['fernet_secret'])
    aiohttp_session.setup(app, EncryptedCookieStorage(secret_key))

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('./template/')
    )

    app.router.add_static('/static', './static/')
    app.router.add_get('/login', login)
    app.router.add_get('/facebook/login', facebook_login)
    app.router.add_get('/api/chat', chat_websocket)
    app.router.add_get('/api/conversation', get_conversation)

    web.run_app(app, port=int(config['server']['port']))
