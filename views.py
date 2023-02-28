import json
from http import HTTPStatus

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.responses import HTMLResponse

from lnbits.core.models import User
from lnbits.decorators import check_user_exists

from . import nostrmarket_ext, nostrmarket_renderer

templates = Jinja2Templates(directory="templates")


@nostrmarket_ext.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return nostrmarket_renderer().TemplateResponse(
        "nostrmarket/index.html",
        {"request": request, "user": user.dict()},
    )


@nostrmarket_ext.get("/market", response_class=HTMLResponse)
async def market(request: Request):
    return nostrmarket_renderer().TemplateResponse(
        "nostrmarket/market.html",
        {
            "request": request,
        },
    )


@nostrmarket_ext.get("/stall/{stall_id}", response_class=HTMLResponse)
async def stall(request: Request, stall_id: str):
    return nostrmarket_renderer().TemplateResponse(
        "nostrmarket/stall.html",
        {"request": request, "stall_id": stall_id},
    )
