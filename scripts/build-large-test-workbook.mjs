import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("outputs", "large-import-e2e");
const outputPath = path.join(outputDir, "faturas_teste_grande_50000.xlsx");
const workbook = Workbook.create();

const palette = {
  navy: "#0F172A",
  blue: "#2563EB",
  paleBlue: "#DBEAFE",
  paleAmber: "#FEF3C7",
  white: "#FFFFFF",
  slate: "#475569",
};

const entities = ["Auto Norte", "Oficina Central", "Frota Atlântico", "Mobilidade Sul", "Peças Lusitanas"];
const products = ["Farol LED", "Filtro de óleo", "Pastilhas de travão", "Bateria 70Ah", "Kit de embraiagem"];
const statuses = ["Pendente", "Pago", "Em validação", "Vencido"];

function excelColumn(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function buildSheet(name, count, titleRows, variant, startIndex) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;

  const headers = variant === 1
    ? ["Estado", "Documento", "Entidade", "Descrição", "Data", "Valor sem IVA", "Taxa IVA", "IVA", "Total", "Valor em aberto", "Dias", "Produto", "Referência", "Stock"]
    : ["Referência", "Produto", "Stock", "Fatura", "Fornecedor", "Descrição movimento", "Data emissão", "Líquido", "IVA", "Total documento", "Montante pendente", "Dias em atraso", "Estado", "Taxa IVA"];

  const headerRow = titleRows + 1;
  const totalCols = headers.length;
  const lastColumn = excelColumn(totalCols - 1);
  sheet.getRange(`A1:${lastColumn}1`).merge();
  sheet.getRange("A1").values = [[`Exportação operacional — ${name}`]];
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: palette.navy,
    font: { bold: true, color: palette.white, size: 16 },
    rowHeight: 30,
    verticalAlignment: "center",
  };
  if (titleRows >= 2) {
    sheet.getRange(`A2:${lastColumn}2`).merge();
    sheet.getRange("A2").values = [["Ficheiro de carga deliberadamente desconfigurado para ensaio de correção automática"]];
    sheet.getRange(`A2:${lastColumn}2`).format = {
      fill: palette.paleBlue,
      font: { color: palette.slate, italic: true },
      rowHeight: 24,
    };
  }
  if (titleRows >= 4) {
    sheet.getRange(`A3:${lastColumn}3`).merge();
    sheet.getRange("A3").values = [["Algumas linhas contêm totais vazios, datas inválidas, duplicados e números em formato PT."]];
    sheet.getRange(`A3:${lastColumn}3`).format = { fill: palette.paleAmber, font: { color: palette.slate }, rowHeight: 22 };
  }

  sheet.getRange(`A${headerRow}:${lastColumn}${headerRow}`).values = [headers];
  sheet.getRange(`A${headerRow}:${lastColumn}${headerRow}`).format = {
    fill: palette.blue,
    font: { bold: true, color: palette.white },
    rowHeight: 28,
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: palette.navy },
  };

  const batchSize = 2000;
  for (let offset = 0; offset < count; offset += batchSize) {
    const size = Math.min(batchSize, count - offset);
    const rows = [];
    for (let local = 0; local < size; local += 1) {
      const i = startIndex + offset + local;
      const isDuplicate = i % 997 === 0;
      const j = isDuplicate ? i - 1 : i;
      const isCredit = j % 197 === 0;
      const docIndex = j;
      const document = `${isCredit ? "NC" : "FT"} 2026/${String(docIndex).padStart(6, "0")}`;
      const net = Number((50 + (j % 700) * 1.37).toFixed(2));
      const rate = j % 11 === 0 ? 0.13 : 0.23;
      const vat = Number((net * rate).toFixed(2));
      let total = Number((net + vat).toFixed(2));
      if (j % 101 === 0) total = null;
      if (j % 313 === 0) total = Number((net + vat + 7.5).toFixed(2));
      const open = statuses[j % statuses.length] === "Pago" ? 0 : Number(((net + vat) * ((j % 5) / 5)).toFixed(2));
      const date = j % 2111 === 0 ? "31/02/2026" : new Date(Date.UTC(2026, j % 12, (j % 27) + 1));
      const stock = j % 503 === 0 ? 0 : (j * 7) % 36;
      const entity = entities[j % entities.length];
      const product = products[j % products.length];
      const description = isCredit ? `Nota de crédito — ${product}` : `Venda e serviço — ${product}`;
      const status = statuses[j % statuses.length];
      const days = status === "Vencido" ? (j % 120) + 1 : 0;
      const sku = `SKU-${String((j % 1500) + 1).padStart(5, "0")}`;

      if (variant === 1) {
        rows.push([status, document, entity, description, date, net, rate, vat, total, open, days, product, sku, stock]);
      } else {
        const localizedNet = j % 89 === 0 ? net.toLocaleString("pt-PT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : net;
        const localizedVat = j % 89 === 0 ? vat.toLocaleString("pt-PT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : vat;
        rows.push([sku, product, stock, document, entity, description, date, localizedNet, localizedVat, total, open, days, status, rate]);
      }
    }
    const firstRow = headerRow + 1 + offset;
    const lastRow = firstRow + size - 1;
    sheet.getRange(`A${firstRow}:${lastColumn}${lastRow}`).values = rows;
  }

  const firstDataRow = headerRow + 1;
  const lastDataRow = headerRow + count;
  const dateColumn = variant === 1 ? "E" : "G";
  const netColumn = variant === 1 ? "F" : "H";
  const rateColumn = variant === 1 ? "G" : "N";
  const vatColumn = variant === 1 ? "H" : "I";
  const totalColumn = variant === 1 ? "I" : "J";
  const openColumn = variant === 1 ? "J" : "K";

  sheet.getRange(`${dateColumn}${firstDataRow}:${dateColumn}${lastDataRow}`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`${netColumn}${firstDataRow}:${netColumn}${lastDataRow}`).format.numberFormat = "€ #,##0.00;[Red](€ #,##0.00);-";
  sheet.getRange(`${vatColumn}${firstDataRow}:${vatColumn}${lastDataRow}`).format.numberFormat = "€ #,##0.00;[Red](€ #,##0.00);-";
  sheet.getRange(`${totalColumn}${firstDataRow}:${totalColumn}${lastDataRow}`).format.numberFormat = "€ #,##0.00;[Red](€ #,##0.00);-";
  sheet.getRange(`${openColumn}${firstDataRow}:${openColumn}${lastDataRow}`).format.numberFormat = "€ #,##0.00;[Red](€ #,##0.00);-";
  sheet.getRange(`${rateColumn}${firstDataRow}:${rateColumn}${lastDataRow}`).format.numberFormat = "0%";
  sheet.freezePanes.freezeRows(headerRow);

  const widths = variant === 1
    ? [15, 21, 18, 30, 14, 18, 12, 16, 17, 19, 14, 22, 16, 12]
    : [16, 22, 10, 22, 19, 34, 15, 18, 16, 19, 19, 15, 17, 12];
  widths.forEach((width, index) => {
    sheet.getRange(`${excelColumn(index)}:${excelColumn(index)}`).format.columnWidth = width;
  });
  sheet.getRange(`A${firstDataRow}:${lastColumn}${Math.min(lastDataRow, firstDataRow + 500)}`).format.borders = {
    insideHorizontal: { style: "thin", color: "#E2E8F0" },
  };
}

buildSheet("Faturas_Desconfiguradas", 30000, 4, 1, 1);
buildSheet("Export_Antigo", 20000, 2, 2, 30001);

await fs.mkdir(outputDir, { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

for (const [sheetName, range] of [
  ["Faturas_Desconfiguradas", "A1:N18"],
  ["Export_Antigo", "A1:N16"],
]) {
  const preview = await workbook.render({ sheetName, range, scale: 1.25, format: "png" });
  await fs.writeFile(path.join(outputDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const inspection = await workbook.inspect({
  kind: "table",
  range: "Faturas_Desconfiguradas!A1:N12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 14,
  maxChars: 7000,
});
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(JSON.stringify({ outputPath, inspection: inspection.ndjson, errors: errors.ndjson }));
