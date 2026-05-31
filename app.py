from flask import Flask, render_template, request, redirect, url_for, abort, flash, jsonify, send_from_directory
import os
import random
import shutil
import sqlite3
from datetime import datetime, date, timedelta
from collections import defaultdict
import numpy as np
from sklearn.linear_model import LinearRegression
from contextlib import contextmanager
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(DATA_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "profile_pics")
LEGACY_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "profile_pics")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

from services.user_context import (
    fecha_hoy_formateada,
    primer_nombre,
    calcular_streak,
    estimar_stats_diarias,
    plan_del_dia,
    progreso_semanal_chart,
    entrenos_recientes,
)
from services.routine_builder import armar_dia_ejercicios, duracion_estimada_min
from services.nutrition_foods import alimentos_recomendados, comidas_del_dia
from services.training_history import build_historial, obtener_registros_entreno
from services.steps import (
    obtener_pasos_hoy,
    guardar_pasos,
    stats_con_pasos,
    meta_pasos_usuario,
)
from services.water import (
    obtener_agua_hoy,
    guardar_vasos,
    agregar_vaso,
    meta_vasos_usuario,
)
from services import push_notifications as push_svc

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-solo-local-cambia-en-produccion")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para conectar a la base de datos (context manager para cerrar siempre)
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Crear tablas si no existen y migrar columnas de rutina
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                edad INTEGER,
                peso_actual REAL,
                estatura REAL,
                objetivo_peso REAL,
                foto_perfil TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sexo TEXT,
                actividad TEXT,
                rutina_inicio TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_peso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                peso REAL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN quiere_rutina INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN dias_rutina INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN tipo_entreno TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN sexo TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN actividad TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN rutina_inicio TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progreso_entreno (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                ejercicios_hechos INTEGER DEFAULT 0,
                UNIQUE(usuario_id, fecha),
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                rol TEXT NOT NULL,
                texto TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_pasos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                pasos INTEGER NOT NULL,
                fuente TEXT DEFAULT 'manual',
                UNIQUE(usuario_id, fecha),
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_agua (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                vasos INTEGER NOT NULL DEFAULT 0,
                UNIQUE(usuario_id, fecha),
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL UNIQUE,
                subscription_json TEXT NOT NULL,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
        for col, sql in [
            ("recordatorio_hora", "ALTER TABLE usuarios ADD COLUMN recordatorio_hora TEXT DEFAULT '09:00'"),
            ("recordatorio_activo", "ALTER TABLE usuarios ADD COLUMN recordatorio_activo INTEGER DEFAULT 0"),
            ("meta_pasos", "ALTER TABLE usuarios ADD COLUMN meta_pasos INTEGER"),
        ]:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass
        conn.commit()
    _migrate_legacy_profile_pics()


def _migrate_legacy_profile_pics():
    """Copia fotos antiguas de static/profile_pics → data/profile_pics."""
    if not os.path.isdir(LEGACY_UPLOAD_FOLDER):
        return
    for name in os.listdir(LEGACY_UPLOAD_FOLDER):
        if name.startswith("."):
            continue
        src = os.path.join(LEGACY_UPLOAD_FOLDER, name)
        dst = os.path.join(UPLOAD_FOLDER, name)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)


def _profile_pic_folder(filename):
    primary = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(primary):
        return app.config["UPLOAD_FOLDER"]
    legacy = os.path.join(LEGACY_UPLOAD_FOLDER, filename)
    if os.path.isfile(legacy):
        return LEGACY_UPLOAD_FOLDER
    return app.config["UPLOAD_FOLDER"]


@app.context_processor
def inject_media_helpers():
    def foto_perfil_src(filename):
        if not filename:
            return ""
        return url_for("profile_pic", filename=filename)

    return dict(foto_perfil_src=foto_perfil_src)


@app.route("/media/profile/<path:filename>")
def profile_pic(filename):
    folder = _profile_pic_folder(filename)
    return send_from_directory(folder, filename)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


def _float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value):
    if value is None:
        return None
    s = str(value)
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def generar_rutina(usuario, imc, dias_rutina, tipo_entreno_raw, semana=1):
    """
    Genera una rutina simple y adaptada a los datos del usuario.
    No se guarda en base de datos: se calcula cada vez que se entra al dashboard.
    """
    dias_rutina = dias_rutina or 3
    if dias_rutina < 2:
        dias_rutina = 2
    if dias_rutina > 7:
        dias_rutina = 7
    if semana < 1:
        semana = 1
    if semana > 4:
        semana = 4

    tipo_entreno = tipo_entreno_raw or "mixto"

    peso_actual = usuario["peso_actual"]
    peso_objetivo = usuario["objetivo_peso"]

    objetivo = "mantener"
    if peso_actual and peso_objetivo:
        if peso_objetivo < peso_actual - 1:
            objetivo = "bajar"
        elif peso_objetivo > peso_actual + 1:
            objetivo = "subir"

    # Determinar enfoque principal según IMC y objetivo
    enfoque_cardio_intenso = False
    enfoque_fuerza = True
    if imc:
        if imc >= 30 or (objetivo == "bajar" and imc >= 27):
            enfoque_cardio_intenso = True
            enfoque_fuerza = False
        elif objetivo == "subir":
            enfoque_fuerza = True

    # Selección anti-repetición: rotar ejercicios por patrones y evitar duplicados
    ejercicios_base = {
        "gym": {
            "push": [
                "Press banca o mancuernas 3x8-10",
                "Press inclinado mancuernas 3x10",
                "Fondos asistidos 3x8-10",
                "Press militar 3x8-10",
                "Elevaciones laterales 3x12-15",
                "Extensión tríceps en polea 3x12",
            ],
            "pull": [
                "Jalón al pecho 3x10-12",
                "Remo con barra o polea 3x10-12",
                "Remo a una mano 3x10 por lado",
                "Face pulls 3x12-15",
                "Curl bíceps 3x12",
                "Curl martillo 3x12",
            ],
            "legs": [
                "Sentadilla o prensa 3x8-10",
                "Peso muerto rumano 3x10",
                "Zancadas caminando 3x10 por pierna",
                "Extensión de cuádriceps 3x12",
                "Curl femoral 3x12",
                "Elevación de talones (gemelos) 3x15-20",
            ],
            "full": [
                "Sentadilla goblet 3x10",
                "Press banca mancuernas 3x10",
                "Remo con mancuernas 3x10",
                "Peso muerto rumano ligero 3x12",
                "Pallof press (cable) 3x12 por lado",
            ],
            "cardio": [
                "Cinta caminata rápida 25-35 min",
                "Elíptica suave 20-30 min",
                "Bicicleta estática 20-30 min",
                "Remo ergómetro 10-15 min (suave)",
            ],
            "core_movil": [
                "Plancha frontal 3x30-45s",
                "Plancha lateral 3x25-35s por lado",
                "Dead bug 3x10 por lado",
                "Crunch en colchoneta 3x15",
                "Estiramientos dinámicos 6-10 min",
            ],
        },
        "casa": {
            "push": [
                "Flexiones 3x8-12",
                "Flexiones diamante 3x6-10",
                "Pike push-ups 3x6-10",
                "Flexiones con pausa (1 s abajo) 3x6-10",
                "Fondos de tríceps en el suelo (reverse plank) 3x10-12",
            ],
            "pull": [
                "Reverse snow angels 3x10-12",
                "Y-T-W en el suelo 2x8-10",
                "Superman (con pausa 1 s) 3x10-12",
                "Remo isométrico (aprieta escápulas 2 s) 3x12",
            ],
            "legs": [
                "Sentadillas al aire 3x12-18",
                "Zancadas estáticas 3x10-12 por pierna",
                "Puente de glúteo 3x15-20",
                "Buenos días sin peso (cadera atrás) 3x12-15",
                "Elevación de talones (gemelos) 3x20-25",
            ],
            "full": [
                "Flexiones 3x8-12",
                "Sentadillas al aire 3x12-18",
                "Zancadas alternas 3x8-10 por pierna",
                "Puente de glúteo 3x15",
                "Plancha 3x25-40s",
            ],
            "cardio": [
                "Marcha en el sitio 25-35 min",
                "Sombra (boxeo en el sitio) 15-20 min",
                "Cuerda imaginaria 12-18 min",
                "Circuito en el lugar (jumping jacks + mountain climbers) 12-18 min",
                "Rodillas altas en el sitio 12-15 min",
                "Burpees moderados (circuito) 10-15 min",
            ],
            "core_movil": [
                "Plancha frontal 3x25-40s",
                "Plancha lateral 3x20-30s por lado",
                "Dead bug 3x10 por lado",
                "Bird-dog 3x10 por lado",
                "Movilidad de cadera y columna 6-10 min",
            ],
        },
    }

    if tipo_entreno == "gym":
        fuente = ejercicios_base["gym"]
    elif tipo_entreno == "casa":
        fuente = ejercicios_base["casa"]
    else:
        # mixto: combinar (fuerza de gym, cardio/core de casa)
        fuente = {
            "push": ejercicios_base["gym"]["push"],
            "pull": ejercicios_base["gym"]["pull"],
            "legs": ejercicios_base["gym"]["legs"],
            "full": ejercicios_base["casa"]["full"],
            "cardio": ejercicios_base["casa"]["cardio"],
            "core_movil": ejercicios_base["casa"]["core_movil"],
        }

    rng = random.Random()
    seed = (usuario["id"] if "id" in usuario.keys() else 0) + int((usuario["edad"] or 0) * 7) + (semana * 101)
    rng.seed(seed)

    def pick(pool, k, used):
        pool = list(pool)
        rng.shuffle(pool)
        chosen = []
        for item in pool:
            if item in used:
                continue
            chosen.append(item)
            used.add(item)
            if len(chosen) >= k:
                break
        # si se agotó el pool sin llegar a k, permitir repetir lo mínimo
        if len(chosen) < k:
            for item in pool:
                if item not in chosen:
                    chosen.append(item)
                if len(chosen) >= k:
                    break
        return chosen

    rutina_dias = []
    used = set()

    if dias_rutina >= 6:
        focos = [
            ("Día 1", "Push (pecho/hombro/tríceps)", ["push"]),
            ("Día 2", "Pull (espalda/bíceps)", ["pull"]),
            ("Día 3", "Pierna", ["legs"]),
            ("Día 4", "Cardio + core", ["cardio", "core_movil"]),
            ("Día 5", "Full body", ["full"]),
            ("Día 6", "Cardio suave / movilidad", ["cardio", "core_movil"]),
            ("Día 7", "Full body (ligero)", ["full", "core_movil"]),
        ]
    elif dias_rutina == 5:
        focos = [
            ("Día 1", "Push (pecho/hombro/tríceps)", ["push"]),
            ("Día 2", "Pull (espalda/bíceps)", ["pull"]),
            ("Día 3", "Pierna", ["legs"]),
            ("Día 4", "Cardio + core", ["cardio", "core_movil"]),
            ("Día 5", "Full body", ["full"]),
        ]
    elif dias_rutina == 4:
        focos = [
            ("Día 1", "Full body", ["full"]),
            ("Día 2", "Push + core", ["push", "core_movil"]),
            ("Día 3", "Pull + core", ["pull", "core_movil"]),
            ("Día 4", "Pierna + cardio suave", ["legs", "cardio"]),
        ]
    elif dias_rutina == 3:
        focos = [
            ("Día 1", "Full body", ["full"]),
            ("Día 2", "Cardio + core", ["cardio", "core_movil"]),
            ("Día 3", "Full body (variación)", ["full"]),
        ]
    else:
        focos = [
            ("Día 1", "Full body", ["full"]),
            ("Día 2", "Cardio + core", ["cardio", "core_movil"]),
        ]

    for idx, (titulo, enfoque, grupos) in enumerate(focos, start=1):
        if idx > dias_rutina:
            break
        lista_ejercicios = []

        for g in grupos:
            pool = fuente.get(g, [])
            if not pool:
                continue

            if g in ("cardio",):
                k = 1 if not enfoque_cardio_intenso else 2
            elif g in ("core_movil",):
                k = 2
            elif g in ("full",):
                k = 5
            elif g in ("legs", "push", "pull"):
                k = 5
            else:
                k = 4
            lista_ejercicios.extend(pick(pool, k, used))

        if enfoque_cardio_intenso and "Cardio" in enfoque:
            enfoque_mensaje = enfoque + " (prioriza mantener ritmo que puedas sostener)"
        elif objetivo == "subir" and "Fuerza" in enfoque:
            enfoque_mensaje = enfoque + " (prioriza aumentar peso de forma progresiva)"
        else:
            enfoque_mensaje = enfoque

        prog = {
            1: "Semana 1: técnica y control (RPE 6-7)",
            2: "Semana 2: +1 serie en 1-2 ejercicios principales (RPE 7)",
            3: "Semana 3: intenta progresar carga/reps (RPE 7-8)",
            4: "Semana 4: consolidación (mantén cargas, cuida forma)",
        }[semana]

        ejercicios_dia = armar_dia_ejercicios(
            lista_ejercicios, grupos, objetivo, enfoque_cardio_intenso, tipo_entreno=tipo_entreno
        )
        rutina_dias.append(
            {
                "titulo": titulo,
                "enfoque": enfoque_mensaje,
                "ejercicios": ejercicios_dia,
                "progresion": prog,
                "duracion_min": duracion_estimada_min(ejercicios_dia),
            }
        )

    if objetivo == "bajar":
        consejo = "Tu objetivo principal es reducir peso: intenta cumplir la mayoría de los días de cardio y cuida especialmente la alimentación."
    elif objetivo == "subir":
        consejo = "Tu objetivo principal es ganar peso: enfócate en fuerza, progresa en cargas y asegúrate de comer suficiente proteína y calorías."
    else:
        consejo = "Tu objetivo es mantenerte: sé constante con los entrenamientos y mantén hábitos de sueño y alimentación estables."

    if enfoque_cardio_intenso:
        consejo += " Debido a tu IMC actual, prioriza el cardio a intensidad moderada y escucha siempre a tu cuerpo."

    return rutina_dias, consejo


