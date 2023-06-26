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

from . import nostr_client, nostrmarket_ext, scheduled_tasks
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
    get_direct_messages,
    get_merchant_by_pubkey,
    get_merchant_for_user,
    get_merchants_ids_with_pubkeys,
    get_order,
    get_orders,
    get_orders_for_stall,
    get_product,
    get_products,
    get_stall,
    get_stalls,
    get_zone,
    get_zones,
    update_customer_no_unread_messages,
    update_merchant,
    update_order_shipped_status,
    update_product,
    update_stall,
    update_zone,
)
from .helpers import normalize_public_key
from .models import (
    Customer,
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
from .services import sign_and_send_to_nostr, update_merchant_to_nostr

######################################## MERCHANT ########################################


@nostrmarket_ext.post("/api/v1/merchant")
async def api_create_merchant(
    data: PartialMerchant,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Merchant:

    try:
        merchant = await get_merchant_by_pubkey(data.public_key)
        assert merchant == None, "A merchant already uses this public key"

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant == None, "A merchant already exists for this user"

        merchant = await create_merchant(wallet.wallet.user, data)

        await nostr_client.subscribe_to_stall_events(data.public_key, 0)
        await nostr_client.subscribe_to_product_events(data.public_key, 0)
        await nostr_client.subscribe_to_direct_messages(data.public_key, 0)

        return merchant
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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


@nostrmarket_ext.delete("/api/v1/merchant/{merchant_id}")
async def api_delete_merchant(
    merchant_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):

    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Merchant cannot be found"
        assert merchant.id == merchant_id, "Wrong merchant ID"

        await delete_merchant_orders(merchant.id)
        await delete_merchant_products(merchant.id)
        await delete_merchant_stalls(merchant.id)
        await delete_merchant_direct_messages(merchant.id)
        await delete_merchant_zones(merchant.id)

        await nostr_client.unsubscribe_from_direct_messages(merchant.public_key)
        await nostr_client.unsubscribe_from_merchant_events(merchant.public_key)
        await delete_merchant(merchant.id)
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        )


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
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get merchant",
        )


@nostrmarket_ext.delete("/api/v1/merchant/{merchant_id}/nostr")
async def api_delete_merchant(
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
        )
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
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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
        zone = await update_zone(merchant.id, data)
        assert zone, "Cannot find updated zone"
        return zone
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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

        await delete_zone(merchant.id, zone_id)
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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

        stall.event_id = event.id
        await update_stall(merchant.id, stall)

        return stall
    except HTTPException as ex:
        raise ex
    except (ValueError, AssertionError) as ex:
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
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall",
        )


@nostrmarket_ext.get("/api/v1/stall")
async def api_get_stalls(
    pending: Optional[bool] = False, wallet: WalletTypeInfo = Depends(get_key_type)
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
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stalls",
        )


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
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get stall products",
        )


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
        )
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

        stall.event_id = event.id
        await update_stall(merchant.id, stall)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete product",
        )


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
        )
    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot get order",
        )


@nostrmarket_ext.get("/api/v1/order")
async def api_get_orders(
    paid: Optional[bool] = None,
    shipped: Optional[bool] = None,
    pubkey: Optional[str] = None,
    wallet: WalletTypeInfo = Depends(get_key_type),
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
        )
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
        assert merchant, "Merchant cannot be found for order {data.id}"

        order = await update_order_shipped_status(merchant.id, data.id, data.shipped)
        assert order, "Cannot find updated order"

        data.paid = order.paid
        dm_content = json.dumps(
            {"type": 2, **data.dict()}, separators=(",", ":"), ensure_ascii=False
        )

        dm_event = merchant.build_dm_event(dm_content, order.public_key)
        await nostr_client.publish_nostr_event(dm_event)

        return order

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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
        await update_customer_no_unread_messages(public_key)
        return messages
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
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
        await nostr_client.publish_nostr_event(dm_event)

        return dm
    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create message",
        )


######################################## CUSTOMERS ########################################


@nostrmarket_ext.get("/api/v1/customer")
async def api_get_customers(
    wallet: WalletTypeInfo = Depends(get_key_type),
) -> List[Customer]:
    try:
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, f"Merchant cannot be found"
        return await get_customers(merchant.id)

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create message",
        )


@nostrmarket_ext.post("/api/v1/customer")
async def api_createcustomer(
    data: Customer,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Customer:

    try:
        pubkey = normalize_public_key(data.public_key)

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "A merchant does not exists for this user"
        assert merchant.id == data.merchant_id, "Invalid merchant id for user"

        existing_customer = await get_customer(merchant.id, pubkey)
        assert existing_customer == None, "This public key already exists"

        customer = await create_customer(
            merchant.id, Customer(merchant_id=merchant.id, public_key=pubkey)
        )
        await nostr_client.subscribe_to_user_profile(pubkey, 0)

        return customer
    except (ValueError, AssertionError) as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create customer",
        )


######################################## OTHER ########################################


@nostrmarket_ext.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@nostrmarket_ext.put("/api/v1/restart")
async def restart_nostr_client(wallet: WalletTypeInfo = Depends(require_admin_key)):
    try:
        ids = await get_merchants_ids_with_pubkeys()
        merchant_public_keys = [id[0] for id in ids]
        await nostr_client.restart(merchant_public_keys)
    except Exception as ex:
        logger.warning(ex)


@nostrmarket_ext.delete("/api/v1", status_code=HTTPStatus.OK)
async def api_stop(wallet: WalletTypeInfo = Depends(check_admin)):
    for t in scheduled_tasks:
        try:
            t.cancel()
        except Exception as ex:
            logger.warning(ex)

    try:
        ids = await get_merchants_ids_with_pubkeys()
        merchant_public_keys = [id[0] for id in ids]
        await nostr_client.stop(merchant_public_keys)
    except Exception as ex:
        logger.warning(ex)

    return {"success": True}
