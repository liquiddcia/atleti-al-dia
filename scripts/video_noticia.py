"""Genera el vídeo vertical de la noticia "Al Atlético le salen las cuentas".

Voz con edge-tts (es-ES-AlvaroNeural) y efecto grave, subtítulos sincronizados
frase a frase, titular rojo arriba y gráfico de barras con zoom lento en el centro.
Debajo suena un fondo generado aquí mismo (ambiente de estadio y música animada)
que baja solo cuando habla el narrador.
Uso: python3 scripts/video_noticia.py salida/video.mp4
"""
import os
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = os.environ.get("FF") or imageio_ffmpeg.get_ffmpeg_exe()
VOZ = "es-ES-AlvaroNeural"
FILTRO_VOZ = "asetrate=24000*0.92,aresample=44100,atempo=1/0.92,bass=g=6:f=120,acompressor"
# edge-tts deja casi medio segundo de silencio al principio y al final de cada frase
RECORTE = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
           "silenceremove=start_periods=1:start_threshold=-45dB,areverse")
ANCHO, ALTO, FPS = 1080, 1920, 30
PAUSA = 0.3  # silencio entre frases (s)
ZOOM_FINAL = 1.10  # el gráfico pasa de 1.00 a 1.10 de forma lineal, sin volver atrás
INTRO, OUTRO = 1.5, 2.0  # cortinillas con el logo solo (s)
FUNDIDO = 0.4  # fundido desde/hacia negro en las cortinillas (s)
SR = 44100
BPM = 100
ACORDES = [  # Do - Sol - La m - Fa: progresión mayor, optimista
    (261.63, 329.63, 392.00), (196.00, 246.94, 293.66),
    (220.00, 261.63, 329.63), (174.61, 220.00, 261.63),
]

TITULAR = "AL ATLÉTICO LE SALEN LAS CUENTAS"
FRASES = [
    "Al Atlético le salen las cuentas.",
    "El equipo de Simeone suma veinticinco de treinta puntos en diez jornadas.",
    "Iguala la 2012-13 y la 2020-21, el año del último título.",
    "Solo la 2013-14, con veintisiete, y la 1995-96, con veintiséis, arrancaron mejor.",
    "Y las dos terminaron con la Liga en las vitrinas rojiblancas.",
    "Los números ilusionan. ¿Será este el año? Esto es Diario Colchonero.",
]
ARRANQUES = [  # (temporada, puntos de 30)
    ("2013-14", 27),
    ("1995-96", 26),
    ("2012-13", 25),
    ("2020-21", 25),
    ("2026-27", 25),
]

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LOGO = os.path.join(RAIZ, "public", "imagenes", "logo-canal.jpg")
# Si aquí hay una canción (mp3, m4a, wav u ogg), se usa como música de fondo en lugar
# de la sintetizada. Pensado para temas de la biblioteca de audio de YouTube.
MUSICA_DIR = os.path.join(RAIZ, "assets", "musica")
ROJO = (203, 53, 36)
AZUL_FONDO = (12, 22, 48)
AZUL_BARRA = (60, 90, 160)
BLANCO = (255, 255, 255)
GRIS = (170, 180, 200)


def fuente(tamano, negrita=True):
    nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    for ruta in (f"/usr/share/fonts/truetype/dejavu/{nombre}", nombre):
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            pass
    return ImageFont.load_default(tamano)


def partir(texto, fnt, ancho_max, draw):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if draw.textlength(prueba, font=fnt) <= ancho_max:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def generar_audio(carpeta):
    """Una pista por frase; devuelve la ruta del wav completo y los tramos (inicio, fin)."""
    muestras, tramos, t = [], [], INTRO + 0.3
    params = None
    for i, frase in enumerate(FRASES):
        mp3 = os.path.join(carpeta, f"frase{i}.mp3")
        wav = os.path.join(carpeta, f"frase{i}.wav")
        subprocess.run(["edge-tts", "--voice", VOZ, "--text", frase, "--write-media", mp3],
                       check=True, timeout=90)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, "-af", f"{FILTRO_VOZ},{RECORTE}",
                        "-ac", "1", "-ar", "44100", "-sample_fmt", "s16", wav], check=True)
        with wave.open(wav) as w:
            params = w.getparams()
            datos = w.readframes(w.getnframes())
            dur = w.getnframes() / w.getframerate()
        muestras.append(datos)
        tramos.append((t, t + dur))
        t += dur + PAUSA
    silencio = lambda s: b"\x00\x00" * int(44100 * s)
    total = os.path.join(carpeta, "voz.wav")
    with wave.open(total, "wb") as w:
        w.setparams(params)
        w.writeframes(silencio(INTRO + 0.3))
        for datos in muestras:
            w.writeframes(datos + silencio(PAUSA))
        w.writeframes(silencio(0.8 + OUTRO))
    duracion = t - PAUSA + 0.8 + OUTRO
    return total, tramos, duracion


