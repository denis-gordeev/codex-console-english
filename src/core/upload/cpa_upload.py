"""CPA (Codex Protocol API) upload function"""

import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from urllib.parse import quote

from curl_cffi import requests as cffi_requests
from curl_cffi import CurlMime

from ...database.session import get_db
from ...database.models import Account
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


def _normalize_cpa_auth_files_url(api_url: str) -> str:
    """Normalize the CPA address filled in by the user to the auth-files interface address."""
    normalized = (api_url or "").strip().rstrip("/")
    lower_url = normalized.lower()

    if not normalized:
        return ""

    if lower_url.endswith("/auth-files"):
        return normalized

    if lower_url.endswith("/v0/management") or lower_url.endswith("/management"):
        return f"{normalized}/auth-files"

    if lower_url.endswith("/v0"):
        return f"{normalized}/management/auth-files"

    return f"{normalized}/v0/management/auth-files"


def _build_cpa_headers(api_token: str, content_type: Optional[str] = None) -> dict:
    headers = {
        "Authorization": f"Bearer {api_token}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _extract_cpa_error(response) -> str:
    error_msg = f"Upload failed: HTTP {response.status_code}"
    try:
        error_detail = response.json()
        if isinstance(error_detail, dict):
            error_msg = error_detail.get("message", error_msg)
    except Exception:
        error_msg = f"{error_msg} - {response.text[:200]}"
    return error_msg


def _post_cpa_auth_file_multipart(upload_url: str, filename: str, file_content: bytes, api_token: str):
    mime = CurlMime()
    mime.addpart(
        name="file",
        data=file_content,
        filename=filename,
        content_type="application/json",
    )

    return cffi_requests.post(
        upload_url,
        multipart=mime,
        headers=_build_cpa_headers(api_token),
        proxies=None,
        timeout=30,
        impersonate="chrome110",
    )


def _post_cpa_auth_file_raw_json(upload_url: str, filename: str, file_content: bytes, api_token: str):
    raw_upload_url = f"{upload_url}?name={quote(filename)}"
    return cffi_requests.post(
        raw_upload_url,
        data=file_content,
        headers=_build_cpa_headers(api_token, content_type="application/json"),
        proxies=None,
        timeout=30,
        impersonate="chrome110",
    )


def generate_token_json(account: Account) -> dict:
    """Generate Token JSON in CPA format

    Args:
        account: account model instance

    Returns:
        Token dictionary in CPA format"""
    return {
        "type": "codex",
        "email": account.email,
        "expired": account.expires_at.strftime("%Y-%m-%dT%H:%M:%S+08:00") if account.expires_at else "",
        "id_token": account.id_token or "",
        "account_id": account.account_id or "",
        "access_token": account.access_token or "",
        "last_refresh": account.last_refresh.strftime("%Y-%m-%dT%H:%M:%S+08:00") if account.last_refresh else "",
        "refresh_token": account.refresh_token or "",
    }


def upload_to_cpa(
    token_data: dict,
    proxy: str = None,
    api_url: str = None,
    api_token: str = None,
) -> Tuple[bool, str]:
    """Upload a single account to the CPA management platform (without using an agent)

    Args:
        token_data: Token JSON data
        proxy: reserved parameter, not used (CPA upload is always directly connected)
        api_url: Specify CPA API URL (takes precedence over global configuration)
        api_token: Specify CPA API Token (takes precedence over global configuration)

    Returns:
        (success sign, message or error message)"""
    settings = get_settings()

    # Priority is given to using the parameters passed in, otherwise it returns to the global configuration.
    effective_url = api_url or settings.cpa_api_url
    effective_token = api_token or (settings.cpa_api_token.get_secret_value() if settings.cpa_api_token else "")

    # Check global enable switch only if no service is specified
    if not api_url and not settings.cpa_enabled:
        return False, "CPA upload is not enabled"

    if not effective_url:
        return False, "CPA API URL not configured"

    if not effective_token:
        return False, "CPA API Token is not configured"

    upload_url = _normalize_cpa_auth_files_url(effective_url)

    filename = f"{token_data['email']}.json"
    file_content = json.dumps(token_data, ensure_ascii=False, indent=2).encode("utf-8")

    try:
        response = _post_cpa_auth_file_multipart(
            upload_url,
            filename,
            file_content,
            effective_token,
        )

        if response.status_code in (200, 201):
            return True, "Upload successful"

        if response.status_code in (404, 405, 415):
            logger.warning("CPA multipart upload failed, try original JSON fallback: %s", response.status_code)
            fallback_response = _post_cpa_auth_file_raw_json(
                upload_url,
                filename,
                file_content,
                effective_token,
            )
            if fallback_response.status_code in (200, 201):
                return True, "Upload successful"
            response = fallback_response

        return False, _extract_cpa_error(response)

    except Exception as e:
        logger.error(f"CPA upload exception: {e}")
        return False, f"Upload exception: {str(e)}"


def batch_upload_to_cpa(
    account_ids: List[int],
    proxy: str = None,
    api_url: str = None,
    api_token: str = None,
) -> dict:
    """Batch upload accounts to CPA management platform

    Args:
        account_ids: Account ID list
        proxy: optional proxy URL
        api_url: Specify CPA API URL (takes precedence over global configuration)
        api_token: Specify CPA API Token (takes precedence over global configuration)

    Returns:
        Dictionary containing success/failure statistics and details"""
    results = {
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": []
    }

    with get_db() as db:
        for account_id in account_ids:
            account = db.query(Account).filter(Account.id == account_id).first()

            if not account:
                results["failed_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": None,
                    "success": False,
                    "error": "Account does not exist"
                })
                continue

            # Check if there is already a Token
            if not account.access_token:
                results["skipped_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": account.email,
                    "success": False,
                    "error": "Missing Token"
                })
                continue

            # Generate Token JSON
            token_data = generate_token_json(account)

            # upload
            success, message = upload_to_cpa(token_data, proxy, api_url=api_url, api_token=api_token)

            if success:
                # Update database status
                account.cpa_uploaded = True
                account.cpa_uploaded_at = datetime.utcnow()
                db.commit()

                results["success_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": account.email,
                    "success": True,
                    "message": message
                })
            else:
                results["failed_count"] += 1
                results["details"].append({
                    "id": account_id,
                    "email": account.email,
                    "success": False,
                    "error": message
                })

    return results


