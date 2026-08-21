from app.agents.audit_agent import AuditAgent
from app.agents.billing_agent import BillingAgent
from app.billing_style import install_billing_styles

# Keep calculation logic in BillingAgent unchanged and apply only the approved
# SVP Auto presentation layer to every execution path (backend and Preview).
install_billing_styles(BillingAgent)

from app.agents.document_agent import BillingRecord, DocumentAgent
from app.agents.manager import AgentManager

__all__ = ["AgentManager", "AuditAgent", "BillingAgent", "BillingRecord", "DocumentAgent"]
