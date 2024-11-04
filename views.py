from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from starlette.responses import HTMLResponse

from . import nostrmarket_ext, nostrmarket_renderer

templates = Jinja2Templates(directory="templates")


@nostrmarket_ext.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return nostrmarket_renderer().TemplateResponse(
        "nostrmarket/index.html",
        {"request": request, "user": user.json()},
    )


@nostrmarket_ext.get("/market", response_class=HTMLResponse)
async def market(request: Request):
    return nostrmarket_renderer().TemplateResponse(
        "nostrmarket/market.html",
        {"request": request},
    )
