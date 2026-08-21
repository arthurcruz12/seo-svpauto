from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Work cloud sync patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

# The task artifact comes from the durable FastAPI backend or from the Preview
# bridge. Keep enough metadata to render it in the existing Nuvem/Ficheiros UI.
text = replace_once(
    text,
    '''  sha256?: string;\n  download_url?: string;\n  inline_base64?: string;\n};''',
    '''  sha256?: string;\n  created_at?: string;\n  download_url?: string;\n  inline_base64?: string;\n};''',
    "assistant artifact creation date",
)

cloud_helpers = r'''
const ASSISTANT_CLOUD_EVENT = "seo:assistant-cloud-artifacts";
const assistantCloudArtifacts = new Map<string, AssistantTaskArtifact>();

function assistantCloudFileId(fileId: string) {
  return `assistant:${fileId}`;
}

function assistantArtifactToCloudFile(artifact: AssistantTaskArtifact): CloudFile {
  return {
    id: assistantCloudFileId(artifact.file_id),
    filename: artifact.filename,
    contentType: artifact.content_type || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    category: "Assistente IA · Trabalho",
    sizeBytes: artifact.size || 0,
    sha256: artifact.sha256 || "",
    uploadedAt: artifact.created_at || new Date().toISOString(),
  };
}

function mergeAssistantCloudFiles(current: CloudFile[], artifacts: AssistantTaskArtifact[]) {
  const valid = artifacts.filter((artifact) => Boolean(artifact?.file_id && artifact?.filename));
  valid.forEach((artifact) => assistantCloudArtifacts.set(assistantCloudFileId(artifact.file_id), artifact));
  const incoming = valid.map(assistantArtifactToCloudFile);
  const incomingIds = new Set(incoming.map((file) => file.id));
  return [...incoming, ...current.filter((file) => !incomingIds.has(file.id))];
}

function emitAssistantCloudArtifacts(artifacts: AssistantTaskArtifact[]) {
  if (!artifacts.length) return;
  artifacts.forEach((artifact) => assistantCloudArtifacts.set(assistantCloudFileId(artifact.file_id), artifact));
  window.dispatchEvent(new CustomEvent<AssistantTaskArtifact[]>(ASSISTANT_CLOUD_EVENT, { detail: artifacts }));
}

'''
text = replace_once(text, "function App() {", cloud_helpers + "function App() {", "cloud helper registration")

text = replace_once(
    text,
    '''  useEffect(() => {\n    configurePersistentAudit(accessToken);\n    return () => configurePersistentAudit("");\n  }, [accessToken]);''',
    '''  useEffect(() => {\n    configurePersistentAudit(accessToken);\n    return () => configurePersistentAudit("");\n  }, [accessToken]);\n\n  useEffect(() => {\n    const handleAssistantCloudArtifacts = (event: Event) => {\n      const artifacts = (event as CustomEvent<AssistantTaskArtifact[]>).detail ?? [];\n      if (artifacts.length) setCloudFiles((current) => mergeAssistantCloudFiles(current, artifacts));\n    };\n    window.addEventListener(ASSISTANT_CLOUD_EVENT, handleAssistantCloudArtifacts);\n    return () => window.removeEventListener(ASSISTANT_CLOUD_EVENT, handleAssistantCloudArtifacts);\n  }, []);''',
    "cloud event listener",
)

text = replace_once(
    text,
    '''  function showToast(message: string) {\n    setToast(message);\n  }''',
    '''  function showToast(message: string) {\n    setToast(message);\n  }\n\n  async function loadAssistantCloudFiles(token: string) {\n    if (!token) return;\n    try {\n      let response = await fetch(`${API_BASE_URL}/api/v1/assistant/tasks?status=COMPLETED&limit=100`, {\n        headers: { Authorization: `Bearer ${token}` },\n      });\n      if (response.status === 404) {\n        response = await fetch("/api/assistant?op=tasks", {\n          headers: { Authorization: `Bearer ${token}` },\n        });\n      }\n      if (!response.ok) return;\n      const payload = await response.json() as { tasks?: AssistantTaskRecord[] };\n      const artifacts = (payload.tasks ?? []).flatMap((task) => task.output_files ?? []);\n      if (artifacts.length) setCloudFiles((current) => mergeAssistantCloudFiles(current, artifacts));\n    } catch {\n      // The legacy cloud remains usable even if the agent task history is unavailable.\n    }\n  }''',
    "assistant cloud history loader",
)

