"""Punto de entrada para producción (Gunicorn en Render u otros hosts)."""
from dotenv import load_dotenv

load_dotenv()

from app import app, init_db  # noqa: E402
from services import push_notifications as push_svc  # noqa: E402

init_db()
push_svc.iniciar_scheduler(app)

application = app
