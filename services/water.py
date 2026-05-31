"""Registro manual de consumo de agua (vasos)."""
from datetime import date

META_VASOS_DEFAULT = 8  # ~2 L (250 ml por vaso)


def meta_vasos_usuario(usuario=None):
    if usuario and "meta_vasos" in usuario.keys() and usuario["meta_vasos"]:
        try:
            v = int(usuario["meta_vasos"])
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    return META_VASOS_DEFAULT


def obtener_agua_hoy(conn, usuario_id):
    hoy = date.today().isoformat()
    row = conn.execute(
        "SELECT vasos FROM registros_agua WHERE usuario_id=? AND fecha=?",
        (usuario_id, hoy),
    ).fetchone()
    return int(row["vasos"]) if row else 0


def guardar_vasos(conn, usuario_id, vasos):
    hoy = date.today().isoformat()
    vasos = max(0, min(30, int(vasos)))
    conn.execute(
        """
        INSERT INTO registros_agua (usuario_id, fecha, vasos)
        VALUES (?, ?, ?)
        ON CONFLICT(usuario_id, fecha) DO UPDATE SET vasos=excluded.vasos
        """,
        (usuario_id, hoy, vasos),
    )
    return vasos


def agregar_vaso(conn, usuario_id, cantidad=1):
    actual = obtener_agua_hoy(conn, usuario_id)
    return guardar_vasos(conn, usuario_id, actual + max(1, int(cantidad)))
