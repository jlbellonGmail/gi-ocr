from __future__ import annotations

import argparse
import sys
from pathlib import Path


def load_dependencies():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias para ejecutar este script. "
            "Instalá requirements con: pip install -r backend/requirements.txt"
        ) from exc

    return cv2, np


def detect_red_zones(image_path: Path, output_path: Path) -> None:
    cv2, np = load_dependencies()

    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    image = cv2.imread(str(image_path))

    if image is None:
        raise RuntimeError(f"No se pudo leer la imagen: {image_path}")

    image_height, image_width = image.shape[:2]

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_red_1 = np.array([0, 100, 100])
    upper_red_1 = np.array([10, 255, 255])
    lower_red_2 = np.array([170, 100, 100])
    upper_red_2 = np.array([180, 255, 255])

    mask_1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
    mask_2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
    mask = cv2.bitwise_or(mask_1, mask_2)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    zones = []

    for contour in contours:
        x, y, zone_width, zone_height = cv2.boundingRect(contour)

        if zone_width <= 50 or zone_height <= 20:
            continue

        x1 = round((x / image_width) * 100, 1)
        y1 = round((y / image_height) * 100, 1)
        x2 = round(((x + zone_width) / image_width) * 100, 1)
        y2 = round(((y + zone_height) / image_height) * 100, 1)

        zones.append(
            {
                "x": x,
                "y": y,
                "width": zone_width,
                "height": zone_height,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            }
        )

    zones.sort(key=lambda zone: (zone["y"], zone["x"]))

    print(f"Imagen: {image_path}")
    print(f"Tamaño: {image_width}x{image_height}")
    print(f"Zonas detectadas: {len(zones)}")
    print()

    display = image.copy()

    for index, zone in enumerate(zones, start=1):
        print(f"Zona {index}: {zone['x1']},{zone['y1']},{zone['x2']},{zone['y2']}")

        cv2.rectangle(
            display,
            (zone["x"], zone["y"]),
            (zone["x"] + zone["width"], zone["y"] + zone["height"]),
            (0, 255, 0),
            2,
        )

        cv2.putText(
            display,
            f"Z{index}",
            (zone["x"], max(zone["y"] - 8, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    saved = cv2.imwrite(str(output_path), display)

    if not saved:
        raise RuntimeError(f"No se pudo guardar la imagen debug en: {output_path}")

    print()
    print(f"Imagen debug guardada en: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detecta rectángulos rojos en una imagen marcada y devuelve coordenadas porcentuales."
    )

    parser.add_argument(
        "image",
        help="Ruta de la imagen marcada.",
    )

    parser.add_argument(
        "--output",
        default="_debug/zones_detected.png",
        help="Ruta de salida para la imagen debug.",
    )

    args = parser.parse_args()

    try:
        detect_red_zones(
            image_path=Path(args.image),
            output_path=Path(args.output),
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
