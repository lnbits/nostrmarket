import asyncio
import json
from asyncio import Queue

import httpx
import websocket
from loguru import logger
from websocket import WebSocketApp

from lnbits.core import get_wallet
from lnbits.core.models import Payment
from lnbits.extensions.nostrmarket.models import PartialOrder
from lnbits.helpers import url_for
from lnbits.tasks import register_invoice_listener

from .crud import (
    get_merchant_by_pubkey,
    get_product,
    get_public_keys_for_merchants,
    get_wallet_for_product,
)
from .helpers import order_from_json
from .nostr.event import NostrEvent
from .nostr.nostr_client import connect_to_nostrclient_ws


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
            print("### req", req)
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
                assert merchant, f"Merchant not found for public key '{public_key}'"

                clear_text_msg = merchant.decrypt_message(event.content, event.pubkey)
                await handle_nip04_message(event.pubkey, event.id, clear_text_msg)

    except Exception as ex:
        logger.warning(ex)


async def handle_nip04_message(from_pubkey: str, event_id: str, msg: str):
    order, text_msg = order_from_json(msg)
    try:
        if order:
            print("### order", from_pubkey, event_id, msg)
            ### check that event_id not parsed already
            order["pubkey"] = from_pubkey
            order["event_id"] = event_id
            partial_order = PartialOrder(**order)
            assert len(partial_order.items) != 0, "Order has no items. Order: " + msg

            first_product_id = partial_order.items[0].product_id
            wallet_id = await get_wallet_for_product(first_product_id)
            assert (
                wallet_id
            ), f"Cannot find wallet id for product id: {first_product_id}"

            wallet = await get_wallet(wallet_id)
            assert wallet, f"Cannot find wallet for product id: {first_product_id}"

            market_url = url_for(f"/nostrmarket/api/v1/order", external=True)
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url=market_url,
                    headers={
                        "X-Api-Key": wallet.adminkey,
                    },
                    json=order,
                )
                resp.raise_for_status()
                data = resp.json()

                print("### payment request", data)
        else:
            print("### text_msg", text_msg)
    except Exception as ex:
        logger.warning(ex)
