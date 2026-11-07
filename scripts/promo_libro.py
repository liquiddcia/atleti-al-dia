"""Short vertical (1080x1920, 30 fps) para promocionar el libro «Sombras de Aranjuez».

Solo la portada, a pantalla completa: empieza muy ampliada sobre el libro y se aleja despacio
hasta verse entera al final. Efectos: viñeteado, grano, parpadeo de farola, balanceo de cámara,
niebla, motas de polvo, destellos de relámpago con sacudida, fallos de imagen (glitch) y eco
fantasma. Voz en off paranormal (edge-tts + capas graves, susurro y reverberación) a velocidad
constante, y ambiente tenebroso sintetizado (dron, cuerdas, campana, viento, susurros, golpes,
truenos y latidos) siempre por debajo de la voz. Sin textos en pantalla.

Uso: python3 scripts/promo_libro.py salida/
Genera salida/sombras_de_aranjuez_shorts.mp4 y salida/voz.mp3.
Con FALSA_VOZ=1 usa tonos en lugar de edge-tts (para probar sin red)."""
import asyncio, math, os, subprocess, sys
import numpy as np
from PIL import Image

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PORTADA = os.path.join(RAIZ, "videos", "imagenes", "libro-sombras-aranjuez.jpg")
W, H, FPS = 1080, 1920, 30
DUR = 30.0          # se recalcula con la voz: si la voz no cabe en 30 s, el vídeo dura lo justo más
SR = 44100
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FF = "ffmpeg"

VOZ, RATE, PITCH = "es-ES-AlvaroNeural", "-18%", "-12Hz"   # lenta y grave, igual en todo el vídeo

# Guion exacto, troceado para colocar las pausas. (inicio previsto, [(texto hablado, pausa después, efecto al empezar)])
GUION = [
    (0.0, [("Hay un libro que tiene cinco casos reales de Aranjuez.", 0, None)]),
    (5.0, [("Cinco.", 0.6, "rayo"), ("Reales.", 0.6, "rayo"), ("Que pasaron aquí.", 0, "golpe")]),
    (10.0, [("No te puedo decir de qué son.", 0.45, None), ("Si te digo de qué son, ya no te hace falta el libro.", 0, "glitch")]),
    (16.0, [("Es de mi amigo Daniel Santiago Sanz García.", 0.4, None), ("Se llama Sombras de Aranjuez.", 0, "rayo")]),
    (21.0, [("Solo te digo una cosa:", 0.5, None), ("el quinto...", 0.7, "rayo"), ("el quinto no lo leas de noche.", 0, "fantasma")]),
    (27.0, [("Está en Amazon, enlace en la descripción.", 0.4, None), ("Expediente cerrado...", 0.5, "glitch"), ("por ahora.", 0, "golpe")]),
]

def ff(*args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)

def leer_wav(ruta):
    raw = subprocess.run([FF, "-loglevel", "error", "-i", ruta, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()

def escribir_wav(ruta, x):
    x = np.asarray(x, dtype=np.float32)
    canales = 1 if x.ndim == 1 else x.shape[1]
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(canales), "-i", "-", ruta],
                         stdin=subprocess.PIPE)
    p.stdin.write(x.tobytes()); p.stdin.close(); p.wait()

# ---------- voz ----------
async def _tts(texto, ruta):
    import edge_tts
    await edge_tts.Communicate(texto, VOZ, rate=RATE, pitch=PITCH).save(ruta)

def trozo_voz(texto, tmp, i):
    mp3, wav = os.path.join(tmp, f"v{i}.mp3"), os.path.join(tmp, f"v{i}.wav")
    if os.environ.get("FALSA_VOZ"):
        n = int(SR * (0.35 + 0.075 * len(texto)))
        t = np.arange(n) / SR
        escribir_wav(wav, 0.3 * np.sin(2 * np.pi * 140 * t) * np.sin(np.pi * t / t[-1]))
    else:
        for intento in range(4):
            try:
                asyncio.run(_tts(texto, mp3)); break
            except Exception:
                if intento == 3: raise
        quitar = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03"
        ff("-i", mp3, "-af", f"{quitar},areverse,{quitar},areverse", "-ar", str(SR), "-ac", "1", wav)
    return leer_wav(wav)

