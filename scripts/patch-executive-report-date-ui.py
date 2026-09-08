from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Executive report date patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")

# Reuse the existing reportDate state already used by the cloud/history area.
text = replace_once(
    text,
    '  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));',
    '  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));\n  const [reportDialogOpen, setReportDialogOpen] = useState(false);',
    "report dialog state",
)

# Make the selected date part of the report request and file name. Unknown query
# parameters are harmless for older backends, while date-aware report endpoints
# can use report_date as the canonical daily report filter.
text = replace_once(
    text,
    '        const response = await fetch(`${API_BASE_URL}/reports/executive.pdf`, {',
    '        const response = await fetch(`${API_BASE_URL}/reports/executive.pdf?report_date=${encodeURIComponent(reportDate)}`, {',
    "date-aware PDF request",
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
                    <div className="w-full max-w-md rounded-[24px] border border-white/10 bg-[#111315] p-6 shadow-2xl">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#a38476]">Relatório Executivo SEO</p>
                      <h2 id="executive-report-date-title" className="mt-2 text-2xl font-semibold text-white">Escolha a data do relatório</h2>
                      <p className="mt-2 text-sm leading-6 text-[#a8a29e]">O SEO irá gerar o documento usando o mapa diário, vendedores, totais, IVA e análise executiva correspondentes ao dia selecionado.</p>

                      <label className="mt-5 block text-xs font-semibold uppercase tracking-[0.12em] text-[#a38476]" htmlFor="executive-report-date">Data</label>
                      <input
                        id="executive-report-date"
                        type="date"
                        value={reportDate}
                        max={new Date().toISOString().slice(0, 10)}
                        onChange={(event) => setReportDate(event.target.value)}
                        className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 text-sm text-white outline-none focus:border-amber-400/40"
                      />

                      <div className="mt-5 rounded-xl border border-amber-400/15 bg-amber-500/[0.05] p-3 text-xs leading-5 text-[#d6d3d1]">
                        O relatório será diário. O total geral e os gráficos acumulados consideram os dados consolidados até esta data, sem alterar o modo Trabalho da Assistente IA.
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
                          disabled={!reportDate}
                          onClick={() => {
                            setReportDialogOpen(false);
                            void exportReport();
                          }}
                          className="inline-flex h-10 items-center gap-2 rounded-full bg-[#0071e3] px-5 text-sm font-semibold text-white hover:bg-[#0077ed] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Download size={16} aria-hidden="true" />
                          Gerar relatório
                        </button>
                      </div>
                    </div>
                  </div>
                )}'''

text = replace_once(text, report_button, report_button_with_dialog, "report date modal")

# CSV fallback must also identify the selected report date.
text = text.replace('downloadCsv(`relatorio-seo-${period}.csv`, rows);', 'downloadCsv(`relatorio-seo-${reportDate}.csv`, rows);')
text = text.replace('auditAction("REPORT_EXPORTED", `Relatório executivo exportado para o período ${selectedPeriod.label}.`);', 'auditAction("REPORT_EXPORTED", `Relatório executivo exportado para ${reportDate}.`);')

path.write_text(text, encoding="utf-8")
print("Patched Relatório: explicit date selection before executive export")
