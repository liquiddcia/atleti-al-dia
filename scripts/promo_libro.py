"""Short vertical (1080x1920, 30 s, 30 fps) para promocionar el libro «Sombras de Aranjuez».

La portada ocupa toda la pantalla: empieza muy ampliada sobre el libro y se aleja despacio
hasta verse entera al final. Viñeteado, grano y parpadeo de farola. Voz en off misteriosa
(edge-tts), música de ambiente sintetizada (dron, cuerdas, campana lejana y viento) muy baja,
subtítulos y textos en pantalla sincronizados con la voz.

Uso: python3 scripts/promo_libro.py salida/
Genera salida/sombras_de_aranjuez_shorts.mp4 y salida/voz.mp3.
Con FALSA_VOZ=1 usa tonos en lugar de edge-tts (para probar sin red)."""
import asyncio, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PORTADA = os.path.join(RAIZ, "videos", "imagenes", "libro-sombras-aranjuez.jpg")
W, H, FPS, DUR = 1080, 1920, 30, 30.0
SR = 44100
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FF = "ffmpeg"

VOZ, RATE, PITCH = "es-ES-AlvaroNeural", "-18%", "-9Hz"   # lenta y grave (el último tramo, algo más ágil para que quepa)

# Guion exacto, troceado para colocar las pausas. (inicio, fin, [(texto hablado, subtítulo, pausa después)])
GUION = [
    (0.0, 5.0, [("Hay un libro que tiene cinco casos reales de Aranjuez.", "Hay un libro que tiene 5 casos reales de Aranjuez.", 0)]),
    (5.0, 10.0, [("Cinco.", "Cinco.", 0.55), ("Reales.", "Reales.", 0.55), ("Que pasaron aquí.", "Que pasaron aquí.", 0)]),
    (10.0, 16.0, [("No te puedo decir de qué son.", "No te puedo decir de qué son.", 0.4),
                  ("Si te digo de qué son, ya no te hace falta el libro.", "Si te digo de qué son, ya no te hace falta el libro.", 0)]),
    (16.0, 21.0, [("Es de mi amigo Daniel Santiago Sanz García.", "Es de mi amigo Daniel Santiago Sanz García.", 0.35),
                  ("Se llama Sombras de Aranjuez.", "Se llama Sombras de Aranjuez.", 0)]),
    (21.0, 27.0, [("Solo te digo una cosa:", "Solo te digo una cosa:", 0.45), ("el quinto...", "el quinto...", 0.55),
                  ("el quinto no lo leas de noche.", "el quinto no lo leas de noche.", 0)]),
    (27.0, 30.0, [("Está en Amazon, enlace en la descripción.", "Está en Amazon, enlace en la descripción.", 0.25),
                  ("Expediente cerrado...", "Expediente cerrado...", 0.3), ("por ahora.", "por ahora.", 0)]),
]
TEXTOS = [(0, 5, "5 CASOS REALES"), (5, 10, "PASARON EN ARANJUEZ"), (10, 16, "NO PUEDO CONTARLOS"),
          (16, 21, "SOMBRAS DE ARANJUEZ"), (21, 27, "EL 5º NO LO LEAS DE NOCHE"),
          (27, 30, "EN AMAZON - ENLACE EN LA DESCRIPCIÓN")]

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
async def _tts(texto, ruta, rate):
    import edge_tts
    await edge_tts.Communicate(texto, VOZ, rate=rate, pitch=PITCH).save(ruta)

def trozo_voz(texto, tmp, i, rate=RATE):
    mp3, wav = os.path.join(tmp, f"v{i}.mp3"), os.path.join(tmp, f"v{i}.wav")
    if os.environ.get("FALSA_VOZ"):
        n = int(SR * (0.35 + 0.068 * len(texto)))
        t = np.arange(n) / SR
        escribir_wav(wav, 0.3 * np.sin(2 * np.pi * 140 * t) * np.sin(np.pi * t / t[-1]))
    else:
        for intento in range(4):
            try:
                asyncio.run(_tts(texto, mp3, rate)); break
            except Exception:
                if intento == 3: raise
        # sin silencios al principio ni al final
        quitar = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03"
        ff("-i", mp3, "-af", f"{quitar},areverse,{quitar},areverse", "-ar", str(SR), "-ac", "1", wav)
    return leer_wav(wav)

def acelerar(x, f, tmp, i):
    a, b = os.path.join(tmp, f"a{i}.wav"), os.path.join(tmp, f"b{i}.wav")
    escribir_wav(a, x); ff("-i", a, "-af", f"atempo={f:.4f}", b); return leer_wav(b)

