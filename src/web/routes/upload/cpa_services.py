"""
CPA Service Management API Routing
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ....database import crud
from ....database.session import get_db
from ....core.upload.cpa_upload import test_cpa_connection

router = APIRouter()


# ============== Pydantic Models ==============

class CpaServiceCreate(BaseModel):
    name: str
    api_url: str
    api_token: str
    enabled: bool = True
    priority: int = 0


class CpaServiceUpdate(BaseModel):
    name: Optional[str] = None
    api_url: Optional[str] = None
    api_token: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class CpaServiceResponse(BaseModel):
    id: int
    name: str
    api_url: str
    has_token: bool
    enabled: bool
    priority: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CpaServiceTestRequest(BaseModel):
    api_url: Optional[str] = None
    api_token: Optional[str] = None


def _to_response(svc) -> CpaServiceResponse:
    return CpaServiceResponse(
        id=svc.id,
        name=svc.name,
        api_url=svc.api_url,
        has_token=bool(svc.api_token),
        enabled=svc.enabled,
        priority=svc.priority,
        created_at=svc.created_at.isoformat() if svc.created_at else None,
        updated_at=svc.updated_at.isoformat() if svc.updated_at else None,
    )


# ============== API Endpoints ==============

@router.get("", response_model=List[CpaServiceResponse])
async def list_cpa_services(enabled: Optional[bool] = None):
    """Get CPA service list"""
    with get_db() as db:
        services = crud.get_cpa_services(db, enabled=enabled)
        return [_to_response(s) for s in services]


@router.post("", response_model=CpaServiceResponse)
async def create_cpa_service(request: CpaServiceCreate):
    """Add CPA service"""
    with get_db() as db:
        service = crud.create_cpa_service(
            db,
            name=request.name,
            api_url=request.api_url,
            api_token=request.api_token,
            enabled=request.enabled,
            priority=request.priority,
        )
        return _to_response(service)


@router.get("/{service_id}", response_model=CpaServiceResponse)
async def get_cpa_service(service_id: int):
    """Get individual CPA service details"""
    with get_db() as db:
        service = crud.get_cpa_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="CPA service does not exist")
        return _to_response(service)


@router.get("/{service_id}/full")
async def get_cpa_service_full(service_id: int):
    """Get the complete configuration of CPA service (including token)"""
    with get_db() as db:
        service = crud.get_cpa_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="CPA service does not exist")
        return {
            "id": service.id,
            "name": service.name,
            "api_url": service.api_url,
            "api_token": service.api_token,
            "enabled": service.enabled,
            "priority": service.priority,
        }


@router.patch("/{service_id}", response_model=CpaServiceResponse)
async def update_cpa_service(service_id: int, request: CpaServiceUpdate):
    """Update CPA service configuration"""
    with get_db() as db:
        service = crud.get_cpa_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="CPA service does not exist")

        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.api_url is not None:
            update_data["api_url"] = request.api_url
        # api_token If left blank, the original value will be retained.
        if request.api_token:
            update_data["api_token"] = request.api_token
        if request.enabled is not None:
            update_data["enabled"] = request.enabled
        if request.priority is not None:
            update_data["priority"] = request.priority

        service = crud.update_cpa_service(db, service_id, **update_data)
        return _to_response(service)


@router.delete("/{service_id}")
async def delete_cpa_service(service_id: int):
    """Delete CPA service"""
    with get_db() as db:
        service = crud.get_cpa_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="CPA service does not exist")
        crud.delete_cpa_service(db, service_id)
        return {"success": True, "message": f"CPA service {service.name} has been deleted"}


@router.post("/{service_id}/test")
async def test_cpa_service(service_id: int):
    """Test CPA service connection"""
    with get_db() as db:
        service = crud.get_cpa_service_by_id(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="CPA service does not exist")
        success, message = test_cpa_connection(service.api_url, service.api_token)
        return {"success": success, "message": message}


@router.post("/test-connection")
async def test_cpa_connection_direct(request: CpaServiceTestRequest):
    """Test CPA connection directly (for pre-add verification)"""
    if not request.api_url or not request.api_token:
        raise HTTPException(status_code=400, detail="api_url and api_token cannot be empty")
    success, message = test_cpa_connection(request.api_url, request.api_token)
    return {"success": success, "message": message}
