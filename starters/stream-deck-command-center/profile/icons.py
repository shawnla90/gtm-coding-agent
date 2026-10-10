"""Key art for the Stream Deck + (144x144 PNG, label baked into the image so it stays crisp).

Sources live in icons/src: app-*.png pulled from installed .app bundles and web-*.png
from site favicons (icons/fetch_icons.sh does both). A missing source never breaks the
build: you get a colored letter tile instead, so a fresh clone renders on day one.
Each function returns PNG bytes; build_profile.py drops them into each page's Images/.
"""
import hashlib
import io
import os

from PIL import Image, ImageDraw, ImageFont

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(KIT, "icons", "src")
SIZE = 144
BG = (18, 18, 20, 255)
CLAUDE_ORANGE = (217, 119, 87)
FONT_PATHS = ["/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc"]
MONO_PATHS = ["/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc"]


def _font(size, paths=FONT_PATHS):
    for p in paths:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            try:
                f.set_variation_by_name("Bold")
            except Exception:
                pass
            return f
    return ImageFont.load_default()


def _letter_tile(name):
    """Fallback art: first letter of the name on a color derived from the name."""
    word = name.split("-", 1)[-1] or name
    h = hashlib.md5(word.encode()).digest()
    color = (60 + h[0] % 160, 60 + h[1] % 160, 60 + h[2] % 160, 255)
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 255, 255), 52, fill=color)
    d.text((128, 136), word[0].upper(), font=_font(160), fill="white", anchor="mm")
    return im


def _src(name):
    p = os.path.join(SRC, name + ".png")
    if not name or not os.path.exists(p):
        return _letter_tile(name or "?")
    im = Image.open(p).convert("RGBA")
    return im.crop(im.getbbox() or (0, 0, *im.size))


def _fit(im, box):
    im = im.copy()
    im.thumbnail((box, box), Image.LANCZOS)
    if max(im.size) < box:  # upscale small favicons
        s = box / max(im.size)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im


def _label(d, text):
    size = 19 if len(text) <= 9 else 16 if len(text) <= 12 else 14
    d.text((SIZE // 2, 127), text, font=_font(size), fill="white", anchor="mm")


def _png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def single(src, label, plate=False):
    """One icon over a label. plate=True sets dark favicons on a white rounded plate."""
    im = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(im)
    top = 12
    if plate:
        d.rounded_rectangle((28, top, 116, top + 88), 20, fill=(255, 255, 255, 255))
        icon = _fit(_src(src), 60)
    else:
        icon = _fit(_src(src), 88)
    im.alpha_composite(icon, ((SIZE - icon.width) // 2, top + (88 - icon.height) // 2))
    _label(d, label)
    return _png(im)


def grid(srcs, label, tint=None):
    """2x2 mini icons for folders (tinted border) and multi-app keys."""
    im = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(im)
    if tint:  # translucent wash so the label keeps contrast
        wash = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(wash).rounded_rectangle((5, 5, SIZE - 6, SIZE - 6), 22, fill=tuple(tint) + (46,),
                                               outline=tuple(tint) + (255,), width=4)
        im.alpha_composite(wash)
    cell, gap, top = 40, 6, 14
    left = (SIZE - (2 * cell + gap)) // 2
    for i, s in enumerate(srcs[:4]):
        icon = _fit(_src(s), cell)
        x = left + (i % 2) * (cell + gap) + (cell - icon.width) // 2
        y = top + (i // 2) * (cell + gap) + (cell - icon.height) // 2
        im.alpha_composite(icon, (x, y))
    _label(d, label)
    return _png(im)


def glyph(big, label, color=CLAUDE_ORANGE):
    """Command keys: a big monospace glyph ("/c", "esc") in a tinted box over a label."""
    im = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((16, 14, SIZE - 17, 100), 18, fill=tuple(color) + (40,),
                        outline=tuple(color) + (255,), width=3)
    size = 40 if len(big) <= 3 else 30 if len(big) <= 5 else 24
    d.text((SIZE // 2, 57), big, font=_font(size, MONO_PATHS), fill="white", anchor="mm")
    _label(d, label)
    return _png(im)


def back(label="BACK"):
    im = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(im)
    c, w = (235, 235, 240), 9
    for seg in ((50, 56, 98, 56), (50, 56, 72, 34), (50, 56, 72, 78)):
        d.line(seg, fill=c, width=w)
    for x, y in ((50, 56), (72, 34), (72, 78), (98, 56)):
        d.ellipse((x - w // 2, y - w // 2, x + w // 2, y + w // 2), fill=c)
    _label(d, label)
    return _png(im)
