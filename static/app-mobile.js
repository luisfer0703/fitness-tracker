/**
 * Móvil: Web Push (recordatorios).
 */
(function () {
  const root = document.documentElement;
  const usuarioId = root.dataset.usuarioId;
  const vapidKey = root.dataset.vapidKey;

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; ++i) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return null;
    try {
      return await navigator.serviceWorker.register('/sw.js', { scope: '/' });
    } catch (e) {
      console.warn('SW no registrado', e);
      return null;
    }
  }

  async function subscribePush() {
    if (!usuarioId || !vapidKey) return false;
    const reg = await registerServiceWorker();
    if (!reg || !('PushManager' in window)) return false;

    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      });
    }

    const res = await fetch(`/api/usuario/${usuarioId}/push/subscribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub.toJSON()),
    });
    return res.ok;
  }

  function bindPushButton() {
    const btn = document.getElementById('btnActivarPush');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      if (!vapidKey) {
        alert('Configura VAPID_PUBLIC_KEY y VAPID_PRIVATE_KEY en el archivo .env del servidor.');
        return;
      }
      if (Notification.permission === 'denied') {
        alert('Las notificaciones están bloqueadas. Actívalas en ajustes del navegador.');
        return;
      }
      const perm = await Notification.requestPermission();
      if (perm !== 'granted') return;
      const ok = await subscribePush();
      alert(
        ok
          ? 'Notificaciones activadas. Recibirás recordatorios a la hora configurada.'
          : 'No se pudo activar. Revisa la configuración del servidor.'
      );
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    registerServiceWorker();
    bindPushButton();
  });

  window.FitnessTracker = { subscribePush };
})();
