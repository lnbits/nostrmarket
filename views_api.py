import json
from http import HTTPStatus
from typing import List, Optional

from fastapi import Depends
from fastapi.exceptions import HTTPException
from lnbits.core.services import websocket_updater
from lnbits.decorators import (
    WalletTypeInfo,
    require_admin_key,
    require_invoice_key,
)
from lnbits.utils.exchange_rates import currencies
from loguru import logger

from . import nostr_client, nostrmarket_ext
from .crud import (
    create_customer,
    create_direct_message,
    create_merchant,
    create_product,
    create_stall,
    create_zone,
    delete_merchant,
    delete_merchant_direct_messages,
    delete_merchant_orders,
    delete_merchant_products,
    delete_merchant_stalls,
    delete_merchant_zones,
    delete_product,
    delete_stall,
    delete_zone,
    get_customer,
    get_customers,
    get_direct_message_by_event_id,
    get_direct_messages,
    get_last_direct_messages_time,
    get_merchant_by_pubkey,
    get_merchant_for_user,
    get_order,
    get_order_by_event_id,
    get_orders,
    get_orders_for_stall,
    get_orders_from_direct_messages,
    get_product,
    get_products,
    get_stall,
    get_stalls,
    get_zone,
    get_zones,
    touch_merchant,
    update_customer_no_unread_messages,
    update_merchant,
    update_order,
    update_order_shipped_status,
    update_product,
    update_stall,
    update_zone,
)
from .helpers import normalize_public_key
from .models import (
    Customer,
    DirectMessage,
    DirectMessageType,
    Merchant,
    Order,
    OrderReissue,
    OrderStatusUpdate,
    PartialDirectMessage,
    PartialMerchant,
    PartialOrder,
    PaymentOption,
    PaymentRequest,
    Product,
    Stall,
    Zone,
)
from .services import (
    build_order_with_payment,
    create_or_update_order_from_dm,
    reply_to_structured_dm,
    resubscribe_to_all_merchants,
    sign_and_send_to_nostr,
    subscribe_to_all_merchants,
    update_merchant_to_nostr,
)

######################################## MERCHANT ######################################


@nostrmarket_ext.post("/api/v1/merchant")
async def api_create_merchant(
    data: PartialMerchant,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Merchant:

    try:
        merchant = await get_merchant_by_pubkey(data.public_key)
        assert merchant is None, "A merchant already uses this public key"

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant is None, "A merchant already exists for this user"

        merchant = await create_merchant(wallet.wallet.user, data)

        await create_zone(
            merchant.id,
            Zone(
                id=f"online-{merchant.public_key}",
                name="Online",
                currency="sat",
                cost=0,
                countries=["Free (digital)"],
            ),
        )

        await resubscribe_to_all_merchants()

        await nostr_client.merchant_temp_subscription(data.public_key)

        return merchant
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create merchant",
        ) from ex


@nostrmarket_ext.get("/api/v1/merchant")
async def api_get_merchant(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> Optional[Merchant]:

    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        if not merchant:
            return None

        merchant = await touch_merchant(wallet.wallet.user, merchant.id)
        assert merchant
        last_dm_time = await get_last_direct_messages_time(merchant.id)
        assert merchant.time
        merchant.config.restore_in_progress = (merchant.time - last_dm_time) < 30

        return merchant
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        ) from ex


@nostrmarket_ext.delete("/api/v1/merchant/{merchant_id}")
async def api_delete_merchant(
    merchant_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):

    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        assert merchant.id == merchant_id, "Wrong merchant ID"

        await nostr_client.unsubscribe_merchants()

        await delete_merchant_orders(merchant.id)
        await delete_merchant_products(merchant.id)
        await delete_merchant_stalls(merchant.id)
        await delete_merchant_direct_messages(merchant.id)
        await delete_merchant_zones(merchant.id)

        await delete_merchant(merchant.id)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        ) from ex
    finally:
        await subscribe_to_all_merchants()


@nostrmarket_ext.put("/api/v1/merchant/{merchant_id}/nostr")
async def api_republish_merchant(
    merchant_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        assert merchant.id == merchant_id, "Wrong merchant ID"

        merchant = await update_merchant_to_nostr(merchant)
        await update_merchant(wallet.wallet.user, merchant.id, merchant.config)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot republish to nostr",
        ) from ex


