import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { loadDotEnv } from '../src/env.js';
import { loadJsonFile, writeJsonFileAtomic } from '../src/storage.js';
import { resolveOpenRouterModel } from '../src/modelDefaults.js';

test('loadDotEnv loads new keys without overriding existing ones', () => {
  const dir = mkdtempSync(join(tmpdir(), 'env-test-'));
  const envPath = join(dir, '.env');
  process.env.EXISTING_KEY = 'keep-me';

  writeFileSync(
    envPath,
    `# comment
PLAIN=plain-value
SPACED = spaced
QUOTED="quoted value"
SINGLE='single value'
MULTILINE="line1\\nline2"
EXISTING_KEY=should-not-overwrite
`,
    'utf8'
  );

  loadDotEnv(envPath);

  assert.equal(process.env.PLAIN, 'plain-value');
  assert.equal(process.env.SPACED, 'spaced');
  assert.equal(process.env.QUOTED, 'quoted value');
  assert.equal(process.env.SINGLE, 'single value');
  assert.equal(process.env.MULTILINE, 'line1\nline2');
  assert.equal(process.env.EXISTING_KEY, 'keep-me');

  delete process.env.PLAIN;
  delete process.env.SPACED;
  delete process.env.QUOTED;
  delete process.env.SINGLE;
  delete process.env.MULTILINE;
  delete process.env.EXISTING_KEY;
  rmSync(dir, { recursive: true, force: true });
});

test('storage helpers fall back safely and write atomically', () => {
  const dir = mkdtempSync(join(tmpdir(), 'storage-test-'));
  const missingPath = join(dir, 'missing.json');
  assert.deepEqual(loadJsonFile(missingPath, { fallback: true }), { fallback: true });

  const badPath = join(dir, 'bad.json');
  writeFileSync(badPath, 'not-json', 'utf8');
  assert.equal(loadJsonFile(badPath, 42), 42);

  const targetPath = join(dir, 'nested', 'data.json');
  writeJsonFileAtomic(targetPath, { ok: true });
  const raw = readFileSync(targetPath, 'utf8');
  assert.equal(raw.endsWith('\n'), true);
  assert.deepEqual(JSON.parse(raw), { ok: true });
  assert.equal(existsSync(`${targetPath}.tmp`), false);

  rmSync(dir, { recursive: true, force: true });
});

test('resolveOpenRouterModel trims configured values and falls back cleanly', () => {
  delete process.env.CUSTOM_MODEL;
  assert.equal(resolveOpenRouterModel('CUSTOM_MODEL', 'fallback-model'), 'fallback-model');

  process.env.CUSTOM_MODEL = ' custom/alpha ';
  assert.equal(resolveOpenRouterModel('CUSTOM_MODEL', 'fallback-model'), 'custom/alpha');

  delete process.env.CUSTOM_MODEL;
});
