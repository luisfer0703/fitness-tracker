/**
 * Tema claro / oscuro (localStorage: ft-theme).
 */
(function () {
  const STORAGE_KEY = 'ft-theme';
  const THEMES = ['dark', 'light'];
  const META_COLORS = { dark: '#0b1220', light: '#eef2f7' };
  const ICONS = { dark: '🌙', light: '☀️' };
  const LABELS = { dark: 'Modo oscuro', light: 'Modo claro' };

  function normalizeTheme(value) {
    return THEMES.includes(value) ? value : 'dark';
  }

  function getTheme() {
    try {
      return normalizeTheme(localStorage.getItem(STORAGE_KEY));
    } catch (e) {
      return 'dark';
    }
  }

  function updateMeta(theme) {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', META_COLORS[theme] || META_COLORS.dark);
  }

  function updateToggleButtons(theme) {
    document.querySelectorAll('.js-theme-toggle').forEach((btn) => {
      const next = theme === 'dark' ? 'light' : 'dark';
      btn.textContent = ICONS[theme];
      btn.setAttribute('aria-label', `Cambiar a modo ${next === 'light' ? 'claro' : 'oscuro'}`);
      btn.setAttribute('title', LABELS[theme]);
    });
    document.querySelectorAll('.js-theme-set').forEach((btn) => {
      const value = btn.getAttribute('data-theme');
      const active = value === theme;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  function applyTheme(theme, persist) {
    const normalized = normalizeTheme(theme);
    document.documentElement.setAttribute('data-theme', normalized);
    updateMeta(normalized);
    updateToggleButtons(normalized);
    if (persist) {
      try {
        localStorage.setItem(STORAGE_KEY, normalized);
      } catch (e) {
        /* ignore */
      }
    }
    return normalized;
  }

  function toggleTheme() {
    const current = getTheme();
    return applyTheme(current === 'dark' ? 'light' : 'dark', true);
  }

  function bindControls() {
    document.querySelectorAll('.js-theme-toggle').forEach((btn) => {
      btn.addEventListener('click', toggleTheme);
    });
    document.querySelectorAll('.js-theme-set').forEach((btn) => {
      btn.addEventListener('click', () => {
        applyTheme(btn.getAttribute('data-theme'), true);
      });
    });
  }

  window.FitnessTheme = { applyTheme, toggleTheme, getTheme };

  document.addEventListener('DOMContentLoaded', () => {
    applyTheme(getTheme(), false);
    bindControls();
  });
})();
