"""
Q-Bank Forensic Unit & Integration Tests
Tests statement parsing, entity extraction, cash deposit detection, Hyundai rules, and Tabulator APIs.
"""

import io
from decimal import Decimal

import pandas as pd
from django.test import Client, TestCase
from django.urls import reverse

from .backend.statement_parser import (
    extract_clean_tracking_name,
    format_inr,
    normalize_dataframe,
)
from .models import BankAccount, BankTransaction, WatchlistRule
from .selectors import (
    fuzzy_search_transactions,
    get_bank_dashboard_metrics,
    get_frequent_counterparties,
    get_hyundai_metrics,
)
from .services import delete_bank_account, ingest_bank_statement_file


class QBankStatementTests(TestCase):
    """
    Validates parsing, normalization, and entity extraction.
    """

    def test_format_inr(self):
        self.assertEqual(format_inr(1000), "1,000.00")
        self.assertEqual(format_inr(150000), "1,50,000.00")
        self.assertEqual(format_inr(12345678.50), "1,23,45,678.50")
        self.assertEqual(format_inr(-50000), "-50,000.00")

    def test_extract_clean_tracking_name(self):
        # UPI VPA
        name1 = extract_clean_tracking_name("UPI/428912/john.doe@okaxis/Payment for supplies")
        self.assertEqual(name1.upper(), "JOHN DOE")

        # Slash-delimited NetBanking
        name2 = extract_clean_tracking_name("NEFT/N1029384/ABC LOGISTICS CORP/HDFC000123")
        self.assertEqual(name2.upper(), "ABC LOGISTICS CORP")

        # POS / Card merchant
        name3 = extract_clean_tracking_name("POS-RESTAURANT CHENNAI 12:30:00")
        self.assertIn("RESTAURANT", name3.upper())

    def test_normalize_dataframe(self):
        raw_data = {
            "Tran Date": ["2026-03-01", "2026-03-02"],
            "Particulars": ["UPI/test@okaxis", "NEFT/SUPPLIER/123"],
            "Withdrawal (Dr)": ["1,500.00", "0.00"],
            "Deposit (Cr)": ["0.00", "25,000.00"],
            "Balance": ["1,00,000.00", "1,25,000.00"],
        }
        df = pd.DataFrame(raw_data)
        normalized = normalize_dataframe(df)

        self.assertIn("Date", normalized.columns)
        self.assertIn("Narration", normalized.columns)
        self.assertIn("Debit Amount", normalized.columns)
        self.assertIn("Credit Amount", normalized.columns)
        self.assertIn("Closing Balance", normalized.columns)
        self.assertEqual(normalized["Debit Amount"].iloc[0], 1500.00)
        self.assertEqual(normalized["Credit Amount"].iloc[1], 25000.00)


