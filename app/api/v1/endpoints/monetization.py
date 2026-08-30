from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies import get_db, get_current_user_optional
from app.services.monetization_service import MonetizationService
from app.schemas.monetization import AdConfigPublicResponse, SponsorResponse, AffiliateProductResponse

router = APIRouter()

@router.get("/ad-config", response_model=AdConfigPublicResponse)
async def get_ad_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional)
):
    """Get the public ad configuration."""
    service = MonetizationService(db)
    # The config returned does not expose any health data or user information.
    # It strictly returns the environment configs and active ad placements.
    return await service.get_public_ad_config()

@router.get("/sponsors", response_model=List[SponsorResponse])
async def get_sponsors(
    db: AsyncSession = Depends(get_db)
):
    """Get all active sponsors."""
    service = MonetizationService(db)
    return await service.get_sponsors()

@router.get("/affiliate-products", response_model=List[AffiliateProductResponse])
async def get_affiliate_products(
    db: AsyncSession = Depends(get_db)
):
    """Get all active affiliate products."""
    service = MonetizationService(db)
    return await service.get_affiliate_products()
