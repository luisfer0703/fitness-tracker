"""Gestión de pasos: registro manual, sync móvil y estimación."""
from datetime import date


def meta_pasos_usuario(actividad, usuario=None):
    custom = None
    if usuario and "meta_pasos" in usuario.keys():
        custom = usuario["meta_pasos"]
    if custom and custom > 0:
        return int(custom)
    return {"baja": 6000, "media": 10000, "alta": 12000}.get(actividad or "", 10000)


def obtener_pasos_hoy(conn, usuario_id):
    hoy = date.today().isoformat()
    row = conn.execute(
        "SELECT pasos, fuente FROM registros_pasos WHERE usuario_id=? AND fecha=?",
        (usuario_id, hoy),
    ).fetchone()
    if row:
        return int(row["pasos"]), row["fuente"] or "manual"
    return None, None


def guardar_pasos(conn, usuario_id, pasos, fuente="manual"):
    hoy = date.today().isoformat()
    pasos = max(0, min(100000, int(pasos)))
    conn.execute(
        """
        INSERT INTO registros_pasos (usuario_id, fecha, pasos, fuente)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(usuario_id, fecha) DO UPDATE SET pasos=excluded.pasos, fuente=excluded.fuente
        """,
        (usuario_id, hoy, pasos, fuente),
    )


def stats_con_pasos(usuario, peso_actual, actividad, kcal_objetivo, pasos_hoy, meta_pasos, pasos_fuente, estimar_fn):
    """Combina pasos reales con estimación para el widget."""
    stats = estimar_fn(usuario, peso_actual, actividad, kcal_objetivo)
    if pasos_hoy is not None:
        stats["pasos"] = pasos_hoy
        stats["pasos_reales"] = True
        stats["pasos_fuente"] = pasos_fuente or "sync"
    else:
        stats["pasos_reales"] = False
        stats["pasos_fuente"] = "estimado"
    stats["meta_pasos"] = meta_pasos
    stats["anillos"]["movimiento"] = min(100, int(stats["pasos"] / meta_pasos * 100)) if meta_pasos else 0
    return stats