def _nombre_ejercicio(ej):
    if isinstance(ej, dict):
        return ej.get("nombre", "")
    return str(ej)


@app.route("/")
def index():
    with get_db_connection() as conn:
        usuarios = conn.execute("SELECT * FROM usuarios").fetchall()
    return render_template("index.html", usuarios=usuarios)

@app.route("/crear_usuario", methods=["POST"])
def crear_usuario():
    nombre = (request.form.get("nombre") or "").strip()
    if not nombre:
        flash("El nombre es obligatorio.", "warning")
        return redirect(url_for("index"))
    edad = _int(request.form.get("edad"), 0)
    peso_actual = _float(request.form.get("peso_actual"))
    estatura = _float(request.form.get("estatura"))
    objetivo_peso = _float(request.form.get("objetivo_peso"))
    if peso_actual is None or estatura is None or objetivo_peso is None:
        flash("Completa todos los campos numéricos antes de guardar.", "warning")
        return redirect(url_for("index"))
    if not (0.5 <= estatura <= 2.5 and 20 <= peso_actual <= 300 and 20 <= objetivo_peso <= 300):
        flash("Revisa los rangos: estatura 0.5–2.5 m y peso 20–300 kg.", "warning")
        return redirect(url_for("index"))

    quiere_rutina = 1 if request.form.get("quiere_rutina") == "1" else 0
    dias_rutina = _int(request.form.get("dias_rutina")) if quiere_rutina else None
    if quiere_rutina and (dias_rutina is None or not (1 <= dias_rutina <= 7)):
        dias_rutina = 3
    tipo_entreno = None
    if quiere_rutina:
        raw = (request.form.get("tipo_entreno") or "").strip()
        if raw in ("gym", "casa", "mixto"):
            tipo_entreno = raw

    sexo = (request.form.get("sexo") or "").strip()
    if sexo not in ("m", "f", "x", ""):
        sexo = ""
    actividad = (request.form.get("actividad") or "").strip()
    if actividad not in ("baja", "media", "alta", ""):
        actividad = ""

    rutina_inicio = datetime.utcnow().isoformat(timespec="seconds") if quiere_rutina else None

    # Foto de perfil (opcional)
    foto_perfil_filename = None
    file = request.files.get("foto_perfil")
    if file and file.filename:
        filename = secure_filename(file.filename)
        if _allowed_file(filename):
            base, ext = os.path.splitext(filename)
            unique_name = f"{nombre.lower().replace(' ', '_')}_{edad or 'na'}_{abs(hash(filename)) % 100000}{ext.lower()}"
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)
            foto_perfil_filename = unique_name
        else:
            flash("La foto debe ser PNG/JPG/JPEG/GIF.", "warning")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (nombre, edad, peso_actual, estatura, objetivo_peso, quiere_rutina, dias_rutina, tipo_entreno, foto_perfil, sexo, actividad, rutina_inicio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre, edad, peso_actual, estatura, objetivo_peso, quiere_rutina, dias_rutina, tipo_entreno, foto_perfil_filename, sexo or None, actividad or None, rutina_inicio))
        usuario_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO registros_peso (usuario_id, peso) VALUES (?, ?)",
            (usuario_id, peso_actual),
        )
        conn.commit()
    flash("Usuario creado correctamente.", "success")
    return redirect(url_for("dashboard", usuario_id=usuario_id))


