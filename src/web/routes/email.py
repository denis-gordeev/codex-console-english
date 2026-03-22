"""
Email service configuration API routing
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...database import crud
from ...database.session import get_db
from ...database.models import EmailService as EmailServiceModel
from ...services import EmailServiceFactory, EmailServiceType

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Pydantic Models ==============

class EmailServiceCreate(BaseModel):
    """Create mailbox service request"""
    service_type: str
    name: str
    config: Dict[str, Any]
    enabled: bool = True
    priority: int = 0


class EmailServiceUpdate(BaseModel):
    """Update Mailbox Service Request"""
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class EmailServiceResponse(BaseModel):
    """Mailbox service response"""
    id: int
    service_type: str
    name: str
    enabled: bool
    priority: int
    config: Optional[Dict[str, Any]] = None # Configuration after filtering sensitive information
    last_used: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class EmailServiceListResponse(BaseModel):
    """Mailbox service list response"""
    total: int
    services: List[EmailServiceResponse]


class ServiceTestResult(BaseModel):
    """Service test results"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class OutlookBatchImportRequest(BaseModel):
    """Outlook bulk import request"""
    data: str #Multiple lines of data, each line format: email----password or email----password----client_id----refresh_token
    enabled: bool = True
    priority: int = 0


class OutlookBatchImportResponse(BaseModel):
    """Outlook batch import response"""
    total: int
    success: int
    failed: int
    accounts: List[Dict[str, Any]]
    errors: List[str]


# ============== Helper Functions ==============

# List of sensitive fields, which need to be filtered when returning the response
SENSITIVE_FIELDS = {'password', 'api_key', 'refresh_token', 'access_token', 'admin_token'}

