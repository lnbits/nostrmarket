from http import HTTPStatus
from typing import Optional

from fastapi import Depends
from fastapi.exceptions import HTTPException
from loguru import logger

from lnbits.decorators import WalletTypeInfo, require_admin_key, require_invoice_key

from . import nostrmarket_ext
from .crud import create_merchant, get_merchant_for_user
from .models import Merchant, PartialMerchant


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