def test_cpa_connection(api_url: str, api_token: str, proxy: str = None) -> Tuple[bool, str]:
    """Test CPA connection (without proxy)

    Args:
        api_url: CPA API URL
        api_token: CPA API Token
        proxy: reserved parameter, not used (CPA is always directly connected)

    Returns:
        (success sign, message)"""
    if not api_url:
        return False, "API URL cannot be empty"

    if not api_token:
        return False, "API Token cannot be empty"

    test_url = _normalize_cpa_auth_files_url(api_url)
    headers = _build_cpa_headers(api_token)

    try:
        response = cffi_requests.get(
            test_url,
            headers=headers,
            proxies=None,
            timeout=10,
            impersonate="chrome110",
        )

        if response.status_code == 200:
            return True, "CPA connection test successful"
        if response.status_code == 401:
            return False, "Connection successful, but API Token is invalid"
        if response.status_code == 403:
            return False, "The connection is successful, but remote management is not enabled on the server or the current Token has no permissions."
        if response.status_code == 404:
            return False, "CPA auth-files interface not found, please check whether the API URL is filled in as the root address, /v0/management or the complete auth-files address"
        if response.status_code == 503:
            return False, "Connection successful, but server authentication manager is unavailable"

        return False, f"The server returns exception status code: {response.status_code}"

    except cffi_requests.exceptions.ConnectionError as e:
        return False, f"Unable to connect to server: {str(e)}"
    except cffi_requests.exceptions.Timeout:
        return False, "Connection timed out, please check network configuration"
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"
