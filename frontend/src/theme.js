/**
 * Centralized theme/accent configuration.
 * Professional telemetry & developer tool accent palette.
 */
export const ACCENT_PRESETS = {
  cobalt: { primary: '#3b82f6', secondary: '#60a5fa', hover: '#2563eb', label: 'Cobalt' },
  emerald: { primary: '#10b981', secondary: '#34d399', hover: '#059669', label: 'Emerald' },
  amber: { primary: '#f59e0b', secondary: '#fbbf24', hover: '#d97706', label: 'Amber' },
  indigo: { primary: '#6366f1', secondary: '#818cf8', hover: '#4f46e5', label: 'Indigo' },
  rose: { primary: '#f43f5e', secondary: '#fb7185', hover: '#e11d48', label: 'Rose' },
  cyan: { primary: '#06b6d4', secondary: '#22d3ee', hover: '#0891b2', label: 'Cyan' },
};

const STORAGE_KEY = 'app_accent';

export function getSavedAccent() {
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
  return saved && ACCENT_PRESETS[saved] ? saved : 'cobalt';
}

export function applyAccentToDocument(accentKey) {
  const preset = ACCENT_PRESETS[accentKey] || ACCENT_PRESETS.cobalt;
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.style.setProperty('--accent-primary', preset.primary);
  root.style.setProperty('--accent-secondary', preset.secondary);
  root.style.setProperty('--accent-hover', preset.hover);
}

export function applySavedAccent() {
  applyAccentToDocument(getSavedAccent());
}
