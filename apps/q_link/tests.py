"""
Q-Link Comprehensive Test Suite
Validates entity resolution, RapidFuzz fuzzy alias matching,
event ingestion, graph pathfinding, risk alerts, LLM tool execution, and REST APIs.
"""

import json

from django.test import Client, TestCase
from django.utils import timezone

from .backend.dispatcher import emit_forensic_finding
from .backend.llm_agent import ForensicCopilotAgent, ForensicToolRegistry
from .models import (
    EntityAlias,
    EvidencePointer,
    ForensicEntity,
    ForensicTimelineEvent,
    RelationshipAlert,
)
from .selectors import (
    find_paths_between,
)
from .services import (
    clean_entity_name,
    create_or_update_relationship,
    evaluate_relationship_risks,
    normalize_identifier,
    record_timeline_event,
    resolve_or_create_entity,
)


class QLinkEntityResolutionTests(TestCase):
    """Tests normalization and fuzzy alias resolution."""

    def test_clean_entity_name(self):
        self.assertEqual(clean_entity_name("ABC Enterprises Pvt Ltd"), "ABC")
        self.assertEqual(clean_entity_name("Global Logistics Solutions LLP"), "GLOBAL LOGISTICS")

    def test_normalize_identifier(self):
        self.assertEqual(
            normalize_identifier("user@example.com", "EMAIL_ID"), "EMAIL:user@example.com"
        )
        self.assertEqual(normalize_identifier("HDFC-123-456", "BANK_ACCOUNT"), "ACC:HDFC123456")

    def test_fuzzy_alias_matching(self):
        # 1. Create canonical vendor
        v1, created1 = resolve_or_create_entity(
            "ABC Enterprises Pvt Ltd", ForensicEntity.EntityType.VENDOR
        )
        self.assertTrue(created1)

        # 2. Ingest variant spelling
        v2, created2 = resolve_or_create_entity(
            "A.B.C. Enterprises", ForensicEntity.EntityType.VENDOR
        )
        self.assertFalse(created2)
        self.assertEqual(v1.id, v2.id)

        # Check alias recorded
        self.assertTrue(
            EntityAlias.objects.filter(entity=v1, alias_name="A.B.C. Enterprises").exists()
        )


class QLinkGraphAndEventDispatcherTests(TestCase):
    """Tests decoupled event ingestion and graph traversal."""

    def setUp(self):
        self.emp, _ = resolve_or_create_entity(
            "Target Custodian A",
            ForensicEntity.EntityType.EMPLOYEE,
            is_target=True,
        )
        self.vendor, _ = resolve_or_create_entity(
            "Apex Global Supplies",
            ForensicEntity.EntityType.VENDOR,
        )

    def test_emit_forensic_finding(self):
        primary, rels = emit_forensic_finding(
            source_module="q_bank",
            event_type="BANK_TRANSFER",
            primary_entity_data={
                "name": "Target Custodian A",
                "type": ForensicEntity.EntityType.EMPLOYEE,
            },
            secondary_entities_data=[
                {
                    "name": "Apex Global Supplies",
                    "type": ForensicEntity.EntityType.VENDOR,
                    "relation_type": "TRANSFERRED_FUNDS",
                    "weight": 500000.0,
                }
            ],
            evidence_data={
                "source_module": "q_bank",
                "source_model": "BankTransaction",
                "source_record_id": "TXN-999",
                "evidence_url": "/bank/account/1/",
                "summary_snippet": "Transfer ₹5,00,000",
            },
            timeline_title="Bank Transfer ₹5,00,000",
            severity="WARNING",
        )

        self.assertEqual(primary.id, self.emp.id)
        self.assertEqual(len(rels), 1)
        self.assertTrue(EvidencePointer.objects.filter(source_record_id="TXN-999").exists())
        self.assertTrue(ForensicTimelineEvent.objects.filter(entity=self.emp).exists())

    def test_multi_hop_pathfinding(self):
        # Create chain: Emp -> Vendor -> Conduit Co -> Target Z
        conduit, _ = resolve_or_create_entity(
            "Conduit Shell Ltd", ForensicEntity.EntityType.COMPANY
        )
        final_dest, _ = resolve_or_create_entity(
            "Offshore Corp Z", ForensicEntity.EntityType.COMPANY
        )

        create_or_update_relationship(self.emp, self.vendor, "ISSUED_PO", source_module="q_ledger")
        create_or_update_relationship(
            self.vendor, conduit, "TRANSFERRED_FUNDS", source_module="q_bank"
        )
        create_or_update_relationship(conduit, final_dest, "CONDUIT_TO", source_module="q_trail")

        paths = find_paths_between(str(self.emp.id), str(final_dest.id), max_hops=4)
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(paths[0]), 3)

    def test_automated_risk_alert(self):
        # Linking across 3 modules triggers Multi-Tool Correlation Alert
        e2, _ = resolve_or_create_entity("Partner B", ForensicEntity.EntityType.COMPANY)
        e3, _ = resolve_or_create_entity("Partner C", ForensicEntity.EntityType.COMPANY)
        e4, _ = resolve_or_create_entity("Partner D", ForensicEntity.EntityType.COMPANY)

        create_or_update_relationship(self.emp, e2, "EMAILED", source_module="q_mail")
        create_or_update_relationship(self.emp, e3, "ISSUED_PO", source_module="q_ledger")
        create_or_update_relationship(self.emp, e4, "TRANSFERRED_FUNDS", source_module="q_bank")

        evaluate_relationship_risks(self.emp)
        self.assertTrue(RelationshipAlert.objects.filter(primary_entity=self.emp).exists())


