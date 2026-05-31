#!/usr/bin/env python3
"""Genera iconos PWA desde tu imagen (iPhone, Android, manifest).

Uso:
  1. Coloca tu imagen en static/icons/app-icon-source.png (o .jpg / .jpeg / .webp)
  2. Ejecuta: python scripts/generate_icons.py
  3. Sube los PNG generados a GitHub y redespliega en Render
  4. En el iPhone: borra el acceso directo viejo y vuelve a "Añadir a pantalla de inicio"
"""
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    print("Instala Pillow: pip install pillow")
    raise

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

SIZES = {
    "apple-touch-icon.png": 180,   # iPhone (obligatorio)
    "icon-192.png": 192,
    "icon-512.png": 512,
    "icon-512-maskable.png": 512,
}


def find_source():
    for name in (
        "app-icon-source.png",
        "app-icon-source.jpg",
        "app-icon-source.jpeg",
        "app-icon-source.webp",
    ):
        path = OUT / name
        if path.is_file():
            return path
    return None


def make_fallback(size):
    """Icono por defecto si no hay imagen fuente."""
    img = Image.new("RGBA", (size, size), (11, 18, 32, 255))
    draw = ImageDraw.Draw(img)
    margin = size // 7
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 5,
        fill=(38, 166, 154, 255),
    )
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("arial.ttf", max(18, size // 4))
    except OSError:
        font = ImageFont.load_default()
    text = "FT"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - size * 0.02), text, fill=(255, 255, 255, 255), font=font)
    return img


def square_icon(source_path, size, maskable=False):
    img = Image.open(source_path).convert("RGBA")
    if maskable:
        # Margen extra para iconos "maskable" (Android recorta en círculo)
        canvas = Image.new("RGBA", (size, size), (11, 18, 32, 255))
        inner = int(size * 0.72)
        fitted = ImageOps.fit(img, (inner, inner), Image.Resampling.LANCZOS)
        offset = (size - inner) // 2
        canvas.paste(fitted, (offset, offset), fitted)
        return canvas
    return ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)


def main():
    source = find_source()
    if source:
        print(f"Usando imagen: {source}")
    else:
        print("No hay app-icon-source.* — generando icono por defecto.")
        print("Para usar tu imagen, copia un PNG/JPG a static/icons/app-icon-source.png")

    for filename, size in SIZES.items():
        maskable = "maskable" in filename
        if source:
            icon = square_icon(source, size, maskable=maskable)
        else:
            icon = make_fallback(size)
        if icon.mode == "RGBA":
            bg = Image.new("RGB", icon.size, (11, 18, 32))
            bg.paste(icon, mask=icon.split()[3])
            icon = bg
        path = OUT / filename
        icon.save(path, "PNG", optimize=True)
        print("OK", path, f"({size}x{size})")


if __name__ == "__main__":
    main()