def voz(tmp):
    """Coloca cada frase en su momento previsto (o justo después de la anterior si se alarga).
    Nunca se acelera la voz: si no cabe en 30 s, el vídeo se alarga lo necesario."""
    global DUR
    trozos, k, fin_ant = [], 0, 0.0
    for (ini, partes) in GUION:
        t = 0.3 if ini == 0 else max(ini + 0.1, fin_ant + 0.35)
        for (texto, pausa, efecto) in partes:
            a = trozo_voz(texto, tmp, k); k += 1
            trozos.append((t, a, texto, efecto))
            t += len(a) / SR + pausa
        fin_ant = t - partes[-1][1]
        print(f"  tramo previsto en {ini:.0f}s → voz {trozos[-len(partes)][0]:.2f}-{fin_ant:.2f}s")
    DUR = max(30.0, math.ceil((fin_ant + 0.9) * FPS) / FPS)
    print(f"  duración del vídeo: {DUR:.2f}s")
    pista = np.zeros(int(SR * DUR), dtype=np.float32)
    eventos = []
    for (t, a, texto, efecto) in trozos:
        i0 = int(t * SR); pista[i0:i0 + len(a)] += a[: len(pista) - i0]
        if efecto: eventos.append((t, efecto, t + len(a) / SR))
    return pista, eventos

def voz_paranormal(pista, tmp):
    """Voz principal + una capa una cuarta más grave + un susurro agudo con flanger, y una sala grande."""
    a, b = os.path.join(tmp, "voz_seca.wav"), os.path.join(tmp, "voz_paranormal.wav")
    escribir_wav(a, pista)
    filtro = (
        "[0:a]asplit=3[v][g][s];"
        f"[g]asetrate={int(SR * 0.75)},aresample={SR},atempo=1.33333,lowpass=f=2500,volume=0.42[g2];"
        "[s]highpass=f=1700,flanger=delay=4:depth=6:speed=0.25:regen=-40,volume=0.5[s2];"
        "[v][g2][s2]amix=inputs=3:normalize=0,highpass=f=55,"
        "equalizer=f=110:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.2:g=-3,"
        "acompressor=threshold=-20dB:ratio=3:attack=10:release=180,"
        "aecho=0.8:0.78:90|190|330|520:0.30|0.22|0.15|0.09,"
        "alimiter=limit=0.89[o]")
    ff("-i", a, "-filter_complex", filtro, "-map", "[o]", "-ar", str(SR), "-ac", "1", b)
    v = leer_wav(b)[: len(pista)]
    return np.pad(v, (0, len(pista) - len(v)))

