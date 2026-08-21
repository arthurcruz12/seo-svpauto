from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Approval UI patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''  } | null>(null);
  const [analysisLevel, setAnalysisLevel] = useState("Elevado");''',
    '''  } | null>(null);
  const [agentApprovalState, setAgentApprovalState] = useState<"idle" | "submitting" | "approved" | "rejected" | "revision" | "error">("idle");
  const [analysisLevel, setAnalysisLevel] = useState("Elevado");''',
    "approval state",
)

text = replace_once(
    text,
    '''      if (routeResponse.ok) {
        setAgentRoute(await routeResponse.json());
      } else {''',
    '''      if (routeResponse.ok) {
        const routedPlan = await routeResponse.json();
        setAgentRoute(routedPlan);
        setAgentApprovalState("idle");
      } else {''',
    "route approval reset",
)

text = replace_once(
    text,
    '''  const startNewConversation = () => {''',
    '''  const submitAgentApproval = async (decision: "approve" | "reject" | "request_change") => {
    if (!agentRoute || !agentRoute.approval_required || agentApprovalState === "submitting") return;
    setAgentApprovalState("submitting");
    try {
      const response = await fetch("/api/agent-approval", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ task_id: agentRoute.task_id, decision }),
      });
      if (!response.ok) throw new Error("Não foi possível registar a decisão.");
      if (decision === "approve") setAgentApprovalState("approved");
      else if (decision === "reject") setAgentApprovalState("rejected");
      else setAgentApprovalState("revision");
    } catch {
      setAgentApprovalState("error");
    }
  };

  const startNewConversation = () => {''',
    "approval function",
)

text = replace_once(
    text,
    '''    setSendError("");
    setWorkSteps([]);''',
    '''    setSendError("");
    setAgentRoute(null);
    setAgentApprovalState("idle");
    setWorkSteps([]);''',
    "approval reset on new conversation",
)

text = replace_once(
    text,
    '''                      {agentRoute.reasons[0] && <p className="mt-2 text-xs leading-5 text-[#a8a29e]">{agentRoute.reasons[0]}</p>}
                    </div>''',
    '''                      {agentRoute.reasons[0] && <p className="mt-2 text-xs leading-5 text-[#a8a29e]">{agentRoute.reasons[0]}</p>}
                      {agentRoute.approval_required && (
                        <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-500/[0.05] p-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-amber-300">Ação proposta · aprovação humana</p>
                          <p className="mt-2 text-xs leading-5 text-[#d6d3d1]">A operação sensível está bloqueada. A sua decisão é registada na auditoria e não executa automaticamente qualquer lançamento.</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <button type="button" disabled={agentApprovalState === "submitting"} onClick={() => void submitAgentApproval("approve")} className="rounded-lg bg-emerald-500/15 px-3 py-2 text-xs font-semibold text-emerald-300 disabled:opacity-50">Aprovar</button>
                            <button type="button" disabled={agentApprovalState === "submitting"} onClick={() => void submitAgentApproval("reject")} className="rounded-lg bg-red-500/15 px-3 py-2 text-xs font-semibold text-red-300 disabled:opacity-50">Rejeitar</button>
                            <button type="button" disabled={agentApprovalState === "submitting"} onClick={() => void submitAgentApproval("request_change")} className="rounded-lg bg-white/[0.06] px-3 py-2 text-xs font-semibold text-[#d6d3d1] disabled:opacity-50">Solicitar alteração</button>
                          </div>
                          {agentApprovalState !== "idle" && (
                            <p className="mt-3 text-xs text-[#a8a29e]">
                              {agentApprovalState === "submitting" ? "A registar decisão…" : agentApprovalState === "approved" ? "Aprovado e registado. Execução automática continua bloqueada." : agentApprovalState === "rejected" ? "Operação rejeitada e registada." : agentApprovalState === "revision" ? "Revisão solicitada e registada." : "Não foi possível registar a decisão."}
                            </p>
                          )}
                        </div>
                      )}
                    </div>''',
    "approval card",
)

path.write_text(text, encoding="utf-8")
print("Added human approval controls; approval never auto-executes")
