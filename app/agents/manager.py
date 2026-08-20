from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from app.agents.audit_agent import AuditAgent
from app.agents.billing_agent import BillingAgent
from app.agents.document_agent import DocumentAgent


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentManager:
    """Execute business tasks; routing alone is never considered completion."""

    def __init__(self) -> None:
        self.document_agent = DocumentAgent()
        self.billing_agent = BillingAgent()
        self.audit_agent = AuditAgent()

    def execute_billing(self, content: bytes, filename: str, task_id: str | None = None) -> dict:
        task_id = task_id or str(uuid4())
        executions: list[dict] = []

        document_started = _now()
        document_result = self.document_agent.execute(content, filename)
        executions.append(
            {
                "agent_name": "DocumentAgent",
                "status": "COMPLETED",
                "started_at": document_started,
                "finished_at": _now(),
                "input_summary": f"source={filename}; bytes={len(content)}",
                "output_summary": f"records={len(document_result['records'])}; rejected={len(document_result['rejected'])}",
                "confidence": 1.0,
                "error_message": None,
            }
        )

        billing_started = _now()
        billing_result = self.billing_agent.execute(document_result)
        executions.append(
            {
                "agent_name": "BillingAgent",
                "status": "COMPLETED",
                "started_at": billing_started,
                "finished_at": _now(),
                "input_summary": f"records={len(document_result['records'])}",
                "output_summary": f"workbook_bytes={len(billing_result['content'])}; sheets=3",
                "confidence": 1.0,
                "error_message": None,
            }
        )

        audit_started = _now()
        audit_result = self.audit_agent.execute(document_result["records"], billing_result["content"])
        audit_status = "COMPLETED" if audit_result["valid"] else "FAILED"
        executions.append(
            {
                "agent_name": "AuditAgent",
                "status": audit_status,
                "started_at": audit_started,
                "finished_at": _now(),
                "input_summary": f"records={len(document_result['records'])}; workbook_bytes={len(billing_result['content'])}",
                "output_summary": f"valid={audit_result['valid']}; checks={len(audit_result.get('checks', {}))}",
                "confidence": 1.0 if audit_result["valid"] else 0.0,
                "error_message": "; ".join(audit_result["errors"])[:1000] if audit_result["errors"] else None,
            }
        )

        status = "COMPLETED" if audit_result["valid"] else "FAILED"
        return {
            "task_id": task_id,
            "status": status,
            "agents_used": ["DocumentAgent", "BillingAgent", "AuditAgent"],
            "executions": executions,
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