text = replace_once(
    text,
    '''  useEffect(() => {\n    if (activeSection === "nuvem" && accessToken) void refreshCloudState();\n  }, [activeSection, accessToken]);''',
    '''  useEffect(() => {\n    if (activeSection === "nuvem" && accessToken) {\n      void (async () => {\n        await refreshCloudState();\n        await loadAssistantCloudFiles(accessToken);\n      })();\n    }\n  }, [activeSection, accessToken]);''',
    "cloud section assistant history refresh",
)

text = replace_once(
    text,
    '''  async function downloadCloudFile(file: CloudFile) {\n    try {\n      const response = await fetch(`${API_BASE_URL}/cloud/files/${encodeURIComponent(file.id)}/download`, {''',
    '''  async function downloadCloudFile(file: CloudFile) {\n    const assistantArtifact = assistantCloudArtifacts.get(file.id);\n    if (assistantArtifact) {\n      try {\n        let blob: Blob;\n        if (assistantArtifact.inline_base64) {\n          const binary = atob(assistantArtifact.inline_base64);\n          const bytes = new Uint8Array(binary.length);\n          for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);\n          blob = new Blob([bytes], { type: assistantArtifact.content_type || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });\n        } else if (assistantArtifact.download_url) {\n          const url = assistantArtifact.download_url.startsWith("/api/")\n            ? `${API_BASE_URL}${assistantArtifact.download_url}`\n            : assistantArtifact.download_url;\n          const response = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } });\n          if (!response.ok) throw new Error("Não foi possível descarregar o resultado da Assistente IA.");\n          blob = await response.blob();\n        } else {\n          throw new Error("O ficheiro da Assistente IA já não está disponível nesta sessão.");\n        }\n\n        const objectUrl = URL.createObjectURL(blob);\n        const link = document.createElement("a");\n        link.href = objectUrl;\n        link.download = assistantArtifact.filename || file.filename || "resultado.xlsx";\n        document.body.appendChild(link);\n        link.click();\n        link.remove();\n        URL.revokeObjectURL(objectUrl);\n        showToast("Ficheiro da Assistente IA descarregado da Nuvem.");\n      } catch (error) {\n        showToast(error instanceof Error ? error.message : "Não foi possível descarregar o ficheiro da Assistente IA.");\n      }\n      return;\n    }\n\n    try {\n      const response = await fetch(`${API_BASE_URL}/cloud/files/${encodeURIComponent(file.id)}/download`, {''',
    "cloud download route for assistant artifacts",
)

text = replace_once(
    text,
    '''      const payload = await response.json() as { tasks?: AssistantTaskRecord[] };\n      setTasks(payload.tasks ?? []);\n      setWorkError("");''',
    '''      const payload = await response.json() as { tasks?: AssistantTaskRecord[] };\n      const nextTasks = payload.tasks ?? [];\n      setTasks(nextTasks);\n      emitAssistantCloudArtifacts(nextTasks.flatMap((task) => task.output_files ?? []));\n      setWorkError("");''',
    "task history cloud registration",
)

text = replace_once(
    text,
    '''      setResult(payload);\n      if (payload.status === "COMPLETED") setSelectedFile(null);\n      await loadTasks();''',
    '''      setResult(payload);\n      if (payload.status === "COMPLETED") {\n        setSelectedFile(null);\n        emitAssistantCloudArtifacts(payload.artifacts ?? []);\n      }\n      await loadTasks();''',
    "completed work cloud registration",
)

required_markers = [
    'ASSISTANT_CLOUD_EVENT = "seo:assistant-cloud-artifacts"',
    'category: "Assistente IA · Trabalho"',
    'loadAssistantCloudFiles(accessToken)',
    'assistantCloudArtifacts.get(file.id)',
    'emitAssistantCloudArtifacts(payload.artifacts ?? [])',
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Work cloud sync marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Connected Trabalho artifacts to the existing Nuvem/Ficheiros experience")
