import json
import time
from sqlite3 import Row
from typing import List, Optional

from pydantic import BaseModel

from .helpers import sign_message_hash
from .nostr.event import NostrEvent


######################################## MERCHANT ########################################
class MerchantConfig(BaseModel):
    name: Optional[str]


class PartialMerchant(BaseModel):
    private_key: str
    public_key: str
    config: MerchantConfig = MerchantConfig()


class Merchant(PartialMerchant):
    id: str

    def sign_hash(self, hash: bytes) -> str:
        return sign_message_hash(self.private_key, hash)

    @classmethod
    def from_row(cls, row: Row) -> "Merchant":
        merchant = cls(**dict(row))
        merchant.config = MerchantConfig(**json.loads(row["meta"]))
        return merchant


######################################## ZONES ########################################
class PartialZone(BaseModel):
    name: Optional[str]
    currency: str
    cost: float
    countries: List[str] = []


class Zone(PartialZone):
    id: str

    @classmethod
    def from_row(cls, row: Row) -> "Zone":
        zone = cls(**dict(row))
        zone.countries = json.loads(row["regions"])
        return zone


######################################## STALLS ########################################


class StallConfig(BaseModel):
    """Last published nostr event id for this Stall"""

    event_id: Optional[str]
    image_url: Optional[str]
    description: Optional[str]


class PartialStall(BaseModel):
    wallet: str
    name: str
    currency: str = "sat"
    shipping_zones: List[PartialZone] = []
    config: StallConfig = StallConfig()

    def validate_stall(self):
        for z in self.shipping_zones:
            if z.currency != self.currency:
                raise ValueError(
                    f"Sipping zone '{z.name}' has different currency than stall."
                )


class Stall(PartialStall):
    id: str

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content = {
            "name": self.name,
            "description": self.config.description,
            "currency": self.currency,
            "shipping": [dict(z) for z in self.shipping_zones],
        }
        event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=30005,
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
            tags=[["e", self.config.event_id]],
            content="Stall deleted",
        )
        delete_event.id = delete_event.event_id

        return delete_event

    @classmethod
    def from_row(cls, row: Row) -> "Stall":
        stall = cls(**dict(row))
        stall.config = StallConfig(**json.loads(row["meta"]))
        stall.shipping_zones = [PartialZone(**z) for z in json.loads(row["zones"])]
        return stall
