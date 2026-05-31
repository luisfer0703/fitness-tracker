"""Contexto compartido para pantallas de la app Fitness Tracker."""
from collections import defaultdict
from datetime import datetime, date, timedelta
import random

import numpy as np
from sklearn.linear_model import LinearRegression


MESES = (
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
)
# Ma = martes, M = miércoles (evita la X poco intuitiva)
DIAS_CORTO = ("L", "Ma", "M", "J", "V", "S", "D")


def parse_dt(value):
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


def fecha_hoy_formateada():
    hoy = datetime.now()
    return f"Hoy, {hoy.day} {MESES[hoy.month - 1]} {hoy.year}"


def primer_nombre(nombre):
    if not nombre:
        return "Usuario"
    return str(nombre).strip().split()[0]


def calcular_streak(registros, progreso_hoy=None):
    """Racha: días consecutivos con registro de peso o entreno del día."""
    fechas_actividad = set()
    for r in registros:
        dt = parse_dt(r["fecha"])
        if dt:
            fechas_actividad.add(dt.date())
    if progreso_hoy and progreso_hoy.get("completados", 0) > 0:
        fechas_actividad.add(date.today())

    if not fechas_actividad:
        return 0

    streak = 0
    d = date.today()
    while d in fechas_actividad:
        streak += 1
        d -= timedelta(days=1)
    return streak


def estimar_stats_diarias(usuario, peso_actual, actividad, kcal_objetivo):
    """Estimaciones para widgets (pasos, calorías quemadas, minutos activos)."""
    uid = usuario["id"] if "id" in usuario.keys() else 0
    rng = random.Random(uid + date.today().toordinal())

    meta_pasos = {"baja": 6000, "media": 10000, "alta": 12000}.get(actividad or "", 8500)
    pasos = int(meta_pasos * rng.uniform(0.75, 1.05))
    pasos = min(pasos, meta_pasos + 500)

    kcal_quemadas = int((kcal_objetivo or 2000) * rng.uniform(0.55, 0.85))
    minutos = int(rng.uniform(25, 75))
    if actividad == "alta":
        minutos = int(rng.uniform(50, 120))
    elif actividad == "baja":
        minutos = int(rng.uniform(15, 45))

    return {
        "pasos": pasos,
        "meta_pasos": meta_pasos,
        "kcal": kcal_quemadas,
        "minutos": minutos,
        "anillos": {
            "movimiento": min(100, int(pasos / meta_pasos * 100)),
            "ejercicio": min(100, int(minutos / 60 * 100)),
            "peso": min(100, 70),  # se sobreescribe con progreso meta si existe
        },
    }


def plan_del_dia(rutina_dias, usuario_id):
    """Elige el día de rutina según día de la semana."""
    if not rutina_dias:
        return None
    idx = datetime.now().weekday() % len(rutina_dias)
    dia = rutina_dias[idx]
    ejercicios = dia.get("ejercicios") or []
    duracion = dia.get("duracion_min") or min(90, 25 + len(ejercicios) * 5)
    return {
        "titulo": dia.get("titulo", "Día de entreno"),
        "enfoque": dia.get("enfoque", "Entrenamiento"),
        "ejercicios": ejercicios,
        "duracion_min": duracion,
        "dia_index": idx,
    }


def _total_ejercicios_dia(rutina_dias, weekday_idx):
    """Ejercicios planificados para un día de la semana (0 = lunes)."""
    if not rutina_dias:
        return 0
    idx = weekday_idx % len(rutina_dias)
    return len(rutina_dias[idx].get("ejercicios") or [])


def _score_dia(hechos, total_entreno, pasos, meta_pasos):
    """Puntuación 0-100 combinando entreno y pasos del día."""
    scores = []
    if total_entreno > 0:
        scores.append(min(100.0, hechos / total_entreno * 100))
    elif hechos > 0:
        scores.append(min(100.0, hechos * 12))
    if pasos is not None and meta_pasos:
        scores.append(min(100.0, pasos / meta_pasos * 100))
    if not scores:
        return 0
    return int(round(sum(scores) / len(scores)))