def _get_progreso_hoy(conn, usuario_id):
    hoy = date.today().isoformat()
    row = conn.execute(
        "SELECT ejercicios_hechos FROM progreso_entreno WHERE usuario_id=? AND fecha=?",
        (usuario_id, hoy),
    ).fetchone()
    return int(row["ejercicios_hechos"]) if row else 0


def build_usuario_context(usuario_id):
    with get_db_connection() as conn:
        usuario = conn.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    if not usuario:
        return None, None

    with get_db_connection() as conn:
        registros = conn.execute(
            "SELECT * FROM registros_peso WHERE usuario_id=? ORDER BY fecha",
            (usuario_id,),
        ).fetchall()
        ejercicios_hechos = _get_progreso_hoy(conn, usuario_id)
        pasos_hoy, pasos_fuente = obtener_pasos_hoy(conn, usuario_id)
        vasos_hoy = obtener_agua_hoy(conn, usuario_id)
        progreso_por_dia = obtener_registros_entreno(conn, usuario_id)
        hoy_semana = date.today()
        lunes_semana = hoy_semana - timedelta(days=hoy_semana.weekday())
        domingo_semana = lunes_semana + timedelta(days=6)
        pasos_semana_rows = conn.execute(
            """
            SELECT fecha, pasos FROM registros_pasos
            WHERE usuario_id=? AND fecha >= ? AND fecha <= ?
            """,
            (usuario_id, lunes_semana.isoformat(), domingo_semana.isoformat()),
        ).fetchall()
        pasos_por_dia = {r["fecha"]: int(r["pasos"]) for r in pasos_semana_rows}
    fechas = [r["fecha"] for r in registros]
    pesos = [r["peso"] for r in registros]
    peso_actual = pesos[-1] if pesos else usuario["peso_actual"]

    weekly, alerts = [], []
    if registros:
        by_week = defaultdict(list)
        for r in registros:
            dt = _parse_dt(r["fecha"])
            if not dt:
                continue
            y, w, _ = dt.isocalendar()
            by_week[(y, w)].append(float(r["peso"]))
        for (y, w) in sorted(by_week.keys()):
            ws = by_week[(y, w)]
            weekly.append({"label": f"{y}-W{w:02d}", "avg": sum(ws) / len(ws), "min": min(ws), "max": max(ws), "n": len(ws)})
        if len(weekly) >= 2:
            delta = weekly[-1]["avg"] - weekly[-2]["avg"]
            if abs(delta) >= 0.7:
                alerts.append(f"Cambio notable esta semana: {delta:+.1f} kg vs la semana anterior.")
        if len(weekly) >= 3:
            a, b, c = weekly[-3]["avg"], weekly[-2]["avg"], weekly[-1]["avg"]
            if a < b < c:
                alerts.append("Tendencia: llevas 3 semanas subiendo de peso.")
            if a > b > c:
                alerts.append("Tendencia: llevas 3 semanas bajando de peso.")

    imc = categoria_imc = recomendacion = None
    estatura = usuario["estatura"]
    if estatura and peso_actual:
        imc = peso_actual / (estatura ** 2)
        if imc < 18.5:
            categoria_imc, recomendacion = "Bajo peso", "Tu IMC indica bajo peso. Aumenta ingesta y entrena fuerza."
        elif imc < 25:
            categoria_imc, recomendacion = "Peso normal", "Tu IMC está en rango saludable. Mantén hábitos constantes."
        elif imc < 30:
            categoria_imc, recomendacion = "Sobrepeso", "Tu IMC indica sobrepeso. Actividad constante y déficit moderado."
        else:
            categoria_imc, recomendacion = "Obesidad", "Tu IMC indica obesidad. Plan progresivo de ejercicio y alimentación."

    mensaje_entrenador = "Registra tu peso semanalmente. Con dos o más registros analizo tu evolución."
    semanas_objetivo = progreso = None
    predicciones = []
    if len(pesos) >= 2:
        X = np.array(range(len(pesos))).reshape(-1, 1)
        y = np.array(pesos)
        modelo = LinearRegression().fit(X, y)
        pendiente = modelo.coef_[0]
        peso_objetivo = usuario["objetivo_peso"]
        peso_inicial = usuario["peso_actual"]
        diff_meta = abs(peso_objetivo - peso_inicial)
        if diff_meta > 0:
            if peso_objetivo < peso_inicial:
                progreso = (peso_inicial - peso_actual) / diff_meta * 100
            else:
                progreso = (peso_actual - peso_inicial) / diff_meta * 100
            progreso = max(0, min(100, progreso))
        if pendiente < -0.01 and peso_actual > peso_objetivo:
            sem = (peso_objetivo - peso_actual) / pendiente
            if sem > 0:
                semanas_objetivo = int(sem)
        if pendiente < -0.15:
            mensaje_entrenador = "¡Increíble! Tu peso va en la dirección correcta. Sigue con constancia."
        elif pendiente < -0.05:
            mensaje_entrenador = "Muy buen progreso. Pérdida saludable; revisa porciones si quieres acelerar."
        elif pendiente < 0:
            mensaje_entrenador = "Vas bien: bajas lentamente. Suma un día de ejercicio o ajusta calorías con cuidado."
        elif pendiente > 0.1:
            mensaje_entrenador = "Tu peso sube. Revisa alimentación y frecuencia de entrenamiento."
        elif pendiente > 0:
            mensaje_entrenador = "Ligera subida; es normal. Mantén hábitos y vuelve a registrar pronto."
        else:
            mensaje_entrenador = "Peso estable. Si tu meta es bajar, aumenta actividad o ajusta dieta."
        futuro = list(range(len(pesos) + 4))
        predicciones = modelo.predict(np.array(futuro).reshape(-1, 1)).tolist()
        fechas = fechas + ["S+1", "S+2", "S+3", "S+4"]

    actividad = usuario["actividad"] if "actividad" in usuario.keys() else None
    objetivo_peso = usuario["objetivo_peso"]
    kcal_base = kcal_objetivo = proteina_g = nutri_nota = None
    if peso_actual:
        factor = {"baja": 28.0, "media": 30.5, "alta": 33.0}.get(actividad or "", 30.0)
        kcal_base = int(round(peso_actual * factor))
        if objetivo_peso and objetivo_peso < peso_actual - 1:
            kcal_objetivo = max(1200, kcal_base - 350)
            nutri_nota = "Déficit moderado para perder peso."
        elif objetivo_peso and objetivo_peso > peso_actual + 1:
            kcal_objetivo = kcal_base + 250
            nutri_nota = "Superávit ligero para ganar peso/masa."
        else:
            kcal_objetivo = kcal_base
            nutri_nota = "Mantenimiento: constancia y calidad alimentaria."
        prot = 1.8 if objetivo_peso and objetivo_peso > peso_actual + 1 else 1.6
        proteina_g = int(round(peso_actual * prot))

    tipo_entreno_raw = usuario["tipo_entreno"] if "tipo_entreno" in usuario.keys() else None
    tipo_entreno_label = {"gym": "Gimnasio", "casa": "En casa", "mixto": "Mixto"}.get(tipo_entreno_raw or "", "")
    quiere_rutina = usuario["quiere_rutina"] if "quiere_rutina" in usuario.keys() else 0
    dias_rutina = usuario["dias_rutina"] if "dias_rutina" in usuario.keys() else None
    tiene_rutina = quiere_rutina and (dias_rutina or tipo_entreno_raw)

    rutina_dias, rutina_consejo, rutina_plan, semana_actual = [], None, [], 1
    if tiene_rutina:
        inicio = _parse_dt(usuario["rutina_inicio"]) if "rutina_inicio" in usuario.keys() else None
        semana_actual = 1 if not inicio else min(4, 1 + max(0, (datetime.utcnow() - inicio).days) // 7)
        for w in range(1, 5):
            d, c = generar_rutina(usuario, imc, dias_rutina, tipo_entreno_raw, semana=w)
            rutina_plan.append({"semana": w, "dias": d, "consejo": c})
        rutina_dias = next(
            (x["dias"] for x in rutina_plan if x["semana"] == semana_actual),
            rutina_plan[0]["dias"],
        )
        rutina_consejo = f"Semana {semana_actual}/4 · " + (next((x["consejo"] for x in rutina_plan if x["semana"] == semana_actual), "") or "")

    plan_base = plan_del_dia(rutina_dias, usuario_id)
    plan_hoy = None
    if plan_base:
        ejercicios = plan_base["ejercicios"]
        total = len(ejercicios)
        hechos = min(ejercicios_hechos, total)
        pct = int(hechos / total * 100) if total else 0
        sig_ej = ejercicios[hechos] if hechos < total else None
        sig = sig_ej if sig_ej else None
        plan_hoy = {**plan_base, "ejercicios": ejercicios, "total": total, "hechos": hechos, "pct": pct, "siguiente": sig}

    meta_p = meta_pasos_usuario(actividad, usuario)
    stats = stats_con_pasos(
        usuario, peso_actual, actividad, kcal_objetivo, pasos_hoy, meta_p, pasos_fuente, estimar_stats_diarias
    )
    if progreso is not None:
        stats["anillos"]["peso"] = int(progreso)

    streak = calcular_streak(registros, {"completados": ejercicios_hechos} if ejercicios_hechos else None)
    chart_semana = progreso_semanal_chart(
        rutina_dias,
        progreso_por_dia,
        pasos_por_dia=pasos_por_dia,
        meta_pasos=meta_p,
    )
    recientes = entrenos_recientes(registros, rutina_dias)

    alimentos = alimentos_recomendados(
        peso_actual, objetivo_peso, actividad, imc, categoria_imc, proteina_g
    )
    alimentos["comidas_dia"] = comidas_del_dia(
        peso_actual, objetivo_peso, actividad, proteina_g
    )
    meta_agua = meta_vasos_usuario(usuario)

    historial_entreno = None
    with get_db_connection() as conn:
        historial_entreno = build_historial(conn, usuario_id)

    ctx = {
        "primer_nombre": primer_nombre(usuario["nombre"]),
        "fecha_hoy": fecha_hoy_formateada(),
        "streak": streak,
        "plan_hoy": plan_hoy,
        "stats": stats,
        "chart_semana": chart_semana,
        "recientes": recientes,
        "mensaje_entrenador": mensaje_entrenador,
        "alerts": alerts,
        "registros": registros,
        "fechas": fechas,
        "pesos": pesos,
        "predicciones": predicciones,
        "semanas_objetivo": semanas_objetivo,
        "progreso": progreso,
        "imc": imc,
        "categoria_imc": categoria_imc,
        "recomendacion": recomendacion,
        "tipo_entreno_label": tipo_entreno_label,
        "tiene_rutina": tiene_rutina,
        "dias_rutina": dias_rutina,
        "rutina_dias": rutina_dias,
        "rutina_consejo": rutina_consejo,
        "rutina_plan": rutina_plan,
        "semana_actual": semana_actual,
        "weekly": weekly[-8:],
        "kcal_base": kcal_base,
        "kcal_objetivo": kcal_objetivo,
        "proteina_g": proteina_g,
        "nutri_nota": nutri_nota,
        "peso_actual": peso_actual,
        "objetivo_peso": objetivo_peso,
        "alimentos": alimentos,
        "historial_entreno": historial_entreno,
        "pasos_hoy": pasos_hoy,
        "pasos_fuente": pasos_fuente,
        "meta_pasos": meta_p,
        "vasos_hoy": vasos_hoy,
        "meta_vasos": meta_agua,
        "agua_pct": min(100, int(vasos_hoy / meta_agua * 100)) if meta_agua else 0,
        "vapid_public_key": push_svc.get_vapid_public_key(),
        "push_habilitado": push_svc.vapid_configured(),
        "recordatorio_activo": usuario["recordatorio_activo"] if "recordatorio_activo" in usuario.keys() else 0,
        "recordatorio_hora": usuario["recordatorio_hora"] if "recordatorio_hora" in usuario.keys() else "09:00",
    }
    return usuario, ctx


def _render_app(usuario_id, template, active_tab, **extra):
    usuario, ctx = build_usuario_context(usuario_id)
    if not usuario:
        abort(404)
    return render_template(template, usuario=usuario, ctx=ctx, active_tab=active_tab, **extra)


@app.route("/usuario/<int:usuario_id>")
def dashboard(usuario_id):
    return _render_app(usuario_id, "home.html", "home")


@app.route("/usuario/<int:usuario_id>/entrenar")
def entrenar(usuario_id):
    return _render_app(usuario_id, "train.html", "train")


@app.route("/usuario/<int:usuario_id>/nutricion")
def nutricion(usuario_id):
    return _render_app(usuario_id, "nutrition.html", "nutrition")


@app.route("/usuario/<int:usuario_id>/metas")
def metas(usuario_id):
    return redirect(url_for("historial_entreno", usuario_id=usuario_id))


@app.route("/usuario/<int:usuario_id>/historial")
def historial_entreno(usuario_id):
    year = _int(request.args.get("year"))
    month = _int(request.args.get("month"))
    usuario, ctx = build_usuario_context(usuario_id)
    if not usuario:
        abort(404)
    with get_db_connection() as conn:
        ctx["historial_entreno"] = build_historial(conn, usuario_id, year, month)
    return render_template(
        "historial.html",
        usuario=usuario,
        ctx=ctx,
        active_tab="historial",
    )


@app.route("/usuario/<int:usuario_id>/progreso")
def progreso(usuario_id):
    return _render_app(usuario_id, "progress.html", "progress")


@app.route("/usuario/<int:usuario_id>/entreno/marcar", methods=["POST"])
def marcar_ejercicio(usuario_id):
    usuario, ctx = build_usuario_context(usuario_id)
    if not usuario:
        abort(404)
    plan = ctx.get("plan_hoy")
    if not plan:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "error": "Sin plan de hoy"}), 400
        flash("No hay plan de entreno para hoy.", "warning")
        return redirect(url_for("dashboard", usuario_id=usuario_id))
    hoy = date.today().isoformat()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT ejercicios_hechos FROM progreso_entreno WHERE usuario_id=? AND fecha=?",
            (usuario_id, hoy),
        ).fetchone()
        hechos_antes = int(row["ejercicios_hechos"]) if row else 0
        if hechos_antes >= plan["total"]:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"ok": False, "error": "Sesión ya completada"}), 400
            flash("Ya completaste la sesión de hoy.", "success")
            return redirect(request.referrer or url_for("entrenar", usuario_id=usuario_id))
        hechos = min(plan["total"], hechos_antes + 1)
        if row:
            conn.execute(
                "UPDATE progreso_entreno SET ejercicios_hechos=? WHERE usuario_id=? AND fecha=?",
                (hechos, usuario_id, hoy),
            )
        else:
            conn.execute(
                "INSERT INTO progreso_entreno (usuario_id, fecha, ejercicios_hechos) VALUES (?,?,?)",
                (usuario_id, hoy, hechos),
            )
        conn.commit()

    ejercicios = plan["ejercicios"]
    ej_completado = ejercicios[hechos - 1] if hechos > 0 and hechos - 1 < len(ejercicios) else None
    descanso_seg = 0
    descanso_label = "—"
    ejercicio_nombre = ""
    if isinstance(ej_completado, dict):
        descanso_seg = int(ej_completado.get("descanso_seg") or 0)
        descanso_label = ej_completado.get("descanso") or "—"
        ejercicio_nombre = ej_completado.get("nombre") or ""

    completado = hechos >= plan["total"]
    payload = {
        "ok": True,
        "hechos": hechos,
        "total": plan["total"],
        "pct": int(hechos / plan["total"] * 100) if plan["total"] else 0,
        "completado": completado,
        "descanso_seg": descanso_seg,
        "descanso": descanso_label,
        "ejercicio": ejercicio_nombre,
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(payload)

    if completado:
        flash("¡Sesión de hoy completada! 🔥", "success")
    else:
        flash("¡Ejercicio completado!", "success")
    return redirect(request.referrer or url_for("entrenar", usuario_id=usuario_id))



@app.route("/usuario/<int:usuario_id>/editar", methods=["GET", "POST"])
def editar_usuario(usuario_id):
    with get_db_connection() as conn:
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not usuario:
        abort(404)

    if request.method == "GET":
        _, ctx = build_usuario_context(usuario_id)
        return render_template("edit_profile.html", usuario=usuario, ctx=ctx or {})

    nombre = (request.form.get("nombre") or "").strip()
    if not nombre:
        flash("El nombre es obligatorio.", "warning")
        return redirect(url_for("editar_usuario", usuario_id=usuario_id))

    edad = _int(request.form.get("edad"))
    estatura = _float(request.form.get("estatura"))
    objetivo_peso = _float(request.form.get("objetivo_peso"))
    if edad is None or estatura is None or objetivo_peso is None:
        flash("Revisa los campos numéricos.", "warning")
        return redirect(url_for("editar_usuario", usuario_id=usuario_id))
    if not (1 <= edad <= 120 and 0.5 <= estatura <= 2.5 and 20 <= objetivo_peso <= 300):
        flash("Revisa los rangos ingresados.", "warning")
        return redirect(url_for("editar_usuario", usuario_id=usuario_id))

    sexo = (request.form.get("sexo") or "").strip()
    if sexo not in ("m", "f", "x", ""):
        sexo = ""
    actividad = (request.form.get("actividad") or "").strip()
    if actividad not in ("baja", "media", "alta", ""):
        actividad = ""

    quiere_rutina = 1 if request.form.get("quiere_rutina") == "1" else 0
    dias_rutina = _int(request.form.get("dias_rutina")) if quiere_rutina else None
    if quiere_rutina and (dias_rutina is None or not (2 <= dias_rutina <= 7)):
        dias_rutina = 3
    tipo_entreno = (request.form.get("tipo_entreno") or "").strip() if quiere_rutina else None
    if quiere_rutina and tipo_entreno not in ("gym", "casa", "mixto"):
        tipo_entreno = "mixto"

    eliminar_foto = request.form.get("eliminar_foto") == "1"

    foto_perfil_filename = usuario["foto_perfil"]
    if eliminar_foto:
        foto_perfil_filename = None

    file = request.files.get("foto_perfil")
    if file and file.filename:
        filename = secure_filename(file.filename)
        if _allowed_file(filename):
            _, ext = os.path.splitext(filename)
            unique_name = f"user_{usuario_id}_{abs(hash(filename)) % 100000}{ext.lower()}"
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)
            foto_perfil_filename = unique_name
        else:
            flash("La foto debe ser PNG/JPG/JPEG/GIF.", "warning")
            return redirect(url_for("editar_usuario", usuario_id=usuario_id))

    rutina_inicio = usuario["rutina_inicio"]
    if quiere_rutina and not rutina_inicio:
        rutina_inicio = datetime.utcnow().isoformat(timespec="seconds")
    if not quiere_rutina:
        rutina_inicio = None

    recordatorio_activo = 1 if request.form.get("recordatorio_activo") == "1" else 0
    recordatorio_hora = (request.form.get("recordatorio_hora") or "09:00").strip()[:5]
    meta_pasos = _int(request.form.get("meta_pasos"))

    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET nombre=?, edad=?, estatura=?, objetivo_peso=?, foto_perfil=?, sexo=?, actividad=?,
                quiere_rutina=?, dias_rutina=?, tipo_entreno=?, rutina_inicio=?,
                recordatorio_activo=?, recordatorio_hora=?, meta_pasos=?
            WHERE id=?
            """,
            (
                nombre,
                edad,
                estatura,
                objetivo_peso,
                foto_perfil_filename,
                sexo or None,
                actividad or None,
                quiere_rutina,
                dias_rutina,
                tipo_entreno,
                rutina_inicio,
                recordatorio_activo,
                recordatorio_hora,
                meta_pasos,
                usuario_id,
            ),
        )
        conn.commit()

    flash("Perfil actualizado.", "success")
    return redirect(url_for("dashboard", usuario_id=usuario_id))

@app.route("/registrar_peso/<int:usuario_id>", methods=["POST"])
def registrar_peso(usuario_id):
    peso = _float(request.form.get("peso"))
    if peso is None or not (20 <= peso <= 300):
        flash("El peso debe estar entre 20 y 300 kg.", "warning")
        return redirect(url_for("dashboard", usuario_id=usuario_id))
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO registros_peso (usuario_id, peso) VALUES (?, ?)",
            (usuario_id, peso),
        )
        conn.commit()
    flash("Peso registrado.", "success")
    return redirect(url_for("progreso", usuario_id=usuario_id))


@app.route("/usuario/<int:usuario_id>/eliminar", methods=["POST"])
def eliminar_usuario(usuario_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM registros_peso WHERE usuario_id = ?", (usuario_id,))
        conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def file_too_large(e):
    flash("La imagen es demasiado grande. Máximo 4 MB.", "warning")
    return redirect(url_for("index"))


@app.route("/usuario/<int:usuario_id>/pasos", methods=["POST"])
def registrar_pasos(usuario_id):
    pasos = _int(request.form.get("pasos"))
    if pasos is None or not (0 <= pasos <= 100000):
        flash("Indica pasos válidos (0–100000).", "warning")
        return redirect(request.referrer or url_for("progreso", usuario_id=usuario_id))
    fuente = (request.form.get("fuente") or "manual").strip()[:32]
    with get_db_connection() as conn:
        guardar_pasos(conn, usuario_id, pasos, fuente)
        conn.commit()
    flash("Pasos registrados.", "success")
    return redirect(request.referrer or url_for("dashboard", usuario_id=usuario_id))


@app.route("/usuario/<int:usuario_id>/agua", methods=["POST"])
def registrar_agua(usuario_id):
    accion = (request.form.get("accion") or "vaso").strip()
    xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    with get_db_connection() as conn:
        if accion == "reset":
            vasos = guardar_vasos(conn, usuario_id, 0)
        elif accion == "set":
            vasos_raw = _int(request.form.get("vasos"))
            if vasos_raw is None or not (0 <= vasos_raw <= 30):
                if xhr:
                    return jsonify({"ok": False, "error": "Vasos inválidos"}), 400
                flash("Indica vasos válidos (0–30).", "warning")
                return redirect(request.referrer or url_for("nutricion", usuario_id=usuario_id))
            vasos = guardar_vasos(conn, usuario_id, vasos_raw)
        else:
            vasos = agregar_vaso(conn, usuario_id)
        conn.commit()
    meta = meta_vasos_usuario()
    with get_db_connection() as conn:
        u = conn.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
        if u:
            meta = meta_vasos_usuario(u)
    payload = {
        "ok": True,
        "vasos": vasos,
        "meta": meta,
        "pct": min(100, int(vasos / meta * 100)) if meta else 0,
    }
    if xhr:
        return jsonify(payload)
    flash("Agua registrada.", "success")
    return redirect(request.referrer or url_for("nutricion", usuario_id=usuario_id))


@app.route("/api/usuario/<int:usuario_id>/pasos/sync", methods=["POST"])
def sync_pasos_api(usuario_id):
    data = request.get_json(silent=True) or {}
    pasos = _int(data.get("pasos"))
    if pasos is None:
        return {"ok": False, "error": "pasos inválidos"}, 400
    fuente = (data.get("fuente") or "dispositivo")[:32]
    with get_db_connection() as conn:
        guardar_pasos(conn, usuario_id, pasos, fuente)
        conn.commit()
    return {"ok": True, "pasos": pasos, "fuente": fuente}


@app.route("/api/push/vapid-public-key")
def vapid_public():
    return {"publicKey": push_svc.get_vapid_public_key()}


@app.route("/api/usuario/<int:usuario_id>/push/subscribe", methods=["POST"])
def push_subscribe(usuario_id):
    sub = request.get_json(silent=True)
    if not sub or not sub.get("endpoint"):
        return {"ok": False}, 400
    with get_db_connection() as conn:
        push_svc.save_subscription(conn, usuario_id, sub)
        conn.commit()
    return {"ok": True}


@app.route("/usuario/<int:usuario_id>/push/probar", methods=["POST"])
def push_probar(usuario_id):
    usuario, ctx = build_usuario_context(usuario_id)
    if not usuario:
        abort(404)
    nombre = ctx["primer_nombre"]
    with get_db_connection() as conn:
        subs = conn.execute(
            "SELECT subscription_json FROM push_subscriptions WHERE usuario_id=? AND activo=1",
            (usuario_id,),
        ).fetchall()
    import json as _json

    ok_any = False
    for s in subs:
        info = _json.loads(s["subscription_json"])
        ok, err = push_svc.send_push(info, "Fitness Tracker", f"Prueba: ¡Hola {nombre}!", "/")
        ok_any = ok_any or ok
    if ok_any:
        flash("Notificación de prueba enviada.", "success")
    else:
        flash("No se pudo enviar. Activa notificaciones y configura VAPID en .env", "warning")
    return redirect(url_for("editar_usuario", usuario_id=usuario_id))


@app.route("/sw.js")
def service_worker():
    return app.send_static_file("sw.js")


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


if __name__ == "__main__":
    init_db()
    push_svc.iniciar_scheduler(app)
    app.run(host="0.0.0.0", port=5000, debug=True)