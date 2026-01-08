import json
import time
from abc import abstractmethod
from enum import Enum
from typing import Any

from lnbits.utils.exchange_rates import btc_price, fiat_amount_as_satoshis
from pydantic import BaseModel

from .helpers import (
    decrypt_message,
    encrypt_message,
    get_shared_secret,
    sign_message_hash,
)
from .nostr.event import NostrEvent

######################################## NOSTR ########################################


class Nostrable:
    @abstractmethod
    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        pass

    @abstractmethod
    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        pass


######################################## MERCHANT ######################################


class MerchantProfile(BaseModel):
    name: str | None = None
    display_name: str | None = None
    about: str | None = None
    picture: str | None = None
    banner: str | None = None
    website: str | None = None
    nip05: str | None = None
    lud16: str | None = None


class MerchantConfig(MerchantProfile):
    event_id: str | None = None
    sync_from_nostr: bool = False
    active: bool = False
    restore_in_progress: bool | None = False


class PartialMerchant(BaseModel):
    private_key: str
    public_key: str
    config: MerchantConfig = MerchantConfig()


class Merchant(PartialMerchant, Nostrable):
    id: str
    time: int | None = 0

    def sign_hash(self, hash_: bytes) -> str:
        return sign_message_hash(self.private_key, hash_)

    def decrypt_message(self, encrypted_message: str, public_key: str) -> str:
        encryption_key = get_shared_secret(self.private_key, public_key)
        return decrypt_message(encrypted_message, encryption_key)

    def encrypt_message(self, clear_text_message: str, public_key: str) -> str:
        encryption_key = get_shared_secret(self.private_key, public_key)
        return encrypt_message(clear_text_message, encryption_key)

    def build_dm_event(self, message: str, to_pubkey: str) -> NostrEvent:
        content = self.encrypt_message(message, to_pubkey)
        event = NostrEvent(
            pubkey=self.public_key,
            created_at=round(time.time()),
            kind=4,
            tags=[["p", to_pubkey]],
            content=content,
        )
        event.id = event.event_id
        event.sig = self.sign_hash(bytes.fromhex(event.id))

        return event

    @classmethod
    def from_row(cls, row: dict) -> "Merchant":
        merchant = cls(**row)
        merchant.config = MerchantConfig(**json.loads(row["meta"]))
        return merchant

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content: dict[str, str] = {}
        if self.config.name:
            content["name"] = self.config.name
        if self.config.display_name:
            content["display_name"] = self.config.display_name
        if self.config.about:
            content["about"] = self.config.about
        if self.config.picture:
            content["picture"] = self.config.picture
        if self.config.banner:
            content["banner"] = self.config.banner
        if self.config.website:
            content["website"] = self.config.website
        if self.config.nip05:
            content["nip05"] = self.config.nip05
        if self.config.lud16:
            content["lud16"] = self.config.lud16
        event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=0,
            tags=[],
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        event.id = event.event_id

        return event

    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        content = {
            "name": f"{self.config.name} (deleted)",
            "about": "Merchant Deleted",
            "picture": "",
        }
        delete_event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=5,
            tags=[],
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        delete_event.id = delete_event.event_id

        return delete_event


######################################## ZONES ########################################
class Zone(BaseModel):
    id: str | None = None
    name: str | None = None
    currency: str
    cost: float
    countries: list[str] = []

    @classmethod
    def from_row(cls, row: dict) -> "Zone":
        zone = cls(**row)
        zone.countries = json.loads(row["regions"])
        return zone


######################################## STALLS ########################################


class StallConfig(BaseModel):
    image_url: str | None = None
    description: str | None = None


class Stall(BaseModel, Nostrable):
    id: str | None = None
    wallet: str
    name: str
    currency: str = "sat"
    shipping_zones: list[Zone] = []
    config: StallConfig = StallConfig()
    pending: bool = False

    """Last published nostr event for this Stall"""
    event_id: str | None = None
    event_created_at: int | None = None

    def validate_stall(self):
        for z in self.shipping_zones:
            if z.currency != self.currency:
                raise ValueError(
                    f"Sipping zone '{z.name}' has different currency than stall."
                )

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content = {
            "id": self.id,
            "name": self.name,
            "description": self.config.description,
            "currency": self.currency,
            "shipping": [dict(z) for z in self.shipping_zones],
        }
        assert self.id
        event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=30017,
            tags=[["d", self.id]],
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        event.id = event.event_id

        return event

    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        delete_event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=5,
            tags=[["e", self.event_id or ""]],
            content=f"Stall '{self.name}' deleted",
        )
        delete_event.id = delete_event.event_id

        return delete_event

    @classmethod
    def from_row(cls, row: dict) -> "Stall":
        stall = cls(**row)
        stall.config = StallConfig(**json.loads(row["meta"]))
        stall.shipping_zones = [Zone(**z) for z in json.loads(row["zones"])]
        return stall


