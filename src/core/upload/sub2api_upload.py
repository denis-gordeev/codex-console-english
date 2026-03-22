"""
Sub2API account upload function
Batch import accounts into the Sub2API platform in sub2api-data format
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from curl_cffi import requests as cffi_requests

from ...database.session import get_db
from ...database.models import Account

logger = logging.getLogger(__name__)


def upload_to_sub2api(
    accounts: List[Account],
    api_url: str,
    api_key: str,
    concurrency: int = 3,
    priority: int = 50,
) -> Tuple[bool, str]:
    """
    Upload the account list to the Sub2API platform (without using an agent)

    Args:
        accounts: list of account model instances
        api_url: Sub2API address, such as http://host
        api_key: Admin API Key (x-api-key header)
        concurrency: number of concurrent accounts, default 3
        priority: account priority, default 50

    Returns:
        (success sign, message)
    """
    if not accounts:
        return False, "No account to upload"

    if not api_url:
        return False, "Sub2API URL is not configured"

    if not api_key:
        return False, "Sub2API API Key is not configured"

    exported_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    account_items = []
    for acc in accounts:
        if not acc.access_token:
            continue
        expires_at = int(acc.expires_at.timestamp()) if acc.expires_at else 0
        account_items.append({
            "name": acc.email,
            "platform": "openai",
            "type": "oauth",
            "credentials": {
                "access_token": acc.access_token,
                "chatgpt_account_id": acc.account_id or "",
                "chatgpt_user_id": "",
                "client_id": acc.client_id or "",
                "expires_at": expires_at,
                "expires_in": 863999,
                "model_mapping": {
                    "gpt-5.1": "gpt-5.1",
                    "gpt-5.1-codex": "gpt-5.1-codex",
                    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
                    "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
                    "gpt-5.2": "gpt-5.2",
                    "gpt-5.2-codex": "gpt-5.2-codex",
                    "gpt-5.3": "gpt-5.3",
                    "gpt-5.3-codex": "gpt-5.3-codex",
                    "gpt-5.4": "gpt-5.4"
                },
                "organization_id": acc.workspace_id or "",
                "refresh_token": acc.refresh_token or "",
            },
            "extra": {},
            "concurrency": concurrency,
            "priority": priority,
            "rate_multiplier": 1,
            "auto_pause_on_expired": True,
        })

    if not account_items:
        return False, "All accounts lack access_token and cannot be uploaded"

    payload = {
        "data": {
            "type": "sub2api-data",
            "version": 1,
            "exported_at": exported_at,
            "proxies": [],
            "accounts": account_items,
        },
        "skip_default_group_bind": True,
    }

    url = api_url.rstrip("/") + "/api/v1/admin/accounts/data"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "Idempotency-Key": f"import-{exported_at}",
    }

    try:
        response = cffi_requests.post(
            url,
            json=payload,
            headers=headers,
            proxies=None,
            timeout=30,
            impersonate="chrome110",
        )

        if response.status_code in (200, 201):
            return True, f"Successfully uploaded {len(account_items)} accounts"

        error_msg = f"Upload failed: HTTP {response.status_code}"
        try:
            detail = response.json()
            if isinstance(detail, dict):
                error_msg = detail.get("message", error_msg)
        except Exception:
            error_msg = f"{error_msg} - {response.text[:200]}"
        return False, error_msg

    except Exception as e:
        logger.error(f"Sub2API upload exception: {e}")
        return False, f"Upload exception: {str(e)}"


def batch_upload_to_sub2api(
    account_ids: List[int],
    api_url: str,
    api_key: str,
    concurrency: int = 3,
    priority: int = 50,
) -> dict:
    """
    Batch upload accounts with specified IDs to the Sub2API platform

    Returns:
        Dictionary containing success/failure/skip statistics and details
    """
    results = {
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": []
    }

    with get_db() as db:
        accounts = []
        for account_id in account_ids:
            acc = db.query(Account).filter(Account.id == account_id).first()
            if not acc:
                results["failed_count"] += 1
                results["details"].append({"id": account_id, "email": None, "success": False, "error": "Account does not exist"})
                continue
            if not acc.access_token:
                results["skipped_count"] += 1
                results["details"].append({"id": account_id, "email": acc.email, "success": False, "error": "Missing access_token"})
                continue
            accounts.append(acc)

        if not accounts:
            return results

        success, message = upload_to_sub2api(accounts, api_url, api_key, concurrency, priority)

        if success:
            for acc in accounts:
                results["success_count"] += 1
                results["details"].append({"id": acc.id, "email": acc.email, "success": True, "message": message})
        else:
            for acc in accounts:
                results["failed_count"] += 1
                results["details"].append({"id": acc.id, "email": acc.email, "success": False, "error": message})

    return results


def test_sub2api_connection(api_url: str, api_key: str) -> Tuple[bool, str]:
    """
    Test Sub2API connection (GET /api/v1/admin/accounts/data test)

    Returns:
        (success sign, message)
    """
    if not api_url:
        return False, "API URL cannot be empty"
    if not api_key:
        return False, "API Key cannot be empty"

    url = api_url.rstrip("/") + "/api/v1/admin/accounts/data"
    headers = {"x-api-key": api_key}

    try:
        response = cffi_requests.get(
            url,
            headers=headers,
            proxies=None,
            timeout=10,
            impersonate="chrome110",
        )

        if response.status_code in (200, 201, 204, 405):
            return True, "Sub2API connection test successful"
        if response.status_code == 401:
            return False, "Connection successful, but API Key is invalid"
        if response.status_code == 403:
            return False, "Connection successful, but insufficient permissions"

        return False, f"The server returned an exception status code: {response.status_code}"

    except cffi_requests.exceptions.ConnectionError as e:
        return False, f"Unable to connect to server: {str(e)}"
    except cffi_requests.exceptions.Timeout:
        return False, "Connection timed out, please check network configuration"
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"
