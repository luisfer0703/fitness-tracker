"""Historial de entrenos y calendario mensual."""
from calendar import monthrange
from datetime import date, datetime, timedelta

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
DIAS_ES = ("L", "Ma", "M", "J", "V", "S", "D")


def _parse_fecha_iso(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def obtener_registros_entreno(conn, usuario_id):
    rows = conn.execute(
        """
        SELECT fecha, ejercicios_hechos
        FROM progreso_entreno
        WHERE usuario_id=?
        ORDER BY fecha
        """,
        (usuario_id,),
    ).fetchall()
    por_dia = {}
    for r in rows:
        d = _parse_fecha_iso(r["fecha"])
        if d:
            por_dia[d.isoformat()] = int(r["ejercicios_hechos"] or 0)
    return por_dia


def _estado_dia(hechos):
    if hechos <= 0:
        return "vacio"
    if hechos >= 6:
        return "completo"
    return "parcial"


def calendario_mes(por_dia, year=None, month=None):
    """Genera rejilla de calendario para un mes."""
    hoy = date.today()
    year = year or hoy.year
    month = month or hoy.month

    first = date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    # Lunes = 0
    start_weekday = (first.weekday()) % 7

    cells = []
    for _ in range(start_weekday):
        cells.append({"tipo": "pad", "dia": None})

    for d in range(1, days_in_month + 1):
        iso = date(year, month, d).isoformat()
        hechos = por_dia.get(iso, 0)
        cells.append(
            {
                "tipo": "dia",
                "dia": d,
                "iso": iso,
                "hechos": hechos,
                "estado": _estado_dia(hechos),
                "es_hoy": iso == hoy.isoformat(),
                "es_futuro": date(year, month, d) > hoy,
            }
        )

    while len(cells) % 7 != 0:
        cells.append({"tipo": "pad", "dia": None})

    weeks = [cells[i : i + 7] for i in range(0, len(cells), 7)]

    prev_m = month - 1
    prev_y = year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    next_m = month + 1
    next_y = year
    if next_m > 12:
        next_m = 1
        next_y += 1

    return {
        "year": year,
        "month": month,
        "mes_label": f"{MESES[month - 1]} {year}",
        "dias_semana": list(DIAS_ES),
        "weeks": weeks,
        "prev": {"year": prev_y, "month": prev_m},
        "next": {"year": next_y, "month": next_m},
        "puede_siguiente": date(next_y, next_m, 1) <= hoy,
    }


def resumen_historial(por_dia, dias_atras=90):
    hoy = date.today()
    inicio = hoy - timedelta(days=dias_atras)
    activos = parciales = completos = 0
    lista = []
    for iso, hechos in sorted(por_dia.items(), reverse=True):
        d = _parse_fecha_iso(iso)
        if not d or d < inicio:
            continue
        est = _estado_dia(hechos)
        if est == "completo":
            completos += 1
        elif est == "parcial":
            parciales += 1
        else:
            continue
        activos += 1
        lista.append(
            {
                "fecha": iso,
                "fecha_fmt": d.strftime("%d/%m/%Y"),
                "hechos": hechos,
                "estado": est,
            }
        )
    return {
        "dias_activos": activos,
        "completos": completos,
        "parciales": parciales,
        "ultimos": lista[:14],
    }


def build_historial(conn, usuario_id, year=None, month=None):
    por_dia = obtener_registros_entreno(conn, usuario_id)
    cal = calendario_mes(por_dia, year, month)
    resumen = resumen_historial(por_dia)
    return {**cal, **resumen, "por_dia": por_dia}
