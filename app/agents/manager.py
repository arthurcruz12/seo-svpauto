from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from app.agents.audit_agent import AuditAgent
from app.agents.billing_agent import BillingAgent
from app.agents.document_agent import DocumentAgent


class AgentManager:
    """Execute business tasks; routing alone is never considered completion."""

    def __init__(self) -> None:
        self.document_agent = DocumentAgent()
        self.billing_agent = BillingAgent()
        self.audit_agent = AuditAgent()

    def execute_billing(self, content: bytes, filename: str) -> dict:
        task_id = str(uuid4())
        document_result = self.document_agent.execute(content, filename)
        billing_result = self.billing_agent.execute(document_result)
        audit_result = self.audit_agent.execute(document_result["records"], billing_result["content"])

        status = "COMPLETED" if audit_result["valid"] else "FAILED"
        return {
            "task_id": task_id,
            "status": status,
            "agents_used": ["DocumentAgent", "BillingAgent", "AuditAgent"],
            "source_sha256": sha256(content).hexdigest(),
            "output_sha256": sha256(billing_result["content"]).hexdigest(),
            "source_filename": filename,
            "output_filename": self._output_filename(filename),
            "output_content": billing_result["content"],
            "audit": audit_result,
            "records_processed": len(document_result["records"]),
            "records_rejected": len(document_result["rejected"]),
            "rejected": document_result["rejected"],
            "approval_required": False,
            "confidence": 1.0 if audit_result["valid"] else 0.0,
            "errors": audit_result["errors"],
        }

    @staticmethod
    def _output_filename(filename: str) -> str:
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        return f"{stem} - Separada, Resumo e Mapa Diário.xlsx"
