import json
from typing import List, Optional, Tuple

from lnbits.helpers import urlsafe_short_hash

from . import db
from .models import (
    Customer,
    CustomerProfile,
    DirectMessage,
    Merchant,
    MerchantConfig,
    Order,
    PartialDirectMessage,
    PartialMerchant,
    Product,
    Stall,
    Zone,
)

######################################## MERCHANT ######################################


async def create_merchant(user_id: str, m: PartialMerchant) -> Merchant:
    merchant_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nostrmarket.merchants
               (user_id, id, private_key, public_key, meta)
        VALUES (:user_id, :id, :private_key, :public_key, :meta)
        """,
        {
            "user_id": user_id,
            "id": merchant_id,
            "private_key": m.private_key,
            "public_key": m.public_key,
            "meta": json.dumps(dict(m.config)),
        },
    )
    merchant = await get_merchant(user_id, merchant_id)
    assert merchant, "Created merchant cannot be retrieved"
    return merchant


async def update_merchant(
    user_id: str, merchant_id: str, config: MerchantConfig
) -> Optional[Merchant]:
    await db.execute(
        f"""
            UPDATE nostrmarket.merchants SET meta = :meta, time = {db.timestamp_now}
            WHERE id = :id AND user_id = :user_id
        """,
        {"meta": json.dumps(config.dict()), "id": merchant_id, "user_id": user_id},
    )
    return await get_merchant(user_id, merchant_id)


async def touch_merchant(user_id: str, merchant_id: str) -> Optional[Merchant]:
    await db.execute(
        f"""
            UPDATE nostrmarket.merchants SET time = {db.timestamp_now}
            WHERE id = :id AND user_id = :user_id
        """,
        {"id": merchant_id, "user_id": user_id},
    )
    return await get_merchant(user_id, merchant_id)


async def get_merchant(user_id: str, merchant_id: str) -> Optional[Merchant]:
    row: dict = await db.fetchone(
        """SELECT * FROM nostrmarket.merchants WHERE user_id = :user_id AND id = :id""",
        {
            "user_id": user_id,
            "id": merchant_id,
        },
    )

    return Merchant.from_row(row) if row else None


async def get_merchant_by_pubkey(public_key: str) -> Optional[Merchant]:
    row: dict = await db.fetchone(
        """SELECT * FROM nostrmarket.merchants WHERE public_key = :public_key""",
        {"public_key": public_key},
    )

    return Merchant.from_row(row) if row else None


async def get_merchants_ids_with_pubkeys() -> List[Tuple[str, str]]:
    rows: list[dict] = await db.fetchall(
        """SELECT id, public_key FROM nostrmarket.merchants""",
    )

    return [(row["id"], row["public_key"]) for row in rows]


async def get_merchant_for_user(user_id: str) -> Optional[Merchant]:
    row: dict = await db.fetchone(
        """SELECT * FROM nostrmarket.merchants WHERE user_id = :user_id """,
        {"user_id": user_id},
    )

    return Merchant.from_row(row) if row else None


async def delete_merchant(merchant_id: str) -> None:
    await db.execute(
        "DELETE FROM nostrmarket.merchants WHERE id = :id",
        {
            "id": merchant_id,
        },
    )


######################################## ZONES ########################################


async def create_zone(merchant_id: str, data: Zone) -> Zone:
    zone_id = data.id or urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nostrmarket.zones (id, merchant_id, name, currency, cost, regions)
        VALUES (:id, :merchant_id, :name, :currency, :cost, :regions)
        """,
        {
            "id": zone_id,
            "merchant_id": merchant_id,
            "name": data.name,
            "currency": data.currency,
            "cost": data.cost,
            "regions": json.dumps(data.countries),
        },
    )

    zone = await get_zone(merchant_id, zone_id)
    assert zone, "Newly created zone couldn't be retrieved"
    return zone


async def update_zone(merchant_id: str, z: Zone) -> Optional[Zone]:
    await db.execute(
        """
        UPDATE nostrmarket.zones
        SET name = :name, cost = :cost, regions = :regions
        WHERE id = :id AND merchant_id = :merchant_id
        """,
        {
            "name": z.name,
            "cost": z.cost,
            "regions": json.dumps(z.countries),
            "id": z.id,
            "merchant_id": merchant_id,
        },
    )
    assert z.id
    return await get_zone(merchant_id, z.id)