# ---------- sonido tenebroso ----------
def ambiente(vref, eventos):
    n = int(SR * DUR); t = np.arange(n) / SR; rng = np.random.default_rng(11)
    def env(a, r, ini, fin):
        e = np.clip((t - ini) / a, 0, 1) * np.clip((fin - t) / r, 0, 1)
        return e * e * (3 - 2 * e)
    def nrm(x): return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)
    def banda(x, centro, ancho):
        F = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
        F *= np.exp(-((np.log(fr + 1) - np.log(centro)) ** 2) / (2 * ancho ** 2))
        return np.fft.irfft(F, len(x))
    # dron muy grave con batido disonante
    lfo = 0.7 + 0.3 * np.sin(2 * np.pi * 0.06 * t)
    dron = sum(g * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f, g in
               ((41.2, 1.0), (41.6, 0.7), (55, 0.6), (58.3, 0.35), (82.4, 0.3), (116.5, 0.12))) * lfo
    # cuerdas lentas y tristes (La menor, Fa, Re menor, Mi) con una disonancia que va y viene
    acordes = [(0.0, (220.0, 261.6, 329.6)), (DUR * 0.25, (174.6, 220.0, 261.6, 277.2)),
               (DUR * 0.5, (146.8, 174.6, 220.0, 293.7)), (DUR * 0.75, (164.8, 207.7, 246.9, 261.6))]
    cuerdas = np.zeros(n)
    for ini, notas in acordes:
        e = env(2.8, 2.8, ini - 0.5, ini + DUR * 0.25 + 0.8)
        for f in notas:
            vib = 1 + 0.004 * np.sin(2 * np.pi * (4.6 + rng.uniform(-0.4, 0.4)) * t)
            for det in (-0.15, 0.0, 0.16):
                fase = 2 * np.pi * np.cumsum((f + det) * vib) / SR + rng.uniform(0, 6)
                cuerdas += e * sum(np.sin(h * fase) / h ** 1.6 for h in range(1, 7)) / 3
    # campana de iglesia lejana
    campana = np.zeros(n)
    for t0 in (DUR * 0.27, DUR * 0.62):
        tt = np.clip(t - t0, 0, None); on = t >= t0
        for r, g, d in ((0.5, 0.6, 7), (1, 1, 5), (1.19, 0.5, 3.5), (1.5, 0.4, 3), (2, 0.35, 2.5), (2.52, 0.2, 2), (3.01, 0.15, 1.6)):
            campana += on * g * np.sin(2 * np.pi * 174.6 * r * tt) * np.exp(-tt / d)
    eco = np.zeros(n)
    for dly, g in ((0.09, 0.6), (0.21, 0.45), (0.37, 0.33), (0.58, 0.22), (0.83, 0.14)):
        k = int(dly * SR); eco[k:] += g * campana[:-k]
    campana = np.convolve(campana + eco, np.ones(9) / 9, mode="same")
    # viento de noche
    viento = banda(rng.standard_normal(n), 380, 0.55)
    viento *= 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 0.06 * t + 1) * np.sin(2 * np.pi * 0.11 * t + 2))
    # susurros: ruido agudo con «sílabas» que aparecen y desaparecen
    sil = np.abs(np.sin(2 * np.pi * 7.3 * t + 3 * np.sin(2 * np.pi * 0.9 * t))) ** 3
    susurro = banda(rng.standard_normal(n), 3200, 0.35) * sil * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t) ** 2)
    # tensión final: trémolo agudo disonante y crescendo hasta el corte
    cre = np.clip((t - (DUR - 3.2)) / 3.2, 0, 1) ** 1.5
    tension = cre * (np.sin(2 * np.pi * 440 * t) + 0.8 * np.sin(2 * np.pi * 466.2 * t) + 0.6 * np.sin(2 * np.pi * 110 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t))
    fondo = 0.55 * nrm(dron) + 0.7 * nrm(cuerdas) + 0.35 * nrm(campana) + 0.35 * nrm(viento) + 0.25 * nrm(susurro)
    fondo = fondo + 0.7 * nrm(tension) * (np.sqrt(np.mean(cre ** 2)) + 1e-9)
    fondo *= (1 + 1.3 * cre) * np.clip(t / 1.2, 0, 1)
    # golpes, truenos y latidos sincronizados con los efectos de imagen
    sfx = np.zeros(n)
    ruido = rng.standard_normal(n)
    for (t0, efecto, t1) in eventos:
        i0 = int(t0 * SR)
        tt = np.arange(n - i0) / SR
        if efecto in ("rayo", "golpe"):
            f = 58 * np.exp(-tt * 1.6) + 30                         # golpe sub-grave que cae
            golpe = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.9)
            trueno = banda(ruido[: n - i0], 180, 0.8) * np.exp(-tt / 1.4) * (1 - np.exp(-tt / 0.02))
            sfx[i0:] += golpe * 1.0 + (trueno * 0.8 if efecto == "rayo" else 0)
            sub = int(1.2 * SR)                                     # subida previa (como al revés)
            j0 = max(0, i0 - sub); m = i0 - j0
            if m > 0:
                rampa = np.linspace(0, 1, m) ** 3
                sfx[j0:i0] += 0.35 * banda(ruido[j0:i0], 900, 0.6) * rampa
        elif efecto == "glitch":
            k = min(n - i0, int(0.25 * SR))
            sfx[i0:i0 + k] += 0.5 * np.sign(np.sin(2 * np.pi * 1200 * tt[:k])) * (rng.random(k) > 0.5) * np.exp(-tt[:k] / 0.12)
        elif efecto == "fantasma":                                  # latidos durante la frase
            for b in np.arange(t0, min(t1 + 1.5, DUR - 0.3), 0.86):
                for d, g in ((0, 1.0), (0.22, 0.7)):
                    j = int((b + d) * SR); tb = np.arange(min(n - j, int(0.35 * SR))) / SR
                    sfx[j:j + len(tb)] += g * np.sin(2 * np.pi * 52 * tb) * np.exp(-tb / 0.09)
    rv = np.sqrt(np.mean(vref[np.abs(vref) > 0.01] ** 2))
    fondo *= (rv * 0.24) / (np.sqrt(np.mean(fondo[: int(SR * (DUR - 3.5))] ** 2)) + 1e-9)   # fondo bajo la voz
    sfx *= (rv * 0.55) / (np.max(np.abs(sfx)) + 1e-9) * 2.2                                  # golpes que se notan
    envv = np.convolve(np.abs(vref), np.ones(int(SR * 0.25)) / int(SR * 0.25), mode="same")
    fondo *= 1 - 0.35 * np.clip(envv / (envv.max() + 1e-9) * 3, 0, 1)
    m = fondo + sfx
    m[-int(SR * 0.008):] *= np.linspace(1, 0, int(SR * 0.008))            # corte en seco
    return m.astype(np.float32)

