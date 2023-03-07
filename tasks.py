import asyncio
import json
from asyncio import Queue

import httpx
import websocket
from loguru import logger
from websocket import WebSocketApp

from lnbits.core import get_wallet
from lnbits.core.models import Payment
from lnbits.helpers import Optional, url_for
from lnbits.tasks import register_invoice_listener

from .crud import (
    create_direct_message,
    get_merchant_by_pubkey,
    get_public_keys_for_merchants,
    get_wallet_for_product,
    update_order_paid_status,
)
from .helpers import order_from_json
from .models import OrderStatusUpdate, PartialDirectMessage, PartialOrder
from .nostr.event import NostrEvent
from .nostr.nostr_client import connect_to_nostrclient_ws, publish_nostr_event


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


async def handle_order_paid(order_id: str, merchant_pubkey: str):
    try:
        order = await update_order_paid_status(order_id, True)
        assert order, f"Paid order cannot be found. Order id: {order_id}"
        order_status = OrderStatusUpdate(
            id=order_id, message="Payment received.", paid=True, shipped=order.shipped
        )

        merchant = await get_merchant_by_pubkey(merchant_pubkey)
        assert merchant, f"Merchant cannot be found for order {order_id}"
        dm_content = json.dumps(
            order_status.dict(), separators=(",", ":"), ensure_ascii=False
        )

        dm_event = merchant.build_dm_event(dm_content, order.pubkey)
        await publish_nostr_event(dm_event)
    except Exception as ex:
        logger.warning(ex)


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
                await handle_nip04_message(public_key, event)

    except Exception as ex:
        logger.warning(ex)


async def handle_nip04_message(public_key: str, event: NostrEvent):
    merchant = await get_merchant_by_pubkey(public_key)
    assert merchant, f"Merchant not found for public key '{public_key}'"

    clear_text_msg = merchant.decrypt_message(event.content, event.pubkey)
    dm_content = await handle_dirrect_message(
        merchant.id, event.pubkey, event.id, clear_text_msg
    )
    if dm_content:
        dm_event = merchant.build_dm_event(dm_content, event.pubkey)
        await publish_nostr_event(dm_event)


async def handle_dirrect_message(
    merchant_id: str, from_pubkey: str, event_id: str, msg: str
) -> Optional[str]:
    order, text_msg = order_from_json(msg)
    try:
        if order:
            order["pubkey"] = from_pubkey
            order["event_id"] = event_id
            return await handle_new_order(PartialOrder(**order))
        else:
            print("### text_msg", text_msg)
            dm = PartialDirectMessage(
                event_id=event_id,
                message=text_msg,
                public_key=from_pubkey,
                incoming=True,
            )
            await create_direct_message(merchant_id, dm)
            return None
    except Exception as ex:
        logger.warning(ex)
        return None


async def handle_new_order(order: PartialOrder):
    ### todo: check that event_id not parsed already

    order.validate_order()

    first_product_id = order.items[0].product_id
    wallet_id = await get_wallet_for_product(first_product_id)
    assert wallet_id, f"Cannot find wallet id for product id: {first_product_id}"

    wallet = await get_wallet(wallet_id)
    assert wallet, f"Cannot find wallet for product id: {first_product_id}"

    market_url = url_for(f"/nostrmarket/api/v1/order", external=True)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url=market_url,
            headers={
                "X-Api-Key": wallet.adminkey,
            },
            json=order.dict(),
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    return None
