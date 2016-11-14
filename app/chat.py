from aiohttp import web
from aiohttp import WSMsgType
from aiohttp_session import get_session
import ujson as json
from lib.authentication import authenticated
from collections import defaultdict


ACTIVE_CONNECTIONS = defaultdict(set)


async def broadcast(convid, message):
    if not convid:
        return
    for ws in ACTIVE_CONNECTIONS[convid]:
        await ws.send_json(message)


@authenticated
async def get_conversation(request):
    params = request.url.query
    session = await get_session(request)
    userid = session['userid']
    if 'convid' not in params:
        conversation = request.app['db'].get_user_current_conversation(userid)
    else:
        try:
            convid = int(params['convid'])
        except ValueError:
            raise web.HTTPBadRequest(text='invalid_convid')
        conversation = request.app['db'].get_conversation(convid, userid=userid)
    return web.json_response(conversation)


@authenticated
async def chat_websocket(request):
    session = await get_session(request)
    userid = session['userid']
    convid = request.app['db'].get_user(userid)['curconv']

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    if not convid:
        raise web.HTTPPreconditionFailed()

    ACTIVE_CONNECTIONS[convid].add(ws)
    async for msg in ws:
        if msg.type == WSMsgType.ERROR:
            ACTIVE_CONNECTIONS[convid].remove(ws)
        elif msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except (ValueError, TypeError):
                ws.send_json({"error": "Could not parse message"})
                continue

            if 'method' not in data:
                ws.send_json({"error": "No method set"})
                continue

            if data['method'] == 'send_message':
                if data['convid'] != convid:
                    ws.send_json({"error": "Sending message on unauthorized "
                                           "conversation"})
                    continue
                elif 'message' not in data:
                    ws.send_json({"error": "No message"})
                    continue
                request.app['db'].new_message_user(convid, userid,
                                                   data['message'])
                broadcast(convid, {
                    "method": "new_message",
                    "convid": convid,
                    "sender": userid,
                    "message": data['message'],
                })
            elif data['method'] == 'typing':
                broadcast(convid, {
                    "method": 'typing',
                    "user": userid,
                })
            elif data['method'] == 'stop_typing':
                broadcast(convid, {
                    "method": 'stop_typing',
                    "user": userid,
                })
