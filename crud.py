import json
from typing import List, Optional

from lnbits.helpers import urlsafe_short_hash

from . import db
from .models import Merchant, PartialMerchant, PartialZone, Zone

######################################## MERCHANT ########################################


async def create_merchant(user_id: str, m: PartialMerchant) -> Merchant:
    merchant_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nostrmarket.merchants (user_id, id, private_key, public_key, meta)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, merchant_id, m.private_key, m.public_key, json.dumps(dict(m.config))),
    )
    merchant = await get_merchant(user_id, merchant_id)
    assert merchant, "Created merchant cannot be retrieved"
    return merchant


async def get_merchant(user_id: str, merchant_id: str) -> Optional[Merchant]:
    row = await db.fetchone(
        """SELECT * FROM nostrmarket.merchants WHERE user_id = ? AND id = ?""",
        (
            user_id,
            merchant_id,
        ),
    )

    return Merchant.from_row(row) if row else None


async def get_merchant_for_user(user_id: str) -> Optional[Merchant]:
    row = await db.fetchone(
        """SELECT * FROM nostrmarket.merchants WHERE user_id = ? """,
        (user_id,),
    )

    return Merchant.from_row(row) if row else None


######################################## ZONES ########################################


async def create_zone(user_id: str, data: PartialZone) -> Zone:
    zone_id = urlsafe_short_hash()
    await db.execute(
        f"""
        INSERT INTO nostrmarket.zones (
            id,
            user_id,
            name,
            currency,
            cost,
            regions

        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            zone_id,
            user_id,
            data.name,
            data.currency,
            data.cost,
            json.dumps(data.countries),
        ),
    )

    zone = await get_zone(user_id, zone_id)
    assert zone, "Newly created zone couldn't be retrieved"
    return zone


async def update_zone(user_id: str, z: Zone) -> Optional[Zone]:
    await db.execute(
        f"UPDATE nostrmarket.zones SET name = ?, cost = ?, regions = ?  WHERE id = ? AND user_id = ?",
        (z.name, z.cost, json.dumps(z.countries), z.id, user_id),
    )
    return await get_zone(user_id, z.id)


async def get_zone(user_id: str, zone_id: str) -> Optional[Zone]:
    row = await db.fetchone(
        "SELECT * FROM nostrmarket.zones WHERE user_id = ? AND id = ?",
        (
            user_id,
            zone_id,
        ),
    )
    return Zone.from_row(row) if row else None


async def get_zones(user_id: str) -> List[Zone]:
    rows = await db.fetchall(
        "SELECT * FROM nostrmarket.zones WHERE user_id = ?", (user_id,)
    )
    return [Zone.from_row(row) for row in rows]


async def delete_zone(zone_id: str) -> None:
    await db.execute("DELETE FROM nostrmarket.zones WHERE id = ?", (zone_id,))
