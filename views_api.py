import json
from http import HTTPStatus
from typing import List, Optional

from fastapi import Depends
from fastapi.exceptions import HTTPException
from loguru import logger

from lnbits.decorators import (
    WalletTypeInfo,
    check_admin,
    get_key_type,
    require_admin_key,
    require_invoice_key,
)
from lnbits.utils.exchange_rates import currencies

from . import nostrmarket_ext, scheduled_tasks
from .crud import (
    create_direct_message,
    create_merchant,
    create_product,
    create_stall,
    create_zone,
    delete_merchant_zones,
    delete_product,
    delete_stall,
    delete_zone,
    get_direct_messages,
    get_merchant_for_user,
    get_order,
    get_orders,
    get_orders_for_stall,
    get_product,
    get_products,
    get_stall,
    get_stalls,
    get_zone,
    get_zones,
    update_order_shipped_status,
    update_product,
    update_stall,
    update_zone,
)
from .models import (
    DirectMessage,
    Merchant,
    Order,
    OrderStatusUpdate,
    PartialDirectMessage,
    PartialMerchant,
    PartialProduct,
    PartialStall,
    PartialZone,
    Product,
    Stall,
    Zone,
)
from .nostr.nostr_client import publish_nostr_event
from .services import sign_and_send_to_nostr

######################################## MERCHANT ########################################


@nostrmarket_ext.post("/api/v1/merchant")
async def api_create_merchant(
    data: PartialMerchant,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Merchant:

    try:
        merchant = await create_merchant(wallet.wallet.user, data)

        return merchant
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create merchant",
        )


@nostrmarket_ext.get("/api/v1/merchant")
async def api_get_merchant(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> Optional[Merchant]:

    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        return merchant
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        )


@nostrmarket_ext.delete("/api/v1/merchant")
async def api_delete_merchant(
    wallet: WalletTypeInfo = Depends(require_admin_key),
):

    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        await delete_merchant_zones(wallet.wallet.user)
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        )


######################################## ZONES ########################################


@nostrmarket_ext.get("/api/v1/zone")
async def api_get_zones(wallet: WalletTypeInfo = Depends(get_key_type)) -> List[Zone]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        return await get_zones(merchant.id)
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get zone",
        )


@nostrmarket_ext.post("/api/v1/zone")
async def api_create_zone(
    data: PartialZone, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        zone = await create_zone(merchant.id, data)
        return zone
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create zone",
        )


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
        zone = await update_zone(wallet.wallet.user, data)
        assert zone, "Cannot find updated zone"
        return zone
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update zone",
        )


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

        await delete_zone(wallet.wallet.user, zone_id)

    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete zone",
        )


######################################## STALLS ########################################


@nostrmarket_ext.post("/api/v1/stall")
async def api_create_stall(
    data: PartialStall,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Stall:
    try:
        data.validate_stall()

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        stall = await create_stall(merchant.id, data=data)

        event = await sign_and_send_to_nostr(merchant, stall)

        stall.config.event_id = event.id
        await update_stall(merchant.id, stall)

        return stall
    except ValueError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create stall",
        )


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

        stall.config.event_id = event.id
        await update_stall(merchant.id, stall)

        return stall
    except HTTPException as ex:
        raise ex
    except ValueError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update stall",
        )


@nostrmarket_ext.get("/api/v1/stall/{stall_id}")
async def api_get_stall(stall_id: str, wallet: WalletTypeInfo = Depends(get_key_type)):
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
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall",
        )


@nostrmarket_ext.get("/api/v1/stall")
async def api_get_stalls(wallet: WalletTypeInfo = Depends(get_key_type)):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        stalls = await get_stalls(merchant.id)
        return stalls
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stalls",
        )


@nostrmarket_ext.get("/api/v1/stall/product/{stall_id}")
async def api_get_stall_products(
    stall_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        products = await get_products(merchant.id, stall_id)
        return products
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall products",
        )


