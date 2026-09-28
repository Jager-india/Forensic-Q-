import os
import sys
from pathlib import Path

import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ForensiQ.settings")

django.setup()

from django.test import Client  # noqa: E402
from q_mail.models import MailboxInvestigation  # noqa: E402

client = Client(SERVER_NAME="127.0.0.1")
session = client.session
session["portal_authenticated"] = True
session.save()

cfo_inv = MailboxInvestigation.objects.get(audit_ref="AUD-MAIL-2026-D688F8")

print("=== 1. Testing Investigation Detail HTML View ===")
r_detail = client.get(f"/mail/investigation/{cfo_inv.id}/")
print("Detail View Status:", r_detail.status_code)
assert r_detail.status_code == 200
assert b"Forensic Checkpoints" in r_detail.content
assert b"Currency Mentions" in r_detail.content
assert b"1-on-1 Direct" in r_detail.content
assert b"Personal Webmail" in r_detail.content
assert b"Primary Bank" in r_detail.content
assert b"UPI Payment" in r_detail.content
print("-> Forensic Checkpoints Tab renders perfectly in HTML")

print("\n=== 2. Testing Checkpoints Summary JSON API ===")
r_sum = client.get(f"/mail/investigation/{cfo_inv.id}/checkpoints/")
print("Summary API Status:", r_sum.status_code)
assert r_sum.status_code == 200
sum_data = r_sum.json()["checkpoints"]
print("Checkpoints Summary Data:", sum_data)
assert sum_data["currency_count"] > 0
assert sum_data["no_cc_bcc_count"] > 0
assert sum_data["personal_sender_count"] > 0
assert sum_data["primary_bank_count"] > 0
assert sum_data["upi_payment_count"] > 0
print("-> All Checkpoint counters aggregated accurately")

print("\n=== 3. Testing Filtered Checkpoint APIs ===")
for cp in [
    "currency",
    "no_cc_bcc",
    "personal_mail",
    "primary_bank",
    "upi_payments",
    "GIFT",
    "PAYMENT",
]:
    r_cp = client.get(f"/mail/investigation/{cfo_inv.id}/messages/?checkpoint={cp}")
    data = r_cp.json()
    count = data.get("total_count", 0)
    print(f"-> Checkpoint [{cp}]: {count} emails matched")
    assert count > 0

print("\n=== 4. Testing Checkpoint Excel Export ===")
r_exp = client.get(f"/mail/investigation/{cfo_inv.id}/export/excel/?checkpoint=currency")
print("Excel Export Status:", r_exp.status_code, "Content-Type:", r_exp["Content-Type"])
assert r_exp.status_code == 200
assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in r_exp["Content-Type"]
print("-> Checkpoints Excel Export generated successfully")

print("\n>>> ALL Q-MAIL FORENSIC CHECKPOINTS TESTS PASSED (100%)! <<<")
