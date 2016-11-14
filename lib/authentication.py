from aiohttp import web
from aiohttp_session import get_session
from functools import wraps


def authenticated(fxn):
    @wraps(fxn)
    async def _(request):
        session = await get_session(request)
        if 'userid' not in session:
            raise web.HTTPSeeOther('/login')
        return await fxn(request)
    return _
