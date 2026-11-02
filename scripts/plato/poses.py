"""Poses del presentador (recortadas del fondo verde) y su animación de boca y parpadeo."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
# corte: fila donde empieza la mesa de la foto (las manos se apoyan ahí)
POSES = {
    "manos":     dict(corte=492, labio=187, boca=(235, 280), ojos=[(228, 130), (283, 130)]),
    "explica":   dict(corte=490, labio=191, boca=(245, 295), ojos=[(259, 127), (308, 132)]),
    "senala":    dict(corte=490, labio=192, boca=(165, 215), ojos=[(161, 132), (213, 130)]),
    "inclinado": dict(corte=496, labio=217, boca=(389, 444), ojos=[(386, 147), (447, 147)]),
    "papeles":   dict(corte=496, labio=195, boca=(329, 384), ojos=[(329, 125), (387, 126)]),
}
ARCHIVOS = {"manos": "p1_manos", "explica": "p2_explica", "senala": "p3_senala",
            "inclinado": "p4_inclinado", "papeles": "p5_papeles"}

def cargar():
    out = {}
    for k, lm in POSES.items():
        im = Image.open(os.path.join(RAIZ, "videos", "plato", "poses", ARCHIVOS[k] + ".png")).convert("RGBA")
        out[k] = im.crop((0, 0, im.width, lm["corte"]))
    return out

def distancia_ojos(lm):
    (x0, y0), (x1, y1) = lm["ojos"]
    return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5

def animar(base, lm, boca, parpadeo):
    im = base.copy()
    e = (lm["boca"][1] - lm["boca"][0]) / 120.0   # escala respecto a la cara de referencia
    ed = distancia_ojos(lm)
    L = lm["labio"]; cx = (lm["boca"][0] + lm["boca"][1]) / 2
    if boca > 0.02:
        d = boca * 16.0 * e
        arr = np.asarray(im).astype(np.float32); h, w = arr.shape[:2]
        y_ini, y_fin = L, min(h, int(L + 171 * e))
        x_ini, x_fin = max(0, int(cx - 130 * e)), min(w, int(cx + 130 * e))
        ys = np.arange(y_ini, y_fin); xs = np.arange(x_ini, x_fin)
        wx = np.clip(1 - ((xs - cx) / (130.0 * e)) ** 2, 0, 1) ** 0.7
        meseta = 30 * e
        wy = np.where(ys < L + meseta, 1.0, np.clip(1 - (ys - L - meseta) / max(y_fin - L - meseta, 1), 0, 1))
        src = np.clip(ys[:, None] - d * wy[:, None] * wx[None, :], 0, h - 1)
        y0 = np.floor(src).astype(int); fr = (src - y0)[..., None]; y1 = np.clip(y0 + 1, 0, h - 1)
        X = np.broadcast_to(xs[None, :], src.shape)
        arr[y_ini:y_fin, x_ini:x_fin] = arr[y0, X] * (1 - fr) + arr[y1, X] * fr
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        capa = Image.new("RGBA", im.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(capa)
        mx0, mx1 = lm["boca"][0] + 14 * e, lm["boca"][1] - 14 * e
        alto = max(d * 0.95, 1)
        dc.ellipse([mx0, L - 2 * e, mx1, L - 2 * e + alto], fill=(45, 14, 16, 255))
        if alto > 6 * e:
            dc.ellipse([mx0 + 16 * e, L - 3 * e, mx1 - 16 * e, L - 3 * e + alto * 0.32], fill=(226, 220, 210, 235))
        im.alpha_composite(capa.filter(ImageFilter.GaussianBlur(max(1.6 * e, 0.7))))
    if parpadeo > 0.05:
        capa = Image.new("RGBA", im.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(capa)
        k = ed / 149.0; px = np.asarray(base)
        for ex, ey in lm["ojos"]:
            parche = px[int(ey + 22 * k):int(ey + 34 * k) + 1, int(ex - 12 * k):int(ex + 12 * k) + 1, :3].reshape(-1, 3)
            piel = tuple(int(v * 0.93) for v in parche.mean(axis=0))
            rx, ry = 25 * k, 12 * k
            baja = ey - ry + 2 * ry * parpadeo
            dc.ellipse([ex - rx, ey - ry - 4 * k, ex + rx, baja], fill=piel + (255,))
            dc.line([(ex - rx + 4 * k, baja - 1), (ex + rx - 4 * k, baja - 1)], fill=(60, 40, 35, 220), width=max(1, int(3 * k)))
        im.alpha_composite(capa.filter(ImageFilter.GaussianBlur(max(1.4 * k, 0.6))))
    return im
