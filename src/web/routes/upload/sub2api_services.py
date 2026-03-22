"""
Sub2API service management API routing
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ....database import crud
from ....database.session import get_db
from ....core.upload.sub2api_upload import test_sub2api_connection, batch_upload_to_sub2api

router = APIRouter()


# ============== Pydantic Models ==============

class Sub2ApiServiceCreate(BaseModel):
    name: str
    api_url: str
    api_key: str
    enabled: bool = True
    priority: int = 0


class Sub2ApiServiceUpdate(BaseModel):
    name: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class Sub2ApiServiceResponse(BaseModel):
    id: int
    name: str
    api_url: str
    has_key: bool
    enabled: bool
    priority: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class Sub2ApiTestRequest(BaseModel):
    api_url: Optional[str] = None
    api_key: Optional[str] = None


class Sub2ApiUploadRequest(BaseModel):
    account_ids: List[int]
    service_id: Optional[int] = None
    concurrency: int = 3
    priority: int = 50


def _to_response(svc) -> Sub2ApiServiceResponse:
    return Sub2ApiServiceResponse(
        id=svc.id,
        name=svc.name,
        api_url=svc.api_url,
        has_key=bool(svc.api_key),
        enabled=svc.enabled,
        priority=svc.priority,
        created_at=svc.created_at.isoformat() if svc.created_at else None,
        updated_at=svc.updated_at.isoformat() if svc.updated_at else None,
    )


# ============== API Endpoints ==============

@router.get("", response_model=List[Sub2ApiServiceResponse])
async def list_sub2api_services(enabled: Optional[bool] = None):
    """Get Sub2API service list"""
    with get_db() as db:
        services = crud.get_sub2api_services(db, enabled=enabled)
        return [_to_response(s) for s in services]


@router.post("", response_model=Sub2ApiServiceResponse)
async def create_sub2api_service(request: Sub2ApiServiceCreate):
    """Add Sub2API service"""
    with get_db() as db:
        svc = crud.create_sub2api_service(
            db,
            name=request.name,
            api_url=request.api_url,
            api_key=request.api_key,
            enabled=request.enabled,
            priority=request.priority,
        )
        return _to_response(svc)


@router.get("/{service_id}", response_model=Sub2ApiServiceResponse)
async def get_sub2api_service(service_id: int):
    """Get individual Sub2API service details"""
    with get_db() as db:
        svc = crud.get_sub2api_service_by_id(db, service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Sub2API service does not exist")
        return _to_response(svc)


@router.get("/{service_id}/full")
async def get_sub2api_service_full(service_id: int):
    """Get the complete configuration of Sub2API service (including API Key)"""
    with get_db() as db:
        svc = crud.get_sub2api_service_by_id(db, service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Sub2API service does not exist")
        return {
            "id": svc.id,
            "name": svc.name,
            "api_url": svc.api_url,
            "api_key": svc.api_key,
            "enabled": svc.enabled,
            "priority": svc.priority,
        }


@router.patch("/{service_id}", response_model=Sub2ApiServiceResponse)
async def update_sub2api_service(service_id: int, request: Sub2ApiServiceUpdate):
    """Update Sub2API service configuration"""
    with get_db() as db:
        svc = crud.get_sub2api_service_by_id(db, service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Sub2API service does not exist")

        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.api_url is not None:
            update_data["api_url"] = request.api_url
        # api_key If left blank, the original value will be retained.
        if request.api_key:
            update_data["api_key"] = request.api_key
        if request.enabled is not None:
            update_data["enabled"] = request.enabled
        if request.priority is not None:
            update_data["priority"] = request.priority

        svc = crud.update_sub2api_service(db, service_id, **update_data)
        return _to_response(svc)


@router.delete("/{service_id}")
async def delete_sub2api_service(service_id: int):
    """Delete Sub2API service"""
    with get_db() as db:
        svc = crud.get_sub2api_service_by_id(db, service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Sub2API service does not exist")
        crud.delete_sub2api_service(db, service_id)
        return {"success": True, "message": f"Sub2API service {svc.name} has been deleted"}


@router.post("/{service_id}/test")
async def test_sub2api_service(service_id: int):
    """Test Sub2API service connection"""
    with get_db() as db:
        svc = crud.get_sub2api_service_by_id(db, service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Sub2API service does not exist")
        success, message = test_sub2api_connection(svc.api_url, svc.api_key)
        return {"success": success, "message": message}


@router.post("/test-connection")
async def test_sub2api_connection_direct(request: Sub2ApiTestRequest):
    """Test Sub2API connection directly (for verification before adding)"""
    if not request.api_url or not request.api_key:
        raise HTTPException(status_code=400, detail="api_url and api_key cannot be empty")
    success, message = test_sub2api_connection(request.api_url, request.api_key)
    return {"success": success, "message": message}


@router.post("/upload")
async def upload_accounts_to_sub2api(request: Sub2ApiUploadRequest):
    """Batch upload accounts to Sub2API platform"""
    if not request.account_ids:
        raise HTTPException(status_code=400, detail="Account ID list cannot be empty")

    with get_db() as db:
        if request.service_id:
            svc = crud.get_sub2api_service_by_id(db, request.service_id)
        else:
            svcs = crud.get_sub2api_services(db, enabled=True)
            svc = svcs[0] if svcs else None

        if not svc:
            raise HTTPException(status_code=400, detail="No available Sub2API service found")

        api_url = svc.api_url
        api_key = svc.api_key

    results = batch_upload_to_sub2api(
        request.account_ids,
        api_url,
        api_key,
        concurrency=request.concurrency,
        priority=request.priority,
    )
    return results
