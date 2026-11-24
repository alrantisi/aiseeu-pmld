"""Gambar zona ROI di atas snapshot. Dipakai Setup ROI dan preview Dashboard."""

from PIL import Image, ImageDraw, ImageFont

COLORS = ["#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"]
LINE_W = 4
DOT_R = 7
LABEL_MARGIN = 6

try:
    FONT = ImageFont.load_default(size=22)
    FONT_SM = ImageFont.load_default(size=18)
except Exception:  # Pillow tanpa dukungan ukuran font
    FONT = FONT_SM = ImageFont.load_default()


def hex_to_rgba(color, alpha):
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)


def polygon_centroid(px):
    """Titik tengah poligon (berbobot luas). Kalau luasnya nol, pakai rata-rata titik."""
    area = 0.0
    cx = 0.0
    cy = 0.0
    n = len(px)
    for i in range(n):
        x0, y0 = px[i]
        x1, y1 = px[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area) < 1e-6:
        return (sum(p[0] for p in px) / n, sum(p[1] for p in px) / n)
    area *= 0.5
    return (cx / (6 * area), cy / (6 * area))


def label_position(draw, text, font, px, size):
    """Posisi gambar teks: di tengah poligon dan tidak keluar dari batas gambar."""
    width, height = size
    cx, cy = polygon_centroid(px)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    tw, th = right - left, bottom - top
    x = min(max(cx - tw / 2, LABEL_MARGIN), max(width - tw - LABEL_MARGIN, LABEL_MARGIN))
    y = min(max(cy - th / 2, LABEL_MARGIN), max(height - th - LABEL_MARGIN, LABEL_MARGIN))
    return (x - left, y - top)


def draw_zones(base, zones, draft_points=None):
    """Return gambar RGB: snapshot + zona tersimpan (+ titik draft kalau ada).

    zones: list dict {zone_id, zone_name, points:[[x,y],...]} skala 0 sampai 1.
    draft_points: list (x, y) skala 0 sampai 1, titik yang sedang diklik.
    """
    width, height = base.size

    def to_px(point):
        return (point[0] * width, point[1] * height)

    img = base.copy().convert("RGBA")

    # Isi zona dengan warna transparan supaya areanya jelas terlihat.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for i, z in enumerate(zones):
        px = [to_px(p) for p in z["points"]]
        overlay_draw.polygon(px, fill=hex_to_rgba(COLORS[i % len(COLORS)], 55))
    img = Image.alpha_composite(img, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    for i, z in enumerate(zones):
        color = COLORS[i % len(COLORS)]
        px = [to_px(p) for p in z["points"]]
        draw.line(px + [px[0]], fill=color, width=LINE_W)
        name = z.get("zone_name", z.get("zone_id", ""))
        draw.text(
            label_position(draw, name, FONT, px, img.size),
            name,
            fill=color,
            font=FONT,
            stroke_width=2,
            stroke_fill="#000000",
        )

    if draft_points:
        px = [to_px(p) for p in draft_points]
        if len(px) > 1:
            draw.line(px, fill="#ffffff", width=LINE_W)
        for n, (x, y) in enumerate(px, start=1):
            draw.ellipse(
                (x - DOT_R, y - DOT_R, x + DOT_R, y + DOT_R),
                fill="#e8a317",
                outline="#ffffff",
                width=2,
            )
            draw.text(
                (x + DOT_R + 4, y - DOT_R - 14),
                str(n),
                fill="#ffffff",
                font=FONT_SM,
                stroke_width=2,
                stroke_fill="#000000",
            )
    return img
