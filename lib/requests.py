import aiohttp
import urllib
import ujson as json


def build_url(url, query):
    if query:
        query = urllib.parse.urlencode(query)
        url = "{}?{}".format(url, query)
    return url

async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json(loads=json.loads)
