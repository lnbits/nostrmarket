from threading import Thread
from typing import Callable

from loguru import logger
from websocket import WebSocketApp

from lnbits.app import settings

from .. import send_req_queue
from .event import NostrEvent


async def publish_nostr_event(e: NostrEvent):
    print("### publish_nostr_event", e.dict())
    await send_req_queue.put(["EVENT", e.dict()])


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


async def subscribe_to_direct_messages(public_key: str, since: int):
    in_messages_filter = {"kind": 4, "#p": [public_key]}
    out_messages_filter = {"kind": 4, "authors": [public_key]}
    if since != 0:
        in_messages_filter["since"] = since
        out_messages_filter["since"] = since
    print("### in_messages_filter", in_messages_filter)
    print("### out_messages_filter", out_messages_filter)

    await send_req_queue.put(
        ["REQ", f"direct-messages-in:{public_key}", in_messages_filter]
    )
    await send_req_queue.put(
        ["REQ", f"direct-messages-out:{public_key}", out_messages_filter]
    )


async def unsubscribe_from_direct_messages(public_key: str):
    await send_req_queue.put(["CLOSE", f"direct-messages-in:{public_key}"])
    await send_req_queue.put(["CLOSE", f"direct-messages-out:{public_key}"])