async def get_zone(merchant_id: str, zone_id: str) -> Optional[Zone]:
    row: dict = await db.fetchone(
        "SELECT * FROM nostrmarket.zones WHERE merchant_id = :merchant_id AND id = :id",
        {
            "merchant_id": merchant_id,
            "id": zone_id,
        },
    )
    return Zone.from_row(row) if row else None


async def get_zones(merchant_id: str) -> List[Zone]:
    rows: list[dict] = await db.fetchall(
        "SELECT * FROM nostrmarket.zones WHERE merchant_id = :merchant_id",
        {"merchant_id": merchant_id},
    )
    return [Zone.from_row(row) for row in rows]


async def delete_zone(merchant_id: str, zone_id: str) -> None:

    await db.execute(
        "DELETE FROM nostrmarket.zones WHERE merchant_id = :merchant_id AND id = :id",
        {
            "merchant_id": merchant_id,
            "id": zone_id,
        },
    )


async def delete_merchant_zones(merchant_id: str) -> None:
    await db.execute(
        "DELETE FROM nostrmarket.zones WHERE merchant_id = ?",
        {"merchant_id": merchant_id},
    )


######################################## STALL ########################################


async def create_stall(merchant_id: str, data: Stall) -> Stall:
    stall_id = data.id or urlsafe_short_hash()

    await db.execute(
        """
        INSERT INTO nostrmarket.stalls
        (
            merchant_id, id,  wallet, name, currency,
            pending, event_id, event_created_at, zones, meta
        )
        VALUES
        (
            :merchant_id, :id, :wallet, :name, :currency,
            :pending, :event_id, :event_created_at, :zones, :meta
        )
        ON CONFLICT(id) DO NOTHING
        """,
        {
            "merchant_id": merchant_id,
            "id": stall_id,
            "wallet": data.wallet,
            "name": data.name,
            "currency": data.currency,
            "pending": data.pending,
            "event_id": data.event_id,
            "event_created_at": data.event_created_at,
            "zones": json.dumps(
                [z.dict() for z in data.shipping_zones]
            ),  # todo: cost is float. should be int for sats
            "meta": json.dumps(data.config.dict()),
        },
    )

    stall = await get_stall(merchant_id, stall_id)
    assert stall, f"Newly created stall couldn't be retrieved. Id: {stall_id}"
    return stall


async def get_stall(merchant_id: str, stall_id: str) -> Optional[Stall]:
    row: dict = await db.fetchone(
        """
        SELECT * FROM nostrmarket.stalls
        WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "merchant_id": merchant_id,
            "id": stall_id,
        },
    )
    return Stall.from_row(row) if row else None


async def get_stalls(merchant_id: str, pending: Optional[bool] = False) -> List[Stall]:
    rows: list[dict] = await db.fetchall(
        """
        SELECT * FROM nostrmarket.stalls
        WHERE merchant_id = :merchant_id AND pending = :pending
        """,
        {
            "merchant_id": merchant_id,
            "pending": pending,
        },
    )
    return [Stall.from_row(row) for row in rows]


async def get_last_stall_update_time() -> int:
    row: dict = await db.fetchone(
        """
            SELECT event_created_at FROM nostrmarket.stalls
            ORDER BY event_created_at DESC LIMIT 1
        """,
        {},
    )
    return row["event_created_at"] or 0 if row else 0


async def update_stall(merchant_id: str, stall: Stall) -> Optional[Stall]:
    await db.execute(
        """
            UPDATE nostrmarket.stalls
            SET wallet = :wallet, name = :name, currency = :currency,
                pending = :pending, event_id = :event_id,
                event_created_at = :event_created_at,
                zones = :zones, meta = :meta
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "wallet": stall.wallet,
            "name": stall.name,
            "currency": stall.currency,
            "pending": stall.pending,
            "event_id": stall.event_id,
            "event_created_at": stall.event_created_at,
            "zones": json.dumps(
                [z.dict() for z in stall.shipping_zones]
            ),  # todo: cost is float. should be int for sats
            "meta": json.dumps(stall.config.dict()),
            "merchant_id": merchant_id,
            "id": stall.id,
        },
    )
    assert stall.id
    return await get_stall(merchant_id, stall.id)


