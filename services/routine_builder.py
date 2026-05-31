"""Construcción de rutinas: calentamiento, ejercicios con descanso y estiramiento."""
import re
import unicodedata


def _normalizar(texto):
    t = (texto or "").lower()
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _formato_descanso(segundos):
    if segundos <= 0:
        return "—"
    if segundos < 60:
        return f"{segundos} s"
    m, s = divmod(segundos, 60)
    if s == 0:
        return f"{m} min"
    return f"{m} min {s} s"


def _parsear_ejercicio(texto):
    """Convierte texto 'Nombre 3x8-10' o 'Cinta 25-35 min' a campos estructurados."""
    t = (texto or "").strip()
    nombre = t
    series = reps = detalle = None
    tipo = "fuerza"

    m_cardio = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*min", t, re.I)
    m_tiempo = re.search(r"(\d+)x(\d+)\s*[-–]?\s*(\d+)?\s*(s|seg|sec)\b", t, re.I)
    m_sets = re.search(r"(\d+)x(\d+(?:\s*[-–]\s*\d+)?)", t, re.I)

    if m_cardio:
        nombre = t[: m_cardio.start()].strip(" ·-")
        series, reps = "1", f"{m_cardio.group(1)}-{m_cardio.group(2)} min"
        detalle = reps
        tipo = "cardio"
    elif m_tiempo:
        nombre = t[: m_tiempo.start()].strip(" ·-")
        series = m_tiempo.group(1)
        reps = f"{m_tiempo.group(2)}-{m_tiempo.group(3) or m_tiempo.group(2)} s"
        detalle = f"{series} x {reps}"
        tipo = "core"
    elif m_sets:
        nombre = t[: m_sets.start()].strip(" ·-")
        series = m_sets.group(1)
        reps = m_sets.group(2).replace(" ", "")
        detalle = f"{series} x {reps}"
    else:
        detalle = t
        nombre = re.sub(r"\s+\d+x.*$", "", t, flags=re.I).strip() or t

    return {
        "nombre": nombre or t,
        "series": series,
        "reps": reps,
        "detalle": detalle or t,
        "tipo": tipo,
    }


def _descanso_segundos(parsed, objetivo, enfoque_cardio):
    """Descanso entre series según tipo de ejercicio y objetivo del usuario."""
    if parsed["tipo"] == "cardio":
        return 0
    if parsed["tipo"] in ("calentamiento", "estiramiento"):
        return 30

    n = _normalizar(parsed["nombre"])
    es_compuesto = any(
        k in n
        for k in (
            "sentadilla",
            "prensa",
            "peso muerto",
            "press banca",
            "press militar",
            "remo con barra",
            "jalon",
            "zancada",
            "flexiones",
        )
    )
    es_aislamiento = any(k in n for k in ("curl", "extension", "elevacion", "face pull", "triceps", "gemelo"))

    if parsed["tipo"] == "core":
        return 45

    if objetivo == "subir":
        base = 105 if es_compuesto else 75
    elif objetivo == "bajar" or enfoque_cardio:
        base = 50 if es_compuesto else 40
    else:
        base = 75 if es_compuesto else 60

    if es_aislamiento and not es_compuesto:
        base = max(45, base - 15)

    return base


def _icono_tipo(tipo):
    return {
        "calentamiento": "🔥",
        "fuerza": "💪",
        "cardio": "❤️",
        "core": "🎯",
        "estiramiento": "🧘",
    }.get(tipo, "💪")


def _a_ejercicio(texto, tipo_forzado=None, objetivo="mantener", enfoque_cardio=False, descanso_fijo=None):
    p = _parsear_ejercicio(texto)
    if tipo_forzado:
        p["tipo"] = tipo_forzado
    seg = descanso_fijo if descanso_fijo is not None else _descanso_segundos(p, objetivo, enfoque_cardio)
    return {
        **p,
        "descanso_seg": seg,
        "descanso": _formato_descanso(seg),
        "icono": _icono_tipo(p["tipo"]),
    }