def ruido_banda(n, rng, f_baja, f_alta):
    espectro = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    espectro[(f < f_baja) | (f > f_alta)] = 0
    x = np.fft.irfft(espectro, n)
    return x / np.max(np.abs(x))


def envolvente(t, puntos):
    """Interpola linealmente una curva de volumen dada como [(segundo, nivel), ...]."""
    xs, ys = zip(*puntos)
    return np.interp(t, xs, ys)


def buscar_musica():
    if not os.path.isdir(MUSICA_DIR):
        return None
    temas = sorted(f for f in os.listdir(MUSICA_DIR)
                   if f.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")))
    return os.path.join(MUSICA_DIR, temas[0]) if temas else None


def cargar_musica(ruta, duracion):
    """Decodifica la canción en mono, repitiéndola si es más corta que el vídeo."""
    crudo = subprocess.run([FF, "-loglevel", "error", "-stream_loop", "-1", "-i", ruta,
                            "-t", f"{duracion:.3f}", "-ac", "1", "-ar", str(SR),
                            "-f", "s16le", "-"], check=True, capture_output=True).stdout
    x = np.frombuffer(crudo, "<i2").astype(np.float64) / 32768
    x = np.pad(x, (0, max(int(duracion * SR) - len(x), 0)))[:int(duracion * SR)]
    return x / (np.max(np.abs(x)) or 1)


def generar_fondo(carpeta, duracion):
    """Ambiente de estadio y música animada: la canción de assets/musica o una sintetizada."""
    rng = np.random.default_rng(1903)
    n = int(duracion * SR)
    t = np.arange(n) / SR
    fin = duracion - OUTRO

    # Grada: murmullo continuo que respira, con rugidos en las cortinillas.
    murmullo = ruido_banda(n, rng, 250, 1800)
    respira = 0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * t) * np.sin(2 * np.pi * 0.07 * t + 1)
    rugido = ruido_banda(n, rng, 400, 3500)
    grada = 0.10 * murmullo * respira + 0.30 * rugido * envolvente(
        t, [(0, 0), (0.3, 1), (INTRO + 0.4, 0.15), (INTRO + 1.2, 0),
            (fin - 0.3, 0), (fin + 0.4, 1), (duracion, 0.6)])

    # Música: acordes suaves, bajo y bombo a 100 bpm.
    pulso = 60 / BPM
    compas = 4 * pulso
    musica = np.zeros(n)
    for i in range(int(duracion / compas) + 1):
        a, b = int(i * compas * SR), min(int((i + 1) * compas * SR), n)
        if a >= n:
            break
        tt = np.arange(b - a) / SR
        acorde = ACORDES[i % len(ACORDES)]
        ataque = np.minimum(tt / 0.25, 1) * np.minimum((compas - tt) / 0.3, 1)
        pad = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2.003 * f * tt)
                  for f in acorde)
        musica[a:b] += 0.05 * pad * ataque
        for golpe in range(4):
            g = int(golpe * pulso * SR)
            m = min(int(0.5 * SR), b - a - g)
            if m <= 0:
                continue
            tg = np.arange(m) / SR
            # bajo en los tiempos 1 y 3, bombo en todos
            if golpe % 2 == 0:
                musica[a + g:a + g + m] += 0.16 * np.sin(2 * np.pi * acorde[0] / 2 * tg) * np.exp(-tg * 5)
            fase = 2 * np.pi * (50 * tg + 70 * (1 - np.exp(-tg * 30)) / 30)
            musica[a + g:a + g + m] += 0.30 * np.sin(fase) * np.exp(-tg * 14)
    cancion = buscar_musica()
    if cancion:
        print(f"Música de fondo: {os.path.basename(cancion)}", flush=True)
        # La canción manda; la grada queda solo como ambiente suave.
        musica = 0.9 * cargar_musica(cancion, duracion)
        grada *= 0.5
        musica *= envolvente(t, [(0, 0), (0.6, 1), (duracion - 1.5, 1), (duracion, 0)])
    else:
        musica *= envolvente(t, [(0, 0), (INTRO, 1), (duracion - 1.5, 1), (duracion, 0)])

    fondo = grada + musica
    fondo = 0.5 * fondo / np.max(np.abs(fondo))
    ruta = os.path.join(carpeta, "fondo.wav")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((fondo * 32767).astype("<i2").tobytes())
    return ruta


