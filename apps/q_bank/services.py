"""
Q-Bank Services Layer (Business Logic & Mutations)
Handles statement ingestion, forensic risk scoring, and atomic batch creations.
"""

import uuid
from decimal import Decimal
from typing import Any

import pandas as pd
from django.db import transaction
from django.utils import timezone
from loguru import logger

from .backend.statement_parser import parse_bank_statement_dataframe
from .models import AuditedPerson, BankAccount, BankTransaction, WatchlistRule


@transaction.atomic
def create_audited_person(
    *,
    full_name: str,
    employee_id: str = "",
    department: str = "",
    designation: str = "",
    pan_number: str = "",
    email: str = "",
    phone: str = "",
    notes: str = "",
) -> AuditedPerson:
    """
    Creates a new target person/custodian profile for forensic statement investigations.
    """
    person = AuditedPerson.objects.create(
        full_name=full_name.strip(),
        employee_id=employee_id.strip(),
        department=department.strip(),
        designation=designation.strip(),
        pan_number=pan_number.strip(),
        email=email.strip(),
        phone=phone.strip(),
        notes=notes.strip(),
    )
    logger.info("Created new audited person profile: '{}' (ID: {})", person.full_name, person.id)
    return person


@transaction.atomic
def delete_audited_person(person_id: str | uuid.UUID) -> bool:
    """
    Deletes an audited person profile and cascades to all linked bank statements and transactions.
    """
    try:
        person = AuditedPerson.objects.get(id=person_id)
        person.delete()
        logger.info("Deleted audited person profile ID {}", person_id)
        return True
    except (AuditedPerson.DoesNotExist, ValueError):
        return False


@transaction.atomic
def get_or_create_audited_person_from_profile(profile: Any) -> AuditedPerson:
    """
    Retrieves or creates an AuditedPerson matching an InvestigationProfile.
    """
    person, created = AuditedPerson.objects.get_or_create(
        full_name=profile.full_name,
        defaults={
            "employee_id": profile.employee_id,
            "department": profile.department,
            "designation": profile.designation,
            "email": profile.email,
            "phone": profile.phone,
            "notes": profile.notes,
        },
    )
    if created:
        logger.info("Created AuditedPerson from InvestigationProfile: '{}'", profile.full_name)
    return person


@transaction.atomic
def ensure_account_linked_to_person(account: BankAccount) -> BankAccount:
    """
    Ensures a bank account is linked to an AuditedPerson, creating a default one if absent.
    """
    if not account.person_id:
        person, _ = AuditedPerson.objects.get_or_create(
            full_name=account.account_holder or "Auditee Custodian",
            defaults={"department": "General Auditee"},
        )
        account.person = person
        account.save(update_fields=["person"])
        logger.info("Linked BankAccount {} to AuditedPerson '{}'", account.id, person.full_name)
    return account


