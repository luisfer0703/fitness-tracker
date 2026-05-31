# Publicar Fitness Tracker gratis (Render + PWA)

Guía paso a paso **sin pagar**. Usa [Render](https://render.com) plan **Free**: HTTPS incluido, ideal para PWA, iPhone y Android.

---

## Antes de empezar

- Cuenta en [GitHub](https://github.com) (gratis)
- Cuenta en [Render](https://render.com) (gratis; puede pedir tarjeta solo para verificar, **no cobra** en plan Free)
- Tu archivo `.env` local con las claves VAPID (no lo subas a GitHub)

---

## Paso 1 — Probar en tu PC

```powershell
cd "d:\Mis Documentos\Semestre 10\Proyecto Integral de Ingeniería en Software\entrenador_inteligente"

# Instalar dependencias
pip install -r requirements.txt

# Migrar datos viejos (solo si ya tenías database.db en la raíz)
if (Test-Path database.db) {
  New-Item -ItemType Directory -Force -Path data\profile_pics | Out-Null
  Move-Item -Force database.db data\database.db
}
if (Test-Path static\profile_pics\*) {
  Copy-Item static\profile_pics\* data\profile_pics\ -ErrorAction SilentlyContinue
}

# Probar como en producción (Windows: usa run_local.py; Gunicorn solo funciona en Linux)
python run_local.py
```

Abre http://127.0.0.1:5000 y verifica que todo funciona. Cierra con `Ctrl+C`.

> **Nota Windows:** `gunicorn` falla con `No module named 'fcntl'` — es normal. En Render (Linux) sí funciona. En tu PC usa `python run_local.py` o `python app.py`.

---

## Paso 2 — Subir el código a GitHub

1. Crea un repositorio nuevo en GitHub (ejemplo: `fitness-tracker`). **Público** o privado, da igual para Render free.

2. En PowerShell, dentro del proyecto:

```powershell
git init
git add .
git commit -m "Preparar despliegue en Render"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/fitness-tracker.git
git push -u origin main
```

> **Importante:** `.env` y `data/database.db` están en `.gitignore` y **no se suben**.

---

## Paso 3 — Crear el servicio en Render (gratis)

1. Entra a https://dashboard.render.com
2. **New +** → **Blueprint** (si ves `render.yaml` en el repo) **o** **Web Service**
3. Conecta tu cuenta de GitHub y elige el repositorio

### Si usas Web Service manual

| Campo | Valor |
|-------|--------|
| **Name** | `fitness-tracker` |
| **Region** | Oregon (US West) o el más cercano |
| **Branch** | `main` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -w 1 -b 0.0.0.0:$PORT wsgi:application` |
| **Plan** | **Free** |

---

## Paso 4 — Variables de entorno en Render

En tu servicio → **Environment** → **Add Environment Variable**:

| Variable | Valor |
|----------|--------|
| `DATA_DIR` | `/opt/render/project/src/data` |
| `SECRET_KEY` | Genera una clave larga (ver abajo) |
| `VAPID_PUBLIC_KEY` | Copia de tu `.env` local |
| `VAPID_PRIVATE_KEY` | Copia de tu `.env` local |
| `VAPID_CLAIM_EMAIL` | `mailto:tu-email@gmail.com` |

Generar `SECRET_KEY` en PowerShell:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Pulsa **Save Changes**. Render redesplegará solo.

---

## Paso 5 — Esperar el despliegue

1. Pestaña **Logs**: debe aparecer algo como `Listening at: 0.0.0.0:10000`
2. Arriba verás la URL: `https://fitness-tracker-xxxx.onrender.com`
3. Abre esa URL en el navegador

### Plan Free: qué esperar

- Tras **~15 min sin visitas**, el servidor se duerme
- La **primera visita** puede tardar **30–60 segundos** en despertar
- Los datos en `data/` **se mantienen** entre reinicios
- Los datos **se pierden** si haces un **nuevo deploy** desde GitHub (vuelves a crear usuarios)

---

## Paso 6 — Instalar en el móvil (PWA)

### iPhone (Safari)

1. Abre tu URL `https://....onrender.com` en **Safari**
2. Botón **Compartir** (cuadrado con flecha)
3. **Añadir a pantalla de inicio**
4. Abre la app desde el icono

### Android (Chrome)

1. Abre la URL en Chrome
2. Menú **⋮** → **Instalar aplicación** o **Añadir a pantalla de inicio**

---

## Paso 7 — Probar todas las funciones

Usa la URL pública (no la IP local):

- [ ] Crear usuario y foto de perfil
- [ ] Inicio, entrenar, marcar ejercicios, temporizador
- [ ] Nutrición e historial
- [ ] Progreso y gráfica de peso
- [ ] Pasos y agua
- [ ] Modo oscuro / claro
- [ ] Editar perfil → **Activar notificaciones** → **Enviar notificación de prueba**

### Notificaciones push

- **Android:** funcionan en Chrome o con la PWA instalada
- **iPhone:** solo si instalaste la app en pantalla de inicio (iOS 16.4+) y aceptaste permisos
- Debes tener las 3 variables VAPID en Render

---

## Paso 8 — Actualizar la app después

```powershell
git add .
git commit -m "Descripción del cambio"
git push
```

Render redespliega solo. **Nota:** en plan free un nuevo deploy puede resetear la carpeta `data/`; haz copia de usuarios de prueba si los necesitas.

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| Error 502 al abrir | Espera 1 min; revisa **Logs** en Render |
| Push no funciona | Revisa VAPID en Environment; en iPhone instala PWA desde Safari |
| Fotos no se ven | Comprueba que `DATA_DIR` esté configurado |
| App muy lenta al entrar | Normal en plan Free (servidor dormido) |
| `ModuleNotFoundError` | Verifica que `requirements.txt` esté en el repo |

---

## Resumen rápido

1. `pip install -r requirements.txt` → probar con `gunicorn`
2. Subir a GitHub (sin `.env`)
3. Render → Web Service → plan **Free**
4. Variables: `DATA_DIR`, `SECRET_KEY`, VAPID × 3
5. Abrir URL HTTPS → instalar en móvil → probar push

¡Listo! Tu Fitness Tracker queda en internet gratis.
