import asyncio
import json
from asyncio import Queue
from threading import Thread
from typing import Callable, List

from loguru import logger
from websocket import WebSocketApp

from lnbits.app import settings

from .event import NostrEvent


class NostrClient:
    def __init__(self):
        self.recieve_event_queue: Queue = Queue()
        self.send_req_queue: Queue = Queue()
        self.ws: WebSocketApp = None


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

    async def get_event(self):
        value = await self.recieve_event_queue.get()
        if isinstance(value, ValueError):
            raise value
        return value

    async def run_forever(self):
        def on_open(_):
            logger.info("Connected to 'nostrclient' websocket")

        def on_message(_, message):
            self.recieve_event_queue.put_nowait(message)

        running = True

        while running:
            try:
                req = None
                if not self.ws:
                    self.ws = await self.connect_to_nostrclient_ws(on_open, on_message)
                    # be sure the connection is open
                    await asyncio.sleep(3)
                req = await self.send_req_queue.get()
                if isinstance(req, ValueError):
                    running = False
                    logger.warning(str(req))
                else:
                    self.ws.send(json.dumps(req))
            except Exception as ex:
                logger.warning(ex)
                if req:
                    await self.send_req_queue.put(req)
                self.ws = None  # todo close
                await asyncio.sleep(5)

    async def publish_nostr_event(self, e: NostrEvent):
        await self.send_req_queue.put(["EVENT", e.dict()])

    async def subscribe_to_direct_messages(self, public_key: str, since: int):
        in_messages_filter = {"kinds": [4], "#p": [public_key]}
        out_messages_filter = {"kinds": [4], "authors": [public_key]}
        if since and since != 0:
            in_messages_filter["since"] = since
            out_messages_filter["since"] = since

        await self.send_req_queue.put(
            ["REQ", f"direct-messages-in:{public_key}", in_messages_filter]
        )
        await self.send_req_queue.put(
            ["REQ", f"direct-messages-out:{public_key}", out_messages_filter]
        )

    async def subscribe_to_merchant_events(self, public_key: str, since: int):
        stall_filter = {"kinds": [30017], "authors": [public_key]}
        product_filter = {"kinds": [30018], "authors": [public_key]}

        await self.send_req_queue.put(
            ["REQ", f"stall-events:{public_key}", stall_filter]
        )
        await self.send_req_queue.put(
            ["REQ", f"product-events:{public_key}", product_filter]
        )
        print("### subscribed to stalls and products", public_key)

    async def subscribe_to_user_profile(self, public_key: str, since: int):
        profile_filter = {"kinds": [0], "authors": [public_key]}
        if since and since != 0:
            profile_filter["since"] = since + 1

        await self.send_req_queue.put(
            ["REQ", f"user-profile-events:{public_key}", profile_filter]
        )

    async def unsubscribe_from_direct_messages(self, public_key: str):
        await self.send_req_queue.put(["CLOSE", f"direct-messages-in:{public_key}"])
        await self.send_req_queue.put(["CLOSE", f"direct-messages-out:{public_key}"])

    async def unsubscribe_from_merchant_events(self, public_key: str):
        await self.send_req_queue.put(["CLOSE", f"stall-events:{public_key}"])
        await self.send_req_queue.put(["CLOSE", f"product-events:{public_key}"])

    async def restart(self, public_keys: List[str]):
        print("### unsubscribe....")
        await self.unsubscribe_merchants(public_keys)
        # Give some time for the CLOSE events to propagate before restarting
        await asyncio.sleep(10)

        print("### restarting....")
        await self.send_req_queue.put(ValueError("Restarting NostrClient..."))
        await self.recieve_event_queue.put(ValueError("Restarting NostrClient..."))

        self.ws.close()
        self.ws = None


    async def stop(self, public_keys: List[str]):
        await self.unsubscribe_merchants(public_keys)       

        # Give some time for the CLOSE events to propagate before closing the connection  
        await asyncio.sleep(10)   
        self.ws.close()
        self.ws = None

    async def unsubscribe_merchants(self,  public_keys: List[str]):
        for pk in public_keys:
            try:
                await self.unsubscribe_from_direct_messages(pk)
                await self.unsubscribe_from_merchant_events(pk)
            except Exception as ex:
                logger.warning(ex)
        
