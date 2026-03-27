import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, '..');
const skillsRoot = '/root/.codex/skills';
const checkedFiles = [
  'src/server.js',
  'src/noteStore.js',
  'src/storage.js',
  'test/server.test.js',
];

const forbiddenPatterns = [
  /\/root\/\.codex\/skills/,
  /(?:from|import)\s+['"`][^'"`]*\.\.\/skills[^'"`]*['"`]/,
  /['"`][^'"`]*\.\.\/skills[^'"`]*['"`]/,
];

function fail(message) {
  console.error(JSON.stringify({ ok: false, message }, null, 2));
  process.exitCode = 1;
}

async function main() {
  let entries;

  try {
    entries = await fs.readdir(skillsRoot, { withFileTypes: true });
  } catch (error) {
    throw new Error(`Skills root is missing or unreadable at ${skillsRoot}: ${error.message}`);
  }

  const skillCount = entries.filter((entry) => entry.isDirectory()).length;

  for (const relativePath of checkedFiles) {
    const absolutePath = path.join(appRoot, relativePath);
    let source;

    try {
      source = await fs.readFile(absolutePath, 'utf8');
    } catch (error) {
      throw new Error(`Unable to read ${relativePath}: ${error.message}`);
    }

    for (const pattern of forbiddenPatterns) {
      if (pattern.test(source)) {
        throw new Error(
          `Compatibility check failed: ${relativePath} references the Codex skills tree directly. Keep the app starter isolated from ${skillsRoot}.`,
        );
      }
    }
  }

  console.log(
    JSON.stringify(
      {
        ok: true,
        message: 'Starter is isolated from /root/.codex/skills and the installed skill set remains available.',
        skillsRoot,
        skillCount,
        checkedFiles,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => fail(error.message));