@nostrmarket_ext.get("/api/v1/stall/order/{stall_id}")
async def api_get_stall_orders(
    stall_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        orders = await get_orders_for_stall(merchant.id, stall_id)
        return orders
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall products",
        )


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

        stall.config.event_id = event.id
        await update_stall(merchant.id, stall)

    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete stall",
        )


######################################## PRODUCTS ########################################


@nostrmarket_ext.post("/api/v1/product")
async def api_create_product(
    data: PartialProduct,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Product:
    try:
        data.validate_product()
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        stall = await get_stall(merchant.id, data.stall_id)
        assert stall, "Stall missing for product"
        data.config.currency = stall.currency

        product = await create_product(merchant.id, data=data)

        event = await sign_and_send_to_nostr(merchant, product)

        product.config.event_id = event.id
        await update_product(merchant.id, product)

        return product
    except ValueError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create product",
        )


@nostrmarket_ext.patch("/api/v1/product/{product_id}")
async def api_update_product(
    product_id: str,
    product: Product,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Product:
    try:
        if product_id != product.id:
            raise ValueError("Bad product ID")

        product.validate_product()
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        stall = await get_stall(merchant.id, product.stall_id)
        assert stall, "Stall missing for product"
        product.config.currency = stall.currency

        product = await update_product(merchant.id, product)

        event = await sign_and_send_to_nostr(merchant, product)

        product.config.event_id = event.id
        await update_product(merchant.id, product)

        return product
    except ValueError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update product",
        )


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
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get product",
        )


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

    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete product",
        )


######################################## ORDERS ########################################


nostrmarket_ext.get("/api/v1/order/{order_id}")


async def api_get_order(order_id: str, wallet: WalletTypeInfo = Depends(get_key_type)):
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
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get order",
        )


@nostrmarket_ext.get("/api/v1/order")
async def api_get_orders(wallet: WalletTypeInfo = Depends(get_key_type)):
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        orders = await get_orders(merchant.id)
        return orders
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get orders",
        )


@nostrmarket_ext.patch("/api/v1/order/{order_id}")
async def api_update_order_status(
    data: OrderStatusUpdate,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Order:
    try:
        assert data.shipped != None, "Shipped value is required for order"
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"

        order = await update_order_shipped_status(merchant.id, data.id, data.shipped)
        assert order, "Cannot find updated order"

        merchant = await get_merchant_for_user(merchant.id)
        assert merchant, f"Merchant cannot be found for order {data.id}"

        data.paid = order.paid
        dm_content = json.dumps(data.dict(), separators=(",", ":"), ensure_ascii=False)

        dm_event = merchant.build_dm_event(dm_content, order.public_key)
        await publish_nostr_event(dm_event)

        return order

    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update order",
        )


######################################## DIRECT MESSAGES ########################################


@nostrmarket_ext.get("/api/v1/message/{public_key}")
async def api_get_messages(
    public_key: str, wallet: WalletTypeInfo = Depends(get_key_type)
) -> List[DirectMessage]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, f"Merchant cannot be found"

        messages = await get_direct_messages(merchant.id, public_key)
        return messages
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get direct message",
        )


@nostrmarket_ext.post("/api/v1/message")
async def api_create_message(
    data: PartialDirectMessage, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> DirectMessage:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, f"Merchant cannot be found"

        dm_event = merchant.build_dm_event(data.message, data.public_key)
        data.event_id = dm_event.id
        data.event_created_at = dm_event.created_at

        dm = await create_direct_message(merchant.id, data)
        await publish_nostr_event(dm_event)

        return dm
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create message",
        )


######################################## OTHER ########################################


@nostrmarket_ext.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@nostrmarket_ext.delete("/api/v1", status_code=HTTPStatus.OK)
async def api_stop(wallet: WalletTypeInfo = Depends(check_admin)):
    for t in scheduled_tasks:
        try:
            t.cancel()
        except Exception as ex:
            logger.warning(ex)

    return {"success": True}