async def delete_stall(merchant_id: str, stall_id: str) -> None:
    await db.execute(
        """
            DELETE FROM nostrmarket.stalls
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "merchant_id": merchant_id,
            "id": stall_id,
        },
    )


async def delete_merchant_stalls(merchant_id: str) -> None:
    await db.execute(
        "DELETE FROM nostrmarket.stalls WHERE merchant_id = :merchant_id",
        {"merchant_id": merchant_id},
    )


######################################## PRODUCTS ######################################


async def create_product(merchant_id: str, data: Product) -> Product:
    product_id = data.id or urlsafe_short_hash()

    await db.execute(
        """
        INSERT INTO nostrmarket.products
        (
            merchant_id, id, stall_id, name, price, quantity,
            active, pending, event_id, event_created_at,
            image_urls, category_list, meta
        )
        VALUES (
            :merchant_id, :id, :stall_id, :name, :price, :quantity,
            :active, :pending, :event_id, :event_created_at,
            :image_urls, :category_list, :meta
        )
        ON CONFLICT(id) DO NOTHING
        """,
        {
            "merchant_id": merchant_id,
            "id": product_id,
            "stall_id": data.stall_id,
            "name": data.name,
            "price": data.price,
            "quantity": data.quantity,
            "active": data.active,
            "pending": data.pending,
            "event_id": data.event_id,
            "event_created_at": data.event_created_at,
            "image_urls": json.dumps(data.images),
            "category_list": json.dumps(data.categories),
            "meta": json.dumps(data.config.dict()),
        },
    )
    product = await get_product(merchant_id, product_id)
    assert product, "Newly created product couldn't be retrieved"

    return product


async def update_product(merchant_id: str, product: Product) -> Product:
    assert product.id
    await db.execute(
        """
        UPDATE nostrmarket.products
        SET name = :name, price = :price, quantity = :quantity,
            active = :active, pending = :pending, event_id =:event_id,
            event_created_at = :event_created_at, image_urls = :image_urls,
            category_list = :category_list, meta = :meta
        WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "name": product.name,
            "price": product.price,
            "quantity": product.quantity,
            "active": product.active,
            "pending": product.pending,
            "event_id": product.event_id,
            "event_created_at": product.event_created_at,
            "image_urls": json.dumps(product.images),
            "category_list": json.dumps(product.categories),
            "meta": json.dumps(product.config.dict()),
            "merchant_id": merchant_id,
            "id": product.id,
        },
    )
    updated_product = await get_product(merchant_id, product.id)
    assert updated_product, "Updated product couldn't be retrieved"

    return updated_product


async def update_product_quantity(
    product_id: str, new_quantity: int
) -> Optional[Product]:
    await db.execute(
        """
            UPDATE nostrmarket.products SET quantity = :quantity
            WHERE id = :id
        """,
        {"quantity": new_quantity, "id": product_id},
    )
    row: dict = await db.fetchone(
        "SELECT * FROM nostrmarket.products WHERE id = :id",
        {"id": product_id},
    )
    return Product.from_row(row) if row else None


async def get_product(merchant_id: str, product_id: str) -> Optional[Product]:
    row: dict = await db.fetchone(
        """
            SELECT * FROM nostrmarket.products
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "merchant_id": merchant_id,
            "id": product_id,
        },
    )
    # TODO: remove from_row
    return Product.from_row(row) if row else None


async def get_products(
    merchant_id: str, stall_id: str, pending: Optional[bool] = False
) -> List[Product]:
    rows: list[dict] = await db.fetchall(
        """
        SELECT * FROM nostrmarket.products
        WHERE merchant_id = :merchant_id
              AND stall_id = :stall_id AND pending = :pending
        """,
        {"merchant_id": merchant_id, "stall_id": stall_id, "pending": pending},
    )
    return [Product.from_row(row) for row in rows]


async def get_products_by_ids(
    merchant_id: str, product_ids: List[str]
) -> List[Product]:
    # todo: revisit

    keys = []
    values = {"merchant_id": merchant_id}
    for i, v in enumerate(product_ids):
        key = f"p_{i}"
        values[key] = v
        keys.append(f":{key}")
    rows: list[dict] = await db.fetchall(
        f"""
            SELECT id, stall_id, name, price, quantity, active, category_list, meta
            FROM nostrmarket.products
            WHERE merchant_id = :merchant_id
                  AND pending = false AND id IN ({", ".join(keys)})
        """,
        values,
    )
    return [Product.from_row(row) for row in rows]


async def get_wallet_for_product(product_id: str) -> Optional[str]:
    row: dict = await db.fetchone(
        """
        SELECT s.wallet as wallet FROM nostrmarket.products p
        INNER JOIN nostrmarket.stalls s
        ON p.stall_id = s.id
        WHERE p.id = :product_id AND p.pending = false AND s.pending = false
       """,
        {"product_id": product_id},
    )
    return row["wallet"] if row else None


async def get_last_product_update_time() -> int:
    row: dict = await db.fetchone(
        """
            SELECT event_created_at FROM nostrmarket.products
            ORDER BY event_created_at DESC LIMIT 1
        """,
        {},
    )
    return row["event_created_at"] or 0 if row else 0


async def delete_product(merchant_id: str, product_id: str) -> None:
    await db.execute(
        """
            DELETE FROM nostrmarket.products
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "merchant_id": merchant_id,
            "id": product_id,
        },
    )


