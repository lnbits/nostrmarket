import asyncio
import json
from asyncio import Queue
from threading import Thread
from typing import Callable, List

from loguru import logger
from websocket import WebSocketApp

from lnbits.app import settings
from lnbits.helpers import urlsafe_short_hash

from .event import NostrEvent


class NostrClient:
    def __init__(self):
        self.recieve_event_queue: Queue = Queue()
        self.send_req_queue: Queue = Queue()
        self.ws: WebSocketApp = None
        self.subscription_id = "nostrmarket-" + urlsafe_short_hash()[:32]

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

    async def subscribe_merchants(
        self,
        public_keys: List[str],
        dm_time=0,
        stall_time=0,
        product_time=0,
        profile_time=0,
    ):
        dm_filters = self._filters_for_direct_messages(public_keys, dm_time)
        stall_filters = self._filters_for_stall_events(public_keys, stall_time)
        product_filters = self._filters_for_product_events(public_keys, product_time)
        profile_filters = self._filters_for_user_profile(public_keys, profile_time)

        merchant_filters = (
            dm_filters + stall_filters + product_filters + profile_filters
        )

        self.subscription_id = "nostrmarket-" + urlsafe_short_hash()[:32]
        await self.send_req_queue.put(["REQ", self.subscription_id] + merchant_filters)

        logger.debug(f"Subscribed to events for: {len(public_keys)} keys. New subscription id: {self.subscription_id}")

        print("###  merchant_filters: ", merchant_filters)


    def _filters_for_direct_messages(self, public_keys: List[str], since: int) -> List:
        in_messages_filter = {"kinds": [4], "#p": public_keys}
        out_messages_filter = {"kinds": [4], "authors": public_keys}
        if since and since != 0:
            in_messages_filter["since"] = since
            out_messages_filter["since"] = since

        return [in_messages_filter, out_messages_filter]

    def _filters_for_stall_events(self, public_keys: List[str], since: int) -> List:
        stall_filter = {"kinds": [30017], "authors": public_keys}
        if since and since != 0:
            stall_filter["since"] = since

        return [stall_filter]

    def _filters_for_product_events(self, public_keys: List[str], since: int) -> List:
        product_filter = {"kinds": [30018], "authors": public_keys}
        if since and since != 0:
            product_filter["since"] = since

        return [product_filter]

    def _filters_for_user_profile(self, public_keys: List[str], since: int) -> List:
        profile_filter = {"kinds": [0], "authors": public_keys}
        if since and since != 0:
            profile_filter["since"] = since

        return [profile_filter]

    # todo: remove
    def subscribe_to_user_profile(self, public_keys: List[str], since: int) -> List:
        profile_filter = {"kinds": [0], "authors": public_keys}
        if since and since != 0:
            profile_filter["since"] = since

    async def restart(self):
        await self.unsubscribe_merchants()
        # Give some time for the CLOSE events to propagate before restarting
        await asyncio.sleep(10)

        logger.info("Restating NostrClient...")
        await self.send_req_queue.put(ValueError("Restarting NostrClient..."))
        await self.recieve_event_queue.put(ValueError("Restarting NostrClient..."))

        self.ws.close()
        self.ws = None

    async def stop(self):
        await self.unsubscribe_merchants()

        # Give some time for the CLOSE events to propagate before closing the connection
        await asyncio.sleep(10)
        self.ws.close()
        self.ws = None


    async def unsubscribe_merchants(self):
        await self.send_req_queue.put(["CLOSE", self.subscription_id])

        logger.debug("Unsubscribed from all merchants events")
