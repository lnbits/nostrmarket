import json
from typing import List, Optional, Tuple

from loguru import logger

from lnbits.bolt11 import decode
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
            {"type": DirectMessageType.ORDER_PAID_OR_SHIPPED.value, **order_status.dict()},
            separators=(",", ":"),
            ensure_ascii=False,
        )
    else:
        dm_content = f"Order cannot be fulfilled. Reason: {message}"

    dm_event = merchant.build_dm_event(dm_content, order.public_key)

    dm = PartialDirectMessage(
        event_id=dm_event.id,
        event_created_at=dm_event.created_at,
        message=dm_content,
        public_key=order.public_key,
        type=DirectMessageType.ORDER_PAID_OR_SHIPPED.value
        if success
        else DirectMessageType.PLAIN_TEXT.value,
    )
    dm_reply = await create_direct_message(merchant.id, dm)

    await nostr_client.publish_nostr_event(dm_event)

    await websocketUpdater(
        merchant.id,
        json.dumps({ "type": f"dm:{dm.type}", "customerPubkey": order.public_key, "dm": dm_reply.dict() }),
    )


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
            print("kind: ", event.kind, ":     ", msg)
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


async def create_or_update_order_from_dm(merchant_id: str, merchant_pubkey: str, dm: DirectMessage):
    type, value = PartialDirectMessage.parse_message(dm.message)
    if "id" not in value:
        return
    
    if type == DirectMessageType.CUSTOMER_ORDER:
        order = await extract_order_from_dm(merchant_id, merchant_pubkey, dm, value)
        new_order = await create_order(merchant_id, order)
        if new_order.stall_id == "None" and order.stall_id != "None":
            await update_order(merchant_id, order.id, **{
                "stall_id": order.stall_id,
                "extra_data": json.dumps(order.extra.dict())
            })
        return
    
    if type == DirectMessageType.PAYMENT_REQUEST:
        payment_request = PaymentRequest(**value)
        pr = next((o.link for o in payment_request.payment_options if o.type == "ln"), None)
        if not pr:
            return
        invoice = decode(pr)
        await update_order(merchant_id, payment_request.id, **{
            "total": invoice.amount_msat / 1000,
            "invoice_id": invoice.payment_hash
        })
        return
    
    if type == DirectMessageType.ORDER_PAID_OR_SHIPPED:
        order_update = OrderStatusUpdate(**value)
        if order_update.paid:
            await update_order_paid_status(order_update.id, True)
        if order_update.shipped:
            await update_order_shipped_status(merchant_id, order_update.id, True)


async def extract_order_from_dm(merchant_id: str, merchant_pubkey: str, dm: DirectMessage, value):
    order_items = [OrderItem(**i) for i in value.get("items", [])]
    products = await get_products_by_ids(merchant_id, [p.product_id for p in order_items])
    extra = await OrderExtra.from_products(products)
    order = Order(
                    id=value.get("id"),
                    event_id=dm.event_id,
                    event_created_at=dm.event_created_at,
                    public_key=dm.public_key,
                    merchant_public_key=merchant_pubkey,
                    shipping_id=value.get("shipping_id", "None"),
                    items=order_items,
                    contact=OrderContact(**value.get("contact")) if value.get("contact") else None,
                    address=value.get("address"),
                    stall_id=products[0].stall_id if len(products) else "None",
                    invoice_id="None",
                    total=0,
                    extra=extra
                )
    
    return order


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
        await increment_customer_unread_messages(merchant.id, event.pubkey)

    dm_type, json_data = PartialDirectMessage.parse_message(clear_text_msg)
    new_dm = await _persist_dm(merchant.id, dm_type.value, event.pubkey, event.id, event.created_at, clear_text_msg)

    if json_data:
        reply_type, dm_reply = await _handle_incoming_structured_dm(merchant, new_dm, json_data)
        if dm_reply:
            await _reply_to_structured_dm(merchant, event, reply_type.value, dm_reply)


async def _handle_outgoing_dms(
    event: NostrEvent, merchant: Merchant, clear_text_msg: str
):
    sent_to = event.tag_values("p")
    type, _ = PartialDirectMessage.parse_message(clear_text_msg)
    if len(sent_to) != 0:
        dm = PartialDirectMessage(
            event_id=event.id,
            event_created_at=event.created_at,
            message=clear_text_msg,
            public_key=sent_to[0],
            type=type.value
        )
        await create_direct_message(merchant.id, dm)


async def _handle_incoming_structured_dm(merchant: Merchant, dm: DirectMessage, json_data) -> Tuple[DirectMessageType, Optional[str]]:
    try:
        if dm.type == DirectMessageType.CUSTOMER_ORDER.value and merchant.config.active:
            json_data["public_key"] = dm.public_key
            json_data["merchant_public_key"] = merchant.public_key
            json_data["event_id"] = dm.event_id
            json_data["event_created_at"] = dm.event_created_at

            json_data = await _handle_new_order(PartialOrder(**json_data))
            return DirectMessageType.PAYMENT_REQUEST, json_data

        return None
    except Exception as ex:
        logger.warning(ex)
        return None


async def _persist_dm(merchant_id: str, dm_type: int, from_pubkey:str, event_id:str, event_created_at: int, msg: str) -> DirectMessage:
    dm = PartialDirectMessage(
            event_id=event_id,
            event_created_at=event_created_at,
            message=msg,
            public_key=from_pubkey,
            incoming=True,
            type=dm_type,
        )
    new_dm = await create_direct_message(merchant_id, dm)

    await websocketUpdater(
        merchant_id,
        json.dumps({"type": f"dm:{dm_type}", "customerPubkey": from_pubkey, "dm": new_dm.dict()}),
    )
    return new_dm

async def _reply_to_structured_dm(merchant: Merchant, event: NostrEvent, dm_type: int, dm_reply: str):
    dm_event = merchant.build_dm_event(dm_reply, event.pubkey)
    dm = PartialDirectMessage(
            event_id=dm_event.id,
            event_created_at=dm_event.created_at,
            message=dm_reply,
            public_key=event.pubkey,
            type=dm_type,
        )
    await create_direct_message(merchant.id, dm)
    await nostr_client.publish_nostr_event(dm_event)

    await websocketUpdater(
        merchant.id,
        json.dumps({ "type": f"dm:{dm_type}", "customerPubkey": dm.public_key, "dm": dm.dict() }),
    )



async def _handle_new_order(order: PartialOrder) -> Optional[str]:
    order.validate_order()

    try:
        first_product_id = order.items[0].product_id
        wallet_id = await get_wallet_for_product(first_product_id)
        assert wallet_id, f"Cannot find wallet id for product id: {first_product_id}"

        wallet = await get_wallet(wallet_id)
        assert wallet, f"Cannot find wallet for product id: {first_product_id}"

        
        payment_req = await create_new_order(order.merchant_public_key, order)
    except Exception as e:
        payment_req = PaymentRequest(id=order.id, message=str(e), payment_options=[])

    if payment_req:
        response = {"type": DirectMessageType.PAYMENT_REQUEST.value, **payment_req.dict()}
        return json.dumps(response, separators=(",", ":"), ensure_ascii=False)
    
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
