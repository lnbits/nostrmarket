import asyncio
import json
import threading

import httpx
import websocket
from loguru import logger

from lnbits.core.models import Payment
from lnbits.helpers import url_for
from lnbits.tasks import register_invoice_listener



async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue)

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "market":
        return

    print("### on_invoice_paid")


async def subscribe_nostrclient_ws():
    print("### subscribe_nostrclient_ws")

