import fs from "node:fs";
import path from "node:path";
import sharp from "file:///C:/Users/evagh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs";

const sourceRoot = path.resolve("tmp/chapter4_diagrams_source/chapter 4 diagrams");
const outputRoot = path.resolve("tmp/chapter4_diagrams_rendered");

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  });
}

fs.mkdirSync(outputRoot, { recursive: true });
for (const sourcePath of walk(sourceRoot).filter((file) => file.endsWith(".svg"))) {
  const relative = path.relative(sourceRoot, sourcePath).replaceAll(path.sep, "__");
  const outputPath = path.join(outputRoot, `${relative}.png`);
  await sharp(sourcePath, { density: 150 }).flatten({ background: "white" }).png().toFile(outputPath);
  process.stdout.write(`${outputPath}\n`);
}
