import httpx
from loguru import logger

from lnbits.app import settings
from lnbits.helpers import url_for

from .event import NostrEvent


async def publish_nostr_event(e: NostrEvent):
    url = url_for("/nostrclient/api/v1/publish", external=True)
    data = dict(e)
    print("### published", dict(data))
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                url,
                json=data,
            )
        except Exception as ex:
            logger.warning(ex)
