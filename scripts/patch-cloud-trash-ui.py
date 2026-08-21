from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Cloud trash UI patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''  Sparkles,
  Target,
  Upload,''',
    '''  Sparkles,
  RotateCcw,
  Target,
  Trash2,
  Upload,
  XCircle,''',
    "trash icons",
)

trash_type = r'''
type TrashCloudFile = CloudFile & {
  deletedAt?: string | null;
  deletedBy?: string | null;
  referenceDate?: string | null;
  taskId?: string | null;
  origin?: string | null;
  parentFileId?: string | null;
};

'''
text = replace_once(text, "function App() {", trash_type + "function App() {", "trash cloud type")

text = replace_once(
    text,
    '''  const [cloudFiles, setCloudFiles] = useState<CloudFile[]>([]);
  const [toast, setToast] = useState("Protótipo pronto para demonstração.");''',
    '''  const [cloudFiles, setCloudFiles] = useState<CloudFile[]>([]);
  const [trashFiles, setTrashFiles] = useState<TrashCloudFile[]>([]);
  const [trashAvailable, setTrashAvailable] = useState(true);
  const [toast, setToast] = useState("Protótipo pronto para demonstração.");''',
    "trash state",
)

trash_actions = r'''
  async function refreshTrashState() {
    if (!accessToken) return;
    try {
      const response = await fetch(`${API_BASE_URL}/cloud/trash?limit=250`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (response.status === 404) {
        setTrashAvailable(false);
        setTrashFiles([]);
        return;
      }
      if (!response.ok) throw new Error("Não foi possível atualizar a Lixeira.");
      const payload = await response.json() as TrashCloudFile[];
      setTrashAvailable(true);
      setTrashFiles(payload);
    } catch (error) {
      setTrashAvailable(false);
      showToast(error instanceof Error ? error.message : "Não foi possível atualizar a Lixeira.");
    }
  }

  async function moveCloudFileToTrash(file: CloudFile) {
    if (file.id.startsWith("assistant:")) {
      showToast("Este ficheiro do Preview ainda não está persistido no backend. A Lixeira fica disponível após a sincronização durável.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/cloud/files/${encodeURIComponent(file.id)}/trash`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const payload = await response.json().catch(() => null) as TrashCloudFile | { detail?: string } | null;
      if (response.status === 404) {
        setTrashAvailable(false);
        throw new Error("A Lixeira está preparada, mas requer a atualização do backend no Oracle.");
      }
      if (!response.ok) {
        const detail = payload && "detail" in payload ? payload.detail : undefined;
        throw new Error(detail || "Não foi possível mover o ficheiro para a Lixeira.");
      }
      setCloudFiles((current) => current.filter((item) => item.id !== file.id));
      await refreshTrashState();
      auditAction("CLOUD_FILE_TRASHED", `${file.filename} movido para a Lixeira.`);
      showToast(`${file.filename} movido para a Lixeira.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível mover o ficheiro para a Lixeira.");
    }
  }

  async function restoreCloudFileFromTrash(file: TrashCloudFile) {
    try {
      const response = await fetch(`${API_BASE_URL}/cloud/trash/${encodeURIComponent(file.id)}/restore`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const payload = await response.json().catch(() => null) as TrashCloudFile | { detail?: string } | null;
      if (!response.ok) {
        const detail = payload && "detail" in payload ? payload.detail : undefined;
        throw new Error(detail || "Não foi possível restaurar o ficheiro.");
      }
      const restored = payload as TrashCloudFile;
      if (restored.taskId) {
        assistantWorkTraceability.set(restored.id, {
          id: restored.id,
          filename: restored.filename,
          contentType: restored.contentType,
          category: restored.category,
          sizeBytes: restored.sizeBytes,
          sha256: restored.sha256,
          uploadedAt: restored.uploadedAt,
          referenceDate: restored.referenceDate,
          taskId: restored.taskId,
          origin: restored.origin,
          parentFileId: restored.parentFileId,
        });
      }
      setCloudFiles((current) => [restored, ...current.filter((item) => item.id !== restored.id)]);
      setTrashFiles((current) => current.filter((item) => item.id !== restored.id));
      auditAction("CLOUD_FILE_RESTORED", `${restored.filename} restaurado da Lixeira.`);
      showToast(`${restored.filename} restaurado da Lixeira.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível restaurar o ficheiro.");
    }
  }

  async function permanentlyDeleteCloudFile(file: TrashCloudFile) {
    const confirmed = window.confirm(`Eliminar definitivamente “${file.filename}”? Esta ação não pode ser desfeita.`);
    if (!confirmed) return;
    try {
      const response = await fetch(`${API_BASE_URL}/cloud/trash/${encodeURIComponent(file.id)}/delete`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const payload = await response.json().catch(() => null) as { detail?: string } | null;
      if (!response.ok) throw new Error(payload?.detail || "Não foi possível eliminar definitivamente o ficheiro.");
      setTrashFiles((current) => current.filter((item) => item.id !== file.id));
      assistantWorkTraceability.delete(file.id);
      auditAction("CLOUD_FILE_PERMANENTLY_DELETED", `${file.filename} eliminado definitivamente da Lixeira.`);
      showToast(`${file.filename} eliminado definitivamente.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível eliminar definitivamente o ficheiro.");
    }
  }

'''
text = replace_once(text, "  async function createSnapshot(", trash_actions + "  async function createSnapshot(", "trash actions")

text = replace_once(
    text,
    '''        await loadAssistantWorkTraceability(accessToken);
        await loadAssistantCloudFiles(accessToken);''',
    '''        await loadAssistantWorkTraceability(accessToken);
        await loadAssistantCloudFiles(accessToken);
        await refreshTrashState();''',
    "trash refresh on cloud open",
)

text = replace_once(
    text,
    '''              onDownloadFile={downloadCloudFile}
              onSetReferenceDate={setCloudReferenceDate}
            />''',
    '''              onDownloadFile={downloadCloudFile}
              onSetReferenceDate={setCloudReferenceDate}
              trashFiles={trashFiles}
              trashAvailable={trashAvailable}
              onMoveToTrash={moveCloudFileToTrash}
              onRestoreTrash={restoreCloudFileFromTrash}
              onDeleteTrash={permanentlyDeleteCloudFile}
              onRefreshTrash={refreshTrashState}
            />''',
    "cloud trash view handlers",
)

text = replace_once(
    text,
    '''  onDownloadFile,
  onSetReferenceDate,
}: {''',
    '''  onDownloadFile,
  onSetReferenceDate,
  trashFiles,
  trashAvailable,
  onMoveToTrash,
  onRestoreTrash,
  onDeleteTrash,
  onRefreshTrash,
}: {''',
    "cloud trash prop destructuring",
)

text = replace_once(
    text,
    '''  onDownloadFile: (file: CloudFile) => void;
  onSetReferenceDate: (fileId: string, date: string) => void;
}) {''',
    '''  onDownloadFile: (file: CloudFile) => void;
  onSetReferenceDate: (fileId: string, date: string) => void;
  trashFiles: TrashCloudFile[];
  trashAvailable: boolean;
  onMoveToTrash: (file: CloudFile) => void;
  onRestoreTrash: (file: TrashCloudFile) => void;
  onDeleteTrash: (file: TrashCloudFile) => void;
  onRefreshTrash: () => void;
}) {''',
    "cloud trash prop types",
)

text = replace_once(
    text,
    '''                    <button type="button" onClick={() => onDownloadFile(file)} className="rounded-lg border border-black/5 p-2 text-slate-500 hover:bg-slate-50" title="Descarregar ficheiro"><Download size={17} aria-hidden="true" /></button>
                  </div>''',
    '''                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => onDownloadFile(file)} className="rounded-lg border border-black/5 p-2 text-slate-500 hover:bg-slate-50" title="Descarregar ficheiro"><Download size={17} aria-hidden="true" /></button>
                      <button
                        type="button"
                        disabled={file.id.startsWith("assistant:")}
                        onClick={() => onMoveToTrash(file)}
                        className="rounded-lg border border-red-100 p-2 text-red-500 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-30"
                        title={file.id.startsWith("assistant:") ? "Disponível após persistência no backend" : "Mover para a Lixeira"}
                      ><Trash2 size={17} aria-hidden="true" /></button>
                    </div>
                  </div>''',
    "trash action on cloud card",
)

trash_panel = r'''
      <Panel title={`Lixeira · ${trashFiles.length}`} action="Atualizar" onAction={onRefreshTrash}>
        {!trashAvailable ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900">
            <div className="flex items-start gap-3"><Trash2 className="mt-0.5 shrink-0" size={20} /><div><p className="font-semibold">Lixeira preparada</p><p className="mt-1">A interface já está restaurada. A movimentação permanente de ficheiros fica ativa assim que o backend de rastreabilidade for atualizado no Oracle.</p></div></div>
          </div>
        ) : trashFiles.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-line bg-mist p-7 text-center">
            <Trash2 className="mx-auto text-slate-400" size={30} />
            <p className="mt-3 font-semibold text-ink">A Lixeira está vazia</p>
            <p className="mt-1 text-sm text-slate-500">Os ficheiros eliminados ficam aqui até serem restaurados ou removidos definitivamente.</p>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {trashFiles.map((file) => (
              <article key={file.id} className="rounded-xl border border-red-100 bg-red-50/30 p-4">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 text-red-600"><Trash2 size={18} aria-hidden="true" /></span>
                  <span className="rounded-full bg-red-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-red-700">Lixeira</span>
                </div>
                <p className="mt-3 truncate text-sm font-semibold text-ink">{file.filename}</p>
                <p className="mt-1 text-xs text-slate-500">{file.category} · {(file.sizeBytes / 1024).toFixed(1)} KB</p>
                <p className="mt-1 text-xs text-slate-500">Eliminado em {file.deletedAt ? new Date(file.deletedAt).toLocaleString("pt-PT") : "—"}</p>
                {file.referenceDate && <p className="mt-1 text-xs font-medium text-emerald-700">Data de referência {new Date(`${file.referenceDate}T12:00:00`).toLocaleDateString("pt-PT")}</p>}
                {file.taskId && <p className="mt-1 truncate text-[10px] text-slate-400">Tarefa {file.taskId}</p>}
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <button type="button" onClick={() => onRestoreTrash(file)} className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"><RotateCcw size={14} /> Restaurar</button>
                  <button type="button" onClick={() => onDeleteTrash(file)} className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white hover:bg-red-700"><XCircle size={14} /> Eliminar</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </Panel>

'''
text = replace_once(
    text,
    '''      <Panel title="Histórico diário de relatórios" action="Guardar hoje" onAction={onCreateSnapshot}>''',
    trash_panel + '''      <Panel title="Histórico diário de relatórios" action="Guardar hoje" onAction={onCreateSnapshot}>''',
    "trash panel",
)

required_markers = [
    "type TrashCloudFile",
    "/cloud/trash?limit=250",
    "/trash`,",
    "Mover para a Lixeira",
    "Lixeira · ${trashFiles.length}",
    "Restaurar",
    "Eliminar definitivamente",
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Cloud trash UI marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Restored SEO cloud trash with move, restore and permanent delete controls")
