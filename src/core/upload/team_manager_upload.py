"""
Team Manager upload function
Refer to the CPA upload mode, direct connection without proxy
"""

import logging
from typing import List, Tuple

from curl_cffi import requests as cffi_requests

from ...database.models import Account
from ...database.session import get_db

logger = logging.getLogger(__name__)


def upload_to_team_manager(
    account: Account,
    api_url: str,
    api_key: str,
) -> Tuple[bool, str]:
    """
    Upload your account to Team Manager (direct connection, no proxy)

    Returns:
        (success sign, message)
    """
    if not api_url:
        return False, "Team Manager API URL is not configured"
    if not api_key:
        return False, "Team Manager API Key is not configured"
    if not account.access_token:
        return False, "Account lacks access_token"

    url = api_url.rstrip("/") + "/admin/teams/import"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "import_type": "single",
        "email": account.email,
        "access_token": account.access_token or "",
        "session_token": account.session_token or "",
        "refresh_token": account.refresh_token or "",
        "client_id": account.client_id or "",
        "account_id": account.account_id or "",
    }

    try:
        resp = cffi_requests.post(
            url,
            headers=headers,
            json=payload,
            proxies=None,
            timeout=30
        )
        if resp.status_code in (200, 201):
            return True, "Upload successful"
        error_msg = f"Upload failed: HTTP {resp.status_code}"
        try:
            detail = resp.json()
            if isinstance(detail, dict):
                error_msg = detail.get("message", error_msg)
        except Exception:
            error_msg = f"{error_msg} - {resp.text[:200]}"
        return False, error_msg
    except Exception as e:
        logger.error(f"Team Manager upload exception: {e}")
        return False, f"Upload exception: {str(e)}"


def batch_upload_to_team_manager(
    account_ids: List[int],
    api_url: str,
    api_key: str,
) -> dict:
    """
    Batch upload accounts to Team Manager (use batch mode to submit all accounts in one request)

    Returns:
        Dictionary containing success/failure statistics and details
    """
    results = {
        "success_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "details": [],
    }

    with get_db() as db:
        lines = []
        valid_accounts = []
        for account_id in account_ids:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                results["failed_count"] += 1
                results["details"].append(
                    {"id": account_id, "email": None, "success": False, "error": "Account does not exist"}
                )
                continue
            if not account.access_token:
                results["skipped_count"] += 1
                results["details"].append(
                    {"id": account_id, "email": account.email, "success": False, "error": "Missing Token"}
                )
                continue
            # Format: Email,AT,RT,ST,ClientID
            lines.append(",".join([
                account.email or "",
                account.access_token or "",
                account.refresh_token or "",
                account.session_token or "",
                account.client_id or "",
            ]))
            valid_accounts.append(account)

        if not valid_accounts:
            return results

        url = api_url.rstrip("/") + "/admin/teams/import"
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "import_type": "batch",
            "content": "\n".join(lines),
        }

        try:
            resp = cffi_requests.post(
                url,
                headers=headers,
                json=payload,
                proxies=None,
                timeout=60,
                impersonate="chrome110",
            )
            if resp.status_code in (200, 201):
                for account in valid_accounts:
                    results["success_count"] += 1
                    results["details"].append(
                        {"id": account.id, "email": account.email, "success": True, "message": "Batch upload successful"}
                    )
            else:
                error_msg = f"Batch upload failed: HTTP {resp.status_code}"
                try:
                    detail = resp.json()
                    if isinstance(detail, dict):
                        error_msg = detail.get("message", error_msg)
                except Exception:
                    error_msg = f"{error_msg} - {resp.text[:200]}"
                for account in valid_accounts:
                    results["failed_count"] += 1
                    results["details"].append(
                        {"id": account.id, "email": account.email, "success": False, "error": error_msg}
                    )
        except Exception as e:
            logger.error(f"Team Manager batch upload exception: {e}")
            error_msg = f"Upload exception: {str(e)}"
            for account in valid_accounts:
                results["failed_count"] += 1
                results["details"].append(
                    {"id": account.id, "email": account.email, "success": False, "error": error_msg}
                )

    return results


def test_team_manager_connection(api_url: str, api_key: str) -> Tuple[bool, str]:
    """
    Test Team Manager connection (direct connection)

    Returns:
        (success sign, message)
    """
    if not api_url:
        return False, "API URL cannot be empty"
    if not api_key:
        return False, "API Key cannot be empty"

    url = api_url.rstrip("/") + "/admin/teams/import"
    headers = {"X-API-Key": api_key}

    try:
        resp = cffi_requests.options(
            url,
            headers=headers,
            proxies=None,
            timeout=10,
            impersonate="chrome110",
        )
        if resp.status_code in (200, 204, 401, 403, 405):
            if resp.status_code == 401:
                return False, "Connection successful, but API Key is invalid"
            return True, "Team Manager connection test successful"
        return False, f"The server returned an exception status code: {resp.status_code}"
    except cffi_requests.exceptions.ConnectionError as e:
        return False, f"Unable to connect to server: {str(e)}"
    except cffi_requests.exceptions.Timeout:
        return False, "Connection timed out, please check network configuration"
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"
