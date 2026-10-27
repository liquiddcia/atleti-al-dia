"""Genera el vídeo vertical de la noticia "Al Atlético le salen las cuentas".

Voz con edge-tts (es-ES-AlvaroNeural) y efecto grave, subtítulos sincronizados
frase a frase, titular rojo arriba y gráfico de barras con zoom lento en el centro.
Uso: python3 scripts/video_noticia.py salida/video.mp4
"""
import os
import subprocess
import sys
import wave

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = os.environ.get("FF") or imageio_ffmpeg.get_ffmpeg_exe()
VOZ = "es-ES-AlvaroNeural"
FILTRO_VOZ = "asetrate=24000*0.85,aresample=44100,atempo=1/0.85,bass=g=6:f=120,acompressor"
ANCHO, ALTO, FPS = 1080, 1920, 30
PAUSA = 0.3  # silencio entre frases (s)
ZOOM_FINAL = 1.10  # el gráfico pasa de 1.00 a 1.10 de forma lineal, sin volver atrás

TITULAR = "AL ATLÉTICO LE SALEN LAS CUENTAS"
FRASES = [
    "Al Atlético le salen las cuentas.",
    "El equipo de Simeone suma veinticinco de treinta puntos en diez jornadas.",
    "Iguala la 2012-13 y la 2020-21, el año del último título.",
    "Solo la 2013-14, con veintisiete, y la 1995-96, con veintiséis, arrancaron mejor.",
    "Y las dos terminaron con la Liga en las vitrinas rojiblancas.",
    "Los números ilusionan. ¿Será este el año? Esto es Atleti al día.",
]
ARRANQUES = [  # (temporada, puntos de 30)
    ("2013-14", 27),
    ("1995-96", 26),
    ("2012-13", 25),
    ("2020-21", 25),
    ("2026-27", 25),
]

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
    muestras, tramos, t = [], [], 0.4
    params = None
    for i, frase in enumerate(FRASES):
        mp3 = os.path.join(carpeta, f"frase{i}.mp3")
        wav = os.path.join(carpeta, f"frase{i}.wav")
        subprocess.run(["edge-tts", "--voice", VOZ, "--text", frase, "--write-media", mp3],
                       check=True, timeout=90)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, "-af", FILTRO_VOZ,
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
        w.writeframes(silencio(0.4))
        for datos in muestras:
            w.writeframes(datos + silencio(PAUSA))
        w.writeframes(silencio(0.8))
    duracion = t - PAUSA + 0.8 + 0.4
    return total, tramos, duracion


def fondo_fijo():
    img = Image.new("RGB", (ANCHO, ALTO), AZUL_FONDO)
    d = ImageDraw.Draw(img)
    for y in range(ALTO):  # degradado vertical suave
        k = y / ALTO
        d.line([(0, y), (ANCHO, y)], fill=(int(12 + 10 * k), int(22 + 8 * k), int(48 - 20 * k)))
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
    print(f"Duración: {duracion:.2f} s", flush=True)
    for (a, b), frase in zip(tramos, FRASES):
        print(f"  {a:6.2f} → {b:6.2f}  {frase}")

    base = fondo_fijo()
    graf = grafico()
    gw, gh = graf.size
    gx, gy = (ANCHO - gw) // 2, 600
    subs = subtitulos(tramos)

    proc = subprocess.Popen([
        FF, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-",
        "-i", voz,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", salida,
    ], stdin=subprocess.PIPE)

    n = int(round(duracion * FPS))
    for f in range(n):
        t = f / FPS
        # Zoom lineal y monótono con coordenadas en coma flotante: sin saltos ni rebote.
        z = 1 + (ZOOM_FINAL - 1) * (f / max(n - 1, 1))
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
