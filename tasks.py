import asyncio
from asyncio import Queue

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .nostr.nostr_client import NostrClient
from .services import (
    handle_order_paid,
    process_nostr_message,
    subscribe_to_all_merchants,
)


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
    while True:
        try:
            await subscribe_to_all_merchants()

            while True:
                message = await nostr_client.get_event()
                await process_nostr_message(message)
        except Exception as e:
            logger.warning(f"Subcription failed. Will retry in one minute: {e}")
            await asyncio.sleep(10)
