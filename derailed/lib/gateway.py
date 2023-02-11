import asyncio
from typing import Any, Callable
import aiohttp
import msgspec


class Emitter:
    def __init__(self) -> None:
        self._events = {}

    async def emit(self, event: str, data: dict[str, Any]) -> None:
        try:
            funcs = self._events[event]
        except KeyError:
            return

        for func in funcs:
            await func(data)

    def subscribe(self, event: str, func: Callable) -> None:
        try:
            self._events[event].append(func)
        except KeyError:
            self._events[event] = [func]


class Gateway:
    _OP_CODES = {
        0: 'dispatch',
        1: 'ready',
        # 2: 'resume',
        3: 'ack',
        4: 'hello'
    }


    def __init__(self, client_session: aiohttp.ClientSession, uri: str, proxy: str | None = None, proxy_auth: aiohttp.BasicAuth | None = None) -> None:
        self._session = client_session
        self._proxy = proxy
        self._proxy_auth = proxy_auth
        self._uri = uri
        self._ack_received = False
        self.emitter = Emitter()


    async def connect(self, token: str) -> None:
        self._token = token

        self._ws = await self._session.ws_connect(self._uri, proxy=self._proxy, proxy_auth=self._proxy_auth)

        asyncio.create_task(self._receive())


    async def send(self, data: dict[str, Any]) -> None:
        await self._ws.send_bytes(msgspec.json.encode(data))


    async def _receive(self) -> None:
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                message = msgspec.json.decode(msg.data, type=dict)

                op = message.get('op')
                t = message.get('t')
                d = message.get('d')

                self._sequence = message['s']

                if op == 0:
                    await self.emitter.emit(t, d)
                elif op == 1:
                    await self.emitter.emit('READY', d)
                elif op == 3:
                    self._ack_received = True
                elif op == 4:
                    await self.identify()


    async def identify(self) -> None:
        self.send({
            'op': self._OP_CODES[1],
            'd': {
                'token': self._token
            }
        })
