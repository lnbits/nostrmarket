import json
from sqlite3 import Row
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel


######################################## MERCHANT ########################################
class MerchantConfig(BaseModel):
    name: Optional[str]


class PartialMerchant(BaseModel):
    private_key: str
    public_key: str
    config: MerchantConfig = MerchantConfig()


class Merchant(PartialMerchant):
    id: str

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
    image_url: Optional[str]
    fiat_base_multiplier: int = 1  # todo: reminder wht is this for?


class PartialStall(BaseModel):
    wallet: str
    name: str
    currency: str = "sat"
    shipping_zones: List[str] = []
    config: StallConfig = StallConfig()


class Stall(PartialStall):
    id: str

    @classmethod
    def from_row(cls, row: Row) -> "Stall":
        stall = cls(**dict(row))
        stall.config = StallConfig(**json.loads(row["meta"]))
        stall.shipping_zones = json.loads(row["zones"])
        return stall
