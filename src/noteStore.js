import { randomUUID } from 'node:crypto';
import { loadJsonFile, writeJsonFileAtomic } from './storage.js';

function normalizeTags(tags) {
  if (!Array.isArray(tags)) {
    return [];
  }

  return [...new Set(tags.map(tag => String(tag).trim()).filter(Boolean))];
}

function normalizeText(value) {
  return String(value ?? '').trim();
}

export function createNoteStore(filePath) {
  let notes = loadJsonFile(filePath, []);

  if (!Array.isArray(notes)) {
    notes = [];
  }

  function persist() {
    writeJsonFileAtomic(filePath, notes);
  }

  return {
    list(limit = 10) {
      return notes.slice(0, Math.max(0, limit));
    },

    search(query, limit = 10) {
      const q = normalizeText(query).toLowerCase();
      if (!q) {
        return [];
      }

      return notes
        .filter(note => {
          const haystack = [
            note.title,
            note.body,
            ...(note.tags ?? [])
          ]
            .join(' ')
            .toLowerCase();

          return haystack.includes(q);
        })
        .slice(0, Math.max(0, limit));
    },

    create({ title, body, tags = [] }) {
      const now = new Date().toISOString();
      const note = {
        id: randomUUID(),
        title: normalizeText(title),
        body: normalizeText(body),
        tags: normalizeTags(tags),
        createdAt: now,
        updatedAt: now,
      };

      notes = [note, ...notes];
      persist();
      return note;
    },

    delete(id) {
      const before = notes.length;
      notes = notes.filter(note => note.id !== id);
      const removed = notes.length !== before;
      if (removed) {
        persist();
      }
      return removed;
    },

    stats() {
      return {
        count: notes.length,
        tags: notes.reduce((acc, note) => {
          for (const tag of note.tags ?? []) {
            acc[tag] = (acc[tag] ?? 0) + 1;
          }
          return acc;
        }, {}),
      };
    },
  };
}
