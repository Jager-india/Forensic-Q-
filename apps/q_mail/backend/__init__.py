"""
Q-Mail Backend Analysis Engine
Contains pure Python PST forensic parsers powered by pypff (libpff-python-windows).
"""

from .checkpoints import (
    DEFAULT_KEYWORDS,
    check_currency,
    check_no_cc_bcc,
    check_non_hmil,
    check_personal_sender,
    check_primary_bank,
    check_upi_payment,
    evaluate_email_checkpoints,
    match_default_keywords,
)
from .pst_parser import ParsedAttachment, ParsedEmail, PSTStreamParser

__all__ = [
    "DEFAULT_KEYWORDS",
    "PSTStreamParser",
    "ParsedAttachment",
    "ParsedEmail",
    "check_currency",
    "check_no_cc_bcc",
    "check_non_hmil",
    "check_personal_sender",
    "check_primary_bank",
    "check_upi_payment",
    "evaluate_email_checkpoints",
    "match_default_keywords",
]
