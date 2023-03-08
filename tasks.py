import asyncio
import json
from asyncio import Queue

import websocket
from loguru import logger
from websocket import WebSocketApp

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener

from .crud import get_public_keys_for_merchants
from .nostr.nostr_client import connect_to_nostrclient_ws
from .services import handle_order_paid, process_nostr_message


async def wait_for_paid_invoices():
    invoice_queue = Queue()
    register_invoice_listener(invoice_queue)

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "nostrmarket":
        return

    order_id = payment.extra.get("order_id")
    merchant_pubkey = payment.extra.get("merchant_pubkey")
    if not order_id or not merchant_pubkey:
        return None

    await handle_order_paid(order_id, merchant_pubkey)


async def subscribe_to_nostr_client(recieve_event_queue: Queue, send_req_queue: Queue):
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
            ws.send(json.dumps(req))
        except Exception as ex:
            logger.warning(ex)
            if req:
                await send_req_queue.put(req)
            ws = None  # todo close
            await asyncio.sleep(5)


async def wait_for_nostr_events(recieve_event_queue: Queue, send_req_queue: Queue):
    public_keys = await get_public_keys_for_merchants()
    for p in public_keys:
        await send_req_queue.put(
            ["REQ", f"direct-messages-in:{p}", {"kind": 4, "#p": [p]}]
        )
        # await send_req_queue.put(
        #     ["REQ", f"direct-messages-out:{p}", {"kind": 4, "authors": [p]}]
        # )

    while True:
        message = await recieve_event_queue.get()
        await process_nostr_message(message)