class QBankServicesAndSelectorsTests(TestCase):
    """
    Validates atomic ingestion, risk scoring, selectors, and API endpoints.
    """

    def setUp(self):
        self.client = Client()
        session = self.client.session
        session["portal_authenticated"] = True
        session.save()

        # Create sample CSV statement in memory
        csv_content = """Date,Narration,Transaction ID,Debit Amount,Credit Amount,Closing Balance
01/01/2026,UPI/998811/sarla_enterprises@okaxis/Invoice 101,TXN1001,500000.00,0.00,1000000.00
02/01/2026,BY CASH DEPOSIT CDM BRANCH,TXN1002,0.00,75000.00,1075000.00
03/01/2026,NEFT/HMIL VENDOR PAYMENT HYUNDAI MOTORS,TXN1003,0.00,250000.00,1325000.00
04/01/2026,UPI/998811/sarla_enterprises@okaxis/Invoice 102,TXN1004,15000.00,0.00,1310000.00
05/01/2026,UPI/998811/sarla_enterprises@okaxis/Invoice 103,TXN1005,20000.00,0.00,1290000.00
"""
        csv_file = io.BytesIO(csv_content.encode("utf-8"))

        WatchlistRule.objects.create(rule_name="Sarla Flag", keyword="sarla", risk_weight=40)

        self.account = ingest_bank_statement_file(
            file_obj_or_path=csv_file,
            filename="hdfc_statement.csv",
            account_holder="Vikash Test Account",
            bank_name="HDFC Bank",
            statement_label="Q1 Audit Investigation",
            account_number="987654321",
        )

    def test_ingest_bank_statement_metrics(self):
        self.assertEqual(self.account.total_transactions, 5)
        self.assertEqual(self.account.cash_deposit_count, 1)
        self.assertEqual(self.account.hyundai_count, 1)
        self.assertGreater(self.account.total_debit, Decimal("500000.00"))

        # Verify transaction risk scoring
        txns = BankTransaction.objects.filter(account=self.account)
        self.assertEqual(txns.count(), 5)

        # CDM cash deposit check
        cdm_txn = txns.filter(is_cash_deposit=True).first()
        self.assertIsNotNone(cdm_txn)
        self.assertEqual(cdm_txn.credit_amount, Decimal("75000.00"))

        # Hyundai check
        hyundai_txn = txns.filter(is_hyundai_related=True).first()
        self.assertIsNotNone(hyundai_txn)

    def test_selectors(self):
        metrics = get_bank_dashboard_metrics()
        self.assertEqual(metrics["total_accounts"], 1)
        self.assertEqual(metrics["total_txns"], 5)
        self.assertEqual(metrics["cash_deposit_count"], 1)
        self.assertEqual(metrics["hyundai_count"], 1)

        frequent = get_frequent_counterparties(account_id=self.account.id, min_interactions=2)
        self.assertTrue(len(frequent) > 0)
        self.assertIn("sarla", frequent[0]["party_name"].lower())

        hyundai_m = get_hyundai_metrics(account_id=self.account.id)
        self.assertTrue(hyundai_m["hyundai_present"])
        self.assertEqual(hyundai_m["total_count"], 1)

        # CDM Rows test
        from .selectors import (
            get_cdm_transactions,
            get_frequent_transactions_breakdown,
            get_hyundai_details,
        )

        cdm_rows = get_cdm_transactions(account_id=self.account.id)
        self.assertEqual(len(cdm_rows), 1)
        self.assertEqual(cdm_rows[0]["credit_amount"], 75000.0)

        # Hyundai details test
        h_details = get_hyundai_details(account_id=self.account.id)
        self.assertTrue(h_details["hyundai_present"])
        self.assertEqual(len(h_details["rows"]), 1)

        # Frequent breakdown test
        breakdown = get_frequent_transactions_breakdown(
            account_id=self.account.id, min_transactions=2
        )
        self.assertIn("debit_choices", breakdown)
        self.assertIn("credit_choices", breakdown)
        self.assertTrue(len(breakdown["debit_choices"]) > 0)

    def test_fuzzy_search(self):
        matches = fuzzy_search_transactions(
            account_id=self.account.id,
            keywords_str="sarla, trust",
            threshold=70,
        )
        self.assertGreater(len(matches), 0)
        self.assertIn("sarla", matches[0]["narration"].lower())

    def test_api_transactions(self):
        res = self.client.get(
            reverse("q_bank:transactions_api"), {"account_id": str(self.account.id)}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_count"], 5)
        self.assertEqual(len(data["data"]), 5)

    def test_views_and_exports(self):
        dash_res = self.client.get(reverse("q_bank:dashboard"))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Q-Bank")

        detail_res = self.client.get(
            reverse("q_bank:account_detail", args=[self.account.id]), follow=True
        )
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Vikash Test Account")

        export_res = self.client.get(reverse("q_bank:export_ledger_excel"))
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(
            export_res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_multi_bank_statements_per_person(self):
        person = self.account.person
        self.assertIsNotNone(person)
        self.assertEqual(person.full_name, "Vikash Test Account")

        # Ingest a second statement (SBI) for the same person
        sbi_csv = """Date,Narration,Transaction ID,Debit Amount,Credit Amount,Closing Balance
10/01/2026,UPI/112233/vendor_corp@sbi/Equip 201,SBI001,12000.00,0.00,50000.00
11/01/2026,BY CASH DEPOSIT CDM SBI KOYAMBEDU,SBI002,0.00,30000.00,80000.00
"""
        sbi_file = io.BytesIO(sbi_csv.encode("utf-8"))
        sbi_acc = ingest_bank_statement_file(
            file_obj_or_path=sbi_file,
            filename="sbi_statement.csv",
            person_id=person.id,
            bank_name="State Bank of India",
            statement_label="SBI Current Account",
            account_number="330011223344",
        )
        self.assertEqual(sbi_acc.person_id, person.id)
        self.assertEqual(person.bank_accounts.count(), 2)

        # Test Person detail view (Combined All Statements)
        person_res = self.client.get(reverse("q_bank:person_detail", args=[person.id]))
        self.assertEqual(person_res.status_code, 200)
        self.assertContains(person_res, "Vikash Test Account")
        self.assertContains(person_res, "HDFC Bank")
        self.assertContains(person_res, "State Bank of India")

        # Test Person detail view scoped to single account
        scoped_res = self.client.get(
            f"{reverse('q_bank:person_detail', args=[person.id])}?account_id={sbi_acc.id}"
        )
        self.assertEqual(scoped_res.status_code, 200)

        # Test API with person_id
        api_res = self.client.get(reverse("q_bank:transactions_api"), {"person_id": str(person.id)})
        self.assertEqual(api_res.status_code, 200)
        self.assertEqual(api_res.json()["total_count"], 7)  # 5 from HDFC + 2 from SBI

    def test_delete_person(self):
        person = self.account.person
        self.assertIsNotNone(person)
        from .services import delete_audited_person

        success = delete_audited_person(person.id)
        self.assertTrue(success)
        self.assertEqual(BankAccount.objects.count(), 0)
        self.assertEqual(BankTransaction.objects.count(), 0)

    def test_delete_account(self):
        success = delete_bank_account(self.account.id)
        self.assertTrue(success)
        self.assertEqual(BankAccount.objects.count(), 0)
        self.assertEqual(BankTransaction.objects.count(), 0)
