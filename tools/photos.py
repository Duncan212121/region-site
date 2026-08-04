#!/usr/bin/env python3
"""Готовит фотографии машины для сайта.

    python3 tools/photos.py toyota-rav4 путь/к/фото1.jpg путь/к/фото2.jpg ...

Порядок аргументов = порядок фотографий на странице, первая идёт в каталог.
Для каждой сохраняется два файла: 01.jpg — крупная, для галереи, и
01-sm.jpg — уменьшенная, для карточки в каталоге и миниатюр. Карточке не
нужен полноразмерный кадр, а на 22 машины разница набегает в мегабайты.
"""

import pathlib
import sys

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIG, SMALL = 1600, 640
Q_BIG, Q_SMALL = 78, 74


def process(slug, sources):
    dst = ROOT / "img/cars" / slug
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob("*.jpg"):
        old.unlink()

    total = 0
    for i, src in enumerate(sources, 1):
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")

        big = im if im.width <= BIG else im.resize(
            (BIG, round(im.height * BIG / im.width)), Image.LANCZOS)
        big_path = dst / f"{i:02d}.jpg"
        big.save(big_path, "JPEG", quality=Q_BIG, optimize=True, progressive=True)

        small = im.resize((SMALL, round(im.height * SMALL / im.width)), Image.LANCZOS)
        small_path = dst / f"{i:02d}-sm.jpg"
        small.save(small_path, "JPEG", quality=Q_SMALL, optimize=True, progressive=True)

        kb = (big_path.stat().st_size + small_path.stat().st_size) / 1024
        total += kb
        print(f"  {big_path.name:10} {big.width}×{big.height}  "
              f"{big_path.stat().st_size/1024:4.0f} КБ  + мелкая {small_path.stat().st_size/1024:3.0f} КБ")

    print(f"\n{slug}: {len(sources)} фото, {total:.0f} КБ")
    print("не забудь прописать имена в data/cars.json и запустить python3 build.py")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    process(sys.argv[1], sys.argv[2:])
