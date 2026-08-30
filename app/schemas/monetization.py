from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# --- Ads ---
class AdPlacementConfigResponse(BaseModel):
    id: str
    placement: str
    provider: str
    is_enabled: bool
    audience_policy: str
    config_json: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AdConfigPublicResponse(BaseModel):
    """Safe ad configuration for frontend."""
    ads_enabled: bool
    provider: str
    publisher_id: Optional[str]
    network_id: Optional[str]
    placements: dict[str, AdPlacementConfigResponse]

# --- Sponsorship ---
class SponsorCreate(BaseModel):
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None

class SponsorUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class SponsorResponse(BaseModel):
    id: str
    name: str
    logo_url: Optional[str]
    website: Optional[str]
    description: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)

# --- Affiliate ---
class AffiliatePartnerCreate(BaseModel):
    name: str
    website: Optional[str] = None

class AffiliatePartnerUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    status: Optional[str] = None

class AffiliatePartnerResponse(BaseModel):
    id: str
    name: str
    website: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)

class AffiliateProductCreate(BaseModel):
    partner_id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: str
    disclosure_text: Optional[str] = None

class AffiliateProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    disclosure_text: Optional[str] = None
    status: Optional[str] = None

class AffiliateProductResponse(BaseModel):
    id: str
    partner_id: str
    name: str
    description: Optional[str]
    image_url: Optional[str]
    url: str
    disclosure_text: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)
