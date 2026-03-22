"""
Registration process engine
Registration process extracted and reconstructed from main.py
"""

import re
import json
import time
import logging
import secrets
import string
from typing import Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime

from curl_cffi import requests as cffi_requests

from .openai.oauth import OAuthManager, OAuthStart
from .http_client import OpenAIHTTPClient, HTTPClientError
from ..services import EmailServiceFactory, BaseEmailService, EmailServiceType
from ..database import crud
from ..database.session import get_db
from ..config.constants import (
    OPENAI_API_ENDPOINTS,
    OPENAI_PAGE_TYPES,
    generate_random_user_info,
    OTP_CODE_PATTERN,
    DEFAULT_PASSWORD_LENGTH,
    PASSWORD_CHARSET,
    AccountStatus,
    TaskStatus,
)
from ..config.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass
class RegistrationResult:
    """Registration results"""
    success: bool
    email: str = ""
    password: str = "" #Registration password
    account_id: str = ""
    workspace_id: str = ""
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    session_token: str = "" # Session token
    error_message: str = ""
    logs: list = None
    metadata: dict = None
    source: str = "register" # 'register' or 'login', to distinguish the account source

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "email": self.email,
            "password": self.password,
            "account_id": self.account_id,
            "workspace_id": self.workspace_id,
            "access_token": self.access_token[:20] + "..." if self.access_token else "",
            "refresh_token": self.refresh_token[:20] + "..." if self.refresh_token else "",
            "id_token": self.id_token[:20] + "..." if self.id_token else "",
            "session_token": self.session_token[:20] + "..." if self.session_token else "",
            "error_message": self.error_message,
            "logs": self.logs or [],
            "metadata": self.metadata or {},
            "source": self.source,
        }


@dataclass
class SignupFormResult:
    """Results of submitting registration form"""
    success: bool
    page_type: str = "" # page.type field in the response
    is_existing_account: bool = False # Whether it is a registered account
    response_data: Dict[str, Any] = None # Complete response data
    error_message: str = ""