def filter_sensitive_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Filter sensitive configuration information"""
    if not config:
        return {}

    filtered = {}
    for key, value in config.items():
        if key in SENSITIVE_FIELDS:
            # Sensitive fields are not returned, but whether the tag exists
            filtered[f"has_{key}"] = bool(value)
        else:
            filtered[key] = value

    # Calculate whether there is OAuth for Outlook
    if config.get('client_id') and config.get('refresh_token'):
        filtered['has_oauth'] = True

    return filtered


def service_to_response(service: EmailServiceModel) -> EmailServiceResponse:
    """Convert service model to response"""
    return EmailServiceResponse(
        id=service.id,
        service_type=service.service_type,
        name=service.name,
        enabled=service.enabled,
        priority=service.priority,
        config=filter_sensitive_config(service.config),
        last_used=service.last_used.isoformat() if service.last_used else None,
        created_at=service.created_at.isoformat() if service.created_at else None,
        updated_at=service.updated_at.isoformat() if service.updated_at else None,
    )


# ============== API Endpoints ==============

@router.get("/stats")
async def get_email_services_stats():
    """Get mailbox service statistics"""
    with get_db() as db:
        from sqlalchemy import func

        # Statistics by type
        type_stats = db.query(
            EmailServiceModel.service_type,
            func.count(EmailServiceModel.id)
        ).group_by(EmailServiceModel.service_type).all()

        # enable quantity
        enabled_count = db.query(func.count(EmailServiceModel.id)).filter(
            EmailServiceModel.enabled == True
        ).scalar()

        stats = {
            'outlook_count': 0,
            'custom_count': 0,
            'temp_mail_count': 0,
            'duck_mail_count': 0,
            'freemail_count': 0,
            'imap_mail_count': 0,
            'tempmail_available': True, # Temporary mailbox is always available
            'enabled_count': enabled_count
        }

        for service_type, count in type_stats:
            if service_type == 'outlook':
                stats['outlook_count'] = count
            elif service_type == 'moe_mail':
                stats['custom_count'] = count
            elif service_type == 'temp_mail':
                stats['temp_mail_count'] = count
            elif service_type == 'duck_mail':
                stats['duck_mail_count'] = count
            elif service_type == 'freemail':
                stats['freemail_count'] = count
            elif service_type == 'imap_mail':
                stats['imap_mail_count'] = count

        return stats


@router.get("/types")
async def get_service_types():
    """Get supported email service types"""
    return {
        "types": [
            {
                "value": "tempmail",
                "label": "Tempmail.lol",
                "description": "Temporary mailbox service, no configuration required",
                "config_fields": [
                    {"name": "base_url", "label": "API address", "default": "https://api.tempmail.lol/v2", "required": False},
                    {"name": "timeout", "label": "timeout", "default": 30, "required": False},
                ]
            },
            {
                "value": "outlook",
                "label": "Outlook",
                "description": "Outlook mailbox, account information needs to be configured",
                "config_fields": [
                    {"name": "email", "label": "Email address", "required": True},
                    {"name": "password", "label": "password", "required": True},
                    {"name": "client_id", "label": "OAuth Client ID", "required": False},
                    {"name": "refresh_token", "label": "OAuth Refresh Token", "required": False},
                ]
            },
            {
                "value": "moe_mail",
                "label": "MoeMail",
                "description": "Customized domain name email service",
                "config_fields": [
                    {"name": "base_url", "label": "API address", "required": True},
                    {"name": "api_key", "label": "API Key", "required": True},
                    {"name": "default_domain", "label": "Default domain name", "required": False},
                ]
            },
            {
                "value": "temp_mail",
                "label": "Temp-Mail (self-deployment)",
                "description": "Self-deployed Cloudflare Worker temporary mailbox, admin mode management",
                "config_fields": [
                    {"name": "base_url", "label": "Worker address", "required": True, "placeholder": "https://mail.example.com"},
                    {"name": "admin_password", "label": "Admin password", "required": True, "secret": True},
                    {"name": "domain", "label": "Email domain name", "required": True, "placeholder": "example.com"},
                    {"name": "enable_prefix", "label": "Enable prefix", "required": False, "default": True},
                ]
            },
            {
                "value": "duck_mail",
                "label": "DuckMail",
                "description": "DuckMail interface email service, supports API Key private domain name access",
                "config_fields": [
                    {"name": "base_url", "label": "API address", "required": True, "placeholder": "https://api.duckmail.sbs"},
                    {"name": "default_domain", "label": "Default domain name", "required": True, "placeholder": "duckmail.sbs"},
                    {"name": "api_key", "label": "API Key", "required": False, "secret": True},
                    {"name": "password_length", "label": "Random password length", "required": False, "default": 12},
                ]
            },
            {
                "value": "freemail",
                "label": "Freemail",
                "description": "Freemail self-deployed Cloudflare Worker temporary mailbox service",
                "config_fields": [
                    {"name": "base_url", "label": "API address", "required": True, "placeholder": "https://freemail.example.com"},
                    {"name": "admin_token", "label": "Admin Token", "required": True, "secret": True},
                    {"name": "domain", "label": "Email domain name", "required": False, "placeholder": "example.com"},
                ]
            },
            {
                "value": "imap_mail",
                "label": "IMAP mailbox",
                "description": "Standard IMAP protocol email (Gmail/QQ/163, etc.), only used to receive verification codes, forced direct connection",
                "config_fields": [
                    {"name": "host", "label": "IMAP Server", "required": True, "placeholder": "imap.gmail.com"},
                    {"name": "port", "label": "port", "required": False, "default": 993},
                    {"name": "use_ssl", "label": "Use SSL", "required": False, "default": True},
                    {"name": "email", "label": "Email address", "required": True},
                    {"name": "password", "label": "Password/Authorization Code", "required": True, "secret": True},
                ]
            }
        ]
    }


@router.get("", response_model=EmailServiceListResponse)
async def list_email_services(
    service_type: Optional[str] = Query(None, description="Service type filtering"),
    enabled_only: bool = Query(False, description="Only show enabled services"),
):
    """Get email service list"""
    with get_db() as db:
        query = db.query(EmailServiceModel)

        if service_type:
            query = query.filter(EmailServiceModel.service_type == service_type)

        if enabled_only:
            query = query.filter(EmailServiceModel.enabled == True)

        services = query.order_by(EmailServiceModel.priority.asc(), EmailServiceModel.id.asc()).all()

        return EmailServiceListResponse(
            total=len(services),
            services=[service_to_response(s) for s in services]
        )


@router.get("/{service_id}", response_model=EmailServiceResponse)
async def get_email_service(service_id: int):
    """Get individual email service details"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")
        return service_to_response(service)


