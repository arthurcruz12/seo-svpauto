from __future__ import annotations

from app.agents.audit_agent import AuditAgent
from app.agents.billing_agent import BillingAgent
from app.agents.document_agent import DocumentAgent

AGENT_REGISTRY = {
    "billing": BillingAgent,
    "document": DocumentAgent,
    "audit": AuditAgent,
}


def get_agent(agent_id: str):
    agent_class = AGENT_REGISTRY.get(agent_id)
    if agent_class is None:
        raise KeyError(f"Unknown agent: {agent_id}")
    return agent_class()
