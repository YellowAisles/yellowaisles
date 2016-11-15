import asyncio
import uvloop
from aiohttp import web
import aiohttp_session
from aiohttp_session import get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiohttp_jinja2
import jinja2

from lib import db
from app import facebook
from app import chat

import strictyaml as yaml
import base64
import logging


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

FORMAT = ('[%(levelname)s][%(module)s.%(funcName)s:%(lineno)d] '
          '%(message)s')
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)


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
    with open("crosstheaisle.yaml") as fd:
        config = yaml.load(fd.read())

    app = web.Application(debug=config['server']['debug'])
    app['config'] = config
    app['db'] = db.Database()

    logging.getLogger().setLevel(logging.DEBUG if config['server']['debug']
                                 else logging.INFO)

    secret_key = base64.urlsafe_b64decode(config['server']['fernet_secret'])
    aiohttp_session.setup(app, EncryptedCookieStorage(secret_key))

    if config['server']['debug']:
        logging.info("Debug on")
        import aiohttp_debugtoolbar
        aiohttp_debugtoolbar.setup(app)
        app.router.add_get('/debug/set_userid', set_userid)

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('./template/')
    )

    app.router.add_static('/static', './static/')
    app.router.add_get('/login', login)
    app.router.add_subapp('/api/chat', chat.create_app(app))
    app.router.add_subapp('/auth/facebook', facebook.create_app(app))

    web.run_app(app, port=int(config['server']['port']))