class RegistrationEngine:
    """
    Register engine
    Responsible for coordinating email services, OAuth processes and OpenAI API calls
    """

    def __init__(
        self,
        email_service: BaseEmailService,
        proxy_url: Optional[str] = None,
        callback_logger: Optional[Callable[[str], None]] = None,
        task_uuid: Optional[str] = None
    ):
        """
        Initialize registration engine

        Args:
            email_service: Email service instance
            proxy_url: proxy URL
            callback_logger: log callback function
            task_uuid: task UUID (used for database records)
        """
        self.email_service = email_service
        self.proxy_url = proxy_url
        self.callback_logger = callback_logger or (lambda msg: logger.info(msg))
        self.task_uuid = task_uuid

        #Create HTTP client
        self.http_client = OpenAIHTTPClient(proxy_url=proxy_url)

        # Create OAuth manager
        settings = get_settings()
        self.oauth_manager = OAuthManager(
            client_id=settings.openai_client_id,
            auth_url=settings.openai_auth_url,
            token_url=settings.openai_token_url,
            redirect_uri=settings.openai_redirect_uri,
            scope=settings.openai_scope,
            proxy_url=proxy_url # Pass proxy configuration
        )

        #State variables
        self.email: Optional[str] = None
        self.password: Optional[str] = None #Registration password
        self.email_info: Optional[Dict[str, Any]] = None
        self.oauth_start: Optional[OAuthStart] = None
        self.session: Optional[cffi_requests.Session] = None
        self.session_token: Optional[str] = None # Session token
        self.logs: list = []
        self._otp_sent_at: Optional[float] = None # OTP sending timestamp
        self._is_existing_account: bool = False # Whether it is a registered account (for automatic login)
        self._token_acquisition_requires_login: bool = False # Newly registered accounts require a second login to get the token

    def _log(self, message: str, level: str = "info"):
        """Log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        #Add to log list
        self.logs.append(log_message)

        # Call the callback function
        if self.callback_logger:
            self.callback_logger(log_message)

        # Record to database (if there are associated tasks)
        if self.task_uuid:
            try:
                with get_db() as db:
                    crud.append_task_log(db, self.task_uuid, log_message)
            except Exception as e:
                logger.warning(f"Failed to record task log: {e}")

        # Record to the log system according to the level
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    def _generate_password(self, length: int = DEFAULT_PASSWORD_LENGTH) -> str:
        """Generate random password"""
        return ''.join(secrets.choice(PASSWORD_CHARSET) for _ in range(length))

    def _check_ip_location(self) -> Tuple[bool, Optional[str]]:
        """Check IP Geolocation"""
        try:
            return self.http_client.check_ip_location()
        except Exception as e:
            self._log(f"Failed to check IP location: {e}", "error")
            return False, None

    def _create_email(self) -> bool:
        """Create email"""
        try:
            self._log(f"Creating {self.email_service.service_type.value} mailbox, give the new account the entire inbox first...")
            self.email_info = self.email_service.create_email()

            if not self.email_info or "email" not in self.email_info:
                self._log("Failed to create mailbox: Incomplete information returned", "error")
                return False

            self.email = self.email_info["email"]
            self._log(f"The mailbox is in place and the address is fresh: {self.email}")
            return True

        except Exception as e:
            self._log(f"Failed to create mailbox: {e}", "error")
            return False

    def _start_oauth(self) -> bool:
        """Start the OAuth process"""
        try:
            self._log("Start the OAuth authorization process, go to the door and swipe your face...")
            self.oauth_start = self.oauth_manager.start_oauth()
            self._log(f"OAuth URL is ready and the channel is opened: {self.oauth_start.auth_url[:80]}...")
            return True
        except Exception as e:
            self._log(f"Failed to generate OAuth URL: {e}", "error")
            return False

    def _init_session(self) -> bool:
        """Initialize session"""
        try:
            self.session = self.http_client.session
            return True
        except Exception as e:
            self._log(f"Failed to initialize session: {e}", "error")
            return False

    def _get_device_id(self) -> Optional[str]:
        """Get Device ID"""
        if not self.oauth_start:
            return None

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                if not self.session:
                    self.session = self.http_client.session

                response = self.session.get(
                    self.oauth_start.auth_url,
                    timeout=20
                )
                did = self.session.cookies.get("oai-did")

                if did:
                    self._log(f"Device ID: {did}")
                    return did

                self._log(
                    f"Failed to obtain Device ID: oai-did Cookie not returned (HTTP {response.status_code}, {attempt}/{max_attempts} times)",
                    "warning" if attempt < max_attempts else "error"
                )
            except Exception as e:
                self._log(
                    f"Failed to obtain Device ID: {e} ({attempt}/{max_attempts} times)",
                    "warning" if attempt < max_attempts else "error"
                )

            if attempt < max_attempts:
                time.sleep(attempt)
                self.http_client.close()
                self.session = self.http_client.session

        return None

    def _check_sentinel(self, did: str) -> Optional[str]:
        """Check Sentinel interception"""
        try:
            sen_token = self.http_client.check_sentinel(did)
            if sen_token:
                self._log(f"Sentinel token obtained successfully")
                return sen_token
            self._log("Sentinel check failed: token not obtained", "warning")
            return None

        except Exception as e:
            self._log(f"Sentinel check exception: {e}", "warning")
            return None

    def _submit_auth_start(
        self,
        did: str,
        sen_token: Optional[str],
        *,
        screen_hint: str,
        referer: str,
        log_label: str,
        record_existing_account: bool = True,
    ) -> SignupFormResult:
        """
        Submit the authorization entry form

        Returns:
            SignupFormResult: Submit the result, including account status judgment
        """
        try:
            request_body = json.dumps({
                "username": {
                    "value": self.email,
                    "kind": "email",
                },
                "screen_hint": screen_hint,
            })

            headers = {
                "referer": referer,
                "accept": "application/json",
                "content-type": "application/json",
            }

            if sen_token:
                sentinel = json.dumps({
                    "p": "",
                    "t": "",
                    "c": sen_token,
                    "id": did,
                    "flow": "authorize_continue",
                })
                headers["openai-sentinel-token"] = sentinel

            response = self.session.post(
                OPENAI_API_ENDPOINTS["signup"],
                headers=headers,
                data=request_body,
            )

            self._log(f"{log_label}status: {response.status_code}")

            if response.status_code != 200:
                return SignupFormResult(
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )

            # Parse the response to determine account status
            try:
                response_data = response.json()
                page_type = response_data.get("page", {}).get("type", "")
                self._log(f"Response page type: {page_type}")

                is_existing = page_type == OPENAI_PAGE_TYPES["EMAIL_OTP_VERIFICATION"]

                if is_existing:
                    self._otp_sent_at = time.time()
                    if record_existing_account:
                        self._log(f"If a registered account is detected, it will automatically switch to the login process")
                        self._is_existing_account = True
                    else:
                        self._log("The login process has been triggered, waiting for the verification code automatically sent by the system")

                return SignupFormResult(
                    success=True,
                    page_type=page_type,
                    is_existing_account=is_existing,
                    response_data=response_data
                )

            except Exception as parse_error:
                self._log(f"Failed to parse response: {parse_error}", "warning")
                # Unable to parse, default is successful
                return SignupFormResult(success=True)

        except Exception as e:
            self._log(f"{log_label} failed: {e}", "error")
            return SignupFormResult(success=False, error_message=str(e))

    def _submit_signup_form(
        self,
        did: str,
        sen_token: Optional[str],
        *,
        record_existing_account: bool = True,
    ) -> SignupFormResult:
        """Submit the registration portal form."""
        return self._submit_auth_start(
            did,
            sen_token,
            screen_hint="signup",
            referer="https://auth.openai.com/create-account",
            log_label="Submit registration form",
            record_existing_account=record_existing_account,
        )

    def _submit_login_start(self, did: str, sen_token: Optional[str]) -> SignupFormResult:
        """Submit the login form."""
        return self._submit_auth_start(
            did,
            sen_token,
            screen_hint="login",
            referer="https://auth.openai.com/log-in",
            log_label="Submit login entry",
            record_existing_account=False,
        )

    def _submit_login_password(self) -> SignupFormResult:
        """Submit your login password and enter the email verification code page."""
        try:
            response = self.session.post(
                OPENAI_API_ENDPOINTS["password_verify"],
                headers={
                    "referer": "https://auth.openai.com/log-in/password",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=json.dumps({"password": self.password}),
            )

            self._log(f"Submit login password status: {response.status_code}")

            if response.status_code != 200:
                return SignupFormResult(
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )

            response_data = response.json()
            page_type = response_data.get("page", {}).get("type", "")
            self._log(f"Login password response page type: {page_type}")

            is_existing = page_type == OPENAI_PAGE_TYPES["EMAIL_OTP_VERIFICATION"]
            if is_existing:
                self._otp_sent_at = time.time()
                self._log("Login password verification passed, waiting for the verification code automatically sent by the system")

            return SignupFormResult(
                success=True,
                page_type=page_type,
                is_existing_account=is_existing,
                response_data=response_data,
            )

        except Exception as e:
            self._log(f"Failed to submit login password: {e}", "error")
            return SignupFormResult(success=False, error_message=str(e))

    def _reset_auth_flow(self) -> None:
        """Reset the session and prepare to reinitiate the OAuth process."""
        self.http_client.close()
        self.session = None
        self.oauth_start = None
        self.session_token = None
        self._otp_sent_at = None

    def _prepare_authorize_flow(self, label: str) -> Tuple[Optional[str], Optional[str]]:
        """Initialize the authorization process at the current stage and return device id and sentinel token."""
        self._log(f"{label}: Warm up the session first...")
        if not self._init_session():
            return None, None

        self._log(f"{label}: The OAuth process is ready to start, tie your shoes...")
        if not self._start_oauth():
            return None, None

        self._log(f"{label}: Receive Device ID pass...")
        did = self._get_device_id()
        if not did:
            return None, None

        self._log(f"{label}: Solve a Sentinel POW question. Only correct answers will be awarded...")
        sen_token = self._check_sentinel(did)
        if not sen_token:
            return did, None

        self._log(f"{label}: Sentinel nodded and moved on")
        return did, sen_token

    def _complete_token_exchange(self, result: RegistrationResult) -> bool:
        """After the login state has been established, continue to complete the workspace and OAuth token acquisition."""
        self._log("Waiting for the login verification code to arrive, the last guest is still on the way...")
        code = self._get_verification_code()
        if not code:
            result.error_message = "Failed to obtain verification code"
            return False

        self._log("Check the login verification code and verify your identity...")
        if not self._validate_verification_code(code):
            result.error_message = "Verification code verification failed"
            return False

        self._log("Touch the Workspace ID to see which table you should sit at...")
        workspace_id = self._get_workspace_id()
        if not workspace_id:
            result.error_message = "Failed to obtain Workspace ID"
            return False

        result.workspace_id = workspace_id

        self._log("Select Workspace and arrange a reliable seat...")
        continue_url = self._select_workspace(workspace_id)
        if not continue_url:
            result.error_message = "Failed to select Workspace"
            return False

        self._log("Follow the redirection breadcrumbs, don't lose track...")
        callback_url = self._follow_redirects(continue_url)
        if not callback_url:
            result.error_message = "Failed to follow redirect chain"
            return False

        self._log("Processing OAuth callback, preparing to request token...")
        token_info = self._handle_oauth_callback(callback_url)
        if not token_info:
            result.error_message = "Failed to handle OAuth callback"
            return False

        result.account_id = token_info.get("account_id", "")
        result.access_token = token_info.get("access_token", "")
        result.refresh_token = token_info.get("refresh_token", "")
        result.id_token = token_info.get("id_token", "")
        result.password = self.password or ""
        result.source = "login" if self._is_existing_account else "register"

        session_cookie = self.session.cookies.get("__Secure-next-auth.session-token")
        if session_cookie:
            self.session_token = session_cookie
            result.session_token = session_cookie
            self._log("Session Token was also obtained, and the network is not in vain today")

        return True

    def _restart_login_flow(self) -> Tuple[bool, str]:
        """After the newly registered account is created, re-initiate the login process to get the token."""
        self._token_acquisition_requires_login = True
        self._log("I'm done with the registration, I'll log in again and ask for the token, and wrap up...")
        self._reset_auth_flow()

        did, sen_token = self._prepare_authorize_flow("Relogin")
        if not did:
            return False, "Failed to obtain Device ID when logging in again"
        if not sen_token:
            return False, "Sentinel POW verification failed when logging in again"

        login_start_result = self._submit_login_start(did, sen_token)
        if not login_start_result.success:
            return False, f"Failed to re-login to submit email: {login_start_result.error_message}"
        if login_start_result.page_type != OPENAI_PAGE_TYPES["LOGIN_PASSWORD"]:
            return False, f"Re-login without entering the password page: {login_start_result.page_type or 'unknown'}"

        password_result = self._submit_login_password()
        if not password_result.success:
            return False, f"Failed to re-login and submit password: {password_result.error_message}"
        if not password_result.is_existing_account:
            return False, f"Re-login without entering the verification code page: {password_result.page_type or 'unknown'}"
        return True, ""

    def _register_password(self) -> Tuple[bool, Optional[str]]:
        """Registration password"""
        try:
            # Generate password
            password = self._generate_password()
            self.password = password # Save password to instance variable
            self._log(f"Generate password: {password}")

            # Submit password registration
            register_body = json.dumps({
                "password": password,
                "username": self.email
            })

            response = self.session.post(
                OPENAI_API_ENDPOINTS["register"],
                headers={
                    "referer": "https://auth.openai.com/create-account/password",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=register_body,
            )

            self._log(f"Submit password status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text[:500]
                self._log(f"Password registration failed: {error_text}", "warning")

                # Parse the error message to determine whether the email address has been registered
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", "")
                    error_code = error_json.get("error", {}).get("code", "")

                    # Check if the email address has been registered
                    if "already" in error_msg.lower() or "exists" in error_msg.lower() or error_code == "user_exists":
                        self._log(f"Email {self.email} may have been registered with OpenAI", "error")
                        # Mark this email as registered
                        self._mark_email_as_registered()
                except Exception:
                    pass

                return False, None

            return True, password

        except Exception as e:
            self._log(f"Password registration failed: {e}", "error")
            return False, None

    def _mark_email_as_registered(self):
        """Mark the mailbox as registered (to prevent repeated attempts)"""
        try:
            with get_db() as db:
                # Check whether a record of this mailbox already exists
                existing = crud.get_account_by_email(db, self.email)
                if not existing:
                    #Create a failure record and mark the email address as already registered
                    crud.create_account(
                        db,
                        email=self.email,
                        password="", # An empty password indicates unsuccessful registration
                        email_service=self.email_service.service_type.value,
                        email_service_id=self.email_info.get("service_id") if self.email_info else None,
                        status="failed",
                        extra_data={"register_failed_reason": "email_already_registered_on_openai"}
                    )
                    self._log(f"The mailbox {self.email} has been marked as registered in the database")
        except Exception as e:
            logger.warning(f"Failed to mark mailbox status: {e}")

    def _send_verification_code(self) -> bool:
        """Send verification code"""
        try:
            # Record sending timestamp
            self._otp_sent_at = time.time()

            response = self.session.get(
                OPENAI_API_ENDPOINTS["send_otp"],
                headers={
                    "referer": "https://auth.openai.com/create-account/password",
                    "accept": "application/json",
                },
            )

            self._log(f"Verification code sending status: {response.status_code}")
            return response.status_code == 200

        except Exception as e:
            self._log(f"Failed to send verification code: {e}", "error")
            return False

    def _get_verification_code(self) -> Optional[str]:
        """Get verification code"""
        try:
            self._log(f"Waiting for the verification code of the email address {self.email}...")

            email_id = self.email_info.get("service_id") if self.email_info else None
            code = self.email_service.get_verification_code(
                email=self.email,
                email_id=email_id,
                timeout=120,
                pattern=OTP_CODE_PATTERN,
                otp_sent_at=self._otp_sent_at,
            )

            if code:
                self._log(f"Successfully obtained verification code: {code}")
                return code
            else:
                self._log("Timeout waiting for verification code", "error")
                return None

        except Exception as e:
            self._log(f"Failed to obtain verification code: {e}", "error")
            return None

    def _validate_verification_code(self, code: str) -> bool:
        """Verify verification code"""
        try:
            code_body = f'{{"code":"{code}"}}'

            response = self.session.post(
                OPENAI_API_ENDPOINTS["validate_otp"],
                headers={
                    "referer": "https://auth.openai.com/email-verification",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=code_body,
            )

            self._log(f"Verification code verification status: {response.status_code}")
            return response.status_code == 200

        except Exception as e:
            self._log(f"Failed to verify verification code: {e}", "error")
            return False

    def _create_user_account(self) -> bool:
        """Create user account"""
        try:
            user_info = generate_random_user_info()
            self._log(f"Generate user information: {user_info['name']}, birthday: {user_info['birthdate']}")
            create_account_body = json.dumps(user_info)

            response = self.session.post(
                OPENAI_API_ENDPOINTS["create_account"],
                headers={
                    "referer": "https://auth.openai.com/about-you",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=create_account_body,
            )

            self._log(f"Account creation status: {response.status_code}")

            if response.status_code != 200:
                self._log(f"Account creation failed: {response.text[:200]}", "warning")
                return False

            return True

        except Exception as e:
            self._log(f"Failed to create account: {e}", "error")
            return False

    def _get_workspace_id(self) -> Optional[str]:
        """Get Workspace ID"""
        try:
            auth_cookie = self.session.cookies.get("oai-client-auth-session")
            if not auth_cookie:
                self._log("Failed to obtain authorization cookie", "error")
                return None

            # Decode JWT
            import base64
            import json as json_module

            try:
                segments = auth_cookie.split(".")
                if len(segments) < 1:
                    self._log("Authorization cookie format error", "error")
                    return None

                # Decode the first segment
                payload = segments[0]
                pad = "=" * ((4 - (len(payload) % 4)) % 4)
                decoded = base64.urlsafe_b64decode((payload + pad).encode("ascii"))
                auth_json = json_module.loads(decoded.decode("utf-8"))

                workspaces = auth_json.get("workspaces") or []
                if not workspaces:
                    self._log("There is no workspace information in the authorization cookie", "error")
                    return None

                workspace_id = str((workspaces[0] or {}).get("id") or "").strip()
                if not workspace_id:
                    self._log("Unable to resolve workspace_id", "error")
                    return None

                self._log(f"Workspace ID: {workspace_id}")
                return workspace_id

            except Exception as e:
                self._log(f"Failed to parse authorization cookie: {e}", "error")
                return None

        except Exception as e:
            self._log(f"Failed to obtain Workspace ID: {e}", "error")
            return None

    def _select_workspace(self, workspace_id: str) -> Optional[str]:
        """Select Workspace"""
        try:
            select_body = f'{{"workspace_id":"{workspace_id}"}}'

            response = self.session.post(
                OPENAI_API_ENDPOINTS["select_workspace"],
                headers={
                    "referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                    "content-type": "application/json",
                },
                data=select_body,
            )

            if response.status_code != 200:
                self._log(f"Failed to select workspace: {response.status_code}", "error")
                self._log(f"Response: {response.text[:200]}", "warning")
                return None

            continue_url = str((response.json() or {}).get("continue_url") or "").strip()
            if not continue_url:
                self._log("continue_url is missing in workspace/select response", "error")
                return None

            self._log(f"Continue URL: {continue_url[:100]}...")
            return continue_url

        except Exception as e:
            self._log(f"Failed to select Workspace: {e}", "error")
            return None

    def _follow_redirects(self, start_url: str) -> Optional[str]:
        """Follow the redirect chain and look for the callback URL"""
        try:
            current_url = start_url
            max_redirects = 6

            for i in range(max_redirects):
                self._log(f"Redirect {i+1}/{max_redirects}: {current_url[:100]}...")

                response = self.session.get(
                    current_url,
                    allow_redirects=False,
                    timeout=15
                )

                location = response.headers.get("Location") or ""

                # If it is not a redirect status code, stop
                if response.status_code not in [301, 302, 303, 307, 308]:
                    self._log(f"Non-redirect status code: {response.status_code}")
                    break

                if not location:
                    self._log("Redirect response missing Location header")
                    break

                # Build next URL
                import urllib.parse
                next_url = urllib.parse.urljoin(current_url, location)

                # Check if callback parameters are included
                if "code=" in next_url and "state=" in next_url:
                    self._log(f"Callback URL found: {next_url[:100]}...")
                    return next_url

                current_url = next_url

            self._log("Callback URL not found in redirect chain", "error")
            return None

        except Exception as e:
            self._log(f"Failed to follow redirect: {e}", "error")
            return None

    def _handle_oauth_callback(self, callback_url: str) -> Optional[Dict[str, Any]]:
        """Handling OAuth callbacks"""
        try:
            if not self.oauth_start:
                self._log("OAuth process not initialized", "error")
                return None

            self._log("Processing OAuth callbacks, trembling at the last moment, hold still...")
            token_info = self.oauth_manager.handle_callback(
                callback_url=callback_url,
                expected_state=self.oauth_start.state,
                code_verifier=self.oauth_start.code_verifier
            )

            self._log("OAuth authorization successful, customs clearance documents obtained")
            return token_info

        except Exception as e:
            self._log(f"Failed to process OAuth callback: {e}", "error")
            return None

    def run(self) -> RegistrationResult:
        """
        Follow the complete registration process

        Support automatic login for registered accounts:
        - If it is detected that the email address has been registered, automatically switch to the login process
        - Registered accounts skip: set password, send verification code, create user account
        - Common steps: Get Verification Code, Verify Verification Code, Workspace and OAuth callbacks

        Returns:
            RegistrationResult: registration result
        """
        result = RegistrationResult(success=False, logs=self.logs)

        try:
            self._is_existing_account = False
            self._token_acquisition_requires_login = False
            self._otp_sent_at = None

            self._log("=" * 60)
            self._log("The registration process starts and starts knocking on the door for you")
            self._log("=" * 60)

            # 1. Check IP geolocation
            self._log("1. First look at where this network comes from, don't end up on the wrong set at the beginning...")
            ip_ok, location = self._check_ip_location()
            if not ip_ok:
                result.error_message = f"IP geographical location is not supported: {location}"
                self._log(f"IP check failed: {location}", "error")
                return result

            self._log(f"IP location: {location}")

            # 2. Create email
            self._log("2. Open a new mailbox and prepare to receive mail...")
            if not self._create_email():
                result.error_message = "Failed to create mailbox"
                return result

            result.email = self.email

            # 3. Prepare for the first round of authorization process
            did, sen_token = self._prepare_authorize_flow("First authorization")
            if not did:
                result.error_message = "Failed to obtain Device ID"
                return result
            if not sen_token:
                result.error_message = "Sentinel POW verification failed"
                return result

            # 4. Submit registration entrance email
            self._log("4. Submit your mailbox and see how OpenAI catches the ball...")
            signup_result = self._submit_signup_form(did, sen_token)
            if not signup_result.success:
                result.error_message = f"Failed to submit registration form: {signup_result.error_message}"
                return result

            if self._is_existing_account:
                self._log("Detected that this is an old friend's account, directly logged in to get the token, no detours")
            else:
                self._log("5. Set a password, don't let thieves laugh...")
                password_ok, _ = self._register_password()
                if not password_ok:
                    result.error_message = "Registration password failed"
                    return result

                self._log("6. Press the registration verification code to go out, it’s time for the postman to sprint...")
                if not self._send_verification_code():
                    result.error_message = "Failed to send verification code"
                    return result

                self._log("7. Wait for the verification code to arrive, please check your email...")
                code = self._get_verification_code()
                if not code:
                    result.error_message = "Failed to obtain verification code"
                    return result

                self._log("8. Check the verification code to see if it is me...")
                if not self._validate_verification_code(code):
                    result.error_message = "Failed to verify verification code"
                    return result

                self._log("9. Create a formal account for the account and write the name in the file...")
                if not self._create_user_account():
                    result.error_message = "Failed to create user account"
                    return result

                login_ready, login_error = self._restart_login_flow()
                if not login_ready:
                    result.error_message = login_error
                    return result

            if not self._complete_token_exchange(result):
                return result

            # 10. Complete
            self._log("=" * 60)
            if self._is_existing_account:
                self._log("Login successful, old friend returned home smoothly")
            else:
                self._log("Registration successful, account has been firmly established, you can open the champagne")
            self._log(f"Email: {result.email}")
            self._log(f"Account ID: {result.account_id}")
            self._log(f"Workspace ID: {result.workspace_id}")
            self._log("=" * 60)

            result.success = True
            result.metadata = {
                "email_service": self.email_service.service_type.value,
                "proxy_used": self.proxy_url,
                "registered_at": datetime.now().isoformat(),
                "is_existing_account": self._is_existing_account,
                "token_acquired_via_relogin": self._token_acquisition_requires_login,
            }

            return result

        except Exception as e:
            self._log(f"An unexpected error occurred during the registration process: {e}", "error")
            result.error_message = str(e)
            return result

    def save_to_database(self, result: RegistrationResult) -> bool:
        """
        Save registration results to database

        Args:
            result: registration result

        Returns:
            Is the save successful?
        """
        if not result.success:
            return False

        try:
            # Get the default client_id
            settings = get_settings()

            with get_db() as db:
                # Save account information
                account = crud.create_account(
                    db,
                    email=result.email,
                    password=result.password,
                    client_id=settings.openai_client_id,
                    session_token=result.session_token,
                    email_service=self.email_service.service_type.value,
                    email_service_id=self.email_info.get("service_id") if self.email_info else None,
                    account_id=result.account_id,
                    workspace_id=result.workspace_id,
                    access_token=result.access_token,
                    refresh_token=result.refresh_token,
                    id_token=result.id_token,
                    proxy_used=self.proxy_url,
                    extra_data=result.metadata,
                    source=result.source
                )

                self._log(f"The account has been stored in the database, it is safe to leave it, ID: {account.id}")
                return True

        except Exception as e:
            self._log(f"Failed to save to database: {e}", "error")
            return False