# Calentamientos por enfoque del día
_CALENTAMIENTO = {
    "push": [
        "Movilidad de hombros — círculos 2x10",
        "Retracciones escapulares (de pie) 2x12",
        "Flexiones ligeras (calentamiento) 2x8",
    ],
    "pull": [
        "Cat-cow y movilidad de columna 2 min",
        "Y-T-W en el suelo 2x6-8",
        "Activación de escápulas (aprieta 2 s) 2x10",
    ],
    "legs": [
        "Marcha en el sitio o caminata 3 min",
        "Sentadillas sin peso 2x12",
        "Zancadas caminando lentas 2x8 por pierna",
    ],
    "full": [
        "Caminata o trote suave 4 min",
        "Sentadillas al aire 2x10",
        "Plancha 2x20 s",
    ],
    "cardio": [
        "Caminata progresiva 5 min",
        "Movilidad dinámica (tobillos, cadera) 3 min",
    ],
    "core_movil": [
        "Movilidad de cadera y columna 3 min",
        "Activación de core (dead bug suave) 2x8",
    ],
}

_CALENTAMIENTO_CASA_SIN_EQUIPO = {
    "push": [
        "Movilidad de hombros — círculos 2x10",
        "Scapular push-ups (solo escápulas) 2x10",
        "Flexiones ligeras (calentamiento) 2x6-8",
    ],
    "pull": [
        "Cat-cow y movilidad de columna 2 min",
        "Y-T-W en el suelo 2x6-8",
        "Reverse snow angels 2x10",
    ],
    "legs": [
        "Marcha en el sitio 3 min",
        "Sentadillas sin peso 2x10-12",
        "Zancadas lentas 2x6-8 por pierna",
    ],
    "full": [
        "Marcha en el sitio 4 min",
        "Sentadillas al aire 2x10",
        "Plancha 2x20 s",
    ],
    "cardio": [
        "Marcha en el sitio progresiva 5 min",
        "Movilidad dinámica (tobillos, cadera) 3 min",
    ],
    "core_movil": [
        "Movilidad de cadera y columna 3 min",
        "Activación de core (dead bug suave) 2x8",
    ],
}

_ESTIRAMIENTO = {
    "push": [
        "Estiramiento de pecho en marco de puerta 30 s por lado",
        "Estiramiento de tríceps 30 s por brazo",
        "Estiramiento de hombros cruzados 30 s",
    ],
    "pull": [
        "Estiramiento de espalda (colgante o rodillas) 40 s",
        "Estiramiento de bíceps en pared 30 s por brazo",
        "Estiramiento de trapecio 25 s por lado",
    ],
    "legs": [
        "Estiramiento de cuádriceps 30 s por pierna",
        "Estiramiento de isquios (tocar puntas) 40 s",
        "Estiramiento de glúteo (figura 4) 30 s por lado",
    ],
    "full": [
        "Estiramiento de cadena posterior 45 s",
        "Estiramiento de pecho y hombros 30 s",
        "Respiración y relajación 1 min",
    ],
    "cardio": [
        "Estiramiento de pantorrillas 30 s",
        "Estiramiento de cadera 30 s por lado",
        "Caminata suave de vuelta a la calma 2 min",
    ],
    "core_movil": [
        "Estiramiento de columna (cobra suave) 30 s",
        "Estiramiento lateral de tronco 25 s por lado",
    ],
}


_ESTIRAMIENTO_CASA = {
    "push": [
        "Estiramiento de pecho en marco de puerta 30 s por lado",
        "Estiramiento de tríceps 30 s por brazo",
        "Estiramiento de hombros cruzados 30 s",
    ],
    "pull": [
        "Estiramiento de espalda (rodillas al pecho) 40 s",
        "Estiramiento de bíceps en pared 30 s por brazo",
        "Estiramiento de trapecio 25 s por lado",
    ],
    "legs": [
        "Estiramiento de cuádriceps 30 s por pierna",
        "Estiramiento de isquios (sentado) 40 s",
        "Estiramiento de glúteo (figura 4) 30 s por lado",
    ],
    "full": [
        "Estiramiento de cadena posterior 45 s",
        "Estiramiento de pecho y hombros 30 s",
        "Respiración y relajación 1 min",
    ],
    "cardio": [
        "Estiramiento de pantorrillas 30 s",
        "Estiramiento de cadera 30 s por lado",
        "Marcha en el sitio suave 2 min",
    ],
    "core_movil": [
        "Estiramiento de columna (cobra suave) 30 s",
        "Estiramiento lateral de tronco 25 s por lado",
    ],
}


