"""Servidor local compatible con Windows (Gunicorn solo funciona en Linux)."""
from waitress import serve

from wsgi import application

if __name__ == "__main__":
    print("Fitness Tracker → http://127.0.0.1:5000")
    print("Ctrl+C para detener")
    serve(application, host="127.0.0.1", port=5000)
