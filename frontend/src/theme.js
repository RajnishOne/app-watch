/**
 * Centralized theme/accent configuration.
 * Accent presets: primary, secondary (lighter), hover (darker).
 */
export const ACCENT_PRESETS = {
  pink: { primary: '#d45a85', secondary: '#e06b95', hover: '#c04d75', label: 'Pink' },
  blue: { primary: '#2196f3', secondary: '#42a5f5', hover: '#1e88e5', label: 'Blue' },
  green: { primary: '#00c853', secondary: '#4caf50', hover: '#00a843', label: 'Green' },
  purple: { primary: '#9c27b0', secondary: '#ab47bc', hover: '#8e24aa', label: 'Purple' },
  orange: { primary: '#ff9800', secondary: '#ffb74d', hover: '#f57c00', label: 'Orange' },
  teal: { primary: '#009688', secondary: '#26a69a', hover: '#00897b', label: 'Teal' },
};

const STORAGE_KEY = 'app_accent';

export function getSavedAccent() {
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
  return saved && ACCENT_PRESETS[saved] ? saved : 'pink';
}

export function applyAccentToDocument(accentKey) {
  const preset = ACCENT_PRESETS[accentKey] || ACCENT_PRESETS.pink;
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.style.setProperty('--accent-primary', preset.primary);
  root.style.setProperty('--accent-secondary', preset.secondary);
  root.style.setProperty('--accent-hover', preset.hover);
}

export function applySavedAccent() {
  applyAccentToDocument(getSavedAccent());
}
