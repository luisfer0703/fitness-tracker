/**
 * Interacciones: skeletons, toasts, marcar ejercicio, temporizador de descanso, agua.
 */
(function () {
  const usuarioId = document.body.dataset.usuarioId;

  function revealSkeleton(wrap) {
    const sk = wrap.querySelector('.ft-skeleton');
    const content = wrap.querySelector('.ft-skeleton-content');
    if (sk) sk.classList.add('ft-skeleton--hide');
    if (content) {
      content.hidden = false;
      content.removeAttribute('hidden');
      content.classList.add('ft-skeleton-content--show');
    }
    wrap.classList.remove('ft-skeleton-wrap--loading');
  }

  /* ——— Skeletons ——— */
  function initSkeletons() {
    document.querySelectorAll('[data-skeleton]').forEach((wrap) => {
      const sk = wrap.querySelector('.ft-skeleton');
      const content = wrap.querySelector('.ft-skeleton-content');
      if (!sk) return;

      if (wrap.dataset.skeleton === 'chart') {
        const canvas = wrap.querySelector('canvas');
        if (canvas && canvas.getAttribute('data-chart-ready') === '1') {
          revealSkeleton(wrap);
          return;
        }
        if (canvas) {
          const obs = new MutationObserver(() => {
            if (canvas.getAttribute('data-chart-ready') === '1') {
              obs.disconnect();
              setTimeout(() => revealSkeleton(wrap), 120);
            }
          });
          obs.observe(canvas, { attributes: true, attributeFilter: ['data-chart-ready'] });
        }
        setTimeout(() => revealSkeleton(wrap), 5000);
      } else {
        requestAnimationFrame(() => setTimeout(() => revealSkeleton(wrap), 280));
      }
    });

    document.body.classList.remove('ft-is-loading');
  }

  /* ——— Toasts ——— */
  function showToast(message, opts = {}) {
    const host = document.getElementById('ftToastHost');
    if (!host) return;
    const el = document.createElement('div');
    el.className = 'ft-toast' + (opts.type ? ` ft-toast--${opts.type}` : '');
    el.innerHTML =
      (opts.icon ? `<span class="ft-toast__icon">${opts.icon}</span>` : '') +
      `<span class="ft-toast__msg">${message}</span>`;
    if (opts.actionLabel && typeof opts.onAction === 'function') {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ft-toast__action';
      btn.textContent = opts.actionLabel;
      btn.addEventListener('click', () => {
        opts.onAction();
        el.remove();
      });
      el.appendChild(btn);
    }
    host.appendChild(el);
    requestAnimationFrame(() => el.classList.add('ft-toast--visible'));
    if (!opts.persistent) {
      setTimeout(() => {
        el.classList.remove('ft-toast--visible');
        setTimeout(() => el.remove(), 300);
      }, opts.duration || 3200);
    }
  }

  /* ——— Temporizador de descanso ——— */
  let restTimerId = null;
  let restRemaining = 0;

  function formatRest(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s} s`;
  }

  function closeRestOverlay() {
    const overlay = document.getElementById('ftRestOverlay');
    if (overlay) overlay.hidden = true;
    if (restTimerId) {
      clearInterval(restTimerId);
      restTimerId = null;
    }
  }

  function startRestTimer(seconds, label) {
    if (!seconds || seconds <= 0) return;
    const overlay = document.getElementById('ftRestOverlay');
    const display = document.getElementById('ftRestTime');
    const sub = document.getElementById('ftRestSub');
    if (!overlay || !display) return;

    restRemaining = seconds;
    display.textContent = formatRest(restRemaining);
    if (sub) sub.textContent = label ? `Descanso · ${label}` : 'Descanso entre series';
    overlay.hidden = false;

    if (restTimerId) clearInterval(restTimerId);
    restTimerId = setInterval(() => {
      restRemaining -= 1;
      display.textContent = formatRest(Math.max(0, restRemaining));
      if (restRemaining <= 0) {
        closeRestOverlay();
        showToast('¡Descanso terminado! Siguiente ejercicio 💪', { icon: '⏱️' });
        if (navigator.vibrate) navigator.vibrate(200);
      }
    }, 1000);
  }

  function bindRestOverlay() {
    const skip = document.getElementById('ftRestSkip');
    if (skip) skip.addEventListener('click', closeRestOverlay);
    const overlay = document.getElementById('ftRestOverlay');
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeRestOverlay();
      });
    }
  }

  /* ——— Marcar ejercicio (AJAX) ——— */
  function updateTrainUI(data) {
    const bar = document.querySelector('[data-train-progress]');
    if (bar) bar.style.width = `${data.pct}%`;
    const pctEl = document.querySelector('[data-train-pct]');
    if (pctEl) pctEl.textContent = `${data.pct}% completado`;
    const countEl = document.querySelector('[data-train-count]');
    if (countEl) countEl.textContent = `${data.hechos} de ${data.total} ejercicios`;
    const metaCount = document.querySelector('[data-train-meta-count]');
    if (metaCount) metaCount.textContent = `${data.hechos}/${data.total} pasos`;

    document.querySelectorAll('.ft-workout-item[data-ej-index]').forEach((li) => {
      const idx = parseInt(li.getAttribute('data-ej-index'), 10);
      li.classList.toggle('ft-workout-item--done', idx < data.hechos);
    });

    const btn = document.getElementById('btnMarcarEjercicio');
    if (btn) {
      if (data.completado) {
        btn.textContent = '✓ Sesión completada';
        btn.disabled = true;
      }
    }
  }

  function bindMarcarEjercicio() {
    const form = document.getElementById('formMarcarEjercicio');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      if (btn?.disabled) return;
      if (btn) btn.disabled = true;

      try {
        const res = await fetch(form.action, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json',
          },
        });
        if (!res.ok) {
          throw new Error('bad status');
        }
        const data = await res.json();
        if (!data.ok) {
          showToast(data.error || 'No se pudo marcar', { type: 'warn', icon: '⚠️' });
          if (btn) btn.disabled = false;
          return;
        }

        updateTrainUI(data);

        if (data.completado) {
          showToast('¡Sesión de hoy completada! 🔥', { icon: '✓', type: 'success', duration: 4000 });
        } else {
          showToast('¡Ejercicio completado!', {
            icon: '✓',
            type: 'success',
            duration: data.descanso_seg > 0 ? 5000 : 3200,
            actionLabel: data.descanso_seg > 0 ? `Descanso ${data.descanso}` : null,
            onAction: data.descanso_seg > 0
              ? () => startRestTimer(data.descanso_seg, data.descanso)
              : null,
          });
          if (data.descanso_seg > 0 && form.dataset.autoRest === '1') {
            setTimeout(() => startRestTimer(data.descanso_seg, data.descanso), 600);
          }
        }
        if (btn && !data.completado) btn.disabled = false;
      } catch (err) {
        showToast('Error de conexión. Intenta de nuevo.', { type: 'warn', icon: '⚠️' });
        if (btn) btn.disabled = false;
      }
    });
  }

  /* ——— Agua ——— */
  function updateWaterUI(vasos, meta, pct) {
    document.querySelectorAll('[data-water-count]').forEach((el) => {
      el.textContent = vasos;
    });
    document.querySelectorAll('[data-water-meta]').forEach((el) => {
      el.textContent = meta;
    });
    document.querySelectorAll('[data-water-pct]').forEach((el) => {
      el.textContent = `${pct}%`;
    });
    document.querySelectorAll('[data-water-bar]').forEach((el) => {
      el.style.width = `${pct}%`;
    });
    document.querySelectorAll('.ft-water-glass').forEach((g, i) => {
      g.classList.toggle('ft-water-glass--filled', i < vasos);
    });
  }

  function bindAgua() {
    document.querySelectorAll('[data-agua-add]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (!usuarioId) return;
        btn.disabled = true;
        try {
          const body = new FormData();
          body.append('accion', 'vaso');
          const res = await fetch(`/usuario/${usuarioId}/agua`, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body,
          });
          const data = await res.json();
          if (data.ok) {
            updateWaterUI(data.vasos, data.meta, data.pct);
            showToast('Vaso registrado 💧', { icon: '💧', duration: 2000 });
          }
        } catch (e) {
          showToast('No se pudo registrar', { type: 'warn' });
        }
        btn.disabled = false;
      });
    });
  }

  /* ——— Chart helper ——— */
  function markChartReady(canvas) {
    if (!canvas) return;
    canvas.setAttribute('data-chart-ready', '1');
    const wrap = canvas.closest('[data-skeleton="chart"]');
    if (wrap) revealSkeleton(wrap);
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('ft-is-loading');
    initSkeletons();
    bindRestOverlay();
    bindMarcarEjercicio();
    bindAgua();
  });

  window.FitnessUI = { showToast, startRestTimer, closeRestOverlay, markChartReady, updateWaterUI };
})();
