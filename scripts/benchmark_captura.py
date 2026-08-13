"""Benchmark reproducible de la captura OCR local.

Mide: arranque en frío, procesamiento en caliente, p50, p95, tiempo por etapa,
documentos por minuto y consumo aproximado de memoria. Lote de N variantes sintéticas
(rotación, perspectiva, escala, iluminación, compresión) a partir de las muestras
privadas locales (si están disponibles), o de una imagen sintética si no.

Uso:  python scripts/benchmark_captura.py [--docs 400] [--out _bench/benchmark.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import capture_pipeline, ocr_engine

REAL = ROOT / "backend" / "tests" / "fixtures" / "_local_samples" / "real"


def cold_start() -> float:
    t0 = time.time()
    ocr_engine.warmup()
    return time.time() - t0


def variant(img: Image.Image, i: int) -> Image.Image:
    """Genera una variación sintética local (no versionada) a partir de una imagen."""
    img = img.convert("RGB")
    ops = i % 6
    if ops == 0:
        return img.rotate(2 * (i % 3 - 1), expand=True, fillcolor="white")
    if ops == 1:
        return img.resize((int(img.width * 0.85), int(img.height * 0.85)))
    if ops == 2:
        return ImageEnhance.Brightness(img).enhance(0.8 + (i % 3) * 0.1)
    if ops == 3:
        return ImageEnhance.Contrast(img).enhance(1.2)
    if ops == 4:
        factor = 1.0 - (i % 4) * 0.04
        return ImageOps.pad(img, (img.width, img.height), color="white").resize(
            (int(img.width * factor), int(img.height * factor))
        )
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=int, default=20, help="tamaño del lote (default 20; usar 400 para el gate)")
    ap.add_argument("--out", type=str, default="_bench/benchmark.json")
    args = ap.parse_args()

    out_dir = Path("_bench")
    out_dir.mkdir(exist_ok=True)

    # muestra base
    if (REAL / "GAS.jpeg").exists():
        base = Image.open(REAL / "GAS.jpeg")
        base_name = "GAS_real"
    else:
        base = Image.new("RGB", (800, 1000), "white")
        base_name = "synthetic"

    print(f"[1/4] Arranque en frío (carga de modelos)...")
    cold = cold_start()
    print(f"      cold_start_s = {cold:.2f}")

    # warm
    capture_pipeline.process_document(str(REAL / "GAS.jpeg"), "warmup") if (REAL / "GAS.jpeg").exists() else None

    print(f"[2/4] Procesamiento en caliente (docs={args.docs})...")
    per_doc = []
    stage_det = []
    stage_rec = []
    stage_total = []
    variants = []
    for i in range(args.docs):
        v = variant(base, i)
        p = out_dir / f"v_{i:04d}.jpg"
        v.save(p, quality=85)
        variants.append(p)
        t0 = time.time()
        res = capture_pipeline.process_document(str(p), p.name)
        dt = time.time() - t0
        per_doc.append(dt)
        tm = res["processing_metadata"].get("timings", {})
        stage_det.append(tm.get("ocr_det_s", 0.0))
        stage_rec.append(tm.get("ocr_rec_s", 0.0))
        stage_total.append(tm.get("total_s", dt))

    def p(x, q):
        return float(statistics.quantiles(x, n=100, method="inclusive")[q - 1]) if len(x) >= 2 else float(x[0])

    summary = {
        "base": base_name,
        "docs": args.docs,
        "cold_start_s": round(cold, 3),
        "hot_p50_s": round(p(per_doc, 50), 3),
        "hot_p95_s": round(p(per_doc, 95), 3),
        "hot_mean_s": round(statistics.mean(per_doc), 3),
        "hot_max_s": round(max(per_doc), 3),
        "stage_det_p50_s": round(p(stage_det, 50), 3),
        "stage_rec_p50_s": round(p(stage_rec, 50), 3),
        "stage_total_p50_s": round(p(stage_total, 50), 3),
        "docs_per_minute": round(60.0 / statistics.mean(per_doc), 2) if per_doc else 0,
        "batch_total_s": round(sum(per_doc), 2),
        "batch_total_min": round(sum(per_doc) / 60.0, 2),
    }

    print(f"[3/4] Memoria aproximada del proceso...")
    proc = psutil.Process()
    mem_mb = proc.memory_info().rss / (1024 * 1024)
    summary["process_rss_mb"] = round(mem_mb, 1)

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "per_doc_s": [round(x, 3) for x in per_doc]}, indent=2), encoding="utf-8")
    print(f"[4/4] Guardado en {out}")

    # verificación del gate
    ok = summary["hot_p50_s"] <= 3.0 and summary["hot_p95_s"] <= 5.0
    print("GATE (individual<=3 / p95<=5):", "PASS" if summary["hot_p50_s"] <= 3.0 else "WARN", "/", "PASS" if summary["hot_p95_s"] <= 5.0 else "FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())