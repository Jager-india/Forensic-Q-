"""
Q-Mail Forensic Checkpoints Demonstration & Seeding Script
Populates comprehensive sample email evidence for testing all 10 Mail Checkpoints:
1. Currency mentions (INR, USD, ₹, Lakhs, Crores)
2. Without CC/BCC (1-on-1 covert messages)
3. Personal Webmail IDs (@gmail.com, @yahoo.com, etc.)
4. Non-HMIL communications
5. Primary Bank statements and alerts (HDFC, SBI, ICICI)
6. UPI payment transaction notifications (PhonePe, GPay, Paytm)
7. Default keywords (PAYMENT, GIFT, SALARY, TAX, LOAN, CIBIL)
8. Custom keywords and date ranges
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import django

# Setup Django Environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ForensiQ.settings")

django.setup()

from q_mail.models import EmailMessage, MailboxInvestigation  # noqa: E402


def seed_mail_checkpoints():
    print("Seeding Q-Mail investigation with forensic checkpoint emails...")

    # Fetch or create CFO investigation
    cfo_inv, _ = MailboxInvestigation.objects.get_or_create(
        audit_ref="AUD-MAIL-2026-D688F8",
        defaults={
            "audit_name": "Executive Email Review",
            "auditee_name": "Chief Financial Officer",
            "auditee_email": "cfo@enterprise.internal",
            "auditee_department": "Executive Board",
            "auditee_designation": "CFO",
            "pst_file_name": "cfo_executive_archive.pst",
            "file_size_bytes": 104857600,
            "status": MailboxInvestigation.IngestionStatus.COMPLETED,
            "progress_percent": 100.0,
            "total_messages_estimated": 12,
            "processed_messages_count": 12,
        },
    )
    cfo_inv.status = MailboxInvestigation.IngestionStatus.COMPLETED
    cfo_inv.error_message = ""
    cfo_inv.progress_percent = 100.0
    cfo_inv.save()

    # Clear old messages for clean demonstration
    cfo_inv.messages.all().delete()

    sample_emails = [
        {
            "message_id": "<CFO-001@enterprise.internal>",
            "subject": "Confidential: Off-ledger vendor wire transfer of ₹45,00,000 INR",
            "sender_name": "Rajesh Kumar (Personal)",
            "sender_email": "rajesh.kumar992@gmail.com",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": [],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 4, 15, 14, 30, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/Inbox",
            "body_plain": "Dear Sir,\n\nAs discussed in private, we have arranged the payment of ₹45,00,000 (Forty-Five Lakhs INR) via direct RTGS transfer. Please keep this off-record without copying anyone else.\n\nRegards,\nRajesh",
            "importance": 2,
            "matched_keywords": ["PAYMENT", "₹", "INR", "Lakhs"],
            "risk_score": 90,
            "risk_level": "High",
            "is_flagged": True,
        },
        {
            "message_id": "<HDFC-ALERT-9921@hdfcbank.net>",
            "subject": "HDFC Bank Alert: Salary Credit of ₹ 3,25,000.00 to Account **4129",
            "sender_name": "HDFC Bank NetBanking",
            "sender_email": "alerts@hdfcbank.net",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": [],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 4, 30, 9, 15, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/Banking",
            "body_plain": "Dear Customer, Your A/c **4129 has been credited with ₹ 3,25,000.00 on 30-APR-2026 by NEFT HYUNDAI MOTOR INDIA LTD SALARY. Available Balance: ₹ 14,82,900.50.",
            "importance": 1,
            "matched_keywords": ["SALARY", "PAYMENT", "HDFC", "₹"],
            "risk_score": 30,
            "risk_level": "Low",
            "is_flagged": False,
        },
        {
            "message_id": "<PHONEPE-UPI-88192@phonepe.com>",
            "subject": "UPI Payment Successful to Sarla Traders: ₹82,800 Ref No 4092182910",
            "sender_name": "PhonePe Support",
            "sender_email": "no-reply@phonepe.com",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": [],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 5, 2, 18, 45, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/UPI Alerts",
            "body_plain": "Payment of ₹82,800 to VPA sarlatraders@yespay is successful. UPI Transaction ID: 4092182910. Debited from State Bank of India A/c **6251.",
            "importance": 1,
            "matched_keywords": ["UPI", "PAYMENT", "₹"],
            "risk_score": 60,
            "risk_level": "Medium",
            "is_flagged": True,
        },
        {
            "message_id": "<SBI-LOAN-4410@sbi.co.in>",
            "subject": "SBI Home Loan Sanction & CIBIL Score Verification Status",
            "sender_name": "State Bank of India",
            "sender_email": "homeloans@sbi.co.in",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": [],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 5, 10, 11, 20, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/Banking",
            "body_plain": "Dear Applicant, Your loan application #LN-99201 for ₹1.25 Crore has been pre-approved based on your updated CIBIL score of 815. Please review the attached loan repayment schedule.",
            "importance": 1,
            "matched_keywords": ["LOAN", "CIBIL", "Crore", "₹"],
            "risk_score": 40,
            "risk_level": "Low",
            "is_flagged": False,
        },
        {
            "message_id": "<GIFT-OFFER-771@yahoo.com>",
            "subject": "Fwd: Festival Gift Voucher & Executive Holiday Package Confirmation",
            "sender_name": "Vikram Transport Logistics",
            "sender_email": "vikram_transport@yahoo.com",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": [],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 5, 18, 16, 0, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/Inbox",
            "body_plain": "Sir, Sending you the luxury resort gift vouchers as agreed for the successful contract renewal. Please confirm receipt on your personal number.",
            "importance": 2,
            "matched_keywords": ["GIFT"],
            "risk_score": 85,
            "risk_level": "High",
            "is_flagged": True,
        },
        {
            "message_id": "<TAX-CONSULT-1029@incometax.internal>",
            "subject": "FY 2025-26 Advance Tax Calculation & TDS Filing Summary",
            "sender_name": "Tax Advisory Services",
            "sender_email": "advisory@taxaudit-chennai.com",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": ["finance.team@hmil.net"],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/Taxation",
            "body_plain": "Dear CFO, Please find attached the quarterly Advance Tax schedule totaling ₹18,50,000 due by 15th June 2026.",
            "importance": 1,
            "matched_keywords": ["TAX", "PAYMENT", "₹"],
            "risk_score": 20,
            "risk_level": "Low",
            "is_flagged": False,
        },
        {
            "message_id": "<GPAY-ALERT-2281@google.com>",
            "subject": "Google Pay: You paid ₹15,000 to Sri Balaji Auto Spares",
            "sender_name": "Google Pay",
            "sender_email": "googlepay-noreply@google.com",
            "recipients_to": ["cfo@enterprise.internal"],
            "recipients_cc": [],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 6, 12, 20, 10, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/UPI Alerts",
            "body_plain": "Your payment of ₹15,000 to sribalajispare@okaxis was completed via UPI ID 281902810. Bank Reference #501982.",
            "importance": 1,
            "matched_keywords": ["UPI", "PAYMENT", "₹"],
            "risk_score": 50,
            "risk_level": "Medium",
            "is_flagged": False,
        },
        {
            "message_id": "<HMIL-INTERNAL-9901@hmil.net>",
            "subject": "Official: Q1 Operating Budget Allocation & Cost Center Approvals",
            "sender_name": "Executive Director Finance",
            "sender_email": "ed.finance@hmil.net",
            "recipients_to": ["cfo@enterprise.internal", "plant.finance@hmil.net"],
            "recipients_cc": ["audit.board@hmil.net"],
            "recipients_bcc": [],
            "sent_date": datetime(2026, 6, 20, 11, 30, tzinfo=UTC),
            "folder_path": "Top of Personal Folders/Corporate",
            "body_plain": "Dear Team, Attached is the official board-approved budget allocation for Q1 FY26 across Chennai plants.",
            "importance": 1,
            "matched_keywords": [],
            "risk_score": 10,
            "risk_level": "Low",
            "is_flagged": False,
        },
    ]

    for item in sample_emails:
        EmailMessage.objects.create(
            mailbox=cfo_inv,
            message_id=item["message_id"],
            subject=item["subject"],
            sender_name=item["sender_name"],
            sender_email=item["sender_email"],
            recipients_to=item["recipients_to"],
            recipients_cc=item["recipients_cc"],
            recipients_bcc=item["recipients_bcc"],
            sent_date=item["sent_date"],
            delivery_date=item["sent_date"],
            folder_path=item["folder_path"],
            body_plain=item["body_plain"],
            importance=item["importance"],
            matched_keywords=item["matched_keywords"],
            risk_score=item["risk_score"],
            risk_level=item["risk_level"],
            is_flagged=item["is_flagged"],
            has_attachments=False,
            attachment_count=0,
        )

    cfo_inv.total_messages_estimated = len(sample_emails)
    cfo_inv.processed_messages_count = len(sample_emails)
    cfo_inv.save()
    print(
        f"Successfully seeded {len(sample_emails)} emails for {cfo_inv.auditee_name} ({cfo_inv.audit_ref})!"
    )


if __name__ == "__main__":
    seed_mail_checkpoints()
