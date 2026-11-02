"""Plató virtual: presentador sentado que mueve la boca con la voz, plano general y
plano con pantalla (presentador a la izquierda, imágenes a la derecha)."""
import sys, os, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from functools import lru_cache
import poses as PZ
from estudio import extender, poner_en_pantalla, K, T

W, H, FPS = 1920, 1080, 30
PLANOS = {
    # silla (x0, x1, y_arriba) y línea de la mesa en px de la imagen original
    "centro":   {"silla": (735, 910, 222), "mesa": 345, "apoyo": 400, "ventana": (360, T - 30, 1284, T + 490)},
    "pantalla": {"silla": (215, 370, 258), "mesa": 362, "apoyo": 393, "ventana": (130, 110, 1672, 977),
                 "cerca": (1032, T + 13, 1672, T + 373),
                 "quad": [(1176, 75), (1609, 36), (1609, 350), (1176, 334)]},
}
NIVELES = 7
REF_OJOS = 8.5  # anchura de hombros / distancia entre ojos en las poses

class Presentador:
    """Sprites de cada pose ya escalados al plano, con boca y parpadeo, en caché."""
    def __init__(self):
        self.base = PZ.cargar()
    def colocar(self, plano, pose):
        x0, x1, _ = PLANOS[plano]["silla"]
        lm = PZ.POSES[pose]
        esc = (x1 - x0) * 1.3 / REF_OJOS / PZ.distancia_ojos(lm) * K
        img = self.base[pose]
        ojos_x = (lm["ojos"][0][0] + lm["ojos"][1][0]) / 2
        x = (x0 + x1) / 2 * K - ojos_x * esc
        y = (PLANOS[plano]["apoyo"] + T) * K - img.height * esc
        return esc, x, y
    @lru_cache(maxsize=120)
    def sprite(self, plano, pose, b, p):
        esc, _, _ = self.colocar(plano, pose)
        img = PZ.animar(self.base[pose], PZ.POSES[pose], b / (NIVELES - 1), p)
        w, h = round(img.width * esc), round(img.height * esc)
        im = img.resize((w, h), Image.LANCZOS)
        px = np.asarray(im).astype(np.float32); px[..., 0] *= 1.03; px[..., 2] *= 0.98
        return Image.fromarray(np.clip(px, 0, 255).astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.5))
    def sombra(self, plano, pose):
        esc, x, y = self.colocar(plano, pose)
        a = self.base[pose].getchannel("A")
        w, h = round(a.width * esc), round(a.height * esc)
        return a.resize((w, h)).filter(ImageFilter.GaussianBlur(10 * K / 3)).point(lambda v: v * 0.45)

def plan_poses(tramos):
    """Qué pose toca en cada momento: señala la pantalla al aparecer una imagen y va cambiando."""
    plan = []
    for i, (ini, fin, plano, slide) in enumerate(tramos):
        if plano == "pantalla":
            seq = ["senala", "explica", "manos", "explica"]
        else:
            seq = ["manos", "explica", "inclinado", "papeles"] if i == 0 else ["explica", "inclinado", "manos"]
        t, k = ini, 0
        while t < fin:
            dur = 2.6 if seq[k % len(seq)] == "senala" else 3.8
            plan.append((t, min(t + dur, fin), seq[k % len(seq)])); t += dur; k += 1
    return plan

def suave(t): return t * t * (3 - 2 * t)

def ventana(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))

def ajustar(v, ancho_max, alto_max):
    """Lleva una ventana a 16:9 conservando su centro."""
    x0, y0, x1, y1 = v; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w = max(x1 - x0, (y1 - y0) * 16 / 9); h = w * 9 / 16
    x0 = min(max(cx - w / 2, 0), ancho_max - w); y0 = min(max(cy - h / 2, 0), alto_max - h)
    return (x0, y0, x0 + w, y0 + h)

def envolvente(wav_path, n_frames):
    with wave.open(wav_path) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        if w.getnchannels() == 2: x = x.reshape(-1, 2).mean(axis=1)
    hop = sr / FPS; e = np.zeros(n_frames)
    for i in range(n_frames):
        seg = x[int(i * hop):int((i + 1) * hop)]
        e[i] = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else -90
    a = np.clip((e + 42) / 22, 0, 1) ** 0.8
    out = np.zeros_like(a); v = 0
    for i, x_ in enumerate(a):  # abre rápido, cierra un poco más lento
        v = x_ if x_ > v else v * 0.55 + x_ * 0.45; out[i] = v
    return out

