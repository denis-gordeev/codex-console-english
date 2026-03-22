"""
Outlook Mailbox Service Module
Support multiple IMAP/API connection methods, automatic failover
"""

from .service import OutlookService

__all__ = ['OutlookService']
