#!/usr/bin/env python3
"""Закрывает лица мозаикой на фотографиях клиентов.

    python3 tools/blur_faces.py              — пройтись по всей галерее
    python3 tools/blur_faces.py --dry        — только показать, что найдено

Лица ищет нейросетевая модель YuNet (tools/face-model.onnx). Снимки перед
поиском увеличиваются втрое: люди на них стоят далеко от камеры и лица
занимают полсотни точек, иначе модель их не видит.

Уже закрытые лица модель не находит — это нормально, повторно их трогать
не нужно.
"""

import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIENTS = ROOT / "img/clients"
MODEL = ROOT / "tools/face-model.onnx"
SCALE = 3        # во сколько раз увеличиваем перед поиском
CONF = 0.55      # порог уверенности
GROW = 0.28      # насколько расширяем рамку — модель обводит лицо впритык
CELLS = 9        # на сколько клеток мозаики делим лицо


def find(im):
    big = cv2.resize(im, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
    h, w = big.shape[:2]
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), CONF, 0.3, 5000)
    det.setInputSize((w, h))
    _, out = det.detect(big)
    if out is None:
        return []
    return [tuple(int(v / SCALE) for v in box[:4]) for box in out]


def pixelate(im, box):
    x, y, w, h = box
    gx, gy = int(w * GROW), int(h * GROW)
    x, y = max(0, x - gx), max(0, y - gy)
    w, h = min(im.shape[1] - x, w + 2 * gx), min(im.shape[0] - y, h + 2 * gy)
    if w < 4 or h < 4:
        return
    face = im[y:y + h, x:x + w]
    small = cv2.resize(face, (CELLS, CELLS), interpolation=cv2.INTER_AREA)
    im[y:y + h, x:x + w] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def main(dry=False):
    changed = faces = 0
    for f in sorted(CLIENTS.glob("client-*.jpg")):
        im = cv2.imread(str(f))
        boxes = find(im)
        faces += len(boxes)
        mark = "—" if not boxes else f"{len(boxes)}"
        print(f"  {f.name}: {mark}")
        if boxes and not dry:
            for b in boxes:
                pixelate(im, b)
            cv2.imwrite(str(f), im, [cv2.IMWRITE_JPEG_QUALITY, 80])
            changed += 1
    print(f"\nнайдено лиц: {faces}" + ("" if dry else f", обработано снимков: {changed}"))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
