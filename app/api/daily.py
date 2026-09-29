"""Daily Business France offers API, independent of application database state."""

from datetime import date as calendar_date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.business_france_daily_service import BusinessFranceDailyService


router = APIRouter(prefix="/api/business-france", tags=["business-france"])


def get_daily_service() -> BusinessFranceDailyService:
    return BusinessFranceDailyService()


async def _daily_payload(date: str | None, verify_external: bool, use_cache: bool, service: BusinessFranceDailyService):
    if date is not None:
        try:
            if calendar_date.fromisoformat(date).isoformat() != date:
                raise ValueError
        except ValueError:
            raise HTTPException(status_code=422, detail="date must be a valid calendar date in YYYY-MM-DD format") from None
    try:
        return await service.get_daily_offers(
            requested_date=date, verify_external=verify_external, use_cache=use_cache,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/daily")
async def get_business_france_daily_offers(
    date: str | None = Query(default=None),
    refresh: bool = False,
    verify_external: bool = True,
    service: BusinessFranceDailyService = Depends(get_daily_service),
):
    """Return source offers for the broadcast date; refresh bypasses the cache."""
    return await _daily_payload(date, verify_external, not refresh, service)


@router.get("/daily-offers", include_in_schema=False)
async def get_business_france_daily_offers_legacy(
    date: str | None = Query(default=None),
    verify_external: bool = True,
    use_cache: bool = True,
    service: BusinessFranceDailyService = Depends(get_daily_service),
):
    return await _daily_payload(date, verify_external, use_cache, service)
