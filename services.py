import json
from typing import Optional

from loguru import logger

from lnbits.core import create_invoice, get_wallet

from .crud import (
    create_direct_message,
    create_order,
    get_merchant_by_pubkey,
    get_merchant_for_user,
    get_order,
    get_order_by_event_id,
    get_products_by_ids,
    get_wallet_for_product,
    update_order_paid_status,
)
from .helpers import order_from_json
from .models import (
    Merchant,
    Nostrable,
    Order,
    OrderExtra,
    OrderStatusUpdate,
    PartialDirectMessage,
    PartialOrder,
    PaymentOption,
    PaymentRequest,
)
from .nostr.event import NostrEvent
from .nostr.nostr_client import publish_nostr_event


async def create_new_order(
    merchant_public_key: str, data: PartialOrder
) -> Optional[PaymentRequest]:
    merchant = await get_merchant_by_pubkey(merchant_public_key)
    assert merchant, "Cannot find merchant!"

    if await get_order(merchant.id, data.id):
        return None
    if data.event_id and await get_order_by_event_id(merchant.id, data.event_id):
        return None

    products = await get_products_by_ids(
        merchant.id, [p.product_id for p in data.items]
    )
    data.validate_order_items(products)

    total_amount = await data.total_sats(products)

    wallet_id = await get_wallet_for_product(data.items[0].product_id)
    assert wallet_id, "Missing wallet for order `{data.id}`"

    payment_hash, invoice = await create_invoice(
        wallet_id=wallet_id,
        amount=round(total_amount),
        memo=f"Order '{data.id}' for pubkey '{data.public_key}'",
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
    await create_order(merchant.id, order)

    return PaymentRequest(
        id=data.id, payment_options=[PaymentOption(type="ln", link=invoice)]
    )


async def sign_and_send_to_nostr(
    merchant: Merchant, n: Nostrable, delete=False
) -> NostrEvent:
    event = (
        n.to_nostr_delete_event(merchant.public_key)
        if delete
        else n.to_nostr_event(merchant.public_key)
    )
    event.sig = merchant.sign_hash(bytes.fromhex(event.id))
    await publish_nostr_event(event)

    return event


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

        dm_event = merchant.build_dm_event(dm_content, order.public_key)
        await publish_nostr_event(dm_event)
    except Exception as ex:
        logger.warning(ex)


async def process_nostr_message(msg: str):
    try:
        type, *rest= json.loads(msg)
        if type.upper() == "EVENT":
            subscription_id, event = rest
            subscription_name, merchant_public_key = subscription_id.split(":")
            event = NostrEvent(**event)
            if event.kind == 4:
                await _handle_nip04_message(
                    subscription_name, merchant_public_key, event
                )
            return
    except Exception as ex:
        logger.warning(ex)


async def _handle_nip04_message(
    subscription_name: str, merchant_public_key: str, event: NostrEvent
):
    merchant = await get_merchant_by_pubkey(merchant_public_key)
    assert merchant, f"Merchant not found for public key '{merchant_public_key}'"

    clear_text_msg = merchant.decrypt_message(event.content, event.pubkey)
    # print("### clear_text_msg", subscription_name, clear_text_msg)
    if subscription_name == "direct-messages-in":
        await _handle_incoming_dms(event, merchant, clear_text_msg)
    else:
        await _handle_outgoing_dms(event, merchant, clear_text_msg)


async def _handle_incoming_dms(
    event: NostrEvent, merchant: Merchant, clear_text_msg: str
):
    dm_content = await _handle_dirrect_message(
        merchant.id,
        merchant.public_key,
        event.pubkey,
        event.id,
        event.created_at,
        clear_text_msg,
    )
    if dm_content:
        dm_event = merchant.build_dm_event(dm_content, event.pubkey)
        await publish_nostr_event(dm_event)


async def _handle_outgoing_dms(
    event: NostrEvent, merchant: Merchant, clear_text_msg: str
):
    sent_to = event.tag_values("p")
    if len(sent_to) != 0:
        dm = PartialDirectMessage(
            event_id=event.id,
            event_created_at=event.created_at,
            message=clear_text_msg,  # exclude if json
            public_key=sent_to[0],
            incoming=True,
        )
        await create_direct_message(merchant.id, dm)


async def _handle_dirrect_message(
    merchant_id: str,
    merchant_public_key: str,
    from_pubkey: str,
    event_id: str,
    event_created_at: int,
    msg: str,
) -> Optional[str]:
    order, text_msg = order_from_json(msg)
    try:
        if order:
            order["public_key"] = from_pubkey
            order["merchant_public_key"] = merchant_public_key
            order["event_id"] = event_id
            order["event_created_at"] = event_created_at
            return await _handle_new_order(PartialOrder(**order))
        else:
            # print("### text_msg", text_msg, event_created_at, event_id)
            dm = PartialDirectMessage(
                event_id=event_id,
                event_created_at=event_created_at,
                message=text_msg,
                public_key=from_pubkey,
                incoming=True,
            )
            await create_direct_message(merchant_id, dm)
            return None
    except Exception as ex:
        logger.warning(ex)
        return None


async def _handle_new_order(order: PartialOrder) -> Optional[str]:
    ### todo: check that event_id not parsed already

    order.validate_order()

    first_product_id = order.items[0].product_id
    wallet_id = await get_wallet_for_product(first_product_id)
    assert wallet_id, f"Cannot find wallet id for product id: {first_product_id}"

    wallet = await get_wallet(wallet_id)
    assert wallet, f"Cannot find wallet for product id: {first_product_id}"

    new_order = await create_new_order(wallet.user, order)
    if new_order:
        return json.dumps(new_order.dict(), separators=(",", ":"), ensure_ascii=False)

    return None