@router.get("/{service_id}/full")
async def get_email_service_full(service_id: int):
    """Get complete details of a single email service (including sensitive fields for editing)"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")

        return {
            "id": service.id,
            "service_type": service.service_type,
            "name": service.name,
            "enabled": service.enabled,
            "priority": service.priority,
            "config": service.config or {}, # Return the complete configuration
            "last_used": service.last_used.isoformat() if service.last_used else None,
            "created_at": service.created_at.isoformat() if service.created_at else None,
            "updated_at": service.updated_at.isoformat() if service.updated_at else None,
        }


@router.post("", response_model=EmailServiceResponse)
async def create_email_service(request: EmailServiceCreate):
    """Create mailbox service configuration"""
    # Verify service type
    try:
        EmailServiceType(request.service_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid service type: {request.service_type}")

    with get_db() as db:
        # Check if the name is duplicated
        existing = db.query(EmailServiceModel).filter(EmailServiceModel.name == request.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Service name already exists")

        service = EmailServiceModel(
            service_type=request.service_type,
            name=request.name,
            config=request.config,
            enabled=request.enabled,
            priority=request.priority
        )
        db.add(service)
        db.commit()
        db.refresh(service)

        return service_to_response(service)


@router.patch("/{service_id}", response_model=EmailServiceResponse)
async def update_email_service(service_id: int, request: EmailServiceUpdate):
    """Update mailbox service configuration"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")

        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.config is not None:
            # Merge configuration instead of replacing
            current_config = service.config or {}
            merged_config = {**current_config, **request.config}
            # Remove null values
            merged_config = {k: v for k, v in merged_config.items() if v}
            update_data["config"] = merged_config
        if request.enabled is not None:
            update_data["enabled"] = request.enabled
        if request.priority is not None:
            update_data["priority"] = request.priority

        for key, value in update_data.items():
            setattr(service, key, value)

        db.commit()
        db.refresh(service)

        return service_to_response(service)


@router.delete("/{service_id}")
async def delete_email_service(service_id: int):
    """Delete mailbox service configuration"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")

        db.delete(service)
        db.commit()

        return {"success": True, "message": f"Service {service.name} has been deleted"}


@router.post("/{service_id}/test", response_model=ServiceTestResult)
async def test_email_service(service_id: int):
    """Test whether the email service is available"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")

        try:
            service_type = EmailServiceType(service.service_type)
            email_service = EmailServiceFactory.create(service_type, service.config, name=service.name)

            health = email_service.check_health()

            if health:
                return ServiceTestResult(
                    success=True,
                    message="Service connection is normal",
                    details=email_service.get_service_info() if hasattr(email_service, 'get_service_info') else None
                )
            else:
                return ServiceTestResult(
                    success=False,
                    message="Service connection failed"
                )

        except Exception as e:
            logger.error(f"Test mailbox service failed: {e}")
            return ServiceTestResult(
                success=False,
                message=f"Test failed: {str(e)}"
            )


