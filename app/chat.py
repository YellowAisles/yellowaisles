from aiohttp import web
from aiohttp import WSMsgType
from aiohttp_session import get_session
import ujson as json
from lib.authentication import authenticated
from collections import defaultdict


ACTIVE_CONNECTIONS = defaultdict(set)


def broadcast(convid, message):
    if not convid:
        return
    for ws in ACTIVE_CONNECTIONS[convid]:
        ws.send_json(message)


@authenticated
async def list_conversations(request):
    session = await get_session(request)
    userid = session['userid']
    conversation_list = request.app['db'].list_user_conversations(userid)
    return web.json_response(conversation_list)


@authenticated
async def deanonymize(request):
    session = await get_session(request)
    userid = session['userid']
    result = request.app['db'].deanonymize_user(userid)
    return web.json_response(result)


@authenticated
async def get_conversation(request):
    params = request.url.query
    session = await get_session(request)
    userid = session['userid']
    if 'convid' in params:
        try:
            convid = int(params['convid'])
        except ValueError:
            raise web.HTTPBadRequest(text='invalid_convid')
    else:
        convid = request.app['db'].get_user_current_convid(userid)
    request.app['db'].set_conversation_read(userid, convid)
    conversation = request.app['db'].get_conversation(convid, userid=userid)
    return web.json_response({'convid': convid, 'data': conversation})


@authenticated
async def chat_websocket(request):
    session = await get_session(request)
    userid = session['userid']
    convid = request.app['db'].get_user(userid)['curconv']
    if not convid:
        raise web.HTTPPreconditionFailed()

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    ACTIVE_CONNECTIONS[convid].add(ws)
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except (ValueError, TypeError):
                ws.send_json({"error": "Could not parse message"})
                continue

            if 'method' not in data:
                ws.send_json({"error": "No method set"})
                continue

            if data['method'] == 'send_message':
                if 'convid' not in data or data['convid'] != convid:
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
    ACTIVE_CONNECTIONS[convid].remove(ws)
    return ws