def voz(tmp):
    pista = np.zeros(int(SR * DUR), dtype=np.float32)
    subs, k, fin_ant = [], 0, 0.0
    for (ini, fin, trozos) in GUION:
        audios = [trozo_voz(t, tmp, k + j, "-4%" if fin >= DUR else RATE) for j, (t, _, _) in enumerate(trozos)]
        pausas = [p for (_, _, p) in trozos]
        hablado = sum(len(a) for a in audios) / SR
        fin_max = DUR - 0.2 if fin >= DUR else fin - 0.15
        hueco = 0.2 if fin >= DUR else 0.3
        arranque = 0.25 if ini == 0 else max(ini + 0.12, fin_ant + hueco)
        if ini > 0 and hablado + sum(pausas) > fin_max - arranque:   # si no cabe, se adelanta un poco si sobró hueco antes
            arranque = max(fin_ant + hueco, ini - 0.8)
        limite = fin_max - arranque
        if hablado + sum(pausas) > limite:      # primero se recortan las pausas, luego se acelera la voz
            pausas = [max(0.15, p * 0.5) if p else 0 for p in pausas]
        if hablado + sum(pausas) > limite:
            f = min(1.55 if fin >= DUR else 1.4, hablado / max(0.5, limite - sum(pausas)))
            audios = [acelerar(a, f, tmp, k + j) for j, a in enumerate(audios)]
            print(f"  tramo {ini:.0f}-{fin:.0f}s: voz acelerada x{f:.2f}")
        t = arranque
        for j, (a, (_, sub, _)) in enumerate(zip(audios, trozos)):
            i0 = int(t * SR); a = a[: max(0, len(pista) - i0)]
            pista[i0:i0 + len(a)] += a
            subs.append((t, t + len(a) / SR, sub.upper()))
            t += len(a) / SR + pausas[j]
        fin_ant = t - pausas[-1]
        k += len(trozos)
        print(f"  tramo {ini:.0f}-{fin:.0f}s → voz {arranque:.2f}-{fin_ant:.2f}s")
    # cada subtítulo se mantiene hasta que empieza el siguiente (sin huecos que parpadeen)
    subs = [(a, (subs[i + 1][0] if i + 1 < len(subs) else DUR), s) for i, (a, b, s) in enumerate(subs)]
    if subs[-1][0] > DUR - 0.5 or fin_ant > DUR:
        print(f"  AVISO: la voz termina en {fin_ant:.2f}s y no cabe del todo en {DUR:.0f}s")
    return pista, subs

def tratar_voz(pista, tmp):
    a, b = os.path.join(tmp, "voz_seca.wav"), os.path.join(tmp, "voz_tratada.wav")
    escribir_wav(a, pista)
    # grave y cercana, con una cola de sala muy suave
    ff("-i", a, "-af", "highpass=f=70,equalizer=f=120:t=q:w=1:g=3,equalizer=f=3500:t=q:w=1.2:g=-2,"
       "acompressor=threshold=-20dB:ratio=3:attack=10:release=150,aecho=0.85:0.6:70|130:0.18|0.10,"
       "alimiter=limit=0.89", "-ar", str(SR), "-ac", "1", b)
    v = leer_wav(b)[: len(pista)]
    return np.pad(v, (0, len(pista) - len(v)))

