"""Email service module"""

from .base import (
    BaseEmailService,
    EmailServiceError,
    EmailServiceStatus,
    EmailServiceFactory,
    create_email_service,
    EmailServiceType
)
from .tempmail import TempmailService
from .outlook import OutlookService
from .moe_mail import MeoMailEmailService
from .temp_mail import TempMailService
from .duck_mail import DuckMailService
from .freemail import FreemailService
from .imap_mail import ImapMailService

# Registration service
EmailServiceFactory.register(EmailServiceType.TEMPMAIL, TempmailService)
EmailServiceFactory.register(EmailServiceType.OUTLOOK, OutlookService)
EmailServiceFactory.register(EmailServiceType.MOE_MAIL, MeoMailEmailService)
EmailServiceFactory.register(EmailServiceType.TEMP_MAIL, TempMailService)
EmailServiceFactory.register(EmailServiceType.DUCK_MAIL, DuckMailService)
EmailServiceFactory.register(EmailServiceType.FREEMAIL, FreemailService)
EmailServiceFactory.register(EmailServiceType.IMAP_MAIL, ImapMailService)

# Export additional content for the Outlook module
from .outlook.base import (
    ProviderType,
    EmailMessage,
    TokenInfo,
    ProviderHealth,
    ProviderStatus,
)
from .outlook.account import OutlookAccount
from .outlook.providers import (
    OutlookProvider,
    IMAPOldProvider,
    IMAPNewProvider,
    GraphAPIProvider,
)

__all__ = [
    # base class
    'BaseEmailService',
    'EmailServiceError',
    'EmailServiceStatus',
    'EmailServiceFactory',
    'create_email_service',
    'EmailServiceType',
    # Service category
    'TempmailService',
    'OutlookService',
    'MeoMailEmailService',
    'TempMailService',
    'DuckMailService',
    'FreemailService',
    'ImapMailService',
    # Outlook module
    'ProviderType',
    'EmailMessage',
    'TokenInfo',
    'ProviderHealth',
    'ProviderStatus',
    'OutlookAccount',
    'OutlookProvider',
    'IMAPOldProvider',
    'IMAPNewProvider',
    'GraphAPIProvider',
]