def mezclar(carpeta, voz, fondo):
    """El fondo se agacha cuando suena la voz (sidechain) y se suma por debajo."""
    ruta = os.path.join(carpeta, "mezcla.wav")
    subprocess.run([
        FF, "-y", "-loglevel", "error", "-i", voz, "-i", fondo, "-filter_complex",
        "[0]asplit[v][clave];[1]anull[f];"
        "[f][clave]sidechaincompress=threshold=0.05:ratio=3:attack=15:release=350[fd];"
        "[v][fd]amix=inputs=2:normalize=0,alimiter=limit=0.95",
        "-ac", "1", "-ar", str(SR), ruta], check=True)
    return ruta


def degradado():
    img = Image.new("RGB", (ANCHO, ALTO), AZUL_FONDO)
    d = ImageDraw.Draw(img)
    for y in range(ALTO):  # degradado vertical suave
        k = y / ALTO
        d.line([(0, y), (ANCHO, y)], fill=(int(12 + 10 * k), int(22 + 8 * k), int(48 - 20 * k)))
    return img


def cortinilla():
    """Pantalla con el logo y el nombre, para el principio y el final."""
    img = degradado()
    lado, borde = 560, 18
    logo = Image.open(LOGO).convert("RGB").resize((lado, lado), Image.LANCZOS)
    logo = logo.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    mascara = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(mascara).ellipse([0, 0, lado - 1, lado - 1], fill=255)
    x, y = (ANCHO - lado) // 2 - borde, (ALTO - lado) // 2 - borde - 90
    d = ImageDraw.Draw(img)
    d.ellipse([x, y, x + lado + 2 * borde, y + lado + 2 * borde], fill=ROJO)
    img.paste(logo, (x + borde, y + borde), mascara)
    d.text((ANCHO / 2, y + lado + 2 * borde + 110), "DIARIO COLCHONERO", font=fuente(70),
           fill=BLANCO, anchor="mm")
    return img


def fondo_fijo():
    img = degradado()
    d = ImageDraw.Draw(img)
    # Marca: logo del oso en círculo con borde rojo y el nombre al lado
    lado, borde, y_logo = 116, 6, 17
    logo = Image.open(LOGO).convert("RGB").resize((lado, lado), Image.LANCZOS)
    mascara = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(mascara).ellipse([0, 0, lado - 1, lado - 1], fill=255)
    fnt_marca = fuente(46)
    texto = "DIARIO COLCHONERO"
    ancho_marca = lado + 2 * borde + 26 + d.textlength(texto, font=fnt_marca)
    x_logo = int((ANCHO - ancho_marca) / 2)
    d.ellipse([x_logo, y_logo, x_logo + lado + 2 * borde, y_logo + lado + 2 * borde], fill=ROJO)
    img.paste(logo, (x_logo + borde, y_logo + borde), mascara)
    d.text((x_logo + lado + 2 * borde + 26, y_logo + borde + lado / 2), texto,
           font=fnt_marca, fill=BLANCO, anchor="lm")
    # Titular rojo
    fnt = fuente(84)
    lineas = partir(TITULAR, fnt, ANCHO - 140, d)
    alto_linea = 100
    caja_alto = alto_linea * len(lineas) + 70
    d.rectangle([0, 150, ANCHO, 150 + caja_alto], fill=ROJO)
    for i, linea in enumerate(lineas):
        d.text((ANCHO / 2, 150 + 35 + alto_linea * i + alto_linea / 2), linea,
               font=fnt, fill=BLANCO, anchor="mm")
    d.text((ANCHO / 2, 150 + caja_alto + 50), "MEJORES ARRANQUES EN LIGA · 10 JORNADAS",
           font=fuente(36), fill=GRIS, anchor="mm")
    return img


