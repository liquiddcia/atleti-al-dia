import numpy as np
from PIL import Image, ImageDraw, ImageFilter

EXT = 150  # píxeles añadidos a cada lado para completar los hombros
LABIO_Y, BOCA_X0, BOCA_X1 = 489, 350, 470
OJOS = [(332, 327), (481, 327)]

def con_hombros(ruta):
    p = Image.open(ruta).convert("RGBA")
    w, h = p.size
    a = np.asarray(p).copy()
    out = np.zeros((h, w + 2 * EXT, 4), np.uint8)
    out[:, EXT:EXT + w] = a
    for lado in (0, 1):
        col = 0 if lado == 0 else w - 1
        alfa = a[:, col, 3]
        filas = np.nonzero(alfa > 200)[0]
        y0 = filas.min()
        for e in range(1, EXT + 1):
            x = EXT - e if lado == 0 else EXT + w - 1 + e
            caida = y0 + EXT * 1.6 * (1 - (1 - (e / EXT) ** 2) ** 0.5)  # hombro redondo que baja hacia el brazo  # hombro que cae y se redondea
            sombra = 1 - 0.45 * (e / EXT) ** 1.4
            for y in range(int(caida), h):
                c = a[y, col, :3].astype(float) * sombra
                out[y, x, :3] = c
                out[y, x, 3] = 255
            yi = int(caida)  # borde suavizado
            if 0 <= yi < h:
                out[yi, x, 3] = int(255 * (1 - (caida - yi)))
    # Alarga el torso hacia abajo para que quede tapado por la mesa
    extra = 420
    abajo = np.repeat(out[-1:, :, :], extra, axis=0).astype(np.float32)
    abajo[..., :3] *= np.linspace(1, 0.8, extra)[:, None, None]
    out = np.concatenate([out, abajo.astype(np.uint8)], axis=0)
    return Image.fromarray(out, "RGBA")

def animar(base, boca, parpadeo):
    """boca 0..1 (abertura de la mandíbula), parpadeo 0..1 (párpado cerrado)."""
    im = base.copy()
    ox = EXT
    if boca > 0.02:
        d = boca * 16.0
        arr = np.asarray(im).astype(np.float32)
        h, w = arr.shape[:2]
        y_ini, y_fin = LABIO_Y, 660
        x_ini, x_fin = ox + 280, ox + 540
        ys = np.arange(y_ini, y_fin)
        xs = np.arange(x_ini, x_fin)
        cx = ox + (BOCA_X0 + BOCA_X1) / 2
        wx = np.clip(1 - ((xs - cx) / 130.0) ** 2, 0, 1) ** 0.7
        wy = np.where(ys < LABIO_Y + 30, 1.0, np.clip(1 - (ys - LABIO_Y - 30) / (y_fin - LABIO_Y - 30), 0, 1))
        desp = d * wy[:, None] * wx[None, :]
        src_y = np.clip(ys[:, None] - desp, 0, h - 1)
        y0i = np.floor(src_y).astype(int); fr = (src_y - y0i)[..., None]
        y1i = np.clip(y0i + 1, 0, h - 1)
        X = np.broadcast_to(xs[None, :], src_y.shape)
        nuevo = arr[y0i, X] * (1 - fr) + arr[y1i, X] * fr
        arr[y_ini:y_fin, x_ini:x_fin] = nuevo
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        # Interior de la boca entre los labios
        capa = Image.new("RGBA", im.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(capa)
        mx0, mx1 = ox + BOCA_X0 + 14, ox + BOCA_X1 - 14
        alto = max(d * 0.95, 2)
        dc.ellipse([mx0, LABIO_Y - 2, mx1, LABIO_Y - 2 + alto], fill=(45, 14, 16, 255))
        if alto > 6:  # dientes de arriba
            dc.ellipse([mx0 + 16, LABIO_Y - 3, mx1 - 16, LABIO_Y - 3 + alto * 0.32], fill=(226, 220, 210, 235))
        im.alpha_composite(capa.filter(ImageFilter.GaussianBlur(1.6)))
    if parpadeo > 0.05:
        capa = Image.new("RGBA", im.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(capa)
        for ex, ey in OJOS:
            x = ox + ex
            parche = np.asarray(base)[ey + 22:ey + 34, x - 12:x + 12, :3].reshape(-1, 3)
            piel = tuple(int(v * 0.93) for v in parche.mean(axis=0))
            rx, ry = 25, 12
            baja = ey - ry + 2 * ry * parpadeo
            dc.ellipse([x - rx, ey - ry - 4, x + rx, baja], fill=piel + (255,))
            dc.line([(x - rx + 4, baja - 1), (x + rx - 4, baja - 1)], fill=(60, 40, 35, 220), width=3)
        im.alpha_composite(capa.filter(ImageFilter.GaussianBlur(1.4)))
    return im
