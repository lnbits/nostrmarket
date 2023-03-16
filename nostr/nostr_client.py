import asyncio
import json
from asyncio import Queue
from threading import Thread
from typing import Callable

from loguru import logger
from websocket import WebSocketApp

from lnbits.app import settings

from .event import NostrEvent


class NostrClient:
    def __init__(self):
        self.recieve_event_queue: Queue = Queue()
        self.send_req_queue: Queue = Queue()
        self.ws: WebSocketApp = None

    async def get_event(self):
        return await self.recieve_event_queue.get()

    async def publish_nostr_event(self, e: NostrEvent):
        print("### publish_nostr_event", e.dict())
        await self.send_req_queue.put(["EVENT", e.dict()])

    async def connect_to_nostrclient_ws(
        self, on_open: Callable, on_message: Callable
    ) -> WebSocketApp:
        def on_error(_, error):
            logger.warning(error)

        logger.debug(f"Subscribing to websockets for nostrclient extension")
        ws = WebSocketApp(
            f"ws://localhost:{settings.port}/nostrclient/api/v1/relay",
            on_message=on_message,
            on_open=on_open,
            on_error=on_error,
        )

        wst = Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()

        return ws

    async def subscribe_to_direct_messages(self, public_key: str, since: int):
        in_messages_filter = {"kind": 4, "#p": [public_key]}
        out_messages_filter = {"kind": 4, "authors": [public_key]}
        if since != 0:
            in_messages_filter["since"] = since
            out_messages_filter["since"] = since
        print("### in_messages_filter", in_messages_filter)
        print("### out_messages_filter", out_messages_filter)

        await self.send_req_queue.put(
            ["REQ", f"direct-messages-in:{public_key}", in_messages_filter]
        )
        await self.send_req_queue.put(
            ["REQ", f"direct-messages-out:{public_key}", out_messages_filter]
        )

    async def subscribe_to_nostr_client(self):
        def on_open(_):
            logger.info("Connected to 'nostrclient' websocket")

        def on_message(_, message):
            # print("### on_message", message)
            self.recieve_event_queue.put_nowait(message)

        while True:
            try:
                req = None
                if not self.ws:
                    self.ws = await self.connect_to_nostrclient_ws(on_open, on_message)
                    # be sure the connection is open
                    await asyncio.sleep(3)
                req = await self.send_req_queue.get()
                self.ws.send(json.dumps(req))
            except Exception as ex:
                logger.warning(ex)
                if req:
                    await self.send_req_queue.put(req)
                self.ws = None  # todo close
                await asyncio.sleep(5)

    async def unsubscribe_from_direct_messages(self, public_key: str):
        await self.send_req_queue.put(["CLOSE", f"direct-messages-in:{public_key}"])
        await self.send_req_queue.put(["CLOSE", f"direct-messages-out:{public_key}"])