@nostrmarket_ext.get("/api/v1/merchant/{merchant_id}/nostr")
async def api_refresh_merchant(
    merchant_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        assert merchant.id == merchant_id, "Wrong merchant ID"

        await nostr_client.merchant_temp_subscription(merchant.public_key)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot refresh from nostr",
        ) from ex


@nostrmarket_ext.put("/api/v1/merchant/{merchant_id}/toggle")
async def api_toggle_merchant(
    merchant_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Merchant:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        assert merchant.id == merchant_id, "Wrong merchant ID"

        merchant.config.active = not merchant.config.active
        await update_merchant(wallet.wallet.user, merchant.id, merchant.config)

        return merchant
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        ) from ex


@nostrmarket_ext.delete("/api/v1/merchant/{merchant_id}/nostr")
async def api_delete_merchant_on_nostr(
    merchant_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        assert merchant.id == merchant_id, "Wrong merchant ID"

        merchant = await update_merchant_to_nostr(merchant, True)
        await update_merchant(wallet.wallet.user, merchant.id, merchant.config)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        ) from ex


######################################## ZONES ########################################


@nostrmarket_ext.get("/api/v1/zone")
async def api_get_zones(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> List[Zone]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        return await get_zones(merchant.id)
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get zone",
        ) from ex


@nostrmarket_ext.post("/api/v1/zone")
async def api_create_zone(
    data: Zone, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        zone = await create_zone(merchant.id, data)
        return zone
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create zone",
        ) from ex


@nostrmarket_ext.patch("/api/v1/zone/{zone_id}")
async def api_update_zone(
    data: Zone,
    zone_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Zone:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        zone = await get_zone(merchant.id, zone_id)
        if not zone:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Zone does not exist.",
            )
        zone = await update_zone(merchant.id, data)
        assert zone, "Cannot find updated zone"
        return zone
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex

    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update zone",
        ) from ex


@nostrmarket_ext.delete("/api/v1/zone/{zone_id}")
async def api_delete_zone(zone_id, wallet: WalletTypeInfo = Depends(require_admin_key)):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        zone = await get_zone(merchant.id, zone_id)

        if not zone:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Zone does not exist.",
            )

        await delete_zone(merchant.id, zone_id)
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete zone",
        ) from ex


######################################## STALLS ########################################


@nostrmarket_ext.post("/api/v1/stall")
async def api_create_stall(
    data: Stall,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Stall:
    try:
        # shipping_zones = await
        data.validate_stall()

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        stall = await create_stall(merchant.id, data=data)

        event = await sign_and_send_to_nostr(merchant, stall)

        stall.event_id = event.id
        await update_stall(merchant.id, stall)

        return stall

    except (ValueError, AssertionError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create stall",
        ) from ex


@nostrmarket_ext.put("/api/v1/stall/{stall_id}")
async def api_update_stall(
    data: Stall,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Stall:
    try:
        data.validate_stall()

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        stall = await update_stall(merchant.id, data)
        assert stall, "Cannot update stall"

        event = await sign_and_send_to_nostr(merchant, stall)

        stall.event_id = event.id
        await update_stall(merchant.id, stall)

        return stall

    except (ValueError, AssertionError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update stall",
        ) from ex


@nostrmarket_ext.get("/api/v1/stall/{stall_id}")
async def api_get_stall(
    stall_id: str, wallet: WalletTypeInfo = Depends(require_invoice_key)
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        stall = await get_stall(merchant.id, stall_id)
        if not stall:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Stall does not exist.",
            )
        return stall
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall",
        ) from ex


@nostrmarket_ext.get("/api/v1/stall")
async def api_get_stalls(
    pending: Optional[bool] = False,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        stalls = await get_stalls(merchant.id, pending)
        return stalls
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stalls",
        ) from ex


@nostrmarket_ext.get("/api/v1/stall/product/{stall_id}")
async def api_get_stall_products(
    stall_id: str,
    pending: Optional[bool] = False,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        products = await get_products(merchant.id, stall_id, pending)
        return products
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall products",
        ) from ex


@nostrmarket_ext.get("/api/v1/stall/order/{stall_id}")
async def api_get_stall_orders(
    stall_id: str,
    paid: Optional[bool] = None,
    shipped: Optional[bool] = None,
    pubkey: Optional[str] = None,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        orders = await get_orders_for_stall(
            merchant.id, stall_id, paid=paid, shipped=shipped, public_key=pubkey
        )
        return orders
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall products",
        ) from ex


@nostrmarket_ext.delete("/api/v1/stall/{stall_id}")
async def api_delete_stall(
    stall_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        stall = await get_stall(merchant.id, stall_id)
        if not stall:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Stall does not exist.",
            )

        await delete_stall(merchant.id, stall_id)

        event = await sign_and_send_to_nostr(merchant, stall, True)

        stall.event_id = event.id
        await update_stall(merchant.id, stall)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete stall",
        ) from ex


