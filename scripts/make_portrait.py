"""Convert source/photo.jpg into ASCII art for the hero panel.

Run locally (needs onnxruntime + opencv + the u2net_human_seg model); the output is committed as
data/portrait.json so CI never has to run the heavy ML model.

    python scripts/make_portrait.py
"""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

INPUT_FILE = Path("source/photo.jpg")
OUTPUT_FILE = Path("data/portrait.json")
MODEL_FILE = Path.home() / ".u2net" / "u2net_human_seg.onnx"

COLS = 112
ROWS = 70
CELL_ASPECT = 0.6 / 1.0  # glyph width / line height used by the hero panel

# Sparse -> dense. Bright pixels get dense glyphs (light text on dark bg).
RAMP = " .`':,;-~=+<icvxzjtfLJunoaeszyXUCQOZmwpqdbkhKA8%#B&WM@"
PALETTE_SIZE = 14
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
MASK_CUTOFF = 0.35


def remove_background(img):
    """Person mask (0..1) from rembg's u2net_human_seg model, run directly.

    Importing rembg itself pulls in numba and can JIT-compile for minutes, so
    we only borrow its model file (downloaded once by rembg to ~/.u2net).
    """
    import onnxruntime as ort

    session = ort.InferenceSession(str(MODEL_FILE), providers=["CPUExecutionProvider"])
    x = np.asarray(img.resize((320, 320), Image.Resampling.LANCZOS), np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    pred = session.run(None, {session.get_inputs()[0].name: x})[0][0, 0]
    pred = (pred - pred.min()) / (pred.max() - pred.min() + 1e-8)
    return cv2.resize(pred, img.size, interpolation=cv2.INTER_LINEAR)


def main():
    img = Image.open(INPUT_FILE).convert("RGB")
    alpha = remove_background(img)
    rgb = np.asarray(img)

    # Crop head-and-shoulders to the panel's aspect ratio.
    h, w = alpha.shape
    target = (COLS * CELL_ASPECT) / ROWS
    x0, x1 = int(w * 0.08), int(w * 0.92)
    crop_h = int((x1 - x0) / target)
    y0 = int(h * 0.035)
    y1 = min(h, y0 + crop_h)
    rgb = rgb[y0:y1, x0:x1]
    alpha = alpha[y0:y1, x0:x1]

    # Local contrast on luminance so skin, eyes and shirt folds keep detail.
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(6, 6))
    lum = clahe.apply(lab[:, :, 0]).astype(np.float32) / 255.0

    # Edge map gives hair and facial contours structure where tone is flat.
    blur = cv2.GaussianBlur(lum, (0, 0), 2.0)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    edges = np.sqrt(gx * gx + gy * gy)
    edges = np.clip(edges / np.percentile(edges, 99), 0, 1)

    size = (COLS, ROWS)
    lum_s = cv2.resize(lum, size, interpolation=cv2.INTER_AREA)
    edge_s = cv2.resize(edges, size, interpolation=cv2.INTER_AREA)
    mask_s = cv2.resize(alpha, size, interpolation=cv2.INTER_AREA)

    # Stretch tones inside the silhouette only, so the face gets the range
    # instead of the white shirt and the backdrop.
    body = lum_s[mask_s > 0.5]
    lo, hi = np.percentile(body, 4), np.percentile(body, 80)
    lum_s = np.clip((lum_s - lo) / (hi - lo), 0, 1) ** 0.8
    value = np.clip(0.1 + 0.9 * lum_s + 0.35 * edge_s, 0, 1)
    value *= np.clip(mask_s * 1.4, 0, 1)  # soften the silhouette edge

    # Colour: hue from the photo, brightness from the tone-mapped value, so
    # skin, hair and shirt separate while staying bright enough on black.
    rgb_s = cv2.resize(rgb, size, interpolation=cv2.INTER_AREA).astype(np.float32)
    hue = rgb_s / np.maximum(rgb_s.max(axis=2, keepdims=True), 1)
    hue = 0.75 * hue + 0.25 * hue.mean(axis=2, keepdims=True)  # tame saturation
    colour = hue * (0.22 + 0.78 * value[..., None]) * 255

    # Quantise to a small palette so each row collapses into few SVG runs.
    inside = mask_s >= MASK_CUTOFF
    samples = colour[inside].reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    cv2.setRNGSeed(7)
    _, labels, centers = cv2.kmeans(samples, PALETTE_SIZE, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    order = np.argsort(centers.sum(axis=1))  # dark -> light, stable output
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    index = np.zeros(size[::-1], np.int32)
    index[inside] = rank[labels.ravel()]
    palette = ["#%02x%02x%02x" % tuple(int(c) for c in centers[i]) for i in order]

    lines, shades = [], []
    for y in range(ROWS):
        line, shade = [], []
        for x in range(COLS):
            if not inside[y, x]:
                line.append(" ")
                shade.append("0")
                continue
            # A density floor keeps dark hair solid; colour carries the tone.
            v = 0.3 + 0.7 * value[y, x]
            line.append(RAMP[min(len(RAMP) - 1, 1 + int(v * (len(RAMP) - 2)))])
            shade.append(DIGITS[index[y, x]])
        lines.append("".join(line))
        shades.append("".join(shade))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps({"cols": COLS, "rows": ROWS, "palette": palette,
                    "lines": lines, "shades": shades}, indent=1),
        encoding="utf-8",
    )
    print("\n".join(lines))
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