@router.post("/{service_id}/enable")
async def enable_email_service(service_id: int):
    """Enable mailbox service"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")

        service.enabled = True
        db.commit()

        return {"success": True, "message": f"Service {service.name} is enabled"}


@router.post("/{service_id}/disable")
async def disable_email_service(service_id: int):
    """Disable mailbox service"""
    with get_db() as db:
        service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service does not exist")

        service.enabled = False
        db.commit()

        return {"success": True, "message": f"Service {service.name} is disabled"}


@router.post("/reorder")
async def reorder_services(service_ids: List[int]):
    """Reorder mailbox service priority"""
    with get_db() as db:
        for index, service_id in enumerate(service_ids):
            service = db.query(EmailServiceModel).filter(EmailServiceModel.id == service_id).first()
            if service:
                service.priority = index

        db.commit()

        return {"success": True, "message": "Priority has been updated"}


@router.post("/outlook/batch-import", response_model=OutlookBatchImportResponse)
async def batch_import_outlook(request: OutlookBatchImportRequest):
    """
    Batch import Outlook email accounts

    Two formats are supported:
    - Format 1 (password authentication): Email ---- Password
    - Format 2 (XOAUTH2 authentication): Email----Password----client_id----refresh_token

    One account per line, using four hyphens (----) to separate fields
    """
    lines = request.data.strip().split("\n")
    total = len(lines)
    success = 0
    failed = 0
    accounts = []
    errors = []

    with get_db() as db:
        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            parts = line.split("----")

            # Verify format
            if len(parts) < 2:
                failed += 1
                errors.append(f"Line {i+1}: format error, at least email and password required")
                continue

            email = parts[0].strip()
            password = parts[1].strip()

            # Verify email format
            if "@" not in email:
                failed += 1
                errors.append(f"Line {i+1}: Invalid email address: {email}")
                continue

            # Check if it already exists
            existing = db.query(EmailServiceModel).filter(
                EmailServiceModel.service_type == "outlook",
                EmailServiceModel.name == email
            ).first()

            if existing:
                failed += 1
                errors.append(f"Line {i+1}: Email already exists: {email}")
                continue

            # Build configuration
            config = {
                "email": email,
                "password": password
            }

            # Check if there is OAuth information (format 2)
            if len(parts) >= 4:
                client_id = parts[2].strip()
                refresh_token = parts[3].strip()
                if client_id and refresh_token:
                    config["client_id"] = client_id
                    config["refresh_token"] = refresh_token

            #Create service record
            try:
                service = EmailServiceModel(
                    service_type="outlook",
                    name=email,
                    config=config,
                    enabled=request.enabled,
                    priority=request.priority
                )
                db.add(service)
                db.commit()
                db.refresh(service)

                accounts.append({
                    "id": service.id,
                    "email": email,
                    "has_oauth": bool(config.get("client_id")),
                    "name": email
                })
                success += 1

            except Exception as e:
                failed += 1
                errors.append(f"Line {i+1}: Creation failed: {str(e)}")
                db.rollback()

    return OutlookBatchImportResponse(
        total=total,
        success=success,
        failed=failed,
        accounts=accounts,
        errors=errors
    )


@router.delete("/outlook/batch")
async def batch_delete_outlook(service_ids: List[int]):
    """Delete Outlook mailbox services in batches"""
    deleted = 0
    with get_db() as db:
        for service_id in service_ids:
            service = db.query(EmailServiceModel).filter(
                EmailServiceModel.id == service_id,
                EmailServiceModel.service_type == "outlook"
            ).first()
            if service:
                db.delete(service)
                deleted += 1
        db.commit()

    return {"success": True, "deleted": deleted, "message": f"{deleted} services have been deleted"}


# ============== Temporary mailbox test ==============

class TempmailTestRequest(BaseModel):
    """Temporary mailbox test request"""
    api_url: Optional[str] = None


@router.post("/test-tempmail")
async def test_tempmail_service(request: TempmailTestRequest):
    """Test whether the temporary mailbox service is available"""
    try:
        from ...services import EmailServiceFactory, EmailServiceType
        from ...config.settings import get_settings

        settings = get_settings()
        base_url = request.api_url or settings.tempmail_base_url

        config = {"base_url": base_url}
        tempmail = EmailServiceFactory.create(EmailServiceType.TEMPMAIL, config)

        # Check service health status
        health = tempmail.check_health()

        if health:
            return {"success": True, "message": "The temporary mailbox connection is normal"}
        else:
            return {"success": False, "message": "Temporary mailbox connection failed"}

    except Exception as e:
        logger.error(f"Failed to test temporary mailbox: {e}")
        return {"success": False, "message": f"Test failed: {str(e)}"}
