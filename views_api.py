import json
from http import HTTPStatus
from typing import List, Optional

from fastapi import Depends
from fastapi.exceptions import HTTPException
from loguru import logger

from lnbits.decorators import (
    WalletTypeInfo,
    get_key_type,
    require_admin_key,
    require_invoice_key,
)
from lnbits.utils.exchange_rates import currencies

from . import nostrmarket_ext
from .crud import (
    create_merchant,
    create_product,
    create_stall,
    create_zone,
    delete_stall,
    delete_zone,
    get_merchant_for_user,
    get_products,
    get_stall,
    get_stalls,
    get_zone,
    get_zones,
    update_stall,
    update_zone,
)
from .models import (
    Merchant,
    PartialMerchant,
    PartialProduct,
    PartialStall,
    PartialZone,
    Product,
    Stall,
    Zone,
)
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
            detail="Cannot create merchant",
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
            detail="Cannot create merchant",
        )


@nostrmarket_ext.post("/api/v1/zone")
async def api_create_zone(
    data: PartialZone, wallet: WalletTypeInfo = Depends(get_key_type)
):
    try:
        zone = await create_zone(wallet.wallet.user, data)
        return zone
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create merchant",
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
            detail="Cannot create merchant",
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
            detail="Cannot create merchant",
        )


######################################## STALLS ########################################


@nostrmarket_ext.post("/api/v1/stall")
async def api_create_stall(
    data: PartialStall,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Stall:
    try:
        data.validate_stall()

        print("### stall", json.dumps(data.dict()))
        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Cannot find merchat for stall"

        stall = await create_stall(wallet.wallet.user, data=data)

        event = stall.to_nostr_event(merchant.public_key)
        event.sig = merchant.sign_hash(bytes.fromhex(event.id))
        await publish_nostr_event(event)

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

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Cannot find merchat for stall"

        event = data.to_nostr_event(merchant.public_key)
        event.sig = merchant.sign_hash(bytes.fromhex(event.id))

        data.config.event_id = event.id
        # data.config.event_created_at =
        stall = await update_stall(wallet.wallet.user, data)
        assert stall, "Cannot update stall"

        await publish_nostr_event(event)

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

        merchant = await get_merchant_for_user(wallet.wallet.user)
        assert merchant, "Cannot find merchat for stall"

        await delete_stall(wallet.wallet.user, stall_id)

        delete_event = stall.to_nostr_delete_event(merchant.public_key)
        delete_event.sig = merchant.sign_hash(bytes.fromhex(delete_event.id))

        await publish_nostr_event(delete_event)

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
        product = await create_product(wallet.wallet.user, data=data)

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


@nostrmarket_ext.get("/api/v1/product/{stall_id}")
async def api_get_product(
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
            detail="Cannot get product",
        )


# @market_ext.delete("/api/v1/products/{product_id}")
# async def api_market_products_delete(
#     product_id, wallet: WalletTypeInfo = Depends(require_admin_key)
# ):
#     product = await get_market_product(product_id)

#     if not product:
#         return {"message": "Product does not exist."}

#     stall = await get_market_stall(product.stall)
#     assert stall

#     if stall.wallet != wallet.wallet.id:
#         return {"message": "Not your Market."}

#     await delete_market_product(product_id)
#     raise HTTPException(status_code=HTTPStatus.NO_CONTENT)


######################################## OTHER ########################################


@nostrmarket_ext.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())
