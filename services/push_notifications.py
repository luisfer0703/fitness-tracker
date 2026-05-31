"""Notificaciones Web Push (recordatorios)."""
import json
import os
from datetime import datetime

_scheduler = None


def get_vapid_claims():
    return {
        "sub": os.environ.get("VAPID_CLAIM_EMAIL", "mailto:fitness@tracker.local"),
    }


def get_vapid_public_key():
    return os.environ.get("VAPID_PUBLIC_KEY", "").strip()


def get_vapid_private_key():
    return os.environ.get("VAPID_PRIVATE_KEY", "").strip()


def vapid_configured():
    return bool(get_vapid_public_key() and get_vapid_private_key())


def save_subscription(conn, usuario_id, subscription_json):
    conn.execute(
        """
        INSERT INTO push_subscriptions (usuario_id, endpoint, subscription_json, activo)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(endpoint) DO UPDATE SET
            usuario_id=excluded.usuario_id,
            subscription_json=excluded.subscription_json,
            activo=1
        """,
        (usuario_id, subscription_json.get("endpoint", ""), json.dumps(subscription_json)),
    )


def send_push(subscription_info, title, body, url="/"):
    if not vapid_configured():
        return False, "VAPID no configurado"

    try:
        from pywebpush import webpush, WebPushException

        payload = json.dumps({"title": title, "body": body, "url": url})
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=get_vapid_private_key(),
            vapid_claims=get_vapid_claims(),
        )
        return True, None
    except Exception as e:
        return False, str(e)


def enviar_recordatorios(conn):
    """Envía recordatorios a usuarios con hora configurada = hora actual."""
    hora = datetime.now().strftime("%H:%M")
    usuarios = conn.execute(
        """
        SELECT u.id, u.nombre FROM usuarios u
        WHERE u.recordatorio_activo=1 AND u.recordatorio_hora=?
        """,
        (hora,),
    ).fetchall()

    enviados = 0
    for u in usuarios:
        subs = conn.execute(
            "SELECT subscription_json FROM push_subscriptions WHERE usuario_id=? AND activo=1",
            (u["id"],),
        ).fetchall()
        nombre = (u["nombre"] or "").split()[0]
        for s in subs:
            info = json.loads(s["subscription_json"])
            ok, _ = send_push(
                info,
                "Fitness Tracker",
                f"¡Hola {nombre}! Registra tu peso o completa el entreno de hoy.",
                url="/",
            )
            if ok:
                enviados += 1
    return enviados


def iniciar_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        def job():
            with app.app_context():
                from app import get_db_connection

                with get_db_connection() as conn:
                    enviar_recordatorios(conn)
                    conn.commit()

        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(job, "cron", minute="*")
        _scheduler.start()
    except ImportError:
        pass
