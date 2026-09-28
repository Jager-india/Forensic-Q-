"""
Q-Bank Database Models
Stores audited bank accounts, statement import campaigns, transactions, and watchlist flags.
"""

from decimal import Decimal

from django.db import models

from core.models import ForensicBaseModel


class AuditedPerson(ForensicBaseModel):
    """
    Individual auditee, custodian, or employee under forensic financial investigation.
    Can hold multiple bank accounts and multiple statements across different institutions.
    """

    full_name = models.CharField(
        max_length=255, db_index=True, help_text="Auditee / Person Full Name"
    )
    employee_id = models.CharField(
        max_length=64, blank=True, default="", help_text="Employee ID / Case Ref"
    )
    department = models.CharField(max_length=128, blank=True, default="")
    designation = models.CharField(max_length=128, blank=True, default="")
    pan_number = models.CharField(max_length=32, blank=True, default="", help_text="PAN / Tax ID")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        app_label = "q_bank"
        ordering = ["full_name"]
        verbose_name = "Audited Person"
        verbose_name_plural = "Audited Persons"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.department or 'General'})"


class BankAccount(ForensicBaseModel):
    """
    Bank account or forensic financial investigation target.
    """

    class AccountStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active Audit"
        COMPLETED = "COMPLETED", "Audit Completed"
        FLAGGED = "FLAGGED", "High Risk / Flagged"

    person = models.ForeignKey(
        AuditedPerson,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
        null=True,
        blank=True,
        help_text="Associated Audited Person / Target Custodian",
    )
    account_number = models.CharField(
        max_length=64, blank=True, default="", db_index=True, help_text="Account / Card Number"
    )
    bank_name = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Financial Institution (e.g. HDFC, ICICI, SBI)",
    )
    account_holder = models.CharField(
        max_length=255, blank=True, default="", help_text="Primary Account Holder / Auditee"
    )
    statement_label = models.CharField(
        max_length=255, blank=True, default="", help_text="Audit Campaign Label"
    )
    source_filename = models.CharField(max_length=255, blank=True, default="")
    currency = models.CharField(max_length=8, default="INR")
    total_transactions = models.IntegerField(default=0)
    total_debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    total_credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    cash_deposit_count = models.IntegerField(default=0)
    hyundai_count = models.IntegerField(default=0)
    high_risk_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        app_label = "q_bank"
        ordering = ["-created_at"]
        verbose_name = "Bank Account Audit"
        verbose_name_plural = "Bank Account Audits"

    def __str__(self) -> str:
        holder = self.account_holder or "Unassigned"
        bank = self.bank_name or "Bank Statement"
        return f"[{bank}] {holder} ({self.total_transactions} txns)"


class BankTransaction(ForensicBaseModel):
    """
    Individual ledger transaction extracted from an audited statement.
    """

    class Direction(models.TextChoices):
        CREDIT = "IN", "Credit (Deposit)"
        DEBIT = "OUT", "Debit (Withdrawal)"

    class RiskLevel(models.TextChoices):
        LOW = "Low", "Low Risk"
        MEDIUM = "Medium", "Medium Risk"
        HIGH = "High", "High Risk / Suspicious"

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
        help_text="Originating Statement Account",
    )
    txn_ref = models.CharField(max_length=128, blank=True, default="", db_index=True)
    txn_date = models.DateTimeField(null=True, blank=True, db_index=True)
    value_date = models.DateTimeField(null=True, blank=True)
    narration = models.TextField(blank=True, default="", help_text="Raw bank transaction narration")
    party_name = models.CharField(
        max_length=255, db_index=True, help_text="Extracted counterparty / tracking entity"
    )
    direction = models.CharField(
        max_length=8,
        choices=Direction.choices,
        default=Direction.DEBIT,
        db_index=True,
    )
    debit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    credit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    closing_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    source_page = models.CharField(
        max_length=64, blank=True, default="", help_text="Source Page / Reference"
    )
    is_cash_deposit = models.BooleanField(
        default=False, db_index=True, help_text="CDM / Cash deposit"
    )
    is_hyundai_related = models.BooleanField(
        default=False, db_index=True, help_text="Hyundai entity match"
    )
    risk_score = models.IntegerField(default=0, db_index=True, help_text="Risk score (0-100)")
    risk_level = models.CharField(
        max_length=16,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
        db_index=True,
    )
    status = models.CharField(max_length=32, default="Cleared")
    flag_reason = models.TextField(blank=True, default="")

    class Meta:
        app_label = "q_bank"
        ordering = ["-txn_date", "-created_at"]
        verbose_name = "Bank Transaction"
        verbose_name_plural = "Bank Transactions"

    def __str__(self) -> str:
        return f"{self.txn_date or 'N/A'} | {self.party_name} | {self.direction} ₹{self.debit_amount or self.credit_amount}"


class WatchlistRule(ForensicBaseModel):
    """
    Customizable keyword and entity risk screening rules.
    """

    rule_name = models.CharField(max_length=128)
    keyword = models.CharField(max_length=128, db_index=True)
    risk_weight = models.IntegerField(default=50)
    category = models.CharField(max_length=64, default="General")
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "q_bank"
        ordering = ["-risk_weight", "rule_name"]
        verbose_name = "Watchlist Rule"
        verbose_name_plural = "Watchlist Rules"

    def __str__(self) -> str:
        return f"{self.rule_name} ('{self.keyword}' -> +{self.risk_weight})"
