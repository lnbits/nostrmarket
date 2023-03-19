from asyncio import Queue
import json

from loguru import logger

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener

from .crud import (
    get_last_direct_messages_time,
    get_last_order_time,
    get_public_keys_for_merchants,
)
from .nostr.nostr_client import NostrClient
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

    logger.warning("### on_invoice_paid")
    order_id = payment.extra.get("order_id")
    merchant_pubkey = payment.extra.get("merchant_pubkey")
    if not order_id or not merchant_pubkey:
        return None

    await handle_order_paid(order_id, merchant_pubkey)


async def wait_for_nostr_events(nostr_client: NostrClient):
    public_keys = await get_public_keys_for_merchants()
    logger.warning("### wait_for_nostr_events" + json.dumps(public_keys))
    for p in public_keys:
        last_order_time = await get_last_order_time(p)
        last_dm_time = await get_last_direct_messages_time(p)
        since = max(last_order_time, last_dm_time)

        await nostr_client.subscribe_to_direct_messages(p, since)

    while True:
        message = await nostr_client.get_event()
        await process_nostr_message(message)
