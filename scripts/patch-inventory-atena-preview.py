from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Inventory preview patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")

mount_anchor = '''          <AgenticExtensions section={activeSection} />
'''
mount_replacement = mount_anchor + '''          <AtenaInventoryPreview section={activeSection} />
'''
text = replace_once(text, mount_anchor, mount_replacement, "Atena inventory mount")

component = r'''

type AtenaStockCode = "CUSA" | "CNOV" | "PUSA" | "PNOV";
type AtenaInventoryRow = {
  code: AtenaStockCode;
  ref: string;
  piece: string;
  brand: string;
  quantity: number;
  unitCost: number;
  warehouse: string;
  lastMovementDays: number;
  status: "Normal" | "Stock baixo" | "Parado";
};

const ATENA_INVENTORY_SAMPLE: AtenaInventoryRow[] = [
  { code: "CUSA", ref: "CUSA-BMW-N47-001", piece: "Motor BMW N47 2.0d", brand: "BMW", quantity: 6, unitCost: 1850, warehouse: "Coimbra · Usado", lastMovementDays: 8, status: "Normal" },
  { code: "CUSA", ref: "CUSA-ZF8-014", piece: "Caixa automática ZF 8HP", brand: "ZF", quantity: 4, unitCost: 1250, warehouse: "Coimbra · Usado", lastMovementDays: 19, status: "Normal" },
  { code: "CUSA", ref: "CUSA-F30-233", piece: "Porta dianteira BMW F30", brand: "BMW", quantity: 9, unitCost: 220, warehouse: "Coimbra · Usado", lastMovementDays: 112, status: "Parado" },
  { code: "CNOV", ref: "CNOV-BRK-401", piece: "Kit discos + pastilhas", brand: "ATE", quantity: 36, unitCost: 68, warehouse: "Coimbra · Novo", lastMovementDays: 2, status: "Normal" },
  { code: "CNOV", ref: "CNOV-TUR-088", piece: "Turbo 2.0 TDI", brand: "Garrett", quantity: 11, unitCost: 540, warehouse: "Coimbra · Novo", lastMovementDays: 14, status: "Normal" },
  { code: "CNOV", ref: "CNOV-LGT-915", piece: "Farol LED dianteiro", brand: "Hella", quantity: 2, unitCost: 310, warehouse: "Coimbra · Novo", lastMovementDays: 7, status: "Stock baixo" },
  { code: "PUSA", ref: "PUSA-OM651-071", piece: "Motor Mercedes OM651", brand: "Mercedes-Benz", quantity: 3, unitCost: 1700, warehouse: "Picoto · Usado", lastMovementDays: 31, status: "Normal" },
  { code: "PUSA", ref: "PUSA-DQ250-019", piece: "Caixa DSG DQ250", brand: "Volkswagen", quantity: 5, unitCost: 900, warehouse: "Picoto · Usado", lastMovementDays: 96, status: "Parado" },
  { code: "PUSA", ref: "PUSA-ALT-340", piece: "Alternador 180A", brand: "Bosch", quantity: 1, unitCost: 145, warehouse: "Picoto · Usado", lastMovementDays: 4, status: "Stock baixo" },
  { code: "PNOV", ref: "PNOV-SHK-155", piece: "Amortecedor dianteiro", brand: "Bilstein", quantity: 40, unitCost: 89, warehouse: "Picoto · Novo", lastMovementDays: 3, status: "Normal" },
  { code: "PNOV", ref: "PNOV-NOX-921", piece: "Sensor NOx", brand: "Bosch", quantity: 18, unitCost: 210, warehouse: "Picoto · Novo", lastMovementDays: 17, status: "Normal" },
  { code: "PNOV", ref: "PNOV-STR-511", piece: "Motor de arranque", brand: "Valeo", quantity: 2, unitCost: 175, warehouse: "Picoto · Novo", lastMovementDays: 11, status: "Stock baixo" },
];

function AtenaInventoryPreview({ section }: { section: SectionId }) {
  const [stockCode, setStockCode] = useState<"TODOS" | AtenaStockCode>("TODOS");
  const [search, setSearch] = useState("");
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [importedFile, setImportedFile] = useState<{ name: string; size: string; chunks: number } | null>(null);
  const [importNotice, setImportNotice] = useState("Modo demonstração: dados Atena simulados. Nenhum dado de produção é alterado.");

  if (section !== "inventario") return null;

  const visibleRows = ATENA_INVENTORY_SAMPLE.filter((row) => {
    const codeMatch = stockCode === "TODOS" || row.code === stockCode;
    const term = search.trim().toLocaleLowerCase("pt-PT");
    const searchMatch = !term || [row.ref, row.piece, row.brand, row.warehouse, row.status].some((value) => value.toLocaleLowerCase("pt-PT").includes(term));
    return codeMatch && searchMatch;
  });

  const totalUnits = ATENA_INVENTORY_SAMPLE.reduce((sum, row) => sum + row.quantity, 0);
  const totalValue = ATENA_INVENTORY_SAMPLE.reduce((sum, row) => sum + row.quantity * row.unitCost, 0);
  const lowStock = ATENA_INVENTORY_SAMPLE.filter((row) => row.status === "Stock baixo").length;
  const stalled = ATENA_INVENTORY_SAMPLE.filter((row) => row.status === "Parado").length;

  const groupSummary = (["CUSA", "CNOV", "PUSA", "PNOV"] as AtenaStockCode[]).map((code) => {
    const rows = ATENA_INVENTORY_SAMPLE.filter((row) => row.code === code);
    return {
      code,
      units: rows.reduce((sum, row) => sum + row.quantity, 0),
      value: rows.reduce((sum, row) => sum + row.quantity * row.unitCost, 0),
    };
  });

  async function handleAtenaFile(file?: File) {
    if (!file) return;
    const allowed = /\.(xlsx|xls|csv|pdf)$/i.test(file.name);
    if (!allowed) {
      setImportNotice("Formato não suportado no teste. Use .xlsx, .xls, .csv ou .pdf.");
      return;
    }

    setProcessing(true);
    setProgress(0);
    const chunkSize = 25 * 1024 * 1024;
    const chunks = Math.max(1, Math.ceil(file.size / chunkSize));
    const steps = Math.max(6, Math.min(20, chunks * 2));

    for (let step = 1; step <= steps; step += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 90));
      setProgress(Math.round((step / steps) * 100));
    }

    setImportedFile({
      name: file.name,
      size: file.size >= 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(file.size / 1024))} KB`,
      chunks,
    });
    setImportNotice(`Pré-validação concluída: ${file.name}. No backend real, o ficheiro será lido em ${chunks} lote(s), sem carregar tudo na memória.`);
    setProcessing(false);
  }

  function exportVisibleCsv() {
    const header = "Codigo;Referencia;Peca;Marca;Quantidade;CustoUnitario;Valor;Armazem;Estado";
    const rows = visibleRows.map((row) => [
      row.code,
      row.ref,
      row.piece,
      row.brand,
      row.quantity,
      row.unitCost.toFixed(2),
      (row.quantity * row.unitCost).toFixed(2),
      row.warehouse,
      row.status,
    ].join(";"));
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "inventario-atena-preview.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="space-y-5 border-t border-white/10 pt-7" aria-label="Preview do inventário Atena">
      <div className="rounded-2xl border border-amber-400/20 bg-amber-500/[0.05] p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-300">Preview isolado · Inventário Atena</p>
            <h3 className="mt-2 text-xl font-semibold text-white">Inventário Inteligente · CUSA / CNOV / PUSA / PNOV</h3>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-[#c3aaa0]">Protótipo para validar o fluxo antes de tocar no backend atual. A faturação diária permanece intacta.</p>
          </div>
          <span className="w-fit rounded-full border border-emerald-400/20 bg-emerald-500/[0.08] px-3 py-1.5 text-xs font-semibold text-emerald-300">Sandbox · sem escrita em produção</span>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <AtenaMetric title="Unidades em stock" value={String(totalUnits)} detail="amostra de teste" />
        <AtenaMetric title="Valor do stock" value={formatCurrency(totalValue)} detail="custo imobilizado" />
        <AtenaMetric title="Stock baixo" value={String(lowStock)} detail="artigos críticos" />
        <AtenaMetric title="Sem movimento > 90d" value={String(stalled)} detail="capital parado" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-white/[0.04]"><Upload className="h-5 w-5 text-amber-300" /></div>
            <div>
              <p className="font-semibold text-white">Importar ficheiro do Atena</p>
              <p className="text-xs text-[#9c8276]">Excel é o fluxo principal. PDF também fica aceite no laboratório.</p>
            </div>
          </div>

          <label className="mt-5 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-white/15 bg-white/[0.025] px-5 py-8 text-center transition hover:border-amber-400/30 hover:bg-amber-500/[0.03]">
            <FileSpreadsheet className="h-7 w-7 text-amber-300" />
            <span className="mt-3 text-sm font-semibold text-white">Selecionar ficheiro Atena</span>
            <span className="mt-1 text-xs text-[#9c8276]">.xlsx · .xls · .csv · .pdf</span>
            <span className="mt-3 rounded-full bg-blue-500/10 px-3 py-1 text-[11px] font-semibold text-blue-300">Ficheiros grandes → processamento em lotes de ~25 MB</span>
            <input className="hidden" type="file" accept=".xlsx,.xls,.csv,.pdf" onChange={(event) => void handleAtenaFile(event.target.files?.[0])} />
          </label>

          {processing && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-[#c3aaa0]"><span>A validar estrutura e preparar lotes…</span><strong className="text-white">{progress}%</strong></div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-amber-300 transition-all" style={{ width: `${progress}%` }} /></div>
            </div>
          )}

          {importedFile && (
            <div className="mt-4 rounded-xl border border-emerald-400/15 bg-emerald-500/[0.05] p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Ficheiro preparado</div>
              <p className="mt-2 text-sm text-white">{importedFile.name}</p>
              <p className="mt-1 text-xs text-[#9c8276]">{importedFile.size} · {importedFile.chunks} lote(s) estimado(s)</p>
            </div>
          )}
          <p className="mt-4 text-xs leading-5 text-[#a38476]">{importNotice}</p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Separação automática Atena</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {groupSummary.map((group) => {
              const labels: Record<AtenaStockCode, string> = { CUSA: "Coimbra · Usado", CNOV: "Coimbra · Novo", PUSA: "Picoto · Usado", PNOV: "Picoto · Novo" };
              const active = stockCode === group.code;
              return (
                <button key={group.code} type="button" onClick={() => setStockCode(active ? "TODOS" : group.code)} className={`rounded-2xl border p-4 text-left transition ${active ? "border-amber-400/40 bg-amber-500/[0.08]" : "border-white/10 bg-white/[0.025] hover:border-white/20"}`}>
                  <div className="flex items-center justify-between"><strong className="text-lg text-white">{group.code}</strong><span className="text-xs font-semibold text-amber-300">{group.units} un.</span></div>
                  <p className="mt-1 text-xs text-[#9c8276]">{labels[group.code]}</p>
                  <p className="mt-3 text-sm font-semibold text-white">{formatCurrency(group.value)}</p>
                </button>
              );
            })}
          </div>
          <div className="mt-4 rounded-xl border border-blue-400/15 bg-blue-500/[0.05] p-4 text-xs leading-5 text-blue-200">No backend real, o parser identifica CUSA/CNOV/PUSA/PNOV pela estrutura do ficheiro Atena, normaliza os campos e envia apenas dados limpos para Oracle/DuckDB.</div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Inventário processado</p>
            <p className="mt-1 text-sm text-white">{visibleRows.length} artigos visíveis · filtro {stockCode}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8d756b]" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Peça, marca, referência…" className="h-10 w-full rounded-xl border border-white/10 bg-white/[0.04] pl-9 pr-3 text-sm text-white outline-none placeholder:text-[#6f5f58] sm:w-64" />
            </div>
            <button type="button" onClick={exportVisibleCsv} className="flex h-10 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 text-xs font-semibold text-white hover:bg-white/[0.07]"><Download className="h-4 w-4" /> Exportar CSV</button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead><tr className="border-b border-white/10 text-xs uppercase tracking-[0.12em] text-[#8d756b]"><th className="px-3 py-3">Grupo</th><th className="px-3 py-3">Referência</th><th className="px-3 py-3">Peça</th><th className="px-3 py-3">Marca</th><th className="px-3 py-3 text-right">Qtd.</th><th className="px-3 py-3 text-right">Custo</th><th className="px-3 py-3 text-right">Valor</th><th className="px-3 py-3">Estado</th></tr></thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.ref} className="border-b border-white/[0.06] text-[#d6d3d1] hover:bg-white/[0.025]">
                  <td className="px-3 py-3"><button type="button" onClick={() => setStockCode(row.code)} className="rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1 text-xs font-bold text-amber-300">{row.code}</button></td>
                  <td className="px-3 py-3 font-mono text-xs text-[#a99186]">{row.ref}</td>
                  <td className="px-3 py-3"><p className="font-medium text-white">{row.piece}</p><p className="mt-1 text-xs text-[#79665e]">{row.warehouse} · mov. há {row.lastMovementDays}d</p></td>
                  <td className="px-3 py-3">{row.brand}</td>
                  <td className="px-3 py-3 text-right font-semibold text-white">{row.quantity}</td>
                  <td className="px-3 py-3 text-right">{formatCurrency(row.unitCost)}</td>
                  <td className="px-3 py-3 text-right font-semibold text-white">{formatCurrency(row.quantity * row.unitCost)}</td>
                  <td className="px-3 py-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${row.status === "Normal" ? "bg-emerald-500/10 text-emerald-300" : row.status === "Stock baixo" ? "bg-amber-500/10 text-amber-300" : "bg-red-500/10 text-red-300"}`}>{row.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <AtenaMetric title="Motor de análise" value="DuckDB" detail="agregações e ficheiros grandes" />
        <AtenaMetric title="Persistência" value="Oracle" detail="estado operacional aprovado" />
        <AtenaMetric title="Integração" value="Atena → Excel" detail="entrada sem mexer na faturação" />
      </div>
    </section>
  );
}

function AtenaMetric({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#806d64]">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-[#9c8276]">{detail}</p>
    </div>
  );
}
'''

export_anchor = "\nexport default App;\n"
text = replace_once(text, export_anchor, component + export_anchor, "component injection")
path.write_text(text, encoding="utf-8")
print("Atena inventory preview patch applied")
