from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Work execution UI patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

execution_type = '''type AssistantAgentExecution = {
  execution_id?: string;
  agent_name: string;
  status: string;
  started_at?: string;
  finished_at?: string;
  input_summary?: string | null;
  output_summary?: string | null;
  confidence?: number;
  error_message?: string | null;
};

'''
text = replace_once(
    text,
    "type AssistantTaskRecord = {",
    execution_type + "type AssistantTaskRecord = {",
    "execution type",
)
text = replace_once(
    text,
    "  records_rejected?: number;\n};\n\ntype AssistantExecutionResult = {",
    "  records_rejected?: number;\n  executions?: AssistantAgentExecution[];\n};\n\ntype AssistantExecutionResult = {",
    "task execution field",
)
text = replace_once(
    text,
    "  confidence?: number;\n  errors?: string[];\n};\n\nfunction AssistantWorkPanel",
    "  confidence?: number;\n  errors?: string[];\n  executions?: AssistantAgentExecution[];\n};\n\nfunction AssistantWorkPanel",
    "result execution field",
)

result_agents = '''                {result.agents_used && result.agents_used.length > 0 && <div className="rounded-2xl border border-white/10 bg-black/15 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Agentes utilizados</p><p className="mt-2 text-sm text-[#d6d3d1]">{result.agents_used.join(" → ")}</p></div>}
'''
result_agents_new = result_agents + '''
                {result.executions && result.executions.length > 0 && (
                  <div className="rounded-2xl border border-white/10 bg-black/15 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Execução por agente</p>
                    <div className="mt-3 space-y-2">
                      {result.executions.map((execution) => (
                        <div key={`${execution.agent_name}-${execution.started_at ?? ""}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 px-3 py-2">
                          <div><p className="text-sm font-medium text-white">{execution.agent_name}</p>{execution.output_summary && <p className="mt-1 text-[11px] text-[#78716c]">{execution.output_summary}</p>}</div>
                          <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold ${statusTone(execution.status)}`}>{execution.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
'''
text = replace_once(text, result_agents, result_agents_new, "result execution states")

history_error = '''                  {task.errors && task.errors.length > 0 && <p className="mt-3 text-xs leading-5 text-red-200">{task.errors.join(" · ")}</p>}
'''
history_new = '''                  {task.executions && task.executions.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {task.executions.map((execution) => <span key={execution.execution_id ?? `${task.task_id}-${execution.agent_name}`} className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold ${statusTone(execution.status)}`}>{execution.agent_name}: {execution.status}</span>)}
                    </div>
                  )}
''' + history_error
text = replace_once(text, history_error, history_new, "history execution states")

for marker in ("AssistantAgentExecution", "Execução por agente", "execution.agent_name", "task.executions"):
    if marker not in text:
        raise SystemExit(f"Work execution UI marker missing: {marker}")

path.write_text(text, encoding="utf-8")
print("Added per-agent execution states to Assistente IA > Trabalho")
