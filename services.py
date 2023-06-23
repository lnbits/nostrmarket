import json
from typing import List, Optional, Tuple

from loguru import logger

from lnbits.core import create_invoice, get_wallet
from lnbits.core.services import websocketUpdater

from . import nostr_client
from .crud import (
    CustomerProfile,
    create_customer,
    create_direct_message,
    create_order,
    create_product,
    create_stall,
    get_customer,
    get_merchant_by_pubkey,
    get_order,
    get_order_by_event_id,
    get_products,
    get_products_by_ids,
    get_stalls,
    get_wallet_for_product,
    get_zone,
    increment_customer_unread_messages,
    update_customer_profile,
    update_order_paid_status,
    update_product,
    update_product_quantity,
    update_stall,
)
from .helpers import order_from_json
from .models import (
    Customer,
    Merchant,
    Nostrable,
    Order,
    OrderExtra,
    OrderItem,
    OrderStatusUpdate,
    PartialDirectMessage,
    PartialOrder,
    PaymentOption,
    PaymentRequest,
    Product,
    Stall,
)
from .nostr.event import NostrEvent


async def create_new_order(
    merchant_public_key: str, data: PartialOrder
) -> Optional[PaymentRequest]:
    merchant = await get_merchant_by_pubkey(merchant_public_key)
    assert merchant, "Cannot find merchant for order!"

    if await get_order(merchant.id, data.id):
        return None
    if data.event_id and await get_order_by_event_id(merchant.id, data.event_id):
        return None

    products = await get_products_by_ids(
        merchant.id, [p.product_id for p in data.items]
    )
    data.validate_order_items(products)
    shipping_zone = await get_zone(merchant.id, data.shipping_id)
    assert shipping_zone, f"Shipping zone not found for order '{data.id}'"

    product_cost_sat, shipping_cost_sat = await data.costs_in_sats(
        products, shipping_zone.cost
    )

    wallet_id = await get_wallet_for_product(data.items[0].product_id)
    assert wallet_id, "Missing wallet for order `{data.id}`"

    product_ids = [i.product_id for i in data.items]
    success, _, message = await compute_products_new_quantity(
        merchant.id, product_ids, data.items
    )
    if not success:
        return PaymentRequest(id=data.id, message=message, payment_options=[])

    payment_hash, invoice = await create_invoice(
        wallet_id=wallet_id,
        amount=round(product_cost_sat + shipping_cost_sat),
        memo=f"Order '{data.id}' for pubkey '{data.public_key}'",
        extra={
            "tag": "nostrmarket",
            "order_id": data.id,
            "merchant_pubkey": merchant.public_key,
        },
    )

    extra = await OrderExtra.from_products(products)
    extra.shipping_cost_sat = shipping_cost_sat
    extra.shipping_cost = shipping_zone.cost

    order = Order(
        **data.dict(),
        stall_id=products[0].stall_id,
        invoice_id=payment_hash,
        total=product_cost_sat + shipping_cost_sat,
        extra=extra,
    )
    await create_order(merchant.id, order)
    await websocketUpdater(
        merchant.id,
        json.dumps(
            {
                "type": "new-order",
                "stallId": products[0].stall_id,
                "customerPubkey": data.public_key,
                "orderId": order.id,
            }
        ),
    )

    return PaymentRequest(
        id=data.id, payment_options=[PaymentOption(type="ln", link=invoice)]
    )


async def update_merchant_to_nostr(
    merchant: Merchant, delete_merchant=False
) -> Merchant:
    stalls = await get_stalls(merchant.id)
    for stall in stalls:
        products = await get_products(merchant.id, stall.id)
        for product in products:
            event = await sign_and_send_to_nostr(merchant, product, delete_merchant)
            product.event_id = event.id
            product.event_created_at = event.created_at
            await update_product(merchant.id, product)
        event = await sign_and_send_to_nostr(merchant, stall, delete_merchant)
        stall.event_id = event.id
        stall.event_created_at = event.created_at
        await update_stall(merchant.id, stall)
    if delete_merchant:
        # merchant profile updates not supported yet
        event = await sign_and_send_to_nostr(merchant, merchant, delete_merchant)
    merchant.config.event_id = event.id
    return merchant


