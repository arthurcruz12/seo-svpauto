from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Work Preview bridge patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''  download_url?: string;
};''',
    '''  download_url?: string;
  inline_base64?: string;
};''',
    "inline preview artifact type",
)

text = replace_once(
    text,
    '''  confidence?: number;
  errors?: string[];
  executions?: AssistantAgentExecution[];
};''',
    '''  confidence?: number;
  errors?: string[];
  executions?: AssistantAgentExecution[];
  preview_bridge?: boolean;
  persistence?: string;
};''',
    "preview execution metadata type",
)

text = replace_once(
    text,
    '''      const response = await fetch(`${API_BASE_URL}/api/v1/assistant/tasks`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) {''',
    '''      let response = await fetch(`${API_BASE_URL}/api/v1/assistant/tasks`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (response.status === 404) {
        response = await fetch("/api/assistant?op=tasks", {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
      }
      if (!response.ok) {''',
    "tasks preview fallback",
)

text = replace_once(
    text,
    '''  const downloadArtifact = async (artifact: AssistantTaskArtifact) => {
    if (!artifact.download_url) return;
    setWorkError("");
    try {''',
    '''  const downloadArtifact = async (artifact: AssistantTaskArtifact) => {
    setWorkError("");
    if (artifact.inline_base64) {
      try {
        const binary = atob(artifact.inline_base64);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
        const blob = new Blob([bytes], { type: artifact.content_type || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = artifact.filename || "resultado.xlsx";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
        return;
      } catch (error) {
        setWorkError(error instanceof Error ? error.message : "Falha ao preparar o ficheiro do Preview.");
        return;
      }
    }
    if (!artifact.download_url) return;
    try {''',
    "inline preview artifact download",
)

text = replace_once(
    text,
    '''      const response = await fetch(`${API_BASE_URL}/api/v1/assistant/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: form,
      });
      const payload = await response.json().catch(() => null) as AssistantExecutionResult | null;''',
    '''      let response = await fetch(`${API_BASE_URL}/api/v1/assistant/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: form,
      });
      if (response.status === 404) {
        response = await fetch("/api/assistant?op=execute", {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: form,
        });
      }
      const payload = await response.json().catch(() => null) as AssistantExecutionResult | null;''',
    "execution preview fallback",
)

text = replace_once(
    text,
    '''                {result.agents_used && result.agents_used.length > 0 && <div className="rounded-2xl border border-white/10 bg-black/15 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Agentes utilizados</p><p className="mt-2 text-sm text-[#d6d3d1]">{result.agents_used.join(" → ")}</p></div>}''',
    '''                {result.preview_bridge && <div className="rounded-2xl border border-blue-400/20 bg-blue-500/[0.06] p-4 text-xs leading-5 text-blue-100"><strong className="text-blue-200">Preview seguro:</strong> a cadeia real de agentes foi executada na branch, sem alterar Production. O histórico deste fallback é temporário; a persistência durável continua reservada ao backend FastAPI.</div>}

                {result.agents_used && result.agents_used.length > 0 && <div className="rounded-2xl border border-white/10 bg-black/15 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Agentes utilizados</p><p className="mt-2 text-sm text-[#d6d3d1]">{result.agents_used.join(" → ")}</p></div>}''',
    "preview bridge notice",
)

required_markers = [
    'fetch("/api/assistant?op=tasks"',
    'fetch("/api/assistant?op=execute"',
    'inline_base64?: string;',
    'executions?: AssistantAgentExecution[];',
    'Preview seguro:',
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Work Preview bridge marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Connected Trabalho to preview-only executable bridge fallback")
