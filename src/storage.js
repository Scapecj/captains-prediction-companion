import { mkdirSync, readFileSync, renameSync, writeFileSync, existsSync } from 'node:fs';
import { dirname } from 'node:path';

function ensureParentDir(filePath) {
  mkdirSync(dirname(filePath), { recursive: true });
}

export function loadJsonFile(filePath, fallbackValue) {
  if (!existsSync(filePath)) {
    return fallbackValue;
  }

  try {
    return JSON.parse(readFileSync(filePath, 'utf8'));
  } catch {
    return fallbackValue;
  }
}

export function writeJsonFileAtomic(filePath, value) {
  ensureParentDir(filePath);
  const tempPath = `${filePath}.tmp`;
  writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  renameSync(tempPath, filePath);
}
