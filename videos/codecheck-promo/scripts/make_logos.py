"""Логотипы НовГУ для ролика: убрать белый фон.

- novsu-white.png — логотип университета (синяя линия на белом) → белый на прозрачном:
  синий на чёрном фоне ролика почти не читается, поэтому альфа = «насколько пиксель не белый».
- ieis-emblem.png — герб ИЭИС: убирается только ВНЕШНИЙ белый фон (заливка от краёв),
  белые орбиты внутри герба остаются.
Запуск: python3 scripts/make_logos.py <путь к гербу.jpg> <путь к логотипу.webp>
"""
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

out = Path(__file__).resolve().parents[1] / "assets" / "logos"
emblem_src, novsu_src = sys.argv[1], sys.argv[2]

# ── логотип университета: белый на прозрачном ──
im = Image.open(novsu_src).convert("RGB")
w, h = im.size
alpha = Image.new("L", (w, h))
px, ap = im.load(), alpha.load()
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        ap[x, y] = max(0, min(255, int((255 - min(r, g, b)) * 1.6)))   # сила линии, сглаженные края сохраняются
white = Image.new("RGBA", (w, h), (255, 255, 255, 0))
white.putalpha(alpha)
white.crop(white.getbbox()).save(out / "novsu-white.png")

# ── герб: заливка внешнего белого от краёв ──
em = Image.open(emblem_src).convert("RGBA")
w, h = em.size
p = em.load()
is_bg = lambda c: c[0] > 228 and c[1] > 228 and c[2] > 228
seen = bytearray(w * h)
q = deque([(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)])
mask = Image.new("L", (w, h), 255)
mp = mask.load()
while q:
    x, y = q.popleft()
    if not (0 <= x < w and 0 <= y < h) or seen[y * w + x]:
        continue
    seen[y * w + x] = 1
    if not is_bg(p[x, y]):
        continue
    mp[x, y] = 0
    q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))  # мягкий край без белой каймы
em.putalpha(mask)
em.crop(em.getbbox()).save(out / "ieis-emblem.png")
print("✓", out / "novsu-white.png", out / "ieis-emblem.png")
