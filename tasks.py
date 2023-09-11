from asyncio import Queue
import asyncio

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener

from .crud import (
    get_all_unique_customers,
    get_last_direct_messages_created_at,
    get_last_order_time,
    get_last_product_update_time,
    get_last_stall_update_time,
    get_merchants_ids_with_pubkeys,
)
from .nostr.nostr_client import NostrClient
from .services import get_last_event_date_for_merchant, handle_order_paid, process_nostr_message


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


async def wait_for_nostr_events(nostr_client: NostrClient):
    merchant_ids = await get_merchants_ids_with_pubkeys()
    for id, pk in merchant_ids:
        since = await get_last_event_date_for_merchant(id)
        await nostr_client.subscribe_merchant(pk, since)
        await asyncio.sleep(0.1) # try to avoid 'too many concurrent REQ' from relays

    # customers = await get_all_unique_customers()
    # for c in customers:
    #     await nostr_client.subscribe_to_user_profile(c.public_key, c.event_created_at)

    while True:
        message = await nostr_client.get_event()
        await process_nostr_message(message)
