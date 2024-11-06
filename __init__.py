import asyncio

from fastapi import APIRouter
from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .nostr.nostr_client import NostrClient

db = Database("ext_nostrmarket")

nostrmarket_ext: APIRouter = APIRouter(prefix="/nostrmarket", tags=["nostrmarket"])

nostrmarket_static_files = [
    {
        "path": "/nostrmarket/static",
        "name": "nostrmarket_static",
    }
]


def nostrmarket_renderer():
    return template_renderer(["nostrmarket/templates"])


nostr_client: NostrClient = NostrClient()


from .tasks import wait_for_nostr_events, wait_for_paid_invoices  # noqa
from .views import *  # noqa
from .views_api import *  # noqa

scheduled_tasks: list[asyncio.Task] = []


async def nostrmarket_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)

    await nostr_client.stop()


def nostrmarket_start():

    async def _subscribe_to_nostr_client():
        # wait for 'nostrclient' extension to initialize
        await asyncio.sleep(10)
        await nostr_client.run_forever()

    async def _wait_for_nostr_events():
        # wait for this extension to initialize
        await asyncio.sleep(15)
        await wait_for_nostr_events(nostr_client)

    task1 = create_permanent_unique_task(
        "ext_nostrmarket_paid_invoices", wait_for_paid_invoices
    )
    task2 = create_permanent_unique_task(
        "ext_nostrmarket_subscribe_to_nostr_client", _subscribe_to_nostr_client
    )
    task3 = create_permanent_unique_task(
        "ext_nostrmarket_wait_for_events", _wait_for_nostr_events
    )
    scheduled_tasks.extend([task1, task2, task3])
