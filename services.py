import asyncio
import json
from typing import List, Optional, Tuple

from lnbits.bolt11 import decode
from lnbits.core.crud import get_wallet
from lnbits.core.services import create_invoice, websocket_updater
from loguru import logger

from . import nostr_client
from .crud import (
    CustomerProfile,
    create_customer,
    create_direct_message,
    create_order,
    create_product,
    create_stall,
    get_customer,
    get_last_direct_messages_created_at,
    get_last_product_update_time,
    get_last_stall_update_time,
    get_merchant_by_pubkey,
    get_merchants_ids_with_pubkeys,
    get_order,
    get_order_by_event_id,
    get_products,
    get_products_by_ids,
    get_stalls,
    get_wallet_for_product,
    get_zone,
    increment_customer_unread_messages,
    update_customer_profile,
    update_order,
    update_order_paid_status,
    update_order_shipped_status,
    update_product,
    update_product_quantity,
    update_stall,
)
from .models import (
    Customer,
    DirectMessage,
    DirectMessageType,
    Merchant,
    Nostrable,
    Order,
    OrderContact,
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

    order, invoice, receipt = await build_order_with_payment(
        merchant.id, merchant.public_key, data
    )
    await create_order(merchant.id, order)

    return PaymentRequest(
        id=data.id,
        payment_options=[PaymentOption(type="ln", link=invoice)],
        message=receipt,
    )


async def build_order_with_payment(
    merchant_id: str, merchant_public_key: str, data: PartialOrder
):
    products = await get_products_by_ids(
        merchant_id, [p.product_id for p in data.items]
    )
    data.validate_order_items(products)
    shipping_zone = await get_zone(merchant_id, data.shipping_id)
    assert shipping_zone, f"Shipping zone not found for order '{data.id}'"

    assert shipping_zone.id
    product_cost_sat, shipping_cost_sat = await data.costs_in_sats(
        products, shipping_zone.id, shipping_zone.cost
    )
    receipt = data.receipt(products, shipping_zone.id, shipping_zone.cost)

    wallet_id = await get_wallet_for_product(data.items[0].product_id)
    assert wallet_id, "Missing wallet for order `{data.id}`"

    product_ids = [i.product_id for i in data.items]
    success, _, message = await compute_products_new_quantity(
        merchant_id, product_ids, data.items
    )
    if not success:
        raise ValueError(message)

    payment = await create_invoice(
        wallet_id=wallet_id,
        amount=round(product_cost_sat + shipping_cost_sat),
        memo=f"Order '{data.id}' for pubkey '{data.public_key}'",
        extra={
            "tag": "nostrmarket",
            "order_id": data.id,
            "merchant_pubkey": merchant_public_key,
        },
    )

    extra = await OrderExtra.from_products(products)
    extra.shipping_cost_sat = shipping_cost_sat
    extra.shipping_cost = shipping_zone.cost

    order = Order(
        **data.dict(),
        stall_id=products[0].stall_id,
        invoice_id=payment.payment_hash,
        total=product_cost_sat + shipping_cost_sat,
        extra=extra,
    )

    return order, payment.bolt11, receipt


async def update_merchant_to_nostr(
    merchant: Merchant, delete_merchant=False
) -> Merchant:
    stalls = await get_stalls(merchant.id)
    event: Optional[NostrEvent] = None
    for stall in stalls:
        assert stall.id
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
    assert event
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

        await autoreply_for_products_in_order(merchant, order)

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
            {
                "type": DirectMessageType.ORDER_PAID_OR_SHIPPED.value,
                **order_status.dict(),
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )
    else:
        dm_content = f"Order cannot be fulfilled. Reason: {message}"

    dm_type = (
        DirectMessageType.ORDER_PAID_OR_SHIPPED.value
        if success
        else DirectMessageType.PLAIN_TEXT.value
    )
    await send_dm(merchant, order.public_key, dm_type, dm_content)


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
        assert p.id
        product = await update_product_quantity(p.id, p.quantity)
        assert product
        event = await sign_and_send_to_nostr(merchant, product)
        product.event_id = event.id
        await update_product(merchant.id, product)

    return True, "ok"


async def autoreply_for_products_in_order(merchant: Merchant, order: Order):
    product_ids = [i.product_id for i in order.items]

    products = await get_products_by_ids(merchant.id, product_ids)
    products_with_autoreply = [p for p in products if p.config.use_autoreply]

    for p in products_with_autoreply:
        dm_content = p.config.autoreply_message or ""
        await send_dm(
            merchant,
            order.public_key,
            DirectMessageType.PLAIN_TEXT.value,
            dm_content,
        )
        await asyncio.sleep(1)  # do not send all autoreplies at once


async def send_dm(
    merchant: Merchant,
    other_pubkey: str,
    type_: int,
    dm_content: str,
):
    dm_event = merchant.build_dm_event(dm_content, other_pubkey)

    dm = PartialDirectMessage(
        event_id=dm_event.id,
        event_created_at=dm_event.created_at,
        message=dm_content,
        public_key=other_pubkey,
        type=type_,
    )
    dm_reply = await create_direct_message(merchant.id, dm)

    await nostr_client.publish_nostr_event(dm_event)

    await websocket_updater(
        merchant.id,
        json.dumps(
            {
                "type": f"dm:{dm.type}",
                "customerPubkey": other_pubkey,
                "dm": dm_reply.dict(),
            }
        ),
    )


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
                f"Quantity not sufficient for product: '{p.name}' ({p.id})."
                f" Required '{required_quantity}' but only have '{p.quantity}'.",
            )

        p.quantity -= required_quantity

    return True, products, "ok"


