from aiohttp import web
from aiohttp import WSMsgType, WSCloseCode
from aiohttp_session import get_session
import ujson as json
from lib.authentication import authenticated
from collections import defaultdict
import logging


CONV_CONNECTIONS = defaultdict(set)
ALL_CONNECTIONS = set()


def create_app(parent):
    app = web.Application(debug=parent.debug)
    app.update(parent)
    app.router.add_get('/websocket', chat_websocket)
    app.router.add_get('/conversation', get_conversation)
    app.router.add_get('/conversations', list_conversations)
    app.router.add_get('/deanonymize', deanonymize)
    app.on_shutdown.append(on_shutdown)
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
    userdata = {'userid': userid, 'username': username, 'convid': convid}

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    CONV_CONNECTIONS[convid].add(ws)
    ALL_CONNECTIONS.add(ws)
    try:
        async for msg in ws:
            dispatch_message(request, ws, msg, userdata)
    finally:
        CONV_CONNECTIONS[convid].remove(ws)
        ALL_CONNECTIONS.remove(ws)
    return ws


def dispatch_message(request, ws, msg, userdata):
    userid = userdata['userid']
    convid = userdata['convid']
    username = userdata['username']
    if msg.type == WSMsgType.TEXT:
        try:
            data = json.loads(msg.data)
        except (ValueError, TypeError):
            return ws.send_json({"error": "Could not parse message"})

        if 'method' not in data:
            return ws.send_json({"error": "No method set"})

        if data['method'] == 'send_message':
            if 'convid' not in data or data['convid'] != convid:
                return ws.send_json({"error": "Sending message on "
                                              "unauthorized conversation"})
            elif 'message' not in data:
                return ws.send_json({"error": "No message"})
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


async def on_shutdown(app):
    for ws in ALL_CONNECTIONS:
        await ws.close(code=WSCloseCode.GOING_AWAY,
                       message='Server shutdown')