######################################## PRODUCTS ######################################


@nostrmarket_ext.post("/api/v1/product")
async def api_create_product(
    data: Product,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Product:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        stall = await get_stall(merchant.id, data.stall_id)
        assert stall, "Stall missing for product"
        data.config.currency = stall.currency

        product = await create_product(merchant.id, data=data)

        event = await sign_and_send_to_nostr(merchant, product)

        product.event_id = event.id
        await update_product(merchant.id, product)

        return product
    except (ValueError, AssertionError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create product",
        ) from ex


@nostrmarket_ext.patch("/api/v1/product/{product_id}")
async def api_update_product(
    product_id: str,
    product: Product,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Product:
    try:
        if product_id != product.id:
            raise ValueError("Bad product ID")

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        stall = await get_stall(merchant.id, product.stall_id)
        assert stall, "Stall missing for product"
        product.config.currency = stall.currency

        product = await update_product(merchant.id, product)
        event = await sign_and_send_to_nostr(merchant, product)
        product.event_id = event.id
        await update_product(merchant.id, product)

        return product
    except (ValueError, AssertionError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update product",
        ) from ex


@nostrmarket_ext.get("/api/v1/product/{product_id}")
async def api_get_product(
    product_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> Optional[Product]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        products = await get_product(merchant.id, product_id)
        return products
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get product",
        ) from ex


@nostrmarket_ext.delete("/api/v1/product/{product_id}")
async def api_delete_product(
    product_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        product = await get_product(merchant.id, product_id)
        if not product:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Product does not exist.",
            )

        await delete_product(merchant.id, product_id)
        await sign_and_send_to_nostr(merchant, product, True)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete product",
        ) from ex


######################################## ORDERS ########################################


@nostrmarket_ext.get("/api/v1/order/{order_id}")
async def api_get_order(
    order_id: str, wallet: WalletTypeInfo = Depends(require_invoice_key)
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        order = await get_order(merchant.id, order_id)
        if not order:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Order does not exist.",
            )
        return order
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get order",
        ) from ex


@nostrmarket_ext.get("/api/v1/order")
async def api_get_orders(
    paid: Optional[bool] = None,
    shipped: Optional[bool] = None,
    pubkey: Optional[str] = None,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        orders = await get_orders(
            merchant_id=merchant.id, paid=paid, shipped=shipped, public_key=pubkey
        )
        return orders
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get orders",
        ) from ex


@nostrmarket_ext.patch("/api/v1/order/{order_id}")
async def api_update_order_status(
    data: OrderStatusUpdate,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Order:
    try:
        assert data.shipped is not None, "Shipped value is required for order"
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found for order {data.id}"

        order = await update_order_shipped_status(merchant.id, data.id, data.shipped)
        assert order, "Cannot find updated order"

        data.paid = order.paid
        dm_content = json.dumps(
            {"type": DirectMessageType.ORDER_PAID_OR_SHIPPED.value, **data.dict()},
            separators=(",", ":"),
            ensure_ascii=False,
        )

        dm_event = merchant.build_dm_event(dm_content, order.public_key)

        dm = PartialDirectMessage(
            event_id=dm_event.id,
            event_created_at=dm_event.created_at,
            message=dm_content,
            public_key=order.public_key,
            type=DirectMessageType.ORDER_PAID_OR_SHIPPED.value,
        )
        await create_direct_message(merchant.id, dm)

        await nostr_client.publish_nostr_event(dm_event)
        await websocket_updater(
            merchant.id,
            json.dumps(
                {
                    "type": f"dm:{dm.type}",
                    "customerPubkey": order.public_key,
                    "dm": dm.dict(),
                }
            ),
        )

        return order

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update order",
        ) from ex