# ---------- música ----------
def musica(vref):
    n = int(SR * DUR); t = np.arange(n) / SR; rng = np.random.default_rng(11)
    def env(a, r, ini, fin):
        e = np.clip((t - ini) / a, 0, 1) * np.clip((fin - t) / r, 0, 1)
        return e * e * (3 - 2 * e)
    # dron grave constante
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    dron = sum(g * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f, g in
               ((55, 1.0), (55.3, 0.6), (82.4, 0.5), (110, 0.25), (165, 0.08))) * lfo
    # cuerdas lentas y tristes (La menor, Fa, Re menor, Mi)
    acordes = [(0.0, (220.0, 261.6, 329.6)), (7.5, (174.6, 220.0, 261.6)), (15.0, (146.8, 174.6, 220.0, 293.7)), (22.5, (164.8, 207.7, 246.9))]
    cuerdas = np.zeros(n)
    for ini, notas in acordes:
        e = env(2.8, 2.8, ini - 0.5, ini + 8.3)
        for f in notas:
            vib = 1 + 0.003 * np.sin(2 * np.pi * (4.6 + rng.uniform(-0.4, 0.4)) * t)
            for det in (-0.12, 0.0, 0.13):
                fase = 2 * np.pi * np.cumsum((f + det) * vib) / SR + rng.uniform(0, 6)
                cuerdas += e * sum(np.sin(h * fase) / h ** 1.6 for h in range(1, 7)) / 3
    # campana de iglesia lejana
    campana = np.zeros(n)
    for t0 in (8.2, 19.6):
        tt = np.clip(t - t0, 0, None); on = t >= t0
        for r, g, d in ((0.5, 0.6, 7), (1, 1, 5), (1.19, 0.5, 3.5), (1.5, 0.4, 3), (2, 0.35, 2.5), (2.52, 0.2, 2), (3.01, 0.15, 1.6)):
            campana += on * g * np.sin(2 * np.pi * 174.6 * r * tt) * np.exp(-tt / d)
    eco = np.zeros(n)
    for dly, g in ((0.09, 0.6), (0.21, 0.45), (0.37, 0.33), (0.58, 0.22), (0.83, 0.14)):
        k = int(dly * SR); eco[k:] += g * campana[:-k]
    campana = campana + eco
    k = 9; campana = np.convolve(campana, np.ones(k) / k, mode="same")      # suave, como si estuviera lejos
    # viento de noche: ruido filtrado con ráfagas lentas
    ruido = rng.standard_normal(n)
    F = np.fft.rfft(ruido); fr = np.fft.rfftfreq(n, 1 / SR)
    F *= np.exp(-((np.log(fr + 1) - np.log(420)) ** 2) / (2 * 0.55 ** 2))
    viento = np.fft.irfft(F, n)
    viento *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.06 * t + 1) * np.sin(2 * np.pi * 0.11 * t + 2)
    # tensión en los últimos 3 segundos: trémolo agudo disonante y crescendo
    cre = np.clip((t - 26.8) / 3.2, 0, 1) ** 1.5
    tension = cre * (np.sin(2 * np.pi * 440 * t) + 0.8 * np.sin(2 * np.pi * 466.2 * t) + 0.5 * np.sin(2 * np.pi * 220 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t))
    def nrm(x): return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)
    m = 0.55 * nrm(dron) + 0.75 * nrm(cuerdas) + 0.35 * nrm(campana) + 0.3 * nrm(viento) + 0.6 * nrm(tension) * (np.sqrt(np.mean(cre ** 2)) + 1e-9)
    m *= 1 + 1.2 * cre                                                   # sube la tensión al final
    m *= np.clip(t / 1.2, 0, 1)                                          # entrada suave
    # muy baja: unos 15-20 dB por debajo de la voz, y aún más baja mientras se habla
    rv = np.sqrt(np.mean(vref[np.abs(vref) > 0.01] ** 2))
    m *= (rv * 0.17) / (np.sqrt(np.mean(m[: int(SR * 26)] ** 2)) + 1e-9)
    envv = np.convolve(np.abs(vref), np.ones(int(SR * 0.25)) / int(SR * 0.25), mode="same")
    m *= 1 - 0.35 * np.clip(envv / (envv.max() + 1e-9) * 3, 0, 1)
    m[-int(SR * 0.008):] *= np.linspace(1, 0, int(SR * 0.008))          # corte en seco, sin chasquido
    return m.astype(np.float32)

# ---------- imagen ----------
def fuente(nombre, tam):
    for r in (f"/usr/share/fonts/truetype/dejavu/{nombre}", nombre):
        try: return ImageFont.truetype(r, tam)
        except OSError: pass
    return ImageFont.load_default()

def partir(texto, f, ancho, d):
    lineas, l = [], ""
    for p in texto.split():
        c = (l + " " + p).strip()
        if d.textlength(c, font=f) <= ancho: l = c
        else: lineas.append(l); l = p
    return lineas + [l]

