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
    create_zone,
    delete_zone,
    get_merchant_for_user,
    get_zone,
    get_zones,
    update_zone,
)
from .models import Merchant, PartialMerchant, PartialZone, Zone

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


@nostrmarket_ext.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())
