"""Mailbox service abstract base class
Base class for all mailbox service implementations"""

import abc
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

from ..config.constants import EmailServiceType


logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Email service abnormality"""
    pass


class EmailServiceStatus(Enum):
    """Email service status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class BaseEmailService(abc.ABC):
    """Mailbox service abstract base class

    All mailbox services must implement this interface"""

    def __init__(self, service_type: EmailServiceType, name: str = None):
        """Initialize mailbox service

        Args:
            service_type: service type
            name: service name"""
        self.service_type = service_type
        self.name = name or f"{service_type.value}_service"
        self._status = EmailServiceStatus.HEALTHY
        self._last_error = None

    @property
    def status(self) -> EmailServiceStatus:
        """Get service status"""
        return self._status

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message"""
        return self._last_error

    @abc.abstractmethod
    def create_email(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new email address

        Args:
            config: configuration parameters, such as email prefix, domain name, etc.

        Returns:
            A dictionary containing email information, containing at least:
            - email: email address
            - service_id: ID in the mailbox service
            - token/credentials: access credentials (if required)

        Raises:
            EmailServiceError: Creation failed"""
        pass

    @abc.abstractmethod
    def get_verification_code(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 120,
        pattern: str = r"(?<!\d)(\d{6})(?!\d)",
        otp_sent_at: Optional[float] = None,
    ) -> Optional[str]:
        """Get verification code

        Args:
            email: email address
            email_id: ID in the email service (if required)
            timeout: timeout (seconds)
            pattern: verification code regular expression
            otp_sent_at: OTP sending timestamp, used to filter old emails

        Returns:
            Verification code string, returns None if timeout or not found

        Raises:
            EmailServiceError: Service error"""
        pass

    @abc.abstractmethod
    def list_emails(self, **kwargs) -> List[Dict[str, Any]]:
        """List all mailboxes (if supported by the service)

        Args:
            **kwargs: other parameters

        Returns:
            Email list

        Raises:
            EmailServiceError: Service error"""
        pass

    @abc.abstractmethod
    def delete_email(self, email_id: str) -> bool:
        """Delete mailbox

        Args:
            email_id: ID in the email service

        Returns:
            Is deletion successful?

        Raises:
            EmailServiceError: Service error"""
        pass

    @abc.abstractmethod
    def check_health(self) -> bool:
        """Check service health status

        Returns:
            Is the service healthy?

        Note:
            This method should not throw an exception, it should catch the exception and return False"""
        pass

    def get_email_info(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Get email information (optional implementation)

        Args:
            email_id: ID in the email service

        Returns:
            Email information dictionary, returns None if it does not exist"""
        # Default implementation: traverse the list to find
        for email_info in self.list_emails():
            if email_info.get("id") == email_id:
                return email_info
        return None

    def wait_for_email(
        self,
        email: str,
        email_id: str = None,
        timeout: int = 120,
        check_interval: int = 3,
        expected_sender: str = None,
        expected_subject: str = None
    ) -> Optional[Dict[str, Any]]:
        """Wait for and get mail (optional implementation)

        Args:
            email: email address
            email_id: ID in the email service
            timeout: timeout (seconds)
            check_interval: check interval (seconds)
            expected_sender: expected sender (check included)
            expected_subject: expected subject (contains checks)

        Returns:
            Email information dictionary, returns None if timeout occurs"""
        import time
        from datetime import datetime

        start_time = time.time()
        last_email_id = None

        while time.time() - start_time < timeout:
            try:
                emails = self.list_emails()
                for email_info in emails:
                    email_data = email_info.get("email", {})
                    current_email_id = email_info.get("id")

                    # Check if it is a new email
                    if last_email_id and current_email_id == last_email_id:
                        continue

                    # Check email address
                    if email_data.get("address") != email:
                        continue

                    # Get mailing list
                    messages = self.get_email_messages(email_id or current_email_id)
                    for message in messages:
                        # Check sender
                        if expected_sender and expected_sender not in message.get("from", ""):
                            continue

                        # Check topic
                        if expected_subject and expected_subject not in message.get("subject", ""):
                            continue

                        # Return email information
                        return {
                            "id": message.get("id"),
                            "from": message.get("from"),
                            "subject": message.get("subject"),
                            "content": message.get("content"),
                            "received_at": message.get("received_at"),
                            "email_info": email_info
                        }

                    # Update last checked email ID
                    if messages:
                        last_email_id = current_email_id

            except Exception as e:
                logger.warning(f"Error while waiting for mail: {e}")

            time.sleep(check_interval)

        return None

    def get_email_messages(self, email_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Get the list of messages in the mailbox (optional implementation)

        Args:
            email_id: ID in the email service
            **kwargs: other parameters

        Returns:
            mailing list

        Note:
            This is an optional method and may not be supported by some services"""
        raise NotImplementedError("This email service does not support obtaining mailing lists")

    def get_message_content(self, email_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Get email content (optional implementation)

        Args:
            email_id: ID in the email service
            message_id: email ID

        Returns:
            Email content dictionary

        Note:
            This is an optional method and may not be supported by some services"""
        raise NotImplementedError("This email service does not support obtaining email content")

    def update_status(self, success: bool, error: Exception = None):
        """Update service status

        Args:
            success: whether the operation was successful
            error: error message"""
        if success:
            self._status = EmailServiceStatus.HEALTHY
            self._last_error = None
        else:
            self._status = EmailServiceStatus.DEGRADED
            if error:
                self._last_error = str(error)

    def __str__(self) -> str:
        """string representation"""
        return f"{self.name} ({self.service_type.value})"


class EmailServiceFactory:
    """Email service factory"""

    _registry: Dict[EmailServiceType, type] = {}

    @classmethod
    def register(cls, service_type: EmailServiceType, service_class: type):
        """Register email service class

        Args:
            service_type: service type
            service_class: service class"""
        if not issubclass(service_class, BaseEmailService):
            raise TypeError(f"{service_class} must be a subclass of BaseEmailService")
        cls._registry[service_type] = service_class
        logger.info(f"Register email service: {service_type.value} -> {service_class.__name__}")

    @classmethod
    def create(
        cls,
        service_type: EmailServiceType,
        config: Dict[str, Any],
        name: str = None
    ) -> BaseEmailService:
        """Create an email service instance

        Args:
            service_type: service type
            config: service configuration
            name: service name

        Returns:
            Email service instance

        Raises:
            ValueError: The service type is not registered or the configuration is invalid"""
        if service_type not in cls._registry:
            raise ValueError(f"Unregistered service type: {service_type.value}")

        service_class = cls._registry[service_type]
        try:
            instance = service_class(config, name)
            return instance
        except Exception as e:
            raise ValueError(f"Failed to create mailbox service: {e}")

    @classmethod
    def get_available_services(cls) -> List[EmailServiceType]:
        """Get all registered service types

        Returns:
            List of registered service types"""
        return list(cls._registry.keys())

    @classmethod
    def get_service_class(cls, service_type: EmailServiceType) -> Optional[type]:
        """Get service class

        Args:
            service_type: service type

        Returns:
            Service class, returns None if not registered"""
        return cls._registry.get(service_type)


# Simplified factory function
def create_email_service(
    service_type: EmailServiceType,
    config: Dict[str, Any],
    name: str = None
) -> BaseEmailService:
    """Create a mailbox service (simplified factory function)

    Args:
        service_type: service type
        config: service configuration
        name: service name

    Returns:
        Email service instance"""
    return EmailServiceFactory.create(service_type, config, name)