def capa_subtitulo(texto):
    im = Image.new("RGBA", (W, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = fuente("DejaVuSans-Bold.ttf", 70)
    ls = partir(texto, f, W - 120, d); alto = 86 * len(ls); y0 = (520 - alto) / 2 + 43
    for i, l in enumerate(ls):
        d.text((W / 2, y0 + 86 * i), l, font=f, fill=(255, 255, 255, 255), anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0, 255))
    return im

def capa_texto(texto):
    im = Image.new("RGBA", (W, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    tam = 64
    while d.textlength(texto, font=fuente("DejaVuSerif-Bold.ttf", tam)) > W - 110: tam -= 2
    f = fuente("DejaVuSerif-Bold.ttf", tam); tw = d.textlength(texto, font=f)
    d.text((W / 2, 92), texto, font=f, fill=(240, 226, 196, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, 255))
    for s in (-1, 1):   # filetes rojos a los lados, como en la portada
        x0 = W / 2 + s * (tw / 2 + 22); d.line([(x0, 92), (x0 + s * 60, 92)], fill=(200, 16, 30, 255), width=4)
    d.line([(W / 2 - 150, 150), (W / 2 + 150, 150)], fill=(200, 16, 30, 230), width=3)
    return im

def a_np(im):
    a = np.asarray(im, dtype=np.float32) / 255.0
    return a[..., :3], a[..., 3:4]

def render(subs, audio_wav, salida):
    src = Image.open(PORTADA).convert("RGB"); sw, sh = src.size
    # encuadre final: portada a pantalla completa (9:16), centrada
    fh = sh; fw = fh * W / H
    Z0 = 2.9                                  # ampliación inicial
    c0, c1 = (548.0, 975.0), (sw / 2, sh / 2)   # empieza sobre el libro y la figura oscura del centro
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    vineta = (1 - 0.72 * np.clip(r - 0.45, 0, 1) ** 1.4)[..., None].astype(np.float32)
    rng = np.random.default_rng(5)
    granos = [np.kron(rng.normal(0, 0.045, (H // 2, W // 2)).astype(np.float32), np.ones((2, 2), np.float32))[..., None] for _ in range(8)]
    n = int(DUR * FPS)
    # parpadeo de farola antigua: oscilación suave y algún bajón breve
    tt = np.arange(n) / FPS
    luz = 1 + 0.025 * np.sin(2 * np.pi * 0.8 * tt) + 0.015 * np.sin(2 * np.pi * 2.3 * tt + 1)
    for c in rng.uniform(1.5, 28.5, 7):
        k = int(c * FPS); luz[k:k + 2] *= 0.86; luz[k + 2:k + 3] *= 0.95
    Y_SUB, Y_TXT = 900, 1460                  # subtítulo sobre el libro; texto en el hueco antes de «YA DISPONIBLE»
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", audio_wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "22", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{DUR}",
                          "-movflags", "+faststart", salida], stdin=subprocess.PIPE)
    for i in range(n):
        u = i / (n - 1)
        e = u * u * (3 - 2 * u) * 0.35 + u * 0.65            # alejamiento continuo, sin tirones
        z = Z0 ** (1 - e)
        cw, ch = fw / z, fh / z
        cx = c0[0] + (c1[0] - c0[0]) * e; cy = c0[1] + (c1[1] - c0[1]) * e
        cx = min(max(cx, cw / 2), sw - cw / 2); cy = min(max(cy, ch / 2), sh - ch / 2)
        fr = src.transform((W, H), Image.EXTENT, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), Image.BICUBIC)
        a = np.asarray(fr, dtype=np.float32) / 255.0
        a = a * vineta * luz[i] + granos[i % 8]
        t = i / FPS
        for capas, y in ():     # sin ningún texto encima: solo la portada
            for (t0, t1, rgb, al) in capas:
                if t0 <= t < t1:   # entra con un fundido muy corto y sale en seco: nunca se ven dos a la vez
                    f = min(1.0, (t - t0) / 0.12 + 0.2)
                    zona = a[y:y + rgb.shape[0]]
                    zona[:] = zona * (1 - al * f) + rgb * al * f
        p.stdin.write((np.clip(a, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()

def main(carpeta):
    os.makedirs(carpeta, exist_ok=True); tmp = os.path.join(carpeta, "tmp"); os.makedirs(tmp, exist_ok=True)
    print("Voz en off…")
    seca, subs = voz(tmp)
    v = tratar_voz(seca, tmp)
    print("Música…")
    m = musica(v)
    mezcla = v + m
    mezcla = np.tanh(mezcla * 1.1) / np.tanh(1.1) * 0.95
    wav = os.path.join(tmp, "final.wav"); escribir_wav(wav, mezcla)
    escribir_wav(os.path.join(tmp, "voz_final.wav"), v)
    ff("-i", os.path.join(tmp, "voz_final.wav"), "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(carpeta, "voz.mp3"))
    print("Vídeo…")
    render(subs, wav, os.path.join(carpeta, "sombras_de_aranjuez_shorts.mp4"))
    for s in subs: print(f"  sub {s[0]:.2f}-{s[1]:.2f} {s[2]}")
    print("Listo:", os.path.join(carpeta, "sombras_de_aranjuez_shorts.mp4"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "salida")
