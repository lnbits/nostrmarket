import asyncio
import json
from asyncio import Queue

import httpx
import websocket
from loguru import logger
from websocket import WebSocketApp

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener

from .crud import get_merchant, get_merchant_by_pubkey, get_public_keys_for_merchants
from .nostr.event import NostrEvent
from .nostr.nostr_client import connect_to_nostrclient_ws

recieve_event_queue: Queue = Queue()
send_req_queue: Queue = Queue()


async def wait_for_paid_invoices():
    invoice_queue = Queue()
    register_invoice_listener(invoice_queue)

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "nostrmarket":
        return

    print("### on_invoice_paid")


async def subscribe_nostrclient():
    print("### subscribe_nostrclient_ws")

    def on_open(_):
        logger.info("Connected to 'nostrclient' websocket")

    def on_message(_, message):
        print("### on_message", message)
        recieve_event_queue.put_nowait(message)

    # wait for 'nostrclient' extension to initialize
    await asyncio.sleep(5)
    ws: WebSocketApp = None
    while True:
        try:
            req = None
            if not ws:
                ws = await connect_to_nostrclient_ws(on_open, on_message)
                # be sure the connection is open
                await asyncio.sleep(3)
            req = await send_req_queue.get()
            print("### req", req)
            ws.send(json.dumps(req))
        except Exception as ex:
            logger.warning(ex)
            if req:
                await send_req_queue.put(req)
            ws = None  # todo close
            await asyncio.sleep(5)


async def wait_for_nostr_events():
    public_keys = await get_public_keys_for_merchants()
    for p in public_keys:
        await send_req_queue.put(
            ["REQ", f"direct-messages:{p}", {"kind": 4, "#p": [p]}]
        )

    while True:
        message = await recieve_event_queue.get()
        await handle_message(message)


async def handle_message(msg: str):
    try:
        type, subscription_id, event = json.loads(msg)
        _, public_key = subscription_id.split(":")
        if type.upper() == "EVENT":
            event = NostrEvent(**event)
            if event.kind == 4:
                merchant = await get_merchant_by_pubkey(public_key)
                if not merchant:
                    return
                clear_text_msg = merchant.decrypt_message(event.content, event.pubkey)
                print("### clear_text_msg", clear_text_msg)

    except Exception as ex:
        logger.warning(ex)
