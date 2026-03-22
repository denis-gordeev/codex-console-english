"""
Email parsing and verification code extraction
"""

import logging
import re
from typing import Optional, List, Dict, Any

from ...config.constants import (
    OTP_CODE_SIMPLE_PATTERN,
    OTP_CODE_SEMANTIC_PATTERN,
    OPENAI_EMAIL_SENDERS,
    OPENAI_VERIFICATION_KEYWORDS,
)
from .base import EmailMessage


logger = logging.getLogger(__name__)


class EmailParser:
    """
    Mail parser
    Used to identify OpenAI verification emails and extract verification codes
    """

    def __init__(self):
        # Compile regular expression
        self._simple_pattern = re.compile(OTP_CODE_SIMPLE_PATTERN)
        self._semantic_pattern = re.compile(OTP_CODE_SEMANTIC_PATTERN, re.IGNORECASE)

    def is_openai_verification_email(
        self,
        email: EmailMessage,
        target_email: Optional[str] = None,
    ) -> bool:
        """
        Determine whether it is an OpenAI verification email

        Args:
            email: email object
            target_email: target email address (used to verify recipients)

        Returns:
            Whether to verify email for OpenAI
        """
        sender = email.sender.lower()

        # 1. The sender must be OpenAI
        if not any(s in sender for s in OPENAI_EMAIL_SENDERS):
            logger.debug(f"The email sender is not OpenAI: {sender}")
            return False

        # 2. The subject or text contains verification keywords
        subject = email.subject.lower()
        body = email.body.lower()
        combined = f"{subject} {body}"

        if not any(kw in combined for kw in OPENAI_VERIFICATION_KEYWORDS):
            logger.debug(f"The email does not contain the verification keyword: {subject[:50]}")
            return False

        # 3. Recipient check has been removed: the recipient in the IMAP header of the alias email may not match, and it is only judged by the sender + keywords.
        logger.debug(f"Identified as OpenAI verification email: {subject[:50]}")
        return True

    def extract_verification_code(
        self,
        email: EmailMessage,
    ) -> Optional[str]:
        """
        Extract verification code from email

        Priority:
        1. Extract from topic (6 digits)
        2. Use semantic regular extraction from the text (such as "code is 123456")
        3. Guarantee: any 6-digit number

        Args:
            email: email object

        Returns:
            Verification code string, returns None if not found
        """
        # 1. Topic priority
        code = self._extract_from_subject(email.subject)
        if code:
            logger.debug(f"Extract verification code from topic: {code}")
            return code

        # 2. Text semantic matching
        code = self._extract_semantic(email.body)
        if code:
            logger.debug(f"Extract verification code from text semantics: {code}")
            return code

        # 3. Bottom line: any 6-digit number in the text
        code = self._extract_simple(email.body)
        if code:
            logger.debug(f"Extract the verification code from the bottom of the text: {code}")
            return code

        return None

    def _extract_from_subject(self, subject: str) -> Optional[str]:
        """Extract verification code from topic"""
        match = self._simple_pattern.search(subject)
        if match:
            return match.group(1)
        return None

    def _extract_semantic(self, body: str) -> Optional[str]:
        """Semantic matching to extract verification code"""
        match = self._semantic_pattern.search(body)
        if match:
            return match.group(1)
        return None

    def _extract_simple(self, body: str) -> Optional[str]:
        """Simple matching to extract verification code"""
        match = self._simple_pattern.search(body)
        if match:
            return match.group(1)
        return None

    def find_verification_code_in_emails(
        self,
        emails: List[EmailMessage],
        target_email: Optional[str] = None,
        min_timestamp: int = 0,
        used_codes: Optional[set] = None,
    ) -> Optional[str]:
        """
        Find verification code from mailing list

        Args:
            emails: mailing list
            target_email: target email address
            min_timestamp: minimum timestamp (used to filter old emails)
            used_codes: used verification code set (used for deduplication)

        Returns:
            Verification code string, returns None if not found
        """
        used_codes = used_codes or set()

        for email in emails:
            # Timestamp filtering
            if min_timestamp > 0 and email.received_timestamp > 0:
                if email.received_timestamp < min_timestamp:
                    logger.debug(f"Skip old emails: {email.subject[:50]}")
                    continue

            # Check if it is an OpenAI verification email
            if not self.is_openai_verification_email(email, target_email):
                continue

            # Extract verification code
            code = self.extract_verification_code(email)
            if code:
                # Deduplication check
                if code in used_codes:
                    logger.debug(f"Skip the used verification code: {code}")
                    continue

                logger.info(
                    f"[{target_email or 'unknown'}] Found verification code: {code}, "
                    f"Email subject: {email.subject[:30]}"
                )
                return code

        return None

    def filter_emails_by_sender(
        self,
        emails: List[EmailMessage],
        sender_patterns: List[str],
    ) -> List[EmailMessage]:
        """
        Filter messages by sender

        Args:
            emails: mailing list
            sender_patterns: list of sender matching patterns

        Returns:
            Filtered mailing list
        """
        filtered = []
        for email in emails:
            sender = email.sender.lower()
            if any(pattern.lower() in sender for pattern in sender_patterns):
                filtered.append(email)
        return filtered

    def filter_emails_by_subject(
        self,
        emails: List[EmailMessage],
        keywords: List[str],
    ) -> List[EmailMessage]:
        """
        Filter emails by subject keywords

        Args:
            emails: mailing list
            keywords: keyword list

        Returns:
            Filtered mailing list
        """
        filtered = []
        for email in emails:
            subject = email.subject.lower()
            if any(kw.lower() in subject for kw in keywords):
                filtered.append(email)
        return filtered


# Global parser instance
_parser: Optional[EmailParser] = None


def get_email_parser() -> EmailParser:
    """Get the global mail parser instance"""
    global _parser
    if _parser is None:
        _parser = EmailParser()
    return _parser
