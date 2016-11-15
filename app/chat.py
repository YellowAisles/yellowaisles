from aiohttp import web
from aiohttp import WSMsgType
from aiohttp_session import get_session
import ujson as json
from lib.authentication import authenticated
from collections import defaultdict


CONV_CONNECTIONS = defaultdict(set)


def create_app(parent):
    app = web.Application(debug=parent.debug)
    app.update(parent)
    app.router.add_get('/chat', chat_websocket)
    app.router.add_get('/conversation', get_conversation)
    app.router.add_get('/conversations', list_conversations)
    app.router.add_get('/deanonymize', deanonymize)
    return app


def broadcast(convid, message):
    if not convid:
        return
    for ws in CONV_CONNECTIONS[convid]:
        ws.send_json(message)


@authenticated
async def list_conversations(request):
    session = await get_session(request)
    userid = session['userid']
    conversation_list = request.app['db'].list_user_conversations(userid)
    for conv in conversation_list:
        conv.pop('partnerid', None)
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
    conversation_names = request.app['db'].get_conversation_names(userid,
                                                                  convid)
    for message in conversation:
        message['sender'] = conversation_names[message['sender']]
        message['reciever'] = conversation_names[message['reciever']]
    return web.json_response({'convid': convid, 'data': conversation})


@authenticated
async def chat_websocket(request):
    session = await get_session(request)
    userid = session['userid']
    username = session['name']
    convid = request.app['db'].get_user(userid)['curconv']
    if not convid:
        raise web.HTTPPreconditionFailed()

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    CONV_CONNECTIONS[convid].add(ws)
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
                    "sender": username,
                    "message": data['message'],
                })
            elif data['method'] == 'typing':
                broadcast(convid, {
                    "method": 'typing',
                    "convid": convid,
                    "user": username,
                })
            elif data['method'] == 'stop_typing':
                broadcast(convid, {
                    "method": 'stop_typing',
                    "convid": convid,
                    "user": username,
                })
    CONV_CONNECTIONS[convid].remove(ws)
    return ws