def grafico():
    # Margen transparente para que el panel no se recorte al hacer zoom.
    w, h, m = 940, 780, 60
    img = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([m, m, m + w - 1, m + h - 1], radius=36, fill=(255, 255, 255, 18))
    fnt_t, fnt_v = fuente(44), fuente(52)
    x0, x_max, alto, hueco = m + 220, m + w - 160, 96, 40
    y = m + 70
    for temporada, puntos in ARRANQUES:
        actual = temporada == "2026-27"
        largo = (x_max - x0) * puntos / 30
        d.text((x0 - 25, y + alto / 2), temporada, font=fnt_t,
               fill=BLANCO if actual else GRIS, anchor="rm")
        d.rounded_rectangle([x0, y, x0 + largo, y + alto], radius=14,
                            fill=ROJO if actual else AZUL_BARRA)
        d.text((x0 + largo + 20, y + alto / 2), f"{puntos}/30", font=fnt_v,
               fill=BLANCO, anchor="lm")
        y += alto + hueco
    return img


def subtitulos(tramos):
    capas = []
    fnt = fuente(58)
    for frase in FRASES:
        capa = Image.new("RGBA", (ANCHO, 380), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        lineas = partir(frase, fnt, ANCHO - 160, d)
        alto_linea = 74
        total = alto_linea * len(lineas)
        y0 = (380 - total) / 2
        ancho = max(d.textlength(l, font=fnt) for l in lineas)
        d.rounded_rectangle([(ANCHO - ancho) / 2 - 36, y0 - 24, (ANCHO + ancho) / 2 + 36,
                             y0 + total + 24], radius=22, fill=(0, 0, 0, 190))
        for i, linea in enumerate(lineas):
            d.text((ANCHO / 2, y0 + alto_linea * i + alto_linea / 2), linea, font=fnt,
                   fill=BLANCO, anchor="mm")
        capas.append(capa)
    return list(zip(tramos, capas))


def main(salida):
    carpeta = os.path.dirname(os.path.abspath(salida))
    os.makedirs(carpeta, exist_ok=True)
    voz, tramos, duracion = generar_audio(carpeta)
    audio = mezclar(carpeta, voz, generar_fondo(carpeta, duracion))
    print(f"Duración: {duracion:.2f} s", flush=True)
    for (a, b), frase in zip(tramos, FRASES):
        print(f"  {a:6.2f} → {b:6.2f}  {frase}")

    base = fondo_fijo()
    graf = grafico()
    gw, gh = graf.size
    gx, gy = (ANCHO - gw) // 2, 600
    subs = subtitulos(tramos)
    logo = cortinilla()
    negro = Image.new("RGB", (ANCHO, ALTO), (0, 0, 0))
    fin_noticia = duracion - OUTRO

    proc = subprocess.Popen([
        FF, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-",
        "-i", audio,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", salida,
    ], stdin=subprocess.PIPE)

    n = int(round(duracion * FPS))
    for f in range(n):
        t = f / FPS
        if t < INTRO or t >= fin_noticia:
            frame = logo
            if t < FUNDIDO:
                frame = Image.blend(negro, logo, t / FUNDIDO)
            elif t > duracion - FUNDIDO:
                frame = Image.blend(negro, logo, max(duracion - t, 0) / FUNDIDO)
            proc.stdin.write(frame.tobytes())
            continue
        # Zoom lineal y monótono con coordenadas en coma flotante: sin saltos ni rebote.
        z = 1 + (ZOOM_FINAL - 1) * ((t - INTRO) / (fin_noticia - INTRO))
        cx, cy = gw / 2, gh / 2
        g = graf.transform((gw, gh), Image.AFFINE,
                           (1 / z, 0, cx - cx / z, 0, 1 / z, cy - cy / z),
                           resample=Image.BICUBIC)
        frame = base.copy()
        frame.paste(g, (gx, gy), g)
        for i, ((a, b), capa) in enumerate(subs):
            if a <= t and (t < b + PAUSA or i == len(subs) - 1):
                frame.paste(capa, (0, 1500), capa)
                break
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falló")
    print(f"Vídeo listo: {salida}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "salida/atleti-cuentas.mp4")
