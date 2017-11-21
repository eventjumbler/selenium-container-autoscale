import logging

import aiohttp

_LOG = logging.getLogger(__name__)

async def http_get(url, params=None, session=None):
    async def do_get(sess):
        async with sess.get(url, params=params) as resp:
            if resp.status not in (200, 201, 204):
                return resp.status, None
            return 200, (await resp.json())
    if session:
        return await do_get(session)
    async with aiohttp.ClientSession() as session:
        return await do_get(session)

async def http_post(url, data=None, json=None, session=None):
    async def do_post(sess):
        async with sess.post(url, data=data, json=json) as resp:
            if resp.status not in (200, 201, 204):
                return resp.status, None
            return 200, (await resp.json())
    if session:
        return await do_post(session)
    async with aiohttp.ClientSession() as session:
        return await do_post(session)


async def http_delete(url, session=None):
    async def do_delete(sess):
        async with sess.delete(url) as resp:
            if resp.status not in (200, 201, 204):
                return resp.status, None
            return 200, (await resp.json())
    if session:
        return await do_delete(session)
    async with aiohttp.ClientSession() as session:
        return await do_delete(session)
