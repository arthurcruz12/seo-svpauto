import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const files = process.argv.slice(2);
if (files.length !== 2) {
  throw new Error("Uso: node compare-faturacao-workbooks.mjs <origem.xlsx> <referencia.xlsx>");
}

for (const file of files) {
  const blob = await FileBlob.load(file);
  const workbook = await SpreadsheetFile.importXlsx(blob);
  const sheetInfo = await workbook.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 12000,
  });
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table,definedName,drawing",
    maxChars: 20000,
    tableMaxRows: 12,
    tableMaxCols: 30,
    tableMaxCellChars: 160,
  });

  const sheets = workbook.worksheets.items;
  const details = [];
  for (const sheet of sheets) {
    const used = sheet.getUsedRange();
    const region = await workbook.inspect({
      kind: "region",
      sheetId: sheet.name,
      range: used?.address ?? "A1:Z50",
      maxChars: 60000,
      tableMaxRows: 200,
      tableMaxCols: 40,
      tableMaxCellChars: 200,
    });
    const formulas = await workbook.inspect({
      kind: "formula",
      sheetId: sheet.name,
      range: used?.address ?? "A1:Z50",
      maxChars: 20000,
      options: { maxResults: 1000 },
    });
    const styles = await workbook.inspect({
      kind: "computedStyle",
      sheetId: sheet.name,
      range: used?.address ?? "A1:Z50",
      maxChars: 20000,
    });
    details.push({
      name: sheet.name,
      usedRange: used?.address ?? null,
      values: used?.values ?? [],
      formulas: used?.formulas ?? [],
      numberFormats: used?.format?.numberFormat ?? null,
      region: region.ndjson,
      formulaInspection: formulas.ndjson,
      styleInspection: styles.ndjson,
    });
  }

  const result = {
    file,
    sheetInfo: sheetInfo.ndjson,
    summary: summary.ndjson,
    details,
  };
  const safeName = file.toLowerCase().includes("separada") ? "referencia" : "origem";
  await fs.mkdir("outputs/faturacao-reference-analysis", { recursive: true });
  await fs.writeFile(
    `outputs/faturacao-reference-analysis/${safeName}.json`,
    JSON.stringify(result, null, 2),
    "utf8",
  );
  console.log(`${safeName}: ${details.map((sheet) => `${sheet.name} ${sheet.usedRange}`).join(", ")}`);
}