async def delete_merchant_products(merchant_id: str) -> None:
    await db.execute(
        "DELETE FROM nostrmarket.products WHERE merchant_id = :merchant_id",
        {"merchant_id": merchant_id},
    )


######################################## ORDERS ########################################


async def create_order(merchant_id: str, o: Order) -> Order:
    await db.execute(
        """
        INSERT INTO nostrmarket.orders (
            merchant_id,
            id,
            event_id,
            event_created_at,
            merchant_public_key,
            public_key,
            address,
            contact_data,
            extra_data,
            order_items,
            shipping_id,
            stall_id,
            invoice_id,
            total
        )
        VALUES (
            :merchant_id,
            :id,
            :event_id,
            :event_created_at,
            :merchant_public_key,
            :public_key,
            :address,
            :contact_data,
            :extra_data,
            :order_items,
            :shipping_id,
            :stall_id,
            :invoice_id,
            :total
        )
        ON CONFLICT(event_id) DO NOTHING
        """,
        {
            "merchant_id": merchant_id,
            "id": o.id,
            "event_id": o.event_id,
            "event_created_at": o.event_created_at,
            "merchant_public_key": o.merchant_public_key,
            "public_key": o.public_key,
            "address": o.address,
            "contact_data": json.dumps(o.contact.dict() if o.contact else {}),
            "extra_data": json.dumps(o.extra.dict()),
            "order_items": json.dumps([i.dict() for i in o.items]),
            "shipping_id": o.shipping_id,
            "stall_id": o.stall_id,
            "invoice_id": o.invoice_id,
            "total": o.total,
        },
    )
    order = await get_order(merchant_id, o.id)
    assert order, "Newly created order couldn't be retrieved"

    return order


