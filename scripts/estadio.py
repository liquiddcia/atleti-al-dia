"""Fondo de estadio de noche generado: cielo, focos con destellos, haces de luz, gradas con
afición rojiblanca, bengalas y humo, césped en perspectiva con sombras. Para miniaturas."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def _ruido(h, w, escala, rng):
    r = rng.standard_normal((h, w))
    F = np.fft.rfft2(r); fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    F *= np.exp(-(fx ** 2 + fy ** 2) * escala)
    x = np.fft.irfft2(F, (h, w)); x -= x.min(); return x / (x.max() + 1e-9)

def fondo(W, H, semilla=7, horizonte=0.58):
    rng = np.random.default_rng(semilla)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    hz = int(H * horizonte)                     # línea donde empieza el césped
    img = np.zeros((H, W, 3), np.float32)
    # cielo nocturno
    t = np.clip(yy / hz, 0, 1)[..., None]
    img += (1 - t) * np.array([8, 10, 28]) + t * np.array([28, 18, 40])
    # gradas: banda de afición con puntos rojos y blancos
    g0, g1 = int(hz * 0.38), hz
    gh = g1 - g0
    grada = np.zeros((gh, W, 3), np.float32) + np.array([25, 18, 30])
    n = int(W * gh / 9)
    px = rng.integers(0, W, n); py = rng.integers(0, gh, n)
    colores = np.array([[220, 30, 40], [240, 240, 240], [200, 20, 30], [30, 60, 160], [255, 255, 255]])
    c = colores[rng.choice(len(colores), n, p=[0.36, 0.3, 0.2, 0.06, 0.08])]
    brillo = 0.75 * (0.45 + 0.55 * rng.random(n))[:, None] * (0.45 + 0.55 * (py / gh))[:, None]
    for dx in range(3):
        for dy in range(4):
            yy2 = np.clip(py + dy, 0, gh - 1); xx2 = np.clip(px + dx, 0, W - 1)
            grada[yy2, xx2] = c * brillo
    # bandas de bufandas / tifo rojiblanco
    for k in range(5):
        y = int(gh * (0.15 + 0.17 * k)); h2 = max(3, gh // 40)
        franja = ((xx[:h2, :] // max(6, W // 120)) % 2 == 0)
        grada[y:y + h2][franja] = grada[y:y + h2][franja] * 0.4 + np.array([200, 25, 35]) * 0.6
    grada = np.asarray(Image.fromarray(grada.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), np.float32)
    img[g0:g1] = grada
    # techo / anillo del estadio
    img[g0 - int(H * 0.012):g0] = np.array([40, 40, 55])
    # césped en perspectiva con franjas
    tz = np.clip((yy - hz) / (H - hz), 0, 1)
    persp = 1 / (1 - 0.8 * tz + 1e-3)
    franjas = (np.floor(persp * 6) % 2)
    verde = np.where(franjas[..., None] > 0, np.array([30, 120, 45]), np.array([24, 100, 38]))
    img = np.where((yy >= hz)[..., None], verde * (0.55 + 0.55 * tz[..., None]), img)
    # línea de medio campo y círculo
    d = Image.fromarray(img.clip(0, 255).astype(np.uint8)); dr = ImageDraw.Draw(d)
    cy = hz + (H - hz) * 0.55
    dr.line([(0, hz + (H - hz) * 0.08), (W, hz + (H - hz) * 0.08)], fill=(190, 230, 190), width=max(2, H // 400))
    dr.ellipse([W / 2 - W * 0.22, cy - (H - hz) * 0.16, W / 2 + W * 0.22, cy + (H - hz) * 0.16], outline=(190, 230, 190), width=max(2, H // 400))
    dr.line([(W / 2, hz + (H - hz) * 0.08), (W / 2, H)], fill=(190, 230, 190), width=max(2, H // 400))
    img = np.asarray(d, np.float32)
    # sombras de jugadores/viñeta sobre el césped
    som = np.exp(-(((xx - W / 2) / (W * 0.45)) ** 2 + ((yy - H) / (H * 0.25)) ** 2))
    img *= (1 - 0.35 * som[..., None])
    # focos: torres con destellos
    luz = np.zeros((H, W), np.float32)
    focos = [(W * 0.08, hz * 0.18), (W * 0.92, hz * 0.18), (W * 0.30, hz * 0.10), (W * 0.70, hz * 0.10)]
    for fx_, fy_ in focos:
        r2 = ((xx - fx_) ** 2 + (yy - fy_) ** 2)
        luz += 1.8 * np.exp(-r2 / (2 * (W * 0.012) ** 2)) + 0.9 * np.exp(-r2 / (2 * (W * 0.06) ** 2))
        # destello en cruz
        luz += 0.5 * np.exp(-((yy - fy_) / (H * 0.004)) ** 2) * np.exp(-np.abs(xx - fx_) / (W * 0.12))
        luz += 0.35 * np.exp(-((xx - fx_) / (W * 0.004)) ** 2) * np.exp(-np.abs(yy - fy_) / (H * 0.08))
        # haz de luz hacia el campo
        ang = np.arctan2(yy - fy_, xx - (W / 2 * 0.7 + fx_ * 0.3) + 1e-3)
        dist = np.sqrt(r2)
        haz = np.exp(-((xx - (fx_ + (W / 2 - fx_) * np.clip((yy - fy_) / (H - fy_), 0, 1))) / (W * 0.05 + dist * 0.12)) ** 2)
        luz += 0.18 * haz * (yy > fy_) * np.exp(-dist / (H * 0.9))
    img += luz[..., None] * np.array([255, 245, 225])
    # humo de bengalas rojas sobre la grada y niebla blanca
    humo = _ruido(H // 4, W // 4, 400, rng)
    humo = np.asarray(Image.fromarray((humo * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    banda = np.exp(-((yy - hz * 0.85) / (H * 0.18)) ** 2)
    img += (humo ** 2 * banda)[..., None] * np.array([210, 40, 40]) * 0.65
    niebla = _ruido(H // 4, W // 4, 900, rng)
    niebla = np.asarray(Image.fromarray((niebla * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    img += (niebla * np.exp(-((yy - hz) / (H * 0.12)) ** 2))[..., None] * np.array([150, 150, 165]) * 0.35
    # bengalas encendidas en la grada
    for _ in range(max(4, W // 250)):
        bx = rng.uniform(0.05, 0.95) * W; by = rng.uniform(g0 + gh * 0.3, g1)
        r2 = (xx - bx) ** 2 + (yy - by) ** 2
        img += (np.exp(-r2 / (2 * (W * 0.006) ** 2)) * 1.6 + np.exp(-r2 / (2 * (W * 0.03) ** 2)) * 0.6)[..., None] * np.array([255, 70, 40])
    # viñeta
    vig = np.sqrt(((xx - W / 2) / (W * 0.65)) ** 2 + ((yy - H / 2) / (H * 0.65)) ** 2)
    img *= np.clip(1.15 - 0.55 * vig, 0.25, 1)[..., None]
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))
