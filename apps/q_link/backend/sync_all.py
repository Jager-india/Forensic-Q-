"""
Q-Link Cross-Module Synchronizer
Reads existing forensic records from Q-Bank, Q-Ledger, Q-Mail, Q-Trail, Q-Verify
and automatically synthesizes them into the unified Q-Link Knowledge Graph.
"""

from decimal import Decimal

from django.apps import apps
from loguru import logger

from ..models import ForensicEntity
from .dispatcher import emit_forensic_finding


def sync_all_modules() -> dict[str, int]:
    """
    Ingests all active historical data across all ForensiQ modules into Q-Link.
    Returns counts of ingested items per module.
    """
    stats = {
        "q_bank": 0,
        "q_ledger": 0,
        "q_mail": 0,
        "q_trail": 0,
        "q_verify": 0,
    }

    # 1. Ingest Q-Bank (Auditees, Bank Accounts, Transactions)
    if apps.is_installed("q_bank"):
        try:
            AuditedPerson = apps.get_model("q_bank", "AuditedPerson")
            BankTransaction = apps.get_model("q_bank", "BankTransaction")

            # Sync auditees
            for person in AuditedPerson.objects.all():
                emit_forensic_finding(
                    source_module="q_bank",
                    event_type="AUDITEE_PROFILE_SYNC",
                    primary_entity_data={
                        "name": person.full_name,
                        "type": ForensicEntity.EntityType.EMPLOYEE,
                        "raw_id": person.pan_number or person.employee_id or person.full_name,
                        "is_target": True,
                        "metadata": {
                            "employee_id": person.employee_id,
                            "department": person.department,
                            "pan_number": person.pan_number,
                            "email": person.email,
                            "phone": person.phone,
                        },
                    },
                )
                stats["q_bank"] += 1

            # Sync transactions
            for txn in BankTransaction.objects.select_related("account", "account__person")[:500]:
                account_holder = txn.account.account_holder if txn.account else "Unknown Account"
                person_name = (
                    txn.account.person.full_name
                    if (txn.account and txn.account.person)
                    else account_holder
                )

                amt = txn.debit_amount if txn.direction == "OUT" else txn.credit_amount
                if not amt or amt == Decimal("0.00"):
                    amt = txn.debit_amount or txn.credit_amount or Decimal("1.00")

                party_clean = txn.party_name.strip() if txn.party_name else "Unknown Counterparty"

                emit_forensic_finding(
                    source_module="q_bank",
                    event_type="BANK_TRANSACTION",
                    primary_entity_data={
                        "name": person_name,
                        "type": ForensicEntity.EntityType.EMPLOYEE,
                        "is_target": True,
                    },
                    secondary_entities_data=[
                        {
                            "name": party_clean,
                            "type": ForensicEntity.EntityType.VENDOR
                            if any(
                                s in party_clean.lower()
                                for s in ["ltd", "corp", "inc", "enterprises", "solutions"]
                            )
                            else ForensicEntity.EntityType.UNKNOWN,
                            "relation_type": "TRANSFERRED_FUNDS",
                            "weight": float(amt),
                            "direction": "out" if txn.direction == "OUT" else "in",
                        }
                    ],
                    evidence_data={
                        "source_module": "q_bank",
                        "source_model": "BankTransaction",
                        "source_record_id": str(txn.id),
                        "evidence_url": f"/bank/account/{txn.account.id}/"
                        if txn.account
                        else "/bank/",
                        "summary_snippet": f"Txn Ref: {txn.txn_ref} | Party: {party_clean} | Amount: ₹{amt:,.2f}",
                        "occurred_at": txn.txn_date,
                    },
                    occurred_at=txn.txn_date,
                    timeline_title=f"Bank Transfer: ₹{amt:,.2f} ({txn.direction})",
                    timeline_description=f"Transaction with '{party_clean}' via Account {txn.account.account_number if txn.account else ''}",
                    severity="WARNING" if getattr(txn, "risk_score", 0) >= 50 else "INFO",
                )
                stats["q_bank"] += 1
        except Exception as err:
            logger.warning(f"Error syncing Q-Bank: {err}")

    # 2. Ingest Q-Ledger (Purchase Orders, Invoices, Vendors)
    if apps.is_installed("q_ledger"):
        try:
            PurchaseOrder = apps.get_model("q_ledger", "PurchaseOrder")

            for po in PurchaseOrder.objects.select_related("vendor")[:300]:
                vendor_name = po.vendor.vendor_name if po.vendor else "Unknown Vendor"
                po_num = po.po_number

                secondary = [
                    {
                        "name": po_num,
                        "type": ForensicEntity.EntityType.PO,
                        "relation_type": "ISSUED_PO",
                        "weight": float(po.total_amount),
                        "direction": "out",
                    }
                ]
                if po.approved_by:
                    secondary.append(
                        {
                            "name": po.approved_by,
                            "type": ForensicEntity.EntityType.EMPLOYEE,
                            "relation_type": "APPROVED_BY",
                            "direction": "in",
                        }
                    )

                emit_forensic_finding(
                    source_module="q_ledger",
                    event_type="PO_ISSUED",
                    primary_entity_data={
                        "name": vendor_name,
                        "type": ForensicEntity.EntityType.VENDOR,
                        "metadata": {"vendor_code": po.vendor.vendor_code if po.vendor else ""},
                    },
                    secondary_entities_data=secondary,
                    evidence_data={
                        "source_module": "q_ledger",
                        "source_model": "PurchaseOrder",
                        "source_record_id": str(po.id),
                        "evidence_url": f"/ledger/?po={po.po_number}",
                        "summary_snippet": f"PO #{po.po_number} | Amount: ₹{po.total_amount:,.2f} | Approved by: {po.approved_by}",
                        "occurred_at": po.po_date,
                    },
                    occurred_at=po.po_date,
                    timeline_title=f"PO Issued: #{po.po_number} (₹{po.total_amount:,.2f})",
                    timeline_description=f"Purchase order issued to {vendor_name}. Approved by: {po.approved_by}",
                    severity="WARNING" if getattr(po, "is_split_po", False) else "INFO",
                )
                stats["q_ledger"] += 1
        except Exception as err:
            logger.warning(f"Error syncing Q-Ledger: {err}")

    # 3. Ingest Q-Mail (Emails, Senders, Recipients)
    if apps.is_installed("q_mail"):
        try:
            EmailMessage = apps.get_model("q_mail", "EmailMessage")

            for msg in EmailMessage.objects.all()[:300]:
                sender = msg.sender_name or msg.sender_email
                if not sender:
                    continue

                recipients = (
                    msg.recipients_to
                    if isinstance(msg.recipients_to, list)
                    else [str(msg.recipients_to)]
                )

                for rec in recipients:
                    rec_str = (
                        rec.get("email") or rec.get("name") if isinstance(rec, dict) else str(rec)
                    )
                    if not rec_str:
                        continue
                    emit_forensic_finding(
                        source_module="q_mail",
                        event_type="EMAIL_SENT",
                        primary_entity_data={
                            "name": sender,
                            "type": ForensicEntity.EntityType.EMPLOYEE
                            if "@" not in sender
                            else ForensicEntity.EntityType.EMAIL_ID,
                        },
                        secondary_entities_data=[
                            {
                                "name": rec_str,
                                "type": ForensicEntity.EntityType.EMAIL_ID
                                if "@" in rec_str
                                else ForensicEntity.EntityType.EMPLOYEE,
                                "relation_type": "EMAILED",
                                "weight": 1.0,
                                "direction": "out",
                            }
                        ],
                        evidence_data={
                            "source_module": "q_mail",
                            "source_model": "EmailMessage",
                            "source_record_id": str(msg.id),
                            "evidence_url": f"/mail/message/{msg.id}/",
                            "summary_snippet": f"Subject: {msg.subject[:60]} | Date: {msg.sent_date}",
                            "occurred_at": msg.sent_date,
                        },
                        occurred_at=msg.sent_date,
                        timeline_title=f"Email: {msg.subject[:35]}...",
                        timeline_description=f"From: {sender} to: {rec_str}",
                        severity="WARNING" if msg.is_flagged else "INFO",
                    )
                    stats["q_mail"] += 1
        except Exception as err:
            logger.warning(f"Error syncing Q-Mail: {err}")

    # 4. Ingest Q-Trail (Multi-hop Money Trails)
    if apps.is_installed("q_trail"):
        try:
            FundTrailPath = apps.get_model("q_trail", "FundTrailPath")

            for trail in FundTrailPath.objects.all()[:100]:
                secondaries = [
                    {
                        "name": trail.destination_entity,
                        "type": ForensicEntity.EntityType.UNKNOWN,
                        "relation_type": "CONDUIT_TO"
                        if trail.hop_count > 1
                        else "TRANSFERRED_FUNDS",
                        "weight": float(trail.total_amount),
                        "direction": "out",
                    }
                ]
                for hop in trail.intermediate_hops:
                    hop_name = hop.get("entity") or hop.get("node_name")
                    if hop_name:
                        secondaries.append(
                            {
                                "name": hop_name,
                                "type": ForensicEntity.EntityType.COMPANY,
                                "relation_type": "CONDUIT_TO",
                                "weight": float(hop.get("amount", trail.total_amount)),
                                "direction": "out",
                            }
                        )

                emit_forensic_finding(
                    source_module="q_trail",
                    event_type="FUND_TRAIL_STITCHED",
                    primary_entity_data={
                        "name": trail.source_entity,
                        "type": ForensicEntity.EntityType.UNKNOWN,
                    },
                    secondary_entities_data=secondaries,
                    evidence_data={
                        "source_module": "q_trail",
                        "source_model": "FundTrailPath",
                        "source_record_id": str(trail.id),
                        "evidence_url": "/trail/",
                        "summary_snippet": f"Multi-hop trail ({trail.hop_count} hops) | Total: ₹{trail.total_amount:,.2f} | Circular: {trail.is_circular}",
                        "occurred_at": trail.created_at,
                    },
                    occurred_at=trail.created_at,
                    timeline_title=f"Money Trail ({trail.hop_count} hops, ₹{trail.total_amount:,.2f})",
                    timeline_description=f"Flow from {trail.source_entity} to {trail.destination_entity}",
                    severity="CRITICAL" if trail.is_circular else "WARNING",
                )
                stats["q_trail"] += 1
        except Exception as err:
            logger.warning(f"Error syncing Q-Trail: {err}")

    # 5. Ingest Q-Verify (Document Alterations)
    if apps.is_installed("q_verify"):
        try:
            VerifiedDocument = apps.get_model("q_verify", "VerifiedDocument")

            for vdoc in VerifiedDocument.objects.select_related("case")[:100]:
                custodian = vdoc.case.custodian_name if vdoc.case else "Investigative Subject"
                emit_forensic_finding(
                    source_module="q_verify",
                    event_type="DOCUMENT_ALTERATION_DETECTED",
                    primary_entity_data={
                        "name": vdoc.filename or "Altered Document",
                        "type": ForensicEntity.EntityType.DOCUMENT,
                        "metadata": {
                            "risk_level": vdoc.risk_level,
                            "score": vdoc.authenticity_score,
                        },
                    },
                    secondary_entities_data=[
                        {
                            "name": custodian,
                            "type": ForensicEntity.EntityType.EMPLOYEE,
                            "relation_type": "MENTIONED_IN",
                            "direction": "in",
                        }
                    ],
                    evidence_data={
                        "source_module": "q_verify",
                        "source_model": "VerifiedDocument",
                        "source_record_id": str(vdoc.id),
                        "evidence_url": f"/verify/case/{vdoc.case.id}/"
                        if vdoc.case
                        else "/verify/",
                        "summary_snippet": f"File: {vdoc.filename} | Score: {vdoc.authenticity_score} | Level: {vdoc.risk_level}",
                        "occurred_at": vdoc.created_at,
                    },
                    occurred_at=vdoc.created_at,
                    timeline_title=f"Doc Verification: {vdoc.filename}",
                    timeline_description=f"Authenticity Score: {vdoc.authenticity_score}/100 for custodian {custodian}",
                    severity="CRITICAL"
                    if vdoc.risk_level in ["HIGH_RISK_TAMPERED", "SUSPICIOUS"]
                    else "INFO",
                )
                stats["q_verify"] += 1
        except Exception as err:
            logger.warning(f"Error syncing Q-Verify: {err}")

    logger.info(f"[Q-Link Synchronizer] Completed full sync: {stats}")
    return stats