@transaction.atomic
def ingest_bank_statement_file(
    *,
    file_obj_or_path: Any,
    filename: str,
    account_holder: str = "",
    bank_name: str = "",
    statement_label: str = "",
    account_number: str = "",
    person_id: str | uuid.UUID | None = None,
) -> BankAccount:
    """
    Parses and ingests a bank statement file (Excel, CSV, Word, or PDF) atomically.
    Executes forensic normalization, entity extraction, cash deposit flagging, and risk classification.
    """
    target_person = None
    if person_id:
        try:
            target_person = AuditedPerson.objects.get(id=person_id)
        except (AuditedPerson.DoesNotExist, ValueError):
            target_person = None

    if not target_person and account_holder:
        target_person, _ = AuditedPerson.objects.get_or_create(
            full_name=account_holder.strip(),
            defaults={"notes": "Auto-created from statement import"},
        )

    auditee_display_name = (
        target_person.full_name if target_person else (account_holder or "Auditee Entity")
    )
    logger.info(
        "Ingesting bank statement file '{}' for auditee '{}'", filename, auditee_display_name
    )

    df = parse_bank_statement_dataframe(file_obj_or_path, filename)
    if df.empty:
        raise ValueError(f"No valid transaction rows could be parsed from '{filename}'.")

    # Determine bank name if unspecified
    if not bank_name:
        fname_upper = filename.upper()
        if "HDFC" in fname_upper:
            bank_name = "HDFC Bank"
        elif "ICICI" in fname_upper:
            bank_name = "ICICI Bank"
        elif "SBI" in fname_upper or "STATE" in fname_upper:
            bank_name = "State Bank of India"
        elif "AXIS" in fname_upper:
            bank_name = "Axis Bank"
        elif "KOTAK" in fname_upper:
            bank_name = "Kotak Mahindra Bank"
        else:
            bank_name = "Bank Account Audit"

    account = BankAccount.objects.create(
        person=target_person,
        account_holder=auditee_display_name,
        bank_name=bank_name,
        statement_label=statement_label or f"Statement Audit - {filename}",
        account_number=account_number,
        source_filename=filename,
    )

    # Active watchlist rules for keyword screening
    watchlist = list(WatchlistRule.objects.filter(is_active=True))

    transactions_to_create = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    cash_deposit_count = 0
    hyundai_count = 0
    high_risk_count = 0

    for _, row in df.iterrows():
        narration = str(row.get("Narration", "")).strip()
        party_name = str(row.get("UPI_Name", row.get("Name", "Other Account Operations"))).strip()
        txn_ref = str(row.get("Transaction ID", "")).strip()

        debit_val = Decimal(str(row.get("Debit Amount", 0.0) or 0.0)).quantize(Decimal("0.01"))
        credit_val = Decimal(str(row.get("Credit Amount", 0.0) or 0.0)).quantize(Decimal("0.01"))
        closing_bal = Decimal(str(row.get("Closing Balance", 0.0) or 0.0)).quantize(Decimal("0.01"))

        direction = (
            BankTransaction.Direction.CREDIT if credit_val > 0 else BankTransaction.Direction.DEBIT
        )
        total_debit += debit_val
        total_credit += credit_val

        # Detect Cash Deposit (CDM)
        is_cash = False
        narr_lower = narration.lower()
        if "cash deposit" in narr_lower or "cdm" in narr_lower or "cash dep" in narr_lower:
            is_cash = True
            cash_deposit_count += 1

        # Detect Hyundai related transactions
        is_hyundai = False
        if "hyundai" in narr_lower or "hmil" in narr_lower or "hyundai" in party_name.lower():
            is_hyundai = True
            hyundai_count += 1

        # Date parsing
        txn_date = None
        raw_date = str(row.get("Date", "")).strip()
        if raw_date and raw_date not in ["0", "", "nan", "None"]:
            try:
                parsed_dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
                if pd.notna(parsed_dt):
                    txn_date = timezone.make_aware(
                        parsed_dt.to_pydatetime(), timezone.get_current_timezone()
                    )
            except Exception:
                txn_date = None

        value_date = None
        raw_vdate = str(row.get("Value Date", "")).strip()
        if raw_vdate and raw_vdate not in ["0", "", "nan", "None"]:
            try:
                parsed_vdt = pd.to_datetime(raw_vdate, dayfirst=True, errors="coerce")
                if pd.notna(parsed_vdt):
                    value_date = timezone.make_aware(
                        parsed_vdt.to_pydatetime(), timezone.get_current_timezone()
                    )
            except Exception:
                value_date = None

        # Risk scoring
        risk_score = 0
        reasons = []

        if is_cash and credit_val >= 50000:
            risk_score += 40
            reasons.append("High-Value Cash Deposit (CDM)")

        if debit_val >= 500000:
            risk_score += 35
            reasons.append("High-Value Debit Wire (> ₹5,00,000)")

        # Watchlist rule screening
        for rule in watchlist:
            if rule.keyword.lower() in narr_lower or rule.keyword.lower() in party_name.lower():
                risk_score += rule.risk_weight
                reasons.append(f"Watchlist Rule: {rule.rule_name}")

        risk_score = min(risk_score, 100)
        risk_level = (
            BankTransaction.RiskLevel.HIGH
            if risk_score >= 70
            else (
                BankTransaction.RiskLevel.MEDIUM
                if risk_score >= 40
                else BankTransaction.RiskLevel.LOW
            )
        )

        if risk_level == BankTransaction.RiskLevel.HIGH:
            high_risk_count += 1

        source_page = str(row.get("Source_Page", "") or "Page_1").strip()

        transactions_to_create.append(
            BankTransaction(
                account=account,
                txn_ref=txn_ref,
                txn_date=txn_date,
                value_date=value_date,
                narration=narration,
                party_name=party_name,
                direction=direction,
                debit_amount=debit_val,
                credit_amount=credit_val,
                closing_balance=closing_bal,
                source_page=source_page,
                is_cash_deposit=is_cash,
                is_hyundai_related=is_hyundai,
                risk_score=risk_score,
                risk_level=risk_level,
                status="Flagged" if risk_score >= 70 else "Cleared",
                flag_reason="; ".join(reasons),
            )
        )

    # Batch insertion for N+1 prevention
    BankTransaction.objects.bulk_create(transactions_to_create, batch_size=250)

    account.total_transactions = len(transactions_to_create)
    account.total_debit = total_debit
    account.total_credit = total_credit
    account.cash_deposit_count = cash_deposit_count
    account.hyundai_count = hyundai_count
    account.high_risk_count = high_risk_count
    account.save(
        update_fields=[
            "total_transactions",
            "total_debit",
            "total_credit",
            "cash_deposit_count",
            "hyundai_count",
            "high_risk_count",
        ]
    )

    logger.info(
        "Successfully ingested {} transactions for account '{}' (Total Debit: ₹{}, Credit: ₹{})",
        account.total_transactions,
        account.account_holder,
        account.total_debit,
        account.total_credit,
    )
    return account


@transaction.atomic
def delete_bank_account(account_id: str | uuid.UUID) -> bool:
    """
    Deletes an audited bank account and cascades to all its associated transactions.
    """
    try:
        account = BankAccount.objects.get(id=account_id)
        account.delete()
        logger.info("Deleted bank account case ID {}", account_id)
        return True
    except (BankAccount.DoesNotExist, ValueError):
        return False
