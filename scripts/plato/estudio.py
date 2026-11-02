import sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
K = 3            # escala del lienzo respecto a la imagen del plató
T, B = 200, 330  # extensión de techo y suelo (px de la imagen original)

def extender(ruta):
    im = Image.open(ruta).convert("RGB"); w, h = im.size
    lienzo = Image.new("RGB", (w, h + T + B), (0, 0, 0)); lienzo.paste(im, (0, T))
    arriba = np.asarray(im.crop((0, 0, w, T)).transpose(Image.FLIP_TOP_BOTTOM)).astype(np.float32)
    g = np.linspace(0.03, 0.30, T)[:, None, None]; arriba *= g
    lienzo.paste(Image.fromarray(arriba.astype(np.uint8)).filter(ImageFilter.GaussianBlur(45)), (0, 0))
    abajo = np.asarray(im.crop((0, h - B, w, h)).transpose(Image.FLIP_TOP_BOTTOM)).astype(np.float32)
    g = np.linspace(0.40, 0.05, B)[:, None, None] ** 1.3; abajo *= g
    lienzo.paste(Image.fromarray(abajo.astype(np.uint8)).filter(ImageFilter.GaussianBlur(18)), (0, T + h))
    big = lienzo.resize((w * K, (h + T + B) * K), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    return big

def _coef(dst, src):
    A = []; b = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()

def poner_en_pantalla(lienzo, slide_path, quad):
    """quad: esquinas TL, TR, BR, BL en px de la imagen original (sin extensión)."""
    q = [((x) * K, (y + T) * K) for x, y in quad]
    xs = [p[0] for p in q]; ys = [p[1] for p in q]
    bx0, by0, bx1, by1 = int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1
    ancho = ((q[1][0] - q[0][0]) + (q[2][0] - q[3][0])) / 2
    alto = ((q[3][1] - q[0][1]) + (q[2][1] - q[1][1])) / 2
    sl = Image.open(slide_path).convert("RGB")
    sw = 1920; sh = int(sw * alto / ancho)
    lb = Image.new("RGB", (sw, sh), (4, 4, 8)); s2 = sl.resize((sw, int(sw * 9 / 16)), Image.LANCZOS)
    lb.paste(s2, (0, (sh - s2.height) // 2))
    dst = [(x - bx0, y - by0) for x, y in q]; src = [(0, 0), (sw, 0), (sw, sh), (0, sh)]
    warp = lb.transform((bx1 - bx0, by1 - by0), Image.PERSPECTIVE, _coef(dst, src), Image.BICUBIC)
    m = Image.new("L", warp.size, 0); ImageDraw.Draw(m).polygon(dst, fill=255)
    out = lienzo.copy(); out.paste(warp, (bx0, by0), m.filter(ImageFilter.GaussianBlur(1)))
    # brillo de cristal
    brillo = Image.new("RGBA", warp.size, (0, 0, 0, 0)); db = ImageDraw.Draw(brillo)
    db.polygon([(0, 0), (warp.width * 0.45, 0), (warp.width * 0.25, warp.height), (0, warp.height)], fill=(255, 255, 255, 14))
    o2 = out.convert("RGBA"); o2.alpha_composite(brillo, (bx0, by0)); return o2.convert("RGB")
