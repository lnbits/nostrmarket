from threading import Thread
from typing import Callable

import httpx
from loguru import logger
from websocket import WebSocketApp

from lnbits.app import settings
from lnbits.helpers import url_for

from .event import NostrEvent


async def publish_nostr_event(e: NostrEvent):
    url = url_for("/nostrclient/api/v1/publish", external=True)
    data = dict(e)
    print("### published", dict(data))
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                url,
                json=data,
            )
        except Exception as ex:
            logger.warning(ex)


async def connect_to_nostrclient_ws(
    on_open: Callable, on_message: Callable
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


# async def handle_event(event, pubkeys):
#     tags = [t[1] for t in event["tags"] if t[0] == "p"]
#     to_merchant = None
#     if tags and len(tags) > 0:
#         to_merchant = tags[0]

#     if event["pubkey"] in pubkeys or to_merchant in pubkeys:
#         logger.debug(f"Event sent to {to_merchant}")
#         pubkey = to_merchant if to_merchant in pubkeys else event["pubkey"]
#         # Send event to market extension
#         await send_event_to_market(event=event, pubkey=pubkey)


# async def send_event_to_market(event: dict, pubkey: str):
#     # Sends event to market extension, for decrypt and handling
#     market_url = url_for(f"/market/api/v1/nip04/{pubkey}", external=True)
#     async with httpx.AsyncClient() as client:
#         await client.post(url=market_url, json=event)