async def sign_and_send_to_nostr(
    merchant: Merchant, n: Nostrable, delete=False
) -> NostrEvent:
    event = (
        n.to_nostr_delete_event(merchant.public_key)
        if delete
        else n.to_nostr_event(merchant.public_key)
    )
    event.sig = merchant.sign_hash(bytes.fromhex(event.id))
    await nostr_client.publish_nostr_event(event)

    return event


async def handle_order_paid(order_id: str, merchant_pubkey: str):
    try:
        order = await update_order_paid_status(order_id, True)
        assert order, f"Paid order cannot be found. Order id: {order_id}"

        merchant = await get_merchant_by_pubkey(merchant_pubkey)
        assert merchant, f"Merchant cannot be found for order {order_id}"

        # todo: lock
        success, message = await update_products_for_order(merchant, order)
        await notify_client_of_order_status(order, merchant, success, message)
    except Exception as ex:
        logger.warning(ex)


async def notify_client_of_order_status(
    order: Order, merchant: Merchant, success: bool, message: str
):
    dm_content = ""
    if success:
        order_status = OrderStatusUpdate(
            id=order.id,
            message="Payment received.",
            paid=True,
            shipped=order.shipped,
        )
        dm_content = json.dumps(
            order_status.dict(), separators=(",", ":"), ensure_ascii=False
        )
    else:
        dm_content = f"Order cannot be fulfilled. Reason: {message}"

    dm_event = merchant.build_dm_event(dm_content, order.public_key)
    await nostr_client.publish_nostr_event(dm_event)


async def update_products_for_order(
    merchant: Merchant, order: Order
) -> Tuple[bool, str]:
    product_ids = [i.product_id for i in order.items]
    success, products, message = await compute_products_new_quantity(
        merchant.id, product_ids, order.items
    )
    if not success:
        return success, message

    for p in products:
        product = await update_product_quantity(p.id, p.quantity)
        event = await sign_and_send_to_nostr(merchant, product)
        product.event_id = event.id
        await update_product(merchant.id, product)

    return True, "ok"


async def compute_products_new_quantity(
    merchant_id: str, product_ids: List[str], items: List[OrderItem]
) -> Tuple[bool, List[Product], str]:
    products: List[Product] = await get_products_by_ids(merchant_id, product_ids)

    for p in products:
        required_quantity = next(
            (i.quantity for i in items if i.product_id == p.id), None
        )
        if not required_quantity:
            return False, [], f"Product not found for order: {p.id}"
        if p.quantity < required_quantity:
            return (
                False,
                [],
                f"Quantity not sufficient for product: {p.id}. Required {required_quantity} but only have {p.quantity}",
            )

        p.quantity -= required_quantity

    return True, products, "ok"


async def process_nostr_message(msg: str):
    try:
        type, *rest = json.loads(msg)
        if type.upper() == "EVENT":
            subscription_id, event = rest
            event = NostrEvent(**event)
            print("### new event", event.kind, subscription_id)
            print("### new event json: ", json.dumps(event.dict()))
            if event.kind == 0:
                await _handle_customer_profile_update(event)
            elif event.kind == 4:
                _, merchant_public_key = subscription_id.split(":")
                await _handle_nip04_message(merchant_public_key, event)
            elif event.kind == 30017:
                await _handle_stall(event)
            elif event.kind == 30018:
                await _handle_product(event)
            return
    except Exception as ex:
        logger.warning(ex)


async def _handle_nip04_message(merchant_public_key: str, event: NostrEvent):
    merchant = await get_merchant_by_pubkey(merchant_public_key)
    assert merchant, f"Merchant not found for public key '{merchant_public_key}'"

    if event.pubkey == merchant_public_key:
        assert len(event.tag_values("p")) != 0, "Outgong message has no 'p' tag"
        clear_text_msg = merchant.decrypt_message(
            event.content, event.tag_values("p")[0]
        )
        await _handle_outgoing_dms(event, merchant, clear_text_msg)
    elif event.has_tag_value("p", merchant_public_key):
        clear_text_msg = merchant.decrypt_message(event.content, event.pubkey)
        await _handle_incoming_dms(event, merchant, clear_text_msg)
    else:
        logger.warning(f"Bad NIP04 event: '{event.id}'")


