#!/usr/bin/env python3
"""Добавляет фотографии клиентов в галерею на главной.

    python3 tools/clients.py путь/к/фото1.jpg путь/к/фото2.jpg ...

Новые снимки встают в начало галереи, а старые сдвигаются следом —
свежие выдачи должны быть на виду. Файлы приводятся к вертикальному
кадру 3:4 под размер плитки, поэтому исходники можно кидать какие есть.
"""

import pathlib
import sys

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
DST = ROOT / "img/clients"
SIZE = (560, 747)  # плитка 3:4, с запасом под экраны с высокой плотностью
QUALITY = 80


def existing():
    return sorted(DST.glob("client-*.jpg"))


def add(sources):
    DST.mkdir(parents=True, exist_ok=True)
    old = existing()

    # старые уводим во временные имена, чтобы освободить начало нумерации
    parked = []
    for i, f in enumerate(old):
        tmp = DST / f"parked-{i:03d}.jpg"
        f.rename(tmp)
        parked.append(tmp)

    n = 0
    for src in sources:
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        im = ImageOps.fit(im, SIZE, Image.LANCZOS, centering=(0.5, 0.4))
        n += 1
        out = DST / f"client-{n:03d}.jpg"
        im.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        print(f"  {out.name}  {out.stat().st_size/1024:3.0f} КБ   ← {pathlib.Path(src).name}")

    for tmp in parked:
        n += 1
        tmp.rename(DST / f"client-{n:03d}.jpg")

    total = sum(f.stat().st_size for f in existing()) / 1024
    print(f"\nв галерее: {n} фотографий ({len(sources)} новых впереди), {total:.0f} КБ")
    print("дальше: python3 build.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    add(sys.argv[1:])