def calentamiento_para_dia(grupos, tipo_entreno="gym"):
    tabla = _CALENTAMIENTO_CASA_SIN_EQUIPO if tipo_entreno == "casa" else _CALENTAMIENTO
    items = []
    vistos = set()
    for g in grupos:
        for ej in tabla.get(g, []):
            if ej not in vistos:
                vistos.add(ej)
                items.append(ej)
    if not items:
        items = tabla["full"][:3]
    return items[:4]


def estiramiento_para_dia(grupos, tipo_entreno="gym"):
    tabla = _ESTIRAMIENTO_CASA if tipo_entreno == "casa" else _ESTIRAMIENTO
    items = []
    vistos = set()
    for g in grupos:
        for ej in tabla.get(g, []):
            if ej not in vistos:
                vistos.add(ej)
                items.append(ej)
    if not items:
        items = tabla["full"]
    return items[:4]


def _requiere_equipamiento(texto):
    t = _normalizar(texto)
    return any(
        k in t
        for k in (
            "mancuer",
            "barra",
            "polea",
            "cable",
            "prensa",
            "banda",
            "botella",
            "mochila",
            "silla",
            "banco",
            "jalon",
            "cinta",
            "eliptica",
            "bicicleta",
            "ergometro",
        )
    )


def _es_actividad_exterior(texto):
    t = _normalizar(texto)
    if any(k in t for k in ("en el sitio", "en el lugar", "imaginaria", "en casa")):
        return False
    return any(
        k in t
        for k in (
            "caminata",
            "caminar rapida",
            "trote",
            " correr",
            "afuera",
            "exterior",
            "al aire libre",
        )
    )


def armar_dia_ejercicios(lista_texto, grupos, objetivo, enfoque_cardio, tipo_entreno="gym"):
    """Calentamiento + ejercicios principales + estiramiento."""
    bloques = []

    for t in calentamiento_para_dia(grupos, tipo_entreno=tipo_entreno):
        bloques.append(_a_ejercicio(t, "calentamiento", objetivo, enfoque_cardio, descanso_fijo=30))

    for t in lista_texto:
        low = _normalizar(t)
        if "estiramiento dinamico" in low or "movilidad de cadera y columna 6" in low:
            continue
        if tipo_entreno == "casa" and _requiere_equipamiento(t):
            # Seguridad: si algo se coló con equipo, lo omitimos para que sea 100% sin equipamiento.
            continue
        if tipo_entreno == "casa" and _es_actividad_exterior(t):
            continue
        bloques.append(_a_ejercicio(t, None, objetivo, enfoque_cardio))

    for t in estiramiento_para_dia(grupos, tipo_entreno=tipo_entreno):
        bloques.append(_a_ejercicio(t, "estiramiento", objetivo, enfoque_cardio, descanso_fijo=20))

    return bloques


def duracion_estimada_min(ejercicios):
    mins = 5
    for e in ejercicios:
        t = e.get("tipo", "fuerza")
        if t == "calentamiento":
            mins += 3
        elif t == "estiramiento":
            mins += 2
        elif t == "cardio":
            m = re.search(r"(\d+)", e.get("reps") or "")
            mins += int(m.group(1)) if m else 20
        else:
            try:
                n_series = int(e.get("series") or 3)
            except ValueError:
                n_series = 3
            mins += n_series * 2 + (e.get("descanso_seg", 60) * max(0, n_series - 1)) // 60
    return min(95, max(25, mins))