######################################## PRODUCTS ######################################


class ProductShippingCost(BaseModel):
    id: str
    cost: int


class ProductConfig(BaseModel):
    description: str | None = None
    currency: str | None = None
    use_autoreply: bool | None = False
    autoreply_message: str | None = None
    shipping: list[ProductShippingCost] = []


class Product(BaseModel, Nostrable):
    id: str | None = None
    stall_id: str
    name: str
    categories: list[str] = []
    images: list[str] = []
    price: float
    quantity: int
    active: bool = True
    pending: bool = False
    config: ProductConfig = ProductConfig()

    """Last published nostr event for this Product"""
    event_id: str | None = None
    event_created_at: int | None = None

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content = {
            "id": self.id,
            "stall_id": self.stall_id,
            "name": self.name,
            "description": self.config.description,
            "images": self.images,
            "currency": self.config.currency,
            "price": self.price,
            "quantity": self.quantity,
            "active": self.active,
            "shipping": [dict(s) for s in self.config.shipping or []],
        }
        categories = [["t", tag] for tag in self.categories]

        assert self.id
        if self.active:
            event = NostrEvent(
                pubkey=pubkey,
                created_at=round(time.time()),
                kind=30018,
                tags=[["d", self.id], *categories],
                content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
            )
            event.id = event.event_id

            return event
        else:
            return self.to_nostr_delete_event(pubkey)

    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        delete_event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=5,
            tags=[["e", self.event_id or ""]],
            content=f"Product '{self.name}' deleted",
        )
        delete_event.id = delete_event.event_id

        return delete_event

    @classmethod
    def from_row(cls, row: dict) -> "Product":
        product = cls(**row)
        product.config = ProductConfig(**json.loads(row["meta"]))
        product.images = json.loads(row["image_urls"]) if "image_urls" in row else []
        product.categories = json.loads(row["category_list"])
        return product


class ProductOverview(BaseModel):
    id: str
    name: str
    price: float
    product_shipping_cost: float | None = None

    @classmethod
    def from_product(cls, p: Product) -> "ProductOverview":
        assert p.id
        return ProductOverview(id=p.id, name=p.name, price=p.price)


######################################## ORDERS ########################################


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class OrderContact(BaseModel):
    nostr: str | None = None
    phone: str | None = None
    email: str | None = None


class OrderExtra(BaseModel):
    products: list[ProductOverview]
    currency: str
    btc_price: str
    shipping_cost: float = 0
    shipping_cost_sat: float = 0
    fail_message: str | None = None

    @classmethod
    async def from_products(cls, products: list[Product]):
        currency = products[0].config.currency if len(products) else "sat"
        exchange_rate = (
            await btc_price(currency) if currency and currency != "sat" else 1
        )

        products_overview = [ProductOverview.from_product(p) for p in products]
        return OrderExtra(
            products=products_overview,
            currency=currency or "sat",
            btc_price=str(exchange_rate),
        )


