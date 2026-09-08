from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Executive report patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")

# Reuse the existing reportDate state already used by the cloud/history area.
# The seller workbook is intentionally scoped only to Executive Report generation;
# it does not feed Work mode or mutate the operational dataset.
text = replace_once(
    text,
    '  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));',
    '  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));\n'
    '  const [reportDialogOpen, setReportDialogOpen] = useState(false);\n'
    '  const [sellerReportFile, setSellerReportFile] = useState<File | null>(null);',
    "report dialog and seller workbook state",
)

# Require the date + seller workbook at the export function level too, so any
# secondary "Exportar PDF executivo" action opens the same report preparation UI.
text = replace_once(
    text,
    '''  async function exportReport() {
    if (!hasPermission(currentAccount, "reports:export")) {
      showToast("Sem permissão para exportar relatórios.");
      auditAction("REPORT_EXPORT_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }

    if (accessToken) {''',
    '''  async function exportReport() {
    if (!hasPermission(currentAccount, "reports:export")) {
      showToast("Sem permissão para exportar relatórios.");
      auditAction("REPORT_EXPORT_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    if (!reportDate || !sellerReportFile) {
      setReportDialogOpen(true);
      showToast(!reportDate ? "Escolha a data do relatório." : "Anexe o Excel de desempenho dos vendedores para gerar o relatório completo.");
      return;
    }

    if (accessToken) {''',
    "report prerequisites",
)

# Send the independently maintained seller workbook together with the selected
# report date. A date-aware/multipart report backend can combine it with the
# SEO operational map without treating seller data as part of the source of truth.
text = replace_once(
    text,
    '''      try {
        const response = await fetch(`${API_BASE_URL}/reports/executive.pdf`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });''',
    '''      try {
        const reportPayload = new FormData();
        reportPayload.append("report_date", reportDate);
        reportPayload.append("seller_file", sellerReportFile, sellerReportFile.name);
        const response = await fetch(`${API_BASE_URL}/reports/executive.pdf`, {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: reportPayload,
        });''',
    "multipart report request",
)

text = replace_once(
    text,
    '        link.download = "relatorio-executivo-seo.pdf";',
    '        link.download = `relatorio-executivo-seo-${reportDate}.pdf`;',
    "date-aware PDF filename",
)

report_button = '''                <button
                  className="inline-flex h-10 items-center gap-2 rounded-full bg-[#0071e3] px-5 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(0,113,227,0.18)] hover:bg-[#0077ed]"
                  onClick={exportReport}
                  type="button"
                >
                  <Download size={17} aria-hidden="true" />
                  Relatório
                </button>'''

