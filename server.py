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
from app.chat import list_conversations
from app.chat import deanonymize

import configparser
import base64


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@aiohttp_jinja2.template('facebook_login.jinja2')
async def login(request):
    session = await get_session(request)
    return {'config': request.app['config'],
            'name': session.get('name', None)}

async def set_userid(request):
    params = request.url.query
    userid = int(params['userid'])
    session = await get_session(request)
    session['userid'] = userid
    return web.json_response({'userid': userid})


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
    app.router.add_get('/api/conversations', list_conversations)
    app.router.add_get('/api/deanonymize', deanonymize)

    if config['server']['debug'].lower() == "true":
        print("Debug mode")
        app.router.add_get('/debug/set_userid', set_userid)

    web.run_app(app, port=int(config['server']['port']))