class PartialOrder(BaseModel):
    id: str
    event_id: str | None = None
    event_created_at: int | None = None
    public_key: str
    merchant_public_key: str
    shipping_id: str
    items: list[OrderItem]
    contact: OrderContact | None = None
    address: str | None = None

    def validate_order(self):
        assert len(self.items) != 0, f"Order has no items. Order: '{self.id}'"

    def validate_order_items(self, product_list: list[Product]):
        assert len(self.items) != 0, f"Order has no items. Order: '{self.id}'"
        assert (
            len(product_list) != 0
        ), f"No products found for order. Order: '{self.id}'"

        product_ids = [p.id for p in product_list]
        for item in self.items:
            if item.product_id not in product_ids:
                raise ValueError(
                    f"Order ({self.id}) item product does not exist: {item.product_id}"
                )

        stall_id = product_list[0].stall_id
        for p in product_list:
            if p.stall_id != stall_id:
                raise ValueError(
                    f"Order ({self.id}) has products from different stalls"
                )

    async def costs_in_sats(
        self, products: list[Product], shipping_id: str, stall_shipping_cost: float
    ) -> tuple[float, float]:
        product_prices = {}
        for p in products:
            product_shipping_cost = next(
                (s.cost for s in p.config.shipping if s.id == shipping_id), 0
            )
            product_prices[p.id] = {
                "price": p.price + product_shipping_cost,
                "currency": p.config.currency or "sat",
            }

        product_cost: float = 0  # todo
        currency = "sat"
        for item in self.items:
            assert item.quantity > 0, "Quantity cannot be negative"
            price = float(str(product_prices[item.product_id]["price"]))
            currency = str(product_prices[item.product_id]["currency"])
            if currency != "sat":
                price = await fiat_amount_as_satoshis(price, currency)
            product_cost += item.quantity * price

        if currency != "sat":
            stall_shipping_cost = await fiat_amount_as_satoshis(
                stall_shipping_cost, currency
            )

        return product_cost, stall_shipping_cost

    def receipt(
        self, products: list[Product], shipping_id: str, stall_shipping_cost: float
    ) -> str:
        if len(products) == 0:
            return "[No Products]"
        receipt = ""
        product_prices: dict[str, ProductOverview] = {}
        for p in products:
            product_shipping_cost = next(
                (s.cost for s in p.config.shipping if s.id == shipping_id), 0
            )
            assert p.id
            product_prices[p.id] = ProductOverview(
                id=p.id,
                name=p.name,
                price=p.price,
                product_shipping_cost=product_shipping_cost,
            )

        currency = products[0].config.currency or "sat"
        products_cost: float = 0  # todo
        items_receipts = []
        for item in self.items:
            prod = product_prices[item.product_id]
            price = prod.price + (prod.product_shipping_cost or 0)

            products_cost += item.quantity * price

            items_receipts.append(
                f"""[{prod.name}:  {item.quantity} x ({prod.price}"""
                f""" + {prod.product_shipping_cost})"""
                f""" = {item.quantity * price} {currency}] """
            )

        receipt = "; ".join(items_receipts)
        receipt += (
            f"[Products cost: {products_cost} {currency}] "
            f"[Stall shipping cost: {stall_shipping_cost} {currency}]; "
        )
        receipt += f"[Total: {products_cost + stall_shipping_cost} {currency}]"

        return receipt


class Order(PartialOrder):
    stall_id: str
    invoice_id: str
    total: float
    paid: bool = False
    shipped: bool = False
    time: int | None = None
    extra: OrderExtra

    @classmethod
    def from_row(cls, row: dict) -> "Order":
        contact = OrderContact(**json.loads(row["contact_data"]))
        extra = OrderExtra(**json.loads(row["extra_data"]))
        items = [OrderItem(**z) for z in json.loads(row["order_items"])]
        order = cls(**row, contact=contact, items=items, extra=extra)
        return order


class OrderStatusUpdate(BaseModel):
    id: str
    message: str | None = None
    paid: bool | None = False
    shipped: bool | None = None


class OrderReissue(BaseModel):
    id: str
    shipping_id: str | None = None


class PaymentOption(BaseModel):
    type: str
    link: str


class PaymentRequest(BaseModel):
    id: str
    message: str | None = None
    payment_options: list[PaymentOption]


######################################## MESSAGE #######################################


class DirectMessageType(Enum):
    """Various types os direct messages."""

    PLAIN_TEXT = -1
    CUSTOMER_ORDER = 0
    PAYMENT_REQUEST = 1
    ORDER_PAID_OR_SHIPPED = 2


class PartialDirectMessage(BaseModel):
    event_id: str | None = None
    event_created_at: int | None = None
    message: str
    public_key: str
    type: int = DirectMessageType.PLAIN_TEXT.value
    incoming: bool = False
    time: int | None = None

    @classmethod
    def parse_message(cls, msg) -> tuple[DirectMessageType, Any | None]:
        try:
            msg_json = json.loads(msg)
            if "type" in msg_json:
                return DirectMessageType(msg_json["type"]), msg_json

            return DirectMessageType.PLAIN_TEXT, None
        except Exception:
            return DirectMessageType.PLAIN_TEXT, None


class DirectMessage(PartialDirectMessage):
    id: str

    @classmethod
    def from_row(cls, row: dict) -> "DirectMessage":
        return cls(**row)


######################################## CUSTOMERS #####################################


class CustomerProfile(BaseModel):
    name: str | None = None
    display_name: str | None = None
    about: str | None = None


class Customer(BaseModel):
    merchant_id: str
    public_key: str
    event_created_at: int | None = None
    profile: CustomerProfile | None = None
    unread_messages: int = 0

    @classmethod
    def from_row(cls, row: dict) -> "Customer":
        customer = cls(**row)
        customer.profile = (
            CustomerProfile(**json.loads(row["meta"])) if "meta" in row else None
        )
        return customer