class QLinkAgentToolCallingTests(TestCase):
    """Tests the LLM tool calling registry and execution."""

    def setUp(self):
        self.emp, _ = resolve_or_create_entity(
            "Arun Kumar", ForensicEntity.EntityType.EMPLOYEE, is_target=True
        )
        self.vendor, _ = resolve_or_create_entity("Alpha Traders", ForensicEntity.EntityType.VENDOR)
        create_or_update_relationship(
            self.emp, self.vendor, "TRANSFERRED_FUNDS", weight=100000.0, source_module="q_bank"
        )
        record_timeline_event(
            self.emp, "Fund Transfer", "Transferred ₹1,00,000", timezone.now(), "q_bank"
        )

    def test_tool_definitions(self):
        defs = ForensicToolRegistry.get_tool_definitions()
        self.assertGreaterEqual(len(defs), 4)

    def test_tool_execution(self):
        res = ForensicToolRegistry.execute_tool(
            "get_entity_network", {"entity_name": "Arun Kumar", "max_hops": 2}
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["target_entity"], "Arun Kumar")
        self.assertEqual(res["connected_nodes_count"], 2)

    def test_copilot_agent_fallback(self):
        agent = ForensicCopilotAgent()
        out = agent.analyze_investigative_query("Investigate Arun Kumar")
        self.assertEqual(
            out["status"] if "status" in out else "agentic_tool_calling", out.get("mode")
        )
        self.assertIn("Arun Kumar", out["response"])
        self.assertGreaterEqual(len(out["tool_calls"]), 2)


class QLinkAPITests(TestCase):
    """Tests Q-Link view endpoints."""

    def setUp(self):
        self.client = Client()
        # Set session master portal auth
        session = self.client.session
        session["portal_authenticated"] = True
        session.save()

        self.emp, _ = resolve_or_create_entity(
            "Investigative Subject", ForensicEntity.EntityType.EMPLOYEE, is_target=True
        )

    def test_dashboard_view(self):
        resp = self.client.get("/link/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Q-Link")

    def test_api_network(self):
        resp = self.client.get("/link/api/network/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("nodes", data)

    def test_api_entity_detail(self):
        resp = self.client.get(f"/link/api/entity/{self.emp.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["entity"]["name"], "Investigative Subject")

    def test_api_copilot_chat(self):
        resp = self.client.post(
            "/link/api/copilot/",
            data=json.dumps({"query": "Investigate Subject"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("response", data)
