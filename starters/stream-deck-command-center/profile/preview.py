#!/usr/bin/env python3
"""Render every page of the built profile as one contact sheet, so you can check the art
before anything touches Stream Deck.

    python3 profile/preview.py [out.png]      (default: profile/preview.png)

Plugin keys that draw their own art show as outlined boxes with their title.
"""
import glob
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, PAD, GUTTER = 144, 10, 110


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KIT, "profile", "preview.png")
    built = [p for p in glob.glob(os.path.join(KIT, "out", "*.streamDeckProfile")) if "MCP Actions" not in p]
    if not built:
        raise SystemExit("Nothing built yet: run python3 profile/build_profile.py")
    z = zipfile.ZipFile(built[0])
    rows = []
    for n in z.namelist():
        if n.endswith("manifest.json") and n.count("/") == 4:
            m = json.loads(z.read(n))
            if m.get("Name") and m["Controllers"][0]["Actions"]:
                rows.append((m["Name"] != "HOME", m["Name"], m, n.rsplit("/", 1)[0]))
    rows.sort(key=lambda r: (r[0], r[1]))  # HOME first, then alphabetical
    sheet = Image.new("RGB", (GUTTER + 4 * (W + PAD), PAD + len(rows) * (2 * W + 3 * PAD)), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    for r, (_, name, m, base) in enumerate(rows):
        y0 = PAD + r * (2 * W + 3 * PAD)
        d.text((8, y0 + W), name, fill="white")
        for k, a in m["Controllers"][0]["Actions"].items():
            col, row = map(int, k.split(","))
            x, y = GUTTER + col * (W + PAD), y0 + row * (W + PAD)
            img = a["States"][0].get("Image")
            if img:
                sheet.paste(Image.open(io.BytesIO(z.read(base + "/" + img))).convert("RGB"), (x, y))
            else:
                d.rectangle((x, y, x + W, y + W), outline="gray")
                d.text((x + 10, y + 64), a["States"][0]["Title"] + " (plugin)", fill="white")
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