async def get_order(merchant_id: str, order_id: str) -> Optional[Order]:
    row: dict = await db.fetchone(
        """
            SELECT * FROM nostrmarket.orders
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "merchant_id": merchant_id,
            "id": order_id,
        },
    )
    return Order.from_row(row) if row else None


async def get_order_by_event_id(merchant_id: str, event_id: str) -> Optional[Order]:
    row: dict = await db.fetchone(
        """
            SELECT * FROM nostrmarket.orders
            WHERE merchant_id = :merchant_id AND  event_id = :event_id
        """,
        {
            "merchant_id": merchant_id,
            "event_id": event_id,
        },
    )
    return Order.from_row(row) if row else None


async def get_orders(merchant_id: str, **kwargs) -> List[Order]:
    q = " AND ".join(
        [
            f"{field[0]} = :{field[0]}"
            for field in kwargs.items()
            if field[1] is not None
        ]
    )
    values = {"merchant_id": merchant_id}
    for field in kwargs.items():
        if field[1] is None:
            continue
        values[field[0]] = field[1]

    rows: list[dict] = await db.fetchall(
        f"""
        SELECT * FROM nostrmarket.orders
        WHERE merchant_id = :merchant_id {q}
        ORDER BY event_created_at DESC
        """,
        values,
    )
    return [Order.from_row(row) for row in rows]


async def get_orders_for_stall(
    merchant_id: str, stall_id: str, **kwargs
) -> List[Order]:
    q = " AND ".join(
        [
            f"{field[0]} = :{field[0]}"
            for field in kwargs.items()
            if field[1] is not None
        ]
    )
    values = {"merchant_id": merchant_id, "stall_id": stall_id}
    for field in kwargs.items():
        if field[1] is None:
            continue
        values[field[0]] = field[1]

    rows: list[dict] = await db.fetchall(
        f"""
            SELECT * FROM nostrmarket.orders
            WHERE merchant_id = :merchant_id AND stall_id = :stall_id {q}
            ORDER BY time DESC
        """,
        values,
    )
    return [Order.from_row(row) for row in rows]


async def update_order(merchant_id: str, order_id: str, **kwargs) -> Optional[Order]:
    q = ", ".join(
        [
            f"{field[0]} = :{field[0]}"
            for field in kwargs.items()
            if field[1] is not None
        ]
    )
    values = {"merchant_id": merchant_id, "id": order_id}
    for field in kwargs.items():
        if field[1] is None:
            continue
        values[field[0]] = field[1]
    await db.execute(
        f"""
            UPDATE nostrmarket.orders
            SET {q} WHERE merchant_id = :merchant_id and id = :id
        """,
        values,
    )

    return await get_order(merchant_id, order_id)


async def update_order_paid_status(order_id: str, paid: bool) -> Optional[Order]:
    await db.execute(
        "UPDATE nostrmarket.orders SET paid = :paid  WHERE id = :id",
        {"paid": paid, "id": order_id},
    )
    row: dict = await db.fetchone(
        "SELECT * FROM nostrmarket.orders WHERE id = :id",
        {"id": order_id},
    )
    return Order.from_row(row) if row else None


async def update_order_shipped_status(
    merchant_id: str, order_id: str, shipped: bool
) -> Optional[Order]:
    await db.execute(
        """
            UPDATE nostrmarket.orders
            SET shipped = :shipped
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {"shipped": shipped, "merchant_id": merchant_id, "id": order_id},
    )

    row: dict = await db.fetchone(
        "SELECT * FROM nostrmarket.orders WHERE id = :id",
        {"id": order_id},
    )
    return Order.from_row(row) if row else None


async def delete_merchant_orders(merchant_id: str) -> None:
    await db.execute(
        "DELETE FROM nostrmarket.orders WHERE merchant_id = :merchant_id",
        {"merchant_id": merchant_id},
    )


######################################## MESSAGES ######################################