async def _handle_incoming_dms(
    event: NostrEvent, merchant: Merchant, clear_text_msg: str
):
    customer = await get_customer(merchant.id, event.pubkey)
    if not customer:
        await _handle_new_customer(event, merchant)
    else:
        await increment_customer_unread_messages(event.pubkey)

    dm_reply = await _handle_dirrect_message(
        merchant.id,
        merchant.public_key,
        event.pubkey,
        event.id,
        event.created_at,
        clear_text_msg,
    )
    if dm_reply:
        dm_event = merchant.build_dm_event(dm_reply, event.pubkey)
        await nostr_client.publish_nostr_event(dm_event)


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
        dm = PartialDirectMessage(
            event_id=event_id,
            event_created_at=event_created_at,
            message=text_msg,
            public_key=from_pubkey,
            incoming=True,
        )
        await create_direct_message(merchant_id, dm)
        await websocketUpdater(
            merchant_id,
            json.dumps({"type": "new-direct-message", "customerPubkey": from_pubkey}),
        )

        if order:
            order["public_key"] = from_pubkey
            order["merchant_public_key"] = merchant_public_key
            order["event_id"] = event_id
            order["event_created_at"] = event_created_at
            return await _handle_new_order(PartialOrder(**order))

        return None
    except Exception as ex:
        logger.warning(ex)
        return None


async def _handle_new_order(order: PartialOrder) -> Optional[str]:
    order.validate_order()

    first_product_id = order.items[0].product_id
    wallet_id = await get_wallet_for_product(first_product_id)
    assert wallet_id, f"Cannot find wallet id for product id: {first_product_id}"

    wallet = await get_wallet(wallet_id)
    assert wallet, f"Cannot find wallet for product id: {first_product_id}"

    new_order = await create_new_order(order.merchant_public_key, order)
    if new_order:
        return json.dumps(new_order.dict(), separators=(",", ":"), ensure_ascii=False)

    return None


async def _handle_new_customer(event, merchant: Merchant):
    await create_customer(
        merchant.id, Customer(merchant_id=merchant.id, public_key=event.pubkey)
    )
    await nostr_client.subscribe_to_user_profile(event.pubkey, 0)


async def _handle_customer_profile_update(event: NostrEvent):
    try:
        profile = json.loads(event.content)
        await update_customer_profile(
            event.pubkey,
            event.created_at,
            CustomerProfile(
                name=profile["name"] if "name" in profile else "",
                about=profile["about"] if "about" in profile else "",
            ),
        )
    except Exception as ex:
        logger.warning(ex)


async def _handle_stall(event: NostrEvent):
    try:
        merchant = await get_merchant_by_pubkey(event.pubkey)
        assert merchant, f"Merchant not found for public key '{event.pubkey}'"
        stall_json = json.loads(event.content)

        if "id" not in stall_json:
            return

        stall = Stall(
            id=stall_json["id"],
            name=stall_json.get("name", "Recoverd Stall (no name)"),
            wallet="",
            currency=stall_json.get("currency", "sat"),
            shipping_zones=stall_json.get("shipping", []),
            pending=True,
            event_id = event.id,
            event_created_at = event.created_at
        )
        stall.config.description = stall_json.get("description", "")
        await create_stall(merchant.id, stall)
        
    except Exception as ex:
        logger.error(ex)

async def _handle_product(event: NostrEvent):
    try:
        merchant = await get_merchant_by_pubkey(event.pubkey)
        assert merchant, f"Merchant not found for public key '{event.pubkey}'"
        product_json = json.loads(event.content)

        assert "id" in product_json, "Product is missing ID"
        assert "stall_id" in product_json, "Product is missing Stall ID"

        
        product = Product(
            id=product_json["id"],
            stall_id=product_json["stall_id"],
            name=product_json.get("name", "Recoverd Product (no name)"),
            images=product_json.get("images", []),
            categories=event.tag_values("t"),
            price=product_json.get("price", 0),
            quantity=product_json.get("quantity", 0),
            pending=True,
            event_id = event.id,
            event_created_at = event.created_at
        )
        product.config.description = product_json.get("description", "")
        product.config.currency = product_json.get("currency", "sat")
        await create_product(merchant.id, product)
        
    except Exception as ex:
        logger.error(ex)