report_button_with_dialog = '''                <button
                  className="inline-flex h-10 items-center gap-2 rounded-full bg-[#0071e3] px-5 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(0,113,227,0.18)] hover:bg-[#0077ed]"
                  onClick={() => setReportDialogOpen(true)}
                  type="button"
                >
                  <Download size={17} aria-hidden="true" />
                  Relatório
                </button>

                {reportDialogOpen && (
                  <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/65 px-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="executive-report-date-title">
                    <div className="w-full max-w-lg rounded-[24px] border border-white/10 bg-[#111315] p-6 shadow-2xl">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#a38476]">Relatório Executivo SEO</p>
                      <h2 id="executive-report-date-title" className="mt-2 text-2xl font-semibold text-white">Preparar relatório</h2>
                      <p className="mt-2 text-sm leading-6 text-[#a8a29e]">Escolha o dia e anexe o Excel que utiliza atualmente para acompanhar o desempenho dos vendedores. O ficheiro será usado somente para completar a secção comercial deste relatório.</p>

                      <label className="mt-5 block text-xs font-semibold uppercase tracking-[0.12em] text-[#a38476]" htmlFor="executive-report-date">1. Data do relatório</label>
                      <input
                        id="executive-report-date"
                        type="date"
                        value={reportDate}
                        max={new Date().toISOString().slice(0, 10)}
                        onChange={(event) => setReportDate(event.target.value)}
                        className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 text-sm text-white outline-none focus:border-amber-400/40"
                      />

                      <label className="mt-5 block text-xs font-semibold uppercase tracking-[0.12em] text-[#a38476]">2. Excel de desempenho dos vendedores</label>
                      <label className="mt-2 flex min-h-24 cursor-pointer items-center justify-between gap-4 rounded-xl border border-dashed border-white/15 bg-white/[0.035] px-4 py-3 transition hover:border-amber-400/35 hover:bg-amber-500/[0.04]">
                        <div>
                          <p className="text-sm font-semibold text-white">{sellerReportFile ? sellerReportFile.name : "Selecionar Excel dos vendedores"}</p>
                          <p className="mt-1 text-xs leading-5 text-[#a8a29e]">Aceita .xlsx, .xls ou .csv. O SEO utilizará apenas os campos disponíveis no ficheiro e não inventará valores ausentes.</p>
                        </div>
                        <Upload size={20} className="shrink-0 text-[#d4a63a]" aria-hidden="true" />
                        <input
                          type="file"
                          accept=".xlsx,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv"
                          className="hidden"
                          onChange={(event) => {
                            const nextFile = event.target.files?.[0] ?? null;
                            setSellerReportFile(nextFile);
                            if (nextFile) showToast(`${nextFile.name} adicionado ao Relatório Executivo.`);
                          }}
                        />
                      </label>

                      {sellerReportFile && (
                        <div className="mt-3 flex items-center justify-between rounded-xl border border-emerald-400/15 bg-emerald-500/[0.05] px-3 py-2 text-xs text-emerald-200">
                          <span>Excel dos vendedores pronto para análise.</span>
                          <button type="button" onClick={() => setSellerReportFile(null)} className="font-semibold text-white hover:underline">Remover</button>
                        </div>
                      )}

                      <div className="mt-5 rounded-xl border border-amber-400/15 bg-amber-500/[0.05] p-3 text-xs leading-5 text-[#d6d3d1]">
                        <p className="font-semibold text-white">O relatório completo irá reunir:</p>
                        <p className="mt-1">Resumo Executivo · Mapa Diário com e sem IVA · FR/FT/NC · Coimbra/Picoto · Novo/Usado · total diário · total geral/acumulado · gráficos e ranking de vendedores · participação por vendedor · Novo × Usado por vendedor quando disponível · Inteligência SEO · Data Quality.</p>
                      </div>

                      <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.025] p-3 text-xs leading-5 text-[#a8a29e]">
                        O Excel dos vendedores é uma fonte complementar do relatório e não altera Atena, o mapa diário, a Assistente IA nem o modo Trabalho.
                      </div>

                      <div className="mt-6 flex justify-end gap-3">
                        <button
                          type="button"
                          onClick={() => setReportDialogOpen(false)}
                          className="h-10 rounded-full border border-white/10 px-4 text-sm font-semibold text-[#d6d3d1] hover:bg-white/[0.05]"
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          disabled={!reportDate || !sellerReportFile}
                          onClick={() => {
                            setReportDialogOpen(false);
                            void exportReport();
                          }}
                          className="inline-flex h-10 items-center gap-2 rounded-full bg-[#0071e3] px-5 text-sm font-semibold text-white hover:bg-[#0077ed] disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Download size={16} aria-hidden="true" />
                          Gerar relatório completo
                        </button>
                      </div>
                    </div>
                  </div>
                )}'''

text = replace_once(text, report_button, report_button_with_dialog, "report preparation modal")

# CSV fallback still identifies the selected date. It intentionally does not try
# to parse XLSX in the browser: seller performance remains a report-only input.
text = text.replace('downloadCsv(`relatorio-seo-${period}.csv`, rows);', 'downloadCsv(`relatorio-seo-${reportDate}.csv`, rows);')
text = text.replace('auditAction("REPORT_EXPORTED", `Relatório executivo exportado para o período ${selectedPeriod.label}.`);', 'auditAction("REPORT_EXPORTED", `Relatório executivo exportado para ${reportDate} com ficheiro de vendedores ${sellerReportFile?.name ?? "não informado"}.`);')

path.write_text(text, encoding="utf-8")
print("Patched Relatório: date + separate seller performance workbook required")
