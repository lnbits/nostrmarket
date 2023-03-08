from typing import Optional

from lnbits.core import create_invoice

from .crud import (
    get_merchant_for_user,
    get_order,
    get_order_by_event_id,
    get_products_by_ids,
    get_wallet_for_product,
)
from .models import (
    Nostrable,
    Order,
    OrderExtra,
    PartialOrder,
    PaymentOption,
    PaymentRequest,
)
from .nostr.event import NostrEvent
from .nostr.nostr_client import publish_nostr_event


async def create_order(user_id: str, data: PartialOrder) -> Optional[PaymentRequest]:
    if await get_order(user_id, data.id):
        return None
    if data.event_id and await get_order_by_event_id(user_id, data.event_id):
        return None

    merchant = await get_merchant_for_user(user_id)
    assert merchant, "Cannot find merchant!"

    products = await get_products_by_ids(user_id, [p.product_id for p in data.items])
    data.validate_order_items(products)

    total_amount = await data.total_sats(products)

    wallet_id = await get_wallet_for_product(data.items[0].product_id)
    assert wallet_id, "Missing wallet for order `{data.id}`"

    payment_hash, invoice = await create_invoice(
        wallet_id=wallet_id,
        amount=round(total_amount),
        memo=f"Order '{data.id}' for pubkey '{data.pubkey}'",
        extra={
            "tag": "nostrmarket",
            "order_id": data.id,
            "merchant_pubkey": merchant.public_key,
        },
    )

    order = Order(
        **data.dict(),
        stall_id=products[0].stall_id,
        invoice_id=payment_hash,
        total=total_amount,
        extra=await OrderExtra.from_products(products),
    )
    await create_order(user_id, order)

    return PaymentRequest(
        id=data.id, payment_options=[PaymentOption(type="ln", link=invoice)]
    )


async def sign_and_send_to_nostr(
    user_id: str, n: Nostrable, delete=False
) -> NostrEvent:
    merchant = await get_merchant_for_user(user_id)
    assert merchant, "Cannot find merchant!"

    event = (
        n.to_nostr_delete_event(merchant.public_key)
        if delete
        else n.to_nostr_event(merchant.public_key)
    )
    event.sig = merchant.sign_hash(bytes.fromhex(event.id))
    await publish_nostr_event(event)

    return event