async def process_nostr_message(msg: str):
    try:
        type_, *rest = json.loads(msg)

        if type_.upper() == "EVENT":
            _, event = rest
            event = NostrEvent(**event)
            if event.kind == 0:
                await _handle_customer_profile_update(event)
            elif event.kind == 4:
                await _handle_nip04_message(event)
            elif event.kind == 30017:
                await _handle_stall(event)
            elif event.kind == 30018:
                await _handle_product(event)
            return

    except Exception as ex:
        logger.debug(ex)


async def create_or_update_order_from_dm(
    merchant_id: str, merchant_pubkey: str, dm: DirectMessage
):
    type_, json_data = PartialDirectMessage.parse_message(dm.message)
    if not json_data or "id" not in json_data:
        return

    if type_ == DirectMessageType.CUSTOMER_ORDER:
        order = await extract_customer_order_from_dm(
            merchant_id, merchant_pubkey, dm, json_data
        )
        new_order = await create_order(merchant_id, order)
        if new_order.stall_id == "None" and order.stall_id != "None":
            await update_order(
                merchant_id,
                order.id,
                **{
                    "stall_id": order.stall_id,
                    "extra_data": json.dumps(order.extra.dict()),
                },
            )
        return

    if type_ == DirectMessageType.PAYMENT_REQUEST:
        payment_request = PaymentRequest(**json_data)
        pr = next(
            (o.link for o in payment_request.payment_options if o.type == "ln"), None
        )
        if not pr:
            return
        invoice = decode(pr)
        total = invoice.amount_msat / 1000 if invoice.amount_msat else 0
        await update_order(
            merchant_id,
            payment_request.id,
            **{"total": total, "invoice_id": invoice.payment_hash},
        )
        return

    if type_ == DirectMessageType.ORDER_PAID_OR_SHIPPED:
        order_update = OrderStatusUpdate(**json_data)
        if order_update.paid:
            await update_order_paid_status(order_update.id, True)
        if order_update.shipped:
            await update_order_shipped_status(merchant_id, order_update.id, True)


async def extract_customer_order_from_dm(
    merchant_id: str, merchant_pubkey: str, dm: DirectMessage, json_data: dict
) -> Order:
    order_items = [OrderItem(**i) for i in json_data.get("items", [])]
    products = await get_products_by_ids(
        merchant_id, [p.product_id for p in order_items]
    )
    extra = await OrderExtra.from_products(products)
    order = Order(
        id=str(json_data.get("id")),
        event_id=dm.event_id,
        event_created_at=dm.event_created_at,
        public_key=dm.public_key,
        merchant_public_key=merchant_pubkey,
        shipping_id=json_data.get("shipping_id", "None"),
        items=order_items,
        contact=(
            OrderContact(**json_data.get("contact", {}))
            if json_data.get("contact")
            else None
        ),
        address=json_data.get("address"),
        stall_id=products[0].stall_id if len(products) else "None",
        invoice_id="None",
        total=0,
        extra=extra,
    )

    return order


async def _handle_nip04_message(event: NostrEvent):
    merchant_public_key = event.pubkey
    merchant = await get_merchant_by_pubkey(merchant_public_key)

    if not merchant:
        p_tags = event.tag_values("p")
        if len(p_tags) and p_tags[0]:
            merchant_public_key = p_tags[0]
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
        await increment_customer_unread_messages(merchant.id, event.pubkey)

    dm_type, json_data = PartialDirectMessage.parse_message(clear_text_msg)
    new_dm = await _persist_dm(
        merchant.id,
        dm_type.value,
        event.pubkey,
        event.id,
        event.created_at,
        clear_text_msg,
    )

    if json_data:
        reply_type, dm_reply = await _handle_incoming_structured_dm(
            merchant, new_dm, json_data
        )
        if dm_reply:
            await reply_to_structured_dm(
                merchant, event.pubkey, reply_type.value, dm_reply
            )


async def _handle_outgoing_dms(
    event: NostrEvent, merchant: Merchant, clear_text_msg: str
):
    sent_to = event.tag_values("p")
    type_, _ = PartialDirectMessage.parse_message(clear_text_msg)
    if len(sent_to) != 0:
        dm = PartialDirectMessage(
            event_id=event.id,
            event_created_at=event.created_at,
            message=clear_text_msg,
            public_key=sent_to[0],
            type=type_.value,
        )
        await create_direct_message(merchant.id, dm)


