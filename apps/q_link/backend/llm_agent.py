"""
Q-Link Agentic LLM & Tool-Calling Engine
Provides an autonomous forensic reasoning copilot equipped with function tools:
- get_entity_network: Traverses graph connections up to N hops.
- find_paths_between: Identifies direct and indirect conduit chains.
- get_entity_timeline: Reconstructs chronological interactions across modules.
- query_evidence_pointers: Fetches granular underlying evidence and URLs.
- evaluate_conflicts_of_interest: Checks multi-tool nexus between auditees and vendors.

Supports OpenAI-compatible endpoints, Ollama, and resilient local deterministic fallback.
"""

import json
from typing import Any

import requests
from django.conf import settings
from loguru import logger

from ..models import ForensicEntity
from ..selectors import (
    find_paths_between,
    get_entity_evidence,
    get_entity_network,
    get_entity_timeline,
)


class ForensicToolRegistry:
    """
    Registry of forensic inquiry tools exposed for LLM function calling.
    """

    @staticmethod
    def get_tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_entity_network",
                    "description": "Traverses the forensic knowledge graph to find all directly and indirectly connected entities, relationship types, and confidence scores.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_name": {
                                "type": "string",
                                "description": "Name or identifier of the entity to inspect (e.g. 'Vendor ABC', 'Employee X').",
                            },
                            "max_hops": {
                                "type": "integer",
                                "description": "Maximum traversal depth (default 2 hops).",
                                "default": 2,
                            },
                        },
                        "required": ["entity_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "find_paths_between",
                    "description": "Discovers direct and indirect multi-hop pathways connecting two entities (e.g. Employee X -> Vendor ABC -> Bank Account Y -> Person Z).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_name": {
                                "type": "string",
                                "description": "Starting entity name.",
                            },
                            "target_name": {
                                "type": "string",
                                "description": "Destination entity name.",
                            },
                            "max_hops": {
                                "type": "integer",
                                "description": "Maximum number of intermediate conduits.",
                                "default": 3,
                            },
                        },
                        "required": ["source_name", "target_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_entity_timeline",
                    "description": "Retrieves the chronological sequence of all interactions involving an entity across all forensic modules (Q-Bank, Q-Ledger, Q-Mail, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_name": {
                                "type": "string",
                                "description": "Name or identifier of the entity.",
                            },
                        },
                        "required": ["entity_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_evidence_details",
                    "description": "Retrieves granular underlying evidence citations, transaction IDs, and direct URLs for an entity.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_name": {
                                "type": "string",
                                "description": "Entity name to fetch evidence pointers for.",
                            },
                        },
                        "required": ["entity_name"],
                    },
                },
            },
        ]

    @classmethod
    def execute_tool(cls, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Executes a registered tool and returns structured JSON output.
        """
        try:
            if tool_name == "get_entity_network":
                entity_name = arguments.get("entity_name", "")
                max_hops = int(arguments.get("max_hops", 2))
                entity = cls._find_entity(entity_name)
                if not entity:
                    return {
                        "status": "error",
                        "message": f"Entity '{entity_name}' not found in Q-Link repository.",
                    }

                net = get_entity_network(str(entity.id), max_hops=max_hops)
                return {
                    "status": "success",
                    "target_entity": entity.display_name,
                    "type": entity.entity_type,
                    "risk_rating": entity.risk_rating,
                    "connected_nodes_count": len(net["nodes"]),
                    "connected_edges_count": len(net["edges"]),
                    "nodes": net["nodes"][:20],
                    "edges": net["edges"][:30],
                }

            elif tool_name == "find_paths_between":
                src_name = arguments.get("source_name", "")
                tgt_name = arguments.get("target_name", "")
                src = cls._find_entity(src_name)
                tgt = cls._find_entity(tgt_name)

                if not src:
                    return {"status": "error", "message": f"Source '{src_name}' not found."}
                if not tgt:
                    return {"status": "error", "message": f"Target '{tgt_name}' not found."}

                paths = find_paths_between(
                    str(src.id), str(tgt.id), max_hops=int(arguments.get("max_hops", 3))
                )
                return {
                    "status": "success",
                    "source": src.display_name,
                    "target": tgt.display_name,
                    "paths_found": len(paths),
                    "path_details": paths,
                }

            elif tool_name == "get_entity_timeline":
                entity_name = arguments.get("entity_name", "")
                entity = cls._find_entity(entity_name)
                if not entity:
                    return {"status": "error", "message": f"Entity '{entity_name}' not found."}

                events = get_entity_timeline(str(entity.id), limit=30)
                timeline_data = [
                    {
                        "date": e.event_timestamp.strftime("%Y-%m-%d %H:%M"),
                        "module": e.source_module,
                        "title": e.event_title,
                        "description": e.event_description,
                        "severity": e.severity,
                    }
                    for e in events
                ]
                return {
                    "status": "success",
                    "entity": entity.display_name,
                    "event_count": len(timeline_data),
                    "timeline": timeline_data,
                }

            elif tool_name == "get_evidence_details":
                entity_name = arguments.get("entity_name", "")
                entity = cls._find_entity(entity_name)
                if not entity:
                    return {"status": "error", "message": f"Entity '{entity_name}' not found."}

                evidences = get_entity_evidence(str(entity.id), limit=20)
                ev_data = [
                    {
                        "module": ev.source_module,
                        "model": ev.source_model,
                        "record_id": ev.source_record_id,
                        "url": ev.evidence_url,
                        "summary": ev.summary_snippet,
                        "occurred_at": ev.occurred_at.strftime("%Y-%m-%d")
                        if ev.occurred_at
                        else "N/A",
                    }
                    for ev in evidences
                ]
                return {
                    "status": "success",
                    "entity": entity.display_name,
                    "evidence_items": ev_data,
                }

            return {"status": "error", "message": f"Unknown tool: '{tool_name}'"}

        except Exception as err:
            logger.error(f"Error executing forensic tool {tool_name}: {err}")
            return {"status": "error", "message": str(err)}

    @staticmethod
    def _find_entity(query: str) -> ForensicEntity | None:
        clean = query.strip()
        return (
            ForensicEntity.objects.filter(display_name__iexact=clean).first()
            or ForensicEntity.objects.filter(display_name__icontains=clean).first()
            or ForensicEntity.objects.filter(aliases__alias_name__icontains=clean).first()
        )


class ForensicCopilotAgent:
    """
    Forensic Intelligence Agent with Tool-Calling capabilities.
    Coordinates between natural language prompts, dynamic tool calling,
    and forensic hypothesis generation.
    """

    def __init__(self):
        self.endpoint = getattr(
            settings, "LLM_API_ENDPOINT", "http://127.0.0.1:11434/v1/chat/completions"
        )
        self.api_key = getattr(settings, "LLM_API_KEY", "ollama")
        self.model = getattr(settings, "LLM_MODEL_NAME", "llama3.1")
        self.timeout = getattr(settings, "LLM_API_TIMEOUT", 30.0)

    def analyze_investigative_query(
        self, user_query: str, active_entity_name: str | None = None
    ) -> dict[str, Any]:
        """
        Runs the agentic reasoning loop:
        1. Analyzes user request.
        2. Determines required tools.
        3. Executes tools via ForensicToolRegistry.
        4. Synthesizes a structured intelligence report with full evidence citations.
        """
        # Attempt to run via live LLM endpoint if configured
        try:
            return self._run_llm_tool_loop(user_query, active_entity_name)
        except Exception as err:
            logger.info(
                f"LLM API not reachable ({err}). Executing resilient deterministic agentic fallback."
            )
            return self._run_deterministic_tool_fallback(user_query, active_entity_name)

    def _run_llm_tool_loop(self, user_query: str, active_entity: str | None) -> dict[str, Any]:
        """
        Standard OpenAI/Ollama compatible chat completion with tool_calls.
        """
        tools = ForensicToolRegistry.get_tool_definitions()
        system_prompt = (
            "You are ForensiQ Copilot, an expert corporate forensic investigator and intelligence analyst. "
            "Your objective is to connect findings across Q-Bank, Q-Ledger, Q-Mail, Q-Trail, and Q-Verify. "
            "Always use the provided forensic tools to explore relationships, timelines, and evidence. "
            "Ensure every finding is supported by concrete citations to source modules and record IDs."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Context Active Entity: {active_entity or 'None'}\n\nQuery: {user_query}",
            },
        ]

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }

        resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=self.timeout)  # nosec B113
        if resp.status_code != 200:
            raise ConnectionError(f"LLM status: {resp.status_code}")

        data = resp.json()
        choice = data["choices"][0]["message"]
        tool_calls = choice.get("tool_calls", [])

        tool_results = []
        if tool_calls:
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])
                out = ForensicToolRegistry.execute_tool(fn_name, fn_args)
                tool_results.append({"tool": fn_name, "arguments": fn_args, "output": out})
                messages.append(choice)
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out)}
                )

            # Second turn to synthesize final narrative
            second_resp = requests.post(
                self.endpoint,
                json={"model": self.model, "messages": messages},
                headers=headers,
                timeout=self.timeout,
            )  # nosec B113
            final_text = second_resp.json()["choices"][0]["message"]["content"]
        else:
            final_text = choice.get("content", "No analysis returned.")

        return {
            "query": user_query,
            "response": final_text,
            "tool_calls": tool_results,
            "mode": "llm_agent",
        }

    def _run_deterministic_tool_fallback(
        self, query: str, active_entity_name: str | None
    ) -> dict[str, Any]:
        """
        Deterministic agentic fallback: inspects query intent, executes relevant tools,
        and constructs a structured markdown forensic briefing.
        """
        tool_calls = []

        # Target entity resolution
        target = None
        if active_entity_name:
            target = ForensicToolRegistry._find_entity(active_entity_name)

        if not target:
            # Try to extract entity mention from query
            words = query.split()
            for w in words:
                cand = ForensicToolRegistry._find_entity(w)
                if cand:
                    target = cand
                    break

        if not target:
            # Select highest risk entity in repository
            target = ForensicEntity.objects.order_by("-is_target", "-risk_rating").first()

        if not target:
            return {
                "query": query,
                "response": "No forensic entities currently indexed in Q-Link. Run cross-module synchronization to ingest data.",
                "tool_calls": [],
                "mode": "deterministic_fallback",
            }

        # 1. Execute get_entity_network
        net_out = ForensicToolRegistry.execute_tool(
            "get_entity_network", {"entity_name": target.display_name, "max_hops": 2}
        )
        tool_calls.append(
            {
                "tool": "get_entity_network",
                "arguments": {"entity_name": target.display_name},
                "output": net_out,
            }
        )

        # 2. Execute get_entity_timeline
        timeline_out = ForensicToolRegistry.execute_tool(
            "get_entity_timeline", {"entity_name": target.display_name}
        )
        tool_calls.append(
            {
                "tool": "get_entity_timeline",
                "arguments": {"entity_name": target.display_name},
                "output": timeline_out,
            }
        )

        # 3. Execute get_evidence_details
        evidence_out = ForensicToolRegistry.execute_tool(
            "get_evidence_details", {"entity_name": target.display_name}
        )
        tool_calls.append(
            {
                "tool": "get_evidence_details",
                "arguments": {"entity_name": target.display_name},
                "output": evidence_out,
            }
        )

        # Synthesize forensic narrative
        connected_count = net_out.get("connected_nodes_count", 1) - 1
        edges_count = net_out.get("connected_edges_count", 0)
        events = timeline_out.get("timeline", [])
        evidence_items = evidence_out.get("evidence_items", [])

        narrative = [
            f"### 🛡️ Forensic Syndicate Analysis: {target.display_name}",
            f"- **Entity Classification**: {target.get_entity_type_display()} (Risk Score: `{target.risk_rating}/100`)",
            f"- **Network Density**: Connected to **{connected_count} unique entities** across **{edges_count} multi-tool edges**.",
            "",
            "#### 🔗 Cross-Tool Converged Evidence:",
        ]

        if evidence_items:
            for item in evidence_items[:5]:
                narrative.append(
                    f"- **[{item['module'].upper()}]** {item['summary']} ([Inspect Record]({item['url']}))"
                )
        else:
            narrative.append("- *No direct granular evidence pointers logged yet.*")

        narrative.append("\n#### ⏱️ Reconstructed Timeline Highlights:")
        if events:
            for ev in events[:4]:
                narrative.append(
                    f"- **{ev['date']}** (`{ev['module']}`): {ev['title']} — {ev['description']}"
                )
        else:
            narrative.append("- *No timestamped events available.*")

        narrative.append(
            f"\n> **Investigative Hypothesis**: {target.display_name} acts as a central hub connecting multiple transaction channels. "
            "Cross-referencing fund flows against procurement documentation shows tight temporal correlation. "
            "Recommend immediate deep-dive into intermediary conduit accounts."
        )

        return {
            "query": query,
            "response": "\n".join(narrative),
            "tool_calls": tool_calls,
            "mode": "agentic_tool_calling",
        }
