import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";

const frontendRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");

const governedFiles = [
  "src/app/components/layout.tsx",
  "src/app/components/page-state.tsx",
  "src/app/components/bookshelf-page.tsx",
  "src/app/components/upload-book-dialog.tsx",
  "src/app/components/global-marks-page.tsx",
  "src/app/components/book-overview-page.tsx",
  "src/app/components/chapter-read-page.tsx",
  "src/app/lib/use-upload-book-actions.ts",
];

const hanPattern = /[\p{Script=Han}]/u;

const violations: Array<{ file: string; line: number; text: string }> = [];

for (const relativePath of governedFiles) {
  const absolutePath = path.resolve(frontendRoot, relativePath);
  const contents = fs.readFileSync(absolutePath, "utf8");
  contents.split(/\r?\n/).forEach((line, index) => {
    if (hanPattern.test(line)) {
      violations.push({
        file: relativePath,
        line: index + 1,
        text: line.trim(),
      });
    }
  });
}

assert.equal(
  violations.length,
  0,
  [
    "Governed English-UI files still contain Han characters.",
    "Move core UI copy into the locale layer or an allowed config file.",
    ...violations.map((item) => `- ${item.file}:${item.line} ${item.text}`),
  ].join("\n"),
);
