"""Email notification utilities for IAMSentry.

This module provides email sending functionality for audit notifications.
Currently implements a stub that logs instead of sending actual emails.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)


def send(
    content: str,
    subject: Optional[str] = None,
    to: Optional[str] = None,
    sender: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    tls: bool = True,
    **kwargs: Any
) -> bool:
    """Send email notification.

    This function sends an email notification. If email configuration
    is incomplete, it will log the notification instead of sending.

    Arguments:
        content: Email body content.
        subject: Email subject line.
        to: Recipient email address.
        sender: Sender email address.
        host: SMTP server hostname.
        port: SMTP server port (default: 587 for TLS, 25 otherwise).
        username: SMTP authentication username.
        password: SMTP authentication password.
        tls: Whether to use TLS encryption (default: True).
        **kwargs: Additional arguments (ignored for compatibility).

    Returns:
        True if email sent successfully (or logged), False on error.

    Example:
        >>> send(
        ...     content='Audit completed successfully',
        ...     subject='IAMSentry Audit Report',
        ...     to='admin@example.com',
        ...     sender='iamsentry@example.com',
        ...     host='smtp.example.com'
        ... )
        True
    """
    # Check if we have minimum configuration to send
    if not all([host, to, sender]):
        _log.debug(
            'Email not configured (missing host, to, or sender). '
            'Logging notification instead.'
        )
        _log.info('Email notification: %s', content[:200] if content else '(empty)')
        return True

    # Set default port
    if port is None:
        port = 587 if tls else 25

    # Set default subject
    if subject is None:
        subject = 'IAMSentry Notification'

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))

        # Connect and send
        with smtplib.SMTP(host, port, timeout=30) as server:
            if tls:
                server.starttls()

            if username and password:
                server.login(username, password)

            server.send_message(msg)

        _log.info('Email sent successfully to %s', to)
        return True

    except smtplib.SMTPAuthenticationError as e:
        _log.error('SMTP authentication failed: %s', e)
        return False

    except smtplib.SMTPException as e:
        _log.error('SMTP error sending email: %s', e)
        return False

    except Exception as e:
        _log.error('Unexpected error sending email: %s: %s', type(e).__name__, e)
        return False


def send_dict(config: Optional[Dict[str, Any]], content: str) -> bool:
    """Send email using configuration dictionary.

    This is a convenience function that unpacks a configuration
    dictionary and calls send().

    Arguments:
        config: Email configuration dictionary with keys matching
            send() parameters. Can be None (will log instead of send).
        content: Email body content.

    Returns:
        True if sent successfully, False on error.

    Example:
        >>> email_config = {
        ...     'host': 'smtp.example.com',
        ...     'to': 'admin@example.com',
        ...     'sender': 'iamsentry@example.com'
        ... }
        >>> send_dict(email_config, 'Audit completed')
        True
    """
    if config is None:
        _log.debug('No email configuration provided, logging notification')
        _log.info('Email notification: %s', content[:200] if content else '(empty)')
        return True

    return send(content=content, **config)
