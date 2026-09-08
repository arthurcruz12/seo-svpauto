from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")
old = '''        const reportPayload = new FormData();
        reportPayload.append("report_date", reportDate);
        reportPayload.append("seller_file", sellerReportFile, sellerReportFile.name);
        const response = await fetch(`${API_BASE_URL}/reports/executive.pdf`, {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: reportPayload,
        });
        if (!response.ok) throw new Error("Não foi possível gerar o PDF executivo.");'''
new = '''        const reportPayload = new FormData();
        reportPayload.append("report_date", reportDate);
        reportPayload.append("seller_file", sellerReportFile, sellerReportFile.name);
        reportPayload.append(
          "operational_json",
          JSON.stringify({
            dashboardSummary,
            documentIntelligence,
            inventory,
            debts,
            issues,
            selectedPeriod,
            dashboardPeriod,
          }),
        );
        const response = await fetch(`/api/executive-report`, {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: reportPayload,
        });
        if (!response.ok) {
          const problem = await response.json().catch(() => null);
          throw new Error(problem?.detail || "Não foi possível gerar o PDF executivo completo.");
        }'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"Executive report generator patch failed: expected 1 match, got {count}")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("Patched Relatório: seller workbook + SEO operational data -> preview PDF generator")
