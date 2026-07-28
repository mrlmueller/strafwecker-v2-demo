from fastapi import APIRouter, Query
from typing import Optional
from app.repositories import network_repository as repo

router = APIRouter(prefix="/network", tags=["network"])
alias_router = APIRouter(tags=["network"])


def _network_logs(
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    minimal: bool = False,
):
    result = repo.get_paginated(limit=limit, page=page,
                                start_date=start_date, end_date=end_date, minimal=minimal)
    return {
        "data": result.data,
        "meta": {"page": result.page, "limit": result.limit,
                 "total": result.total, "pages": result.pages},
    }


@router.get("/logs")
def get_network_logs(
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    minimal: bool = False,
):
    return _network_logs(limit, page, start_date, end_date, minimal)


@alias_router.get("/network_logs")
def get_network_logs_alias(
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    minimal: bool = False,
):
    return _network_logs(limit, page, start_date, end_date, minimal)