async def create_direct_message(
    merchant_id: str, dm: PartialDirectMessage
) -> DirectMessage:
    dm_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nostrmarket.direct_messages
        (
            merchant_id, id, event_id, event_created_at,
            message, public_key, type, incoming
        )
        VALUES
            (
            :merchant_id, :id, :event_id, :event_created_at,
            :message, :public_key, :type, :incoming
            )
        ON CONFLICT(event_id) DO NOTHING
        """,
        {
            "merchant_id": merchant_id,
            "id": dm_id,
            "event_id": dm.event_id,
            "event_created_at": dm.event_created_at,
            "message": dm.message,
            "public_key": dm.public_key,
            "type": dm.type,
            "incoming": dm.incoming,
        },
    )
    if dm.event_id:
        msg = await get_direct_message_by_event_id(merchant_id, dm.event_id)
    else:
        msg = await get_direct_message(merchant_id, dm_id)
    assert msg, "Newly created dm couldn't be retrieved"
    return msg


async def get_direct_message(merchant_id: str, dm_id: str) -> Optional[DirectMessage]:
    row: dict = await db.fetchone(
        """
            SELECT * FROM nostrmarket.direct_messages
            WHERE merchant_id = :merchant_id AND id = :id
        """,
        {
            "merchant_id": merchant_id,
            "id": dm_id,
        },
    )
    return DirectMessage.from_row(row) if row else None


async def get_direct_message_by_event_id(
    merchant_id: str, event_id: str
) -> Optional[DirectMessage]:
    row: dict = await db.fetchone(
        """
        SELECT * FROM nostrmarket.direct_messages
        WHERE merchant_id = :merchant_id AND event_id = :event_id
        """,
        {
            "merchant_id": merchant_id,
            "event_id": event_id,
        },
    )
    return DirectMessage.from_row(row) if row else None


async def get_direct_messages(merchant_id: str, public_key: str) -> List[DirectMessage]:
    rows: list[dict] = await db.fetchall(
        """
        SELECT * FROM nostrmarket.direct_messages
        WHERE merchant_id = :merchant_id AND public_key = :public_key
        ORDER BY event_created_at
        """,
        {"merchant_id": merchant_id, "public_key": public_key},
    )
    return [DirectMessage.from_row(row) for row in rows]


async def get_orders_from_direct_messages(merchant_id: str) -> List[DirectMessage]:
    rows: list[dict] = await db.fetchall(
        """
        SELECT * FROM nostrmarket.direct_messages
        WHERE merchant_id = :merchant_id AND type >= 0 ORDER BY event_created_at, type
        """,
        {"merchant_id": merchant_id},
    )
    return [DirectMessage.from_row(row) for row in rows]


async def get_last_direct_messages_time(merchant_id: str) -> int:
    row: dict = await db.fetchone(
        """
            SELECT time FROM nostrmarket.direct_messages
            WHERE merchant_id = :merchant_id ORDER BY time DESC LIMIT 1
        """,
        {"merchant_id": merchant_id},
    )
    return row["time"] if row else 0


async def get_last_direct_messages_created_at() -> int:
    row: dict = await db.fetchone(
        """
            SELECT event_created_at FROM nostrmarket.direct_messages
            ORDER BY event_created_at DESC LIMIT 1
        """,
        {},
    )
    return row["event_created_at"] if row else 0


async def delete_merchant_direct_messages(merchant_id: str) -> None:
    await db.execute(
        "DELETE FROM nostrmarket.direct_messages WHERE merchant_id = :merchant_id",
        {"merchant_id": merchant_id},
    )


######################################## CUSTOMERS #####################################


async def create_customer(merchant_id: str, data: Customer) -> Customer:
    await db.execute(
        """
        INSERT INTO nostrmarket.customers (merchant_id, public_key, meta)
        VALUES (:merchant_id, :public_key, :meta)
        """,
        {
            "merchant_id": merchant_id,
            "public_key": data.public_key,
            "meta": json.dumps(data.profile) if data.profile else "{}",
        },
    )

    customer = await get_customer(merchant_id, data.public_key)
    assert customer, "Newly created customer couldn't be retrieved"
    return customer


async def get_customer(merchant_id: str, public_key: str) -> Optional[Customer]:
    row: dict = await db.fetchone(
        """
            SELECT * FROM nostrmarket.customers
            WHERE merchant_id = :merchant_id AND public_key = :public_key
        """,
        {
            "merchant_id": merchant_id,
            "public_key": public_key,
        },
    )
    return Customer.from_row(row) if row else None


async def get_customers(merchant_id: str) -> List[Customer]:
    rows: list[dict] = await db.fetchall(
        "SELECT * FROM nostrmarket.customers WHERE merchant_id = :merchant_id",
        {"merchant_id": merchant_id},
    )
    return [Customer.from_row(row) for row in rows]


async def get_all_unique_customers() -> List[Customer]:
    q = """
            SELECT public_key, MAX(merchant_id) as merchant_id, MAX(event_created_at)
            FROM nostrmarket.customers
            GROUP BY public_key
        """
    rows: list[dict] = await db.fetchall(q)
    return [Customer.from_row(row) for row in rows]


async def update_customer_profile(
    public_key: str, event_created_at: int, profile: CustomerProfile
):
    await db.execute(
        """
        UPDATE nostrmarket.customers
        SET event_created_at = :event_created_at, meta = :meta
        WHERE public_key = :public_key
        """,
        {
            "event_created_at": event_created_at,
            "meta": json.dumps(profile.dict()),
            "public_key": public_key,
        },
    )


async def increment_customer_unread_messages(merchant_id: str, public_key: str):
    await db.execute(
        """
        UPDATE nostrmarket.customers
        SET unread_messages = unread_messages + 1
        WHERE merchant_id = :merchant_id AND public_key = :public_key
        """,
        {
            "merchant_id": merchant_id,
            "public_key": public_key,
        },
    )


# ??? two merchants
async def update_customer_no_unread_messages(merchant_id: str, public_key: str):
    await db.execute(
        """
        UPDATE nostrmarket.customers
        SET unread_messages = 0
        WHERE merchant_id = :merchant_id AND public_key = :public_key
        """,
        {
            "merchant_id": merchant_id,
            "public_key": public_key,
        },
    )