# ---------- imagen ----------
def suave(shape, escala, rng):
    """Ruido suave (niebla) por FFT."""
    r = rng.standard_normal(shape)
    F = np.fft.rfft2(r); fy = np.fft.fftfreq(shape[0])[:, None]; fx = np.fft.rfftfreq(shape[1])[None, :]
    F *= np.exp(-(fx ** 2 + fy ** 2) * escala)
    x = np.fft.irfft2(F, shape); x -= x.min(); return (x / x.max()).astype(np.float32)

def render(eventos, audio_wav, salida):
    src = Image.open(PORTADA).convert("RGB"); sw, sh = src.size
    fh = sh; fw = fh * W / H                      # encuadre final: portada a pantalla completa (9:16)
    Z0 = 2.9
    c0, c1 = (548.0, 975.0), (sw / 2, sh / 2)     # empieza sobre el libro y la figura oscura del centro
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    vineta = (1 - 0.75 * np.clip(r - 0.42, 0, 1) ** 1.3)[..., None].astype(np.float32)
    rng = np.random.default_rng(5)
    granos = [np.kron(rng.normal(0, 0.045, (H // 2, W // 2)).astype(np.float32), np.ones((2, 2), np.float32))[..., None] for _ in range(8)]
    niebla = suave((240, 270), 900, rng)          # se desplaza despacio, se amplía a pantalla completa
    n = int(round(DUR * FPS)); tt = np.arange(n) / FPS
    luz = 1 + 0.025 * np.sin(2 * np.pi * 0.8 * tt) + 0.015 * np.sin(2 * np.pi * 2.3 * tt + 1)
    for c in rng.uniform(1.5, DUR - 1.5, 8):        # parpadeo de farola
        k = int(c * FPS); luz[k:k + 2] *= 0.85; luz[k + 2:k + 3] *= 0.95
    motas = rng.uniform(0, 1, (90, 4))              # x, y, velocidad, fase
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", audio_wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "22", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                          "-ac", "2", "-t", f"{DUR}", "-movflags", "+faststart", salida], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS; u = i / (n - 1)
        e = u * u * (3 - 2 * u) * 0.35 + u * 0.65            # alejamiento continuo
        z = Z0 ** (1 - e)
        cw, ch = fw / z, fh / z
        cx = c0[0] + (c1[0] - c0[0]) * e; cy = c0[1] + (c1[1] - c0[1]) * e
        # balanceo de cámara en mano (se apaga en el último segundo para ver la portada quieta)
        amp = min(1.0, (DUR - t) / 1.5)
        cx += amp * 6 / z * math.sin(2 * math.pi * 0.13 * t); cy += amp * 5 / z * math.sin(2 * math.pi * 0.09 * t + 1)
        rot = amp * math.radians(0.6) * math.sin(2 * math.pi * 0.07 * t)
        # sacudida y destello tras cada rayo o golpe
        flash, glitch, fantasma = 0.0, 0.0, 0.0
        for (t0, ef, t1) in eventos:
            dt = t - t0
            if ef in ("rayo", "golpe") and 0 <= dt < 0.8:
                s = 1.0 if ef == "rayo" else 0.6
                k = math.exp(-dt / 0.18) * s * amp
                cx += k * 14 / z * math.sin(97 * t + i); cy += k * 12 / z * math.cos(83 * t + 2 * i)
                if ef == "rayo":
                    flash = max(flash, 0.75 * math.exp(-dt / 0.09) + (0.35 if 0.12 < dt < 0.17 else 0))
                else:
                    flash = max(flash, 0.3 * math.exp(-dt / 0.12))
            if ef == "glitch" and 0 <= dt < 0.3:
                glitch = 1.0 if (int(dt * FPS) % 3 != 2) else 0.0
            if ef == "fantasma" and t0 <= t < t1 + 0.6:
                fantasma = 0.5 + 0.5 * math.sin(2 * math.pi * 1.1 * (t - t0))
        cx = min(max(cx, cw / 2), sw - cw / 2); cy = min(max(cy, ch / 2), sh - ch / 2)
        sx = cw / W; co, si = math.cos(rot), math.sin(rot)
        a_, b_, d_, e_ = sx * co, -sx * si, sx * si, sx * co
        coef = (a_, b_, cx - a_ * W / 2 - b_ * H / 2, d_, e_, cy - d_ * W / 2 - e_ * H / 2)
        fr = src.transform((W, H), Image.AFFINE, coef, Image.BICUBIC)
        a = np.asarray(fr, dtype=np.float32) / 255.0
        # niebla que se desliza
        off = int(t * 4) % 270
        nb = np.roll(niebla, -off, axis=1)[:, :135]
        nb = np.asarray(Image.fromarray((nb * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), dtype=np.float32)[..., None] / 255.0
        a = a + nb * 0.10 * np.array([0.75, 0.8, 0.95], np.float32)
        if fantasma > 0:                              # eco fantasma desplazado
            a = a * (1 - 0.22 * fantasma) + np.roll(a, int(22 * fantasma), axis=1) * 0.22 * fantasma
        a = a * vineta * luz[i]
        if flash > 0:                                 # destello azulado de relámpago
            a = a + flash * np.array([0.82, 0.88, 1.0], np.float32) * (0.55 + 0.45 * vineta)
        if glitch > 0:                                # aberración de color y franjas desplazadas
            a[..., 0] = np.roll(a[..., 0], 12, axis=1); a[..., 2] = np.roll(a[..., 2], -12, axis=1)
            for _ in range(3):
                y0 = int(rng.uniform(0, H - 120)); hgt = int(rng.uniform(20, 110))
                a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], int(rng.uniform(-60, 60)), axis=1)
        # motas de polvo que flotan
        for (mx, my, mv, mf) in motas:
            x = int((mx * W + 25 * math.sin(t * 0.7 + mf * 6)) % W); y = int((my * H - t * (15 + 35 * mv)) % H)
            b = 0.25 + 0.35 * (0.5 + 0.5 * math.sin(t * 3 + mf * 20))
            a[max(0, y - 1):y + 2, max(0, x - 1):x + 2] += b * np.array([1.0, 0.85, 0.6], np.float32)
        a = a + granos[i % 8]
        p.stdin.write((np.clip(a, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()

def main(carpeta):
    os.makedirs(carpeta, exist_ok=True); tmp = os.path.join(carpeta, "tmp"); os.makedirs(tmp, exist_ok=True)
    print("Voz en off…")
    seca, eventos = voz(tmp)
    v = voz_paranormal(seca, tmp)
    print("Ambiente…")
    m = ambiente(v, eventos)
    mezcla = np.tanh((v + m) * 1.1) / np.tanh(1.1) * 0.95
    wav = os.path.join(tmp, "final.wav"); escribir_wav(wav, mezcla)
    escribir_wav(os.path.join(tmp, "voz_final.wav"), v)
    ff("-i", os.path.join(tmp, "voz_final.wav"), "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(carpeta, "voz.mp3"))
    print("Vídeo…")
    for ev in eventos: print(f"  efecto {ev[1]} en {ev[0]:.2f}s")
    render(eventos, wav, os.path.join(carpeta, "sombras_de_aranjuez_shorts.mp4"))
    print("Listo:", os.path.join(carpeta, "sombras_de_aranjuez_shorts.mp4"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "salida")
