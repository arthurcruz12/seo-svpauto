import fs from "node:fs";

const files = [
  "src/App.tsx",
  "src/services/insights.ts",
  "src/services/auth.ts",
  "src/services/importer.ts",
  "src/domain/accounts.ts",
  "src/domain/types.ts",
  "README.md",
  "backend/app/main.py",
  "backend/app/security.py",
];

const replacements = new Map([
  ["\u00c3\u00a7", "ç"],
  ["\u00c3\u00a3", "ã"],
  ["\u00c3\u00a1", "á"],
  ["\u00c3\u00a2", "â"],
  ["\u00c3\u00aa", "ê"],
  ["\u00c3\u00a9", "é"],
  ["\u00c3\u00ad", "í"],
  ["\u00c3\u00b3", "ó"],
  ["\u00c3\u00ba", "ú"],
  ["\u00c3\u00b5", "õ"],
  ["\u00c3\u00a0", "à"],
  ["\u00c3\u0087", "Ç"],
  ["\u00c3\u0081", "Á"],
  ["\u00c3\u0089", "É"],
  ["\u00c3\u008d", "Í"],
  ["\u00c3\u0093", "Ó"],
  ["\u00c3\u009a", "Ú"],
  ["\u00c2\u00b7", "·"],
  ["\u00c2\u00ba", "º"],
  ["\u00c2\u00aa", "ª"],
  ["\u00e2\u201a\u00ac", "€"],
  ["\u00e2\u20ac\u201c", "-"],
  ["\u00e2\u20ac\u201d", "-"],
  ["\u00e2\u20ac\u0153", "\""],
  ["\u00e2\u20ac\u009d", "\""],
  ["\u00e2\u20ac\u02dc", "'"],
  ["\u00e2\u20ac\u2122", "'"],
]);

for (const file of files) {
  if (!fs.existsSync(file)) continue;
  let text = fs.readFileSync(file, "utf8");
  for (const [bad, good] of replacements) {
    text = text.split(bad).join(good);
  }
  fs.writeFileSync(file, text, "utf8");
}

console.log("Encoding normalized");
