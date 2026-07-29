import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [file, reference] = process.argv.slice(2);
if (!file) throw new Error("Indique o ficheiro a verificar.");

async function load(path) {
  return SpreadsheetFile.importXlsx(await FileBlob.load(path));
}

const workbook = await load(file);
const sheet = workbook.worksheets.getItemAt(0);
const used = sheet.getUsedRange();
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 200 },
  summary: "final formula error scan",
  maxChars: 8000,
});

let comparison = null;
if (reference) {
  const expected = await load(reference);
  const expectedSheet = expected.worksheets.getItemAt(0);
  const actualFormulas = await workbook.inspect({ kind: "formula", sheetId: sheet.name, range: used.address, maxChars: 30000 });
  const expectedFormulas = await expected.inspect({ kind: "formula", sheetId: expectedSheet.name, range: expectedSheet.getUsedRange().address, maxChars: 30000 });
  const normalizeFormulaInspection = (text) => text.split("\n").filter(Boolean).map((line) => {
    const item = JSON.parse(line);
    return `${item.address}:${item.formula}`;
  });
  comparison = {
    actualRange: used.address,
    expectedRange: expectedSheet.getUsedRange().address,
    formulasEqual: JSON.stringify(normalizeFormulaInspection(actualFormulas.ndjson)) === JSON.stringify(normalizeFormulaInspection(expectedFormulas.ndjson)),
  };
}

await fs.mkdir("outputs/faturacao-reference-analysis", { recursive: true });
const preview = await workbook.render({ sheetName: sheet.name, range: "A1:M77", scale: 1, format: "png" });
await fs.writeFile(
  "outputs/faturacao-reference-analysis/resultado-gerado.png",
  new Uint8Array(await preview.arrayBuffer()),
);

console.log(JSON.stringify({
  sheet: sheet.name,
  range: used.address,
  formulaErrors: errors.ndjson,
  comparison,
  preview: "outputs/faturacao-reference-analysis/resultado-gerado.png",
}, null, 2));
