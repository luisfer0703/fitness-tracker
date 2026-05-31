#!/usr/bin/env python3
"""Genera iconos PWA mínimos en static/icons/"""
import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("pip install pillow")
    raise

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def make_icon(size):
    img = Image.new("RGBA", (size, size), (11, 18, 32, 255))
    d = ImageDraw.Draw(img)
    margin = size // 8
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 6,
        fill=(38, 166, 154, 255),
    )
    d.text((size // 2 - size // 8, size // 2 - size // 10), "FT", fill=(4, 42, 39, 255))
    return img


for s in (192, 512):
    p = OUT / f"icon-{s}.png"
    make_icon(s).save(p)
    print("OK", p)