@nostrmarket_ext.put("/api/v1/order/restore/{event_id}")
async def api_restore_order(
    event_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Optional[Order]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        dm = await get_direct_message_by_event_id(merchant.id, event_id)
        assert dm, "Canot find direct message"

        await create_or_update_order_from_dm(merchant.id, merchant.public_key, dm)

        return await get_order_by_event_id(merchant.id, event_id)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot restore order",
        ) from ex


@nostrmarket_ext.put("/api/v1/orders/restore")
async def api_restore_orders(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> None:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        dms = await get_orders_from_direct_messages(merchant.id)
        for dm in dms:
            try:
                await create_or_update_order_from_dm(
                    merchant.id, merchant.public_key, dm
                )
            except Exception as e:
                logger.debug(
                    f"Failed to restore order from event '{dm.event_id}': '{e!s}'."
                )

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot restore orders",
        ) from ex


@nostrmarket_ext.put("/api/v1/order/reissue")
async def api_reissue_order_invoice(
    reissue_data: OrderReissue,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Order:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        data = await get_order(merchant.id, reissue_data.id)
        assert data, "Order cannot be found"

        if reissue_data.shipping_id:
            data.shipping_id = reissue_data.shipping_id

        order, invoice, receipt = await build_order_with_payment(
            merchant.id, merchant.public_key, PartialOrder(**data.dict())
        )

        order_update = {
            "stall_id": order.stall_id,
            "total": order.total,
            "invoice_id": order.invoice_id,
            "shipping_id": order.shipping_id,
            "extra_data": json.dumps(order.extra.dict()),
        }

        await update_order(
            merchant.id,
            order.id,
            **order_update,
        )
        payment_req = PaymentRequest(
            id=data.id,
            payment_options=[PaymentOption(type="ln", link=invoice)],
            message=receipt,
        )
        response = {
            "type": DirectMessageType.PAYMENT_REQUEST.value,
            **payment_req.dict(),
        }
        dm_reply = json.dumps(response, separators=(",", ":"), ensure_ascii=False)

        await reply_to_structured_dm(
            merchant,
            order.public_key,
            DirectMessageType.PAYMENT_REQUEST.value,
            dm_reply,
        )

        return order
    except (AssertionError, ValueError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot reissue order invoice",
        ) from ex


######################################## DIRECT MESSAGES ###############################


@nostrmarket_ext.get("/api/v1/message/{public_key}")
async def api_get_messages(
    public_key: str, wallet: WalletTypeInfo = Depends(require_invoice_key)
) -> List[DirectMessage]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        messages = await get_direct_messages(merchant.id, public_key)
        await update_customer_no_unread_messages(merchant.id, public_key)
        return messages
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get direct message",
        ) from ex


@nostrmarket_ext.post("/api/v1/message")
async def api_create_message(
    data: PartialDirectMessage, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> DirectMessage:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        dm_event = merchant.build_dm_event(data.message, data.public_key)
        data.event_id = dm_event.id
        data.event_created_at = dm_event.created_at

        dm = await create_direct_message(merchant.id, data)
        await nostr_client.publish_nostr_event(dm_event)

        return dm
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create message",
        ) from ex


######################################## CUSTOMERS #####################################


@nostrmarket_ext.get("/api/v1/customer")
async def api_get_customers(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> List[Customer]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        return await get_customers(merchant.id)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create message",
        ) from ex


@nostrmarket_ext.post("/api/v1/customer")
async def api_create_customer(
    data: Customer,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Customer:

    try:
        pubkey = normalize_public_key(data.public_key)

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "A merchant does not exists for this user"
        assert merchant.id == data.merchant_id, "Invalid merchant id for user"

        existing_customer = await get_customer(merchant.id, pubkey)
        assert existing_customer is None, "This public key already exists"

        customer = await create_customer(
            merchant.id, Customer(merchant_id=merchant.id, public_key=pubkey)
        )

        await nostr_client.user_profile_temp_subscribe(pubkey)

        return customer
    except (ValueError, AssertionError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create customer",
        ) from ex


######################################## OTHER ########################################


@nostrmarket_ext.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@nostrmarket_ext.put("/api/v1/restart")
async def restart_nostr_client(wallet: WalletTypeInfo = Depends(require_admin_key)):
    try:
        await nostr_client.restart()
    except Exception as ex:
        logger.warning(ex)
