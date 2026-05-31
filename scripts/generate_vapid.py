#!/usr/bin/env python3
"""Genera claves VAPID para Web Push. Copia el resultado a tu archivo .env"""
from py_vapid import Vapid

v = Vapid()
v.generate_keys()
print("VAPID_PUBLIC_KEY=" + v.public_key.decode() if isinstance(v.public_key, bytes) else v.public_key)
print("VAPID_PRIVATE_KEY=" + (v.private_key.decode() if isinstance(v.private_key, bytes) else v.private_key))
print("VAPID_CLAIM_EMAIL=mailto:tu-email@ejemplo.com")