async def _handle_incoming_structured_dm(
    merchant: Merchant, dm: DirectMessage, json_data: dict
) -> Tuple[DirectMessageType, Optional[str]]:
    try:
        if dm.type == DirectMessageType.CUSTOMER_ORDER.value and merchant.config.active:
            json_resp = await _handle_new_order(
                merchant.id, merchant.public_key, dm, json_data
            )

            return DirectMessageType.PAYMENT_REQUEST, json_resp

    except Exception as ex:
        logger.warning(ex)

    return DirectMessageType.PLAIN_TEXT, None


async def _persist_dm(
    merchant_id: str,
    dm_type: int,
    from_pubkey: str,
    event_id: str,
    event_created_at: int,
    msg: str,
) -> DirectMessage:
    dm = PartialDirectMessage(
        event_id=event_id,
        event_created_at=event_created_at,
        message=msg,
        public_key=from_pubkey,
        incoming=True,
        type=dm_type,
    )
    new_dm = await create_direct_message(merchant_id, dm)

    await websocket_updater(
        merchant_id,
        json.dumps(
            {
                "type": f"dm:{dm_type}",
                "customerPubkey": from_pubkey,
                "dm": new_dm.dict(),
            }
        ),
    )
    return new_dm


async def reply_to_structured_dm(
    merchant: Merchant, customer_pubkey: str, dm_type: int, dm_reply: str
):
    dm_event = merchant.build_dm_event(dm_reply, customer_pubkey)
    dm = PartialDirectMessage(
        event_id=dm_event.id,
        event_created_at=dm_event.created_at,
        message=dm_reply,
        public_key=customer_pubkey,
        type=dm_type,
    )
    await create_direct_message(merchant.id, dm)
    await nostr_client.publish_nostr_event(dm_event)

    await websocket_updater(
        merchant.id,
        json.dumps(
            {"type": f"dm:{dm_type}", "customerPubkey": dm.public_key, "dm": dm.dict()}
        ),
    )


async def _handle_new_order(
    merchant_id: str, merchant_public_key: str, dm: DirectMessage, json_data: dict
) -> str:

    partial_order = PartialOrder(
        **{
            **json_data,
            "merchant_public_key": merchant_public_key,
            "public_key": dm.public_key,
            "event_id": dm.event_id,
            "event_created_at": dm.event_created_at,
        }
    )
    partial_order.validate_order()

    try:
        first_product_id = partial_order.items[0].product_id
        wallet_id = await get_wallet_for_product(first_product_id)
        assert wallet_id, f"Cannot find wallet id for product id: {first_product_id}"

        wallet = await get_wallet(wallet_id)
        assert wallet, f"Cannot find wallet for product id: {first_product_id}"

        payment_req = await create_new_order(merchant_public_key, partial_order)
    except Exception as e:
        logger.debug(e)
        payment_req = await create_new_failed_order(
            merchant_id,
            merchant_public_key,
            dm,
            json_data,
            "Order received, but cannot be processed. Please contact merchant.",
        )
    assert payment_req
    response = {
        "type": DirectMessageType.PAYMENT_REQUEST.value,
        **payment_req.dict(),
    }
    return json.dumps(response, separators=(",", ":"), ensure_ascii=False)


async def create_new_failed_order(
    merchant_id: str,
    merchant_public_key: str,
    dm: DirectMessage,
    json_data: dict,
    fail_message: str,
) -> PaymentRequest:
    order = await extract_customer_order_from_dm(
        merchant_id, merchant_public_key, dm, json_data
    )
    order.extra.fail_message = fail_message
    await create_order(merchant_id, order)
    return PaymentRequest(id=order.id, message=fail_message, payment_options=[])


async def resubscribe_to_all_merchants():
    await nostr_client.unsubscribe_merchants()
    # give some time for the message to propagate
    await asyncio.sleep(1)
    await subscribe_to_all_merchants()


async def subscribe_to_all_merchants():
    ids = await get_merchants_ids_with_pubkeys()
    public_keys = [pk for _, pk in ids]

    last_dm_time = await get_last_direct_messages_created_at()
    last_stall_time = await get_last_stall_update_time()
    last_prod_time = await get_last_product_update_time()

    await nostr_client.subscribe_merchants(
        public_keys, last_dm_time, last_stall_time, last_prod_time, 0
    )


async def _handle_new_customer(event: NostrEvent, merchant: Merchant):
    await create_customer(
        merchant.id, Customer(merchant_id=merchant.id, public_key=event.pubkey)
    )
    await nostr_client.user_profile_temp_subscribe(event.pubkey)


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
            event_id=event.id,
            event_created_at=event.created_at,
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
            event_id=event.id,
            event_created_at=event.created_at,
        )
        product.config.description = product_json.get("description", "")
        product.config.currency = product_json.get("currency", "sat")
        await create_product(merchant.id, product)

    except Exception as ex:
        logger.error(ex)
