from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Sequence
import json

from app.models.monetization import AdPlacementConfig, Sponsor, AffiliatePartner, AffiliateProduct
from app.core.config import get_settings
from app.schemas.monetization import AdConfigPublicResponse, AdPlacementConfigResponse

settings = get_settings()

class MonetizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_public_ad_config(self) -> AdConfigPublicResponse:
        """Fetch the public ad configurations securely without exposing secrets."""
        # Fetch enabled placements
        result = await self.db.execute(
            select(AdPlacementConfig).where(AdPlacementConfig.is_enabled == True)
        )
        placements = result.scalars().all()
        
        placements_dict = {}
        for p in placements:
            placements_dict[p.placement] = AdPlacementConfigResponse.model_validate(p)

        return AdConfigPublicResponse(
            ads_enabled=settings.public_ads_enabled,
            provider="ADSENSE" if settings.adsense_publisher_id else ("GAM" if settings.ad_manager_network_id else "NONE"),
            publisher_id=settings.adsense_publisher_id,
            network_id=settings.ad_manager_network_id,
            placements=placements_dict
        )

    async def get_sponsors(self) -> Sequence[Sponsor]:
        result = await self.db.execute(
            select(Sponsor).order_by(Sponsor.name)
        )
        return result.scalars().all()

    async def create_sponsor(self, data: dict) -> Sponsor:
        s = Sponsor(**data)
        self.db.add(s)
        await self.db.commit()
        await self.db.refresh(s)
        return s

    async def update_sponsor(self, sponsor_id: str, data: dict) -> Sponsor | None:
        result = await self.db.execute(select(Sponsor).where(Sponsor.id == sponsor_id))
        s = result.scalars().first()
        if not s:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(s, k, v)
        await self.db.commit()
        await self.db.refresh(s)
        return s

    async def get_affiliate_partners(self) -> Sequence[AffiliatePartner]:
        result = await self.db.execute(
            select(AffiliatePartner).order_by(AffiliatePartner.name)
        )
        return result.scalars().all()

    async def create_affiliate_partner(self, data: dict) -> AffiliatePartner:
        p = AffiliatePartner(**data)
        self.db.add(p)
        await self.db.commit()
        await self.db.refresh(p)
        return p

    async def update_affiliate_partner(self, partner_id: str, data: dict) -> AffiliatePartner | None:
        result = await self.db.execute(select(AffiliatePartner).where(AffiliatePartner.id == partner_id))
        p = result.scalars().first()
        if not p:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(p, k, v)
        await self.db.commit()
        await self.db.refresh(p)
        return p

    async def get_affiliate_products(self, only_active: bool = False) -> Sequence[AffiliateProduct]:
        stmt = select(AffiliateProduct).order_by(AffiliateProduct.name)
        if only_active:
            stmt = stmt.where(AffiliateProduct.status == "ACTIVE")
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_affiliate_product(self, data: dict) -> AffiliateProduct:
        p = AffiliateProduct(**data)
        self.db.add(p)
        await self.db.commit()
        await self.db.refresh(p)
        return p

    async def update_affiliate_product(self, product_id: str, data: dict) -> AffiliateProduct | None:
        result = await self.db.execute(select(AffiliateProduct).where(AffiliateProduct.id == product_id))
        p = result.scalars().first()
        if not p:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(p, k, v)
        await self.db.commit()
        await self.db.refresh(p)
        return p