def progreso_semanal_chart(rutina_dias, progreso_por_dia, pasos_por_dia=None, meta_pasos=10000, hoy=None):
    """Progreso diario L-D de la semana actual según entreno y pasos reales del usuario."""
    labels = list(DIAS_CORTO)
    hoy = hoy or date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    pasos_por_dia = pasos_por_dia or {}
    progreso_por_dia = progreso_por_dia or {}

    values = []
    for i in range(7):
        d = lunes + timedelta(days=i)
        iso = d.isoformat()
        if d > hoy:
            values.append(None)
            continue
        hechos = int(progreso_por_dia.get(iso, 0) or 0)
        total = _total_ejercicios_dia(rutina_dias, d.weekday())
        pasos = pasos_por_dia.get(iso)
        values.append(_score_dia(hechos, total, pasos, meta_pasos))

    valid = [v for v in values if v is not None]
    pct = int(round(sum(valid) / len(valid))) if valid else 0
    return {"labels": labels, "values": values, "porcentaje": pct}


def entrenos_recientes(registros, rutina_dias, limit=5):
    items = []
    for r in reversed(registros[-limit:]):
        dt = parse_dt(r["fecha"])
        label = dt.strftime("%d %b") if dt else str(r["fecha"])[:10]
        items.append({
            "titulo": "Registro de peso",
            "detalle": f"{r['peso']} kg",
            "fecha": label,
            "icono": "⚖️",
        })
    if rutina_dias and len(items) < limit:
        for dia in reversed(rutina_dias[:2]):
            items.insert(0, {
                "titulo": dia.get("enfoque", "Entrenamiento"),
                "detalle": dia.get("titulo", ""),
                "fecha": "Planificado",
                "icono": "🏋️",
            })
    return items[:limit]


def respuesta_chat(pregunta, ctx):
    """Coach IA basado en reglas (sin API externa)."""
    q = (pregunta or "").lower().strip()
    nombre = ctx.get("primer_nombre", "atleta")
    peso = ctx.get("peso_actual")
    meta = ctx.get("objetivo_peso")
    imc = ctx.get("imc")
    msg = ctx.get("mensaje_entrenador", "")

    if not q:
        return "¿En qué puedo ayudarte hoy? Pregunta por rutina, nutrición o tu progreso."

    if any(w in q for w in ("hola", "buenas", "hey")):
        return f"¡Hola {nombre}! Estoy aquí para guiarte. ¿Quieres revisar tu plan de hoy o tu nutrición?"

    if any(w in q for w in ("rutina", "entreno", "ejercicio", "plan")):
        plan = ctx.get("plan_hoy")
        if plan:
            sig = plan["ejercicios"][0] if plan.get("ejercicios") else "tu primer ejercicio"
            return (
                f"Hoy toca: {plan['enfoque']}. Duración estimada {plan['duracion_min']} min. "
                f"Empieza con: {sig}."
            )
        return "Aún no tienes rutina activa. Actívala en Editar perfil → Rutina personalizada."

    if any(w in q for w in ("proteína", "proteina", "calor", "comer", "dieta", "nutri")):
        k = ctx.get("kcal_objetivo")
        p = ctx.get("proteina_g")
        if k and p:
            return f"Objetivo diario: ~{k} kcal y {p} g de proteína. {ctx.get('nutri_nota', '')}"
        return "Registra tu peso y completa tu perfil para estimar calorías y proteína."

    if any(w in q for w in ("peso", "bajar", "subir", "meta")):
        if peso and meta:
            return f"Peso actual ~{peso:.1f} kg, meta {meta:.1f} kg. {msg}"
        return msg or "Registra tu peso con frecuencia para ver tendencias."

    if any(w in q for w in ("imc", "grasa", "salud")):
        if imc:
            return f"Tu IMC es {imc:.1f} ({ctx.get('categoria_imc', '')}). {ctx.get('recomendacion', '')}"
        return "Necesito estatura y peso para calcular tu IMC."

    return (
        f"{msg} Si quieres, pregúntame por 'rutina', 'nutrición' o 'progreso' y te oriento con tus datos."
    )
