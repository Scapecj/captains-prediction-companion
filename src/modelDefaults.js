export const DEFAULT_OPENROUTER_MODEL = 'openrouter/free';

export function resolveOpenRouterModel(envVar, fallback = DEFAULT_OPENROUTER_MODEL) {
  const configured = process.env[envVar];
  if (typeof configured !== 'string') return fallback;
  const cleaned = configured.trim();
  return cleaned || fallback;
}
