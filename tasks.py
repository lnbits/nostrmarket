from asyncio import Queue

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener

from .crud import (
    get_all_customers,
    get_last_direct_messages_time,
    get_last_order_time,
    get_last_product_update_time,
    get_last_stall_update_time,
    get_merchants_ids_with_pubkeys,
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

    order_id = payment.extra.get("order_id")
    merchant_pubkey = payment.extra.get("merchant_pubkey")
    if not order_id or not merchant_pubkey:
        return None

    await handle_order_paid(order_id, merchant_pubkey)


async def wait_for_nostr_events(nostr_client: NostrClient):
    merchant_ids = await get_merchants_ids_with_pubkeys()
    for id, pk in merchant_ids:
        last_order_time = await get_last_order_time(id)
        last_dm_time = await get_last_direct_messages_time(id)
        since = max(last_order_time, last_dm_time)

        await nostr_client.subscribe_to_direct_messages(pk, since)

    for id, pk in merchant_ids:
        last_stall_update = await get_last_stall_update_time(id)
        await nostr_client.subscribe_to_stall_events(pk, last_stall_update)

    for id, pk in merchant_ids:
        last_product_update = await get_last_product_update_time(id)
        await nostr_client.subscribe_to_product_events(pk, last_product_update)

    customers = await get_all_customers()
    for c in customers:
        await nostr_client.subscribe_to_user_profile(c.public_key, c.event_created_at)

    while True:
        message = await nostr_client.get_event()
        await process_nostr_message(message)
