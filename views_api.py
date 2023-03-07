import json
from http import HTTPStatus
from typing import List, Optional

from fastapi import Depends
from fastapi.exceptions import HTTPException
from loguru import logger

from lnbits.core import create_invoice
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
    create_merchant,
    create_order,
    create_product,
    create_stall,
    create_zone,
    delete_product,
    delete_stall,
    delete_zone,
    get_merchant_for_user,
    get_order,
    get_order_by_event_id,
    get_orders,
    get_orders_for_stall,
    get_product,
    get_products,
    get_products_by_ids,
    get_stall,
    get_stalls,
    get_wallet_for_product,
    get_zone,
    get_zones,
    update_order_shipped_status,
    update_product,
    update_stall,
    update_zone,
)
from .models import (
    Merchant,
    Nostrable,
    Order,
    OrderExtra,
    OrderStatusUpdate,
    PartialMerchant,
    PartialOrder,
    PartialProduct,
    PartialStall,
    PartialZone,
    PaymentOption,
    PaymentRequest,
    Product,
    Stall,
    Zone,
)
from .nostr.event import NostrEvent
from .nostr.nostr_client import publish_nostr_event

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


######################################## ZONES ########################################


@nostrmarket_ext.get("/api/v1/zone")
async def api_get_zones(wallet: WalletTypeInfo = Depends(get_key_type)) -> List[Zone]:
    try:
        return await get_zones(wallet.wallet.user)
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
        zone = await create_zone(wallet.wallet.user, data)
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
        zone = await get_zone(wallet.wallet.user, zone_id)
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
        zone = await get_zone(wallet.wallet.user, zone_id)

        if not zone:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Zone does not exist.",
            )

        await delete_zone(zone_id)

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

        stall = await create_stall(wallet.wallet.user, data=data)

        event = await sign_and_send_to_nostr(wallet.wallet.user, stall)

        stall.config.event_id = event.id
        await update_stall(wallet.wallet.user, stall)

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

        stall = await update_stall(wallet.wallet.user, data)
        assert stall, "Cannot update stall"

        event = await sign_and_send_to_nostr(wallet.wallet.user, stall)

        stall.config.event_id = event.id
        await update_stall(wallet.wallet.user, stall)

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
        stall = await get_stall(wallet.wallet.user, stall_id)
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
        stalls = await get_stalls(wallet.wallet.user)
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
        products = await get_products(wallet.wallet.user, stall_id)
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
        orders = await get_orders_for_stall(wallet.wallet.user, stall_id)
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
        stall = await get_stall(wallet.wallet.user, stall_id)
        if not stall:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Stall does not exist.",
            )

        await delete_stall(wallet.wallet.user, stall_id)

        event = await sign_and_send_to_nostr(wallet.wallet.user, stall, True)

        stall.config.event_id = event.id
        await update_stall(wallet.wallet.user, stall)

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

        stall = await get_stall(wallet.wallet.user, data.stall_id)
        assert stall, "Stall missing for product"
        data.config.currency = stall.currency

        product = await create_product(wallet.wallet.user, data=data)

        event = await sign_and_send_to_nostr(wallet.wallet.user, product)

        product.config.event_id = event.id
        await update_product(wallet.wallet.user, product)

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

        stall = await get_stall(wallet.wallet.user, product.stall_id)
        assert stall, "Stall missing for product"
        product.config.currency = stall.currency

        product = await update_product(wallet.wallet.user, product)

        event = await sign_and_send_to_nostr(wallet.wallet.user, product)

        product.config.event_id = event.id
        await update_product(wallet.wallet.user, product)

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
        products = await get_product(wallet.wallet.user, product_id)
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
        product = await get_product(wallet.wallet.user, product_id)
        if not product:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Product does not exist.",
            )

        await delete_product(wallet.wallet.user, product_id)
        await sign_and_send_to_nostr(wallet.wallet.user, product, True)

    except HTTPException as ex:
        raise ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot delete product",
        )


######################################## ORDERS ########################################


@nostrmarket_ext.post("/api/v1/order")
async def api_create_order(
    data: PartialOrder, wallet: WalletTypeInfo = Depends(require_admin_key)
) -> Optional[PaymentRequest]:
    try:
        # print("### new order: ", json.dumps(data.dict()))
        if await get_order(wallet.wallet.user, data.id):
            return None
        if data.event_id and await get_order_by_event_id(
            wallet.wallet.user, data.event_id
        ):
            return None

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Cannot find merchant!"

        products = await get_products_by_ids(
            wallet.wallet.user, [p.product_id for p in data.items]
        )
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
        await create_order(wallet.wallet.user, order)

        return PaymentRequest(
            id=data.id, payment_options=[PaymentOption(type="ln", link=invoice)]
        )
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create order",
        )


nostrmarket_ext.get("/api/v1/order/{order_id}")


async def api_get_order(order_id: str, wallet: WalletTypeInfo = Depends(get_key_type)):
    try:
        order = await get_order(wallet.wallet.user, order_id)
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
        orders = await get_orders(wallet.wallet.user)
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
        order = await update_order_shipped_status(
            wallet.wallet.user, data.id, data.shipped
        )
        assert order, "Cannot find updated order"

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, f"Merchant cannot be found for order {data.id}"

        data.paid = order.paid
        dm_content = json.dumps(data.dict(), separators=(",", ":"), ensure_ascii=False)

        dm_event = merchant.build_dm_event(dm_content, order.pubkey)
        await publish_nostr_event(dm_event)

        return order

    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot update order",
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


######################################## HELPERS ########################################


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