def render(fondo_centro, fondo_pantalla, pres_png, tramos, voz_wav, salida_mp4, audio_final=None):
    """tramos: lista de (inicio_s, fin_s, plano, slide_png o None)."""
    pres = Presentador()
    lienzos = {"centro": extender(fondo_centro), "pantalla": extender(fondo_pantalla)}
    plan = plan_poses(tramos)
    con_slide = {}
    dur = tramos[-1][1]; n = int(round(dur * FPS))
    boca = envolvente(voz_wav, n)
    rng = np.random.default_rng(7); parpados = np.zeros(n); t_sig = 2.0
    while t_sig < dur:
        f = int(t_sig * FPS)
        for k, v in enumerate((0.6, 1.0, 1.0, 0.6)):
            if f + k < n: parpados[f + k] = v
        t_sig += rng.uniform(2.8, 5.5)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_final or voz_wav,
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", salida_mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n):
        t = f / FPS
        ini, fin, plano, slide = next(x for x in tramos if x[0] <= t < x[1] or x is tramos[-1])
        P = PLANOS[plano]; L = lienzos[plano]
        if plano == "pantalla" and slide:
            if slide not in con_slide: con_slide[slide] = poner_en_pantalla(L, slide, P["quad"])
            L = con_slide[slide]
        lw, lh = L.width / K, L.height / K
        u = (t - ini) / (fin - ini)
        if plano == "centro":
            v = ajustar(P["ventana"], lw, lh); z = 1 + 0.05 * u
            cx, cy = (v[0] + v[2]) / 2, (v[1] + v[3]) / 2; hw, hh = (v[2] - v[0]) / 2 / z, (v[3] - v[1]) / 2 / z
            v = (cx - hw, cy - hh, cx + hw, cy + hh)
        else:
            amplia = ajustar(P["ventana"], lw, lh); cerca = ajustar(P["cerca"], lw, lh)
            d = fin - ini; t_in = min(max(d * 0.35, 2.5), d - 2); s = (t - ini - t_in) / 1.3
            v = ventana(amplia, cerca, suave(min(max(s, 0), 1)))
        box = tuple(int(round(c * K)) for c in v)
        frame = L.crop(box).convert("RGBA")
        b = int(round(boca[f] * (NIVELES - 1))); p = parpados[f]
        dx = 1.5 * K * math.sin(2 * math.pi * 0.17 * t); dy = 1.5 * K * math.sin(2 * math.pi * 0.23 * t)
        j = max(i for i, x in enumerate(plan) if x[0] <= t)
        actual = plan[j][2]; capas = [(actual, 1.0)]
        FUND = 0.35
        if j > 0 and t - plan[j][0] < FUND and plan[j - 1][2] != actual:  # fundido entre poses
            a_ = (t - plan[j][0]) / FUND; capas = [(plan[j - 1][2], 1.0), (actual, a_)]
        for pose, alfa in capas:
            esc, sx, sy = pres.colocar(plano, pose)
            im = pres.sprite(plano, pose, b, p)
            px, py = int(sx + dx - box[0]), int(sy + dy - box[1])
            if not (-im.width < px < frame.width and -im.height < py < frame.height):
                continue
            if alfa < 1:
                im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alfa)))
            sh = pres.sombra(plano, pose)
            capa_s = Image.new("RGBA", sh.size, (0, 0, 0, 0)); capa_s.putalpha(sh.point(lambda v: int(v * alfa)))
            frame.alpha_composite(capa_s.crop((0, 0, sh.width, sh.height)), (px + int(6 * K / 3), py + int(10 * K / 3))) if px >= 0 and py >= 0 else None
            frame.paste(im, (px, py), im)
        proc.stdin.write(frame.convert("RGB").resize((W, H), Image.BILINEAR).tobytes())
    proc.stdin.close(); proc.wait()

FFMPEG = os.environ.get("FF", "ffmpeg")
