"""Genera un vídeo vertical de noticia a partir de un archivo videos/<nombre>.json.

Voz con edge-tts (es-ES-AlvaroNeural) y efecto grave, subtítulos sincronizados
frase a frase, titular rojo arriba e imagen central (barras o lista) con zoom lento.
Debajo suena un fondo (ambiente de estadio y música) que baja solo cuando habla el
narrador. El formato del json está explicado en videos/LEEME.md.
Uso: python3 scripts/video_noticia.py videos/<nombre>.json [salida/<nombre>.mp4]
"""
import json
import os
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

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
GRIS_CLARO = (205, 212, 225)
COLORES = {"verde": (46, 204, 113), "ambar": (245, 166, 35), "rojo": ROJO, "gris": GRIS}
# Zona de la pantalla para la imagen central: debajo del titular y encima de los subtítulos
Y_SUBTITULOS, ALTO_SUBTITULOS = 1490, 400


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


def generar_audio(carpeta, frases):
    """Una pista por frase; devuelve la ruta del wav completo y los tramos (inicio, fin)."""
    muestras, tramos, t = [], [], INTRO + 0.3
    params = None
    for i, frase in enumerate(frases):
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


def fondo_fijo(titular, titulo_imagen):
    """Marca, titular rojo y título de la imagen; devuelve la imagen y dónde acaba."""
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
    # Titular rojo, con las líneas tal cual vienen en el json y el tamaño que quepa
    lineas = titular if isinstance(titular, list) else partir(titular, fuente(84), ANCHO - 140, d)
    tamano = 100
    while tamano > 50 and max(d.textlength(l, font=fuente(tamano)) for l in lineas) > ANCHO - 120:
        tamano -= 2
    fnt = fuente(tamano)
    alto_linea = int(tamano * 1.18)
    caja_alto = alto_linea * len(lineas) + 70
    d.rectangle([0, 150, ANCHO, 150 + caja_alto], fill=ROJO)
    for i, linea in enumerate(lineas):
        d.text((ANCHO / 2, 150 + 35 + alto_linea * i + alto_linea / 2), linea,
               font=fnt, fill=BLANCO, anchor="mm")
    y = 150 + caja_alto
    if titulo_imagen:
        d.text((ANCHO / 2, y + 50), titulo_imagen, font=fuente(36), fill=GRIS, anchor="mm")
        y += 80
    return img, y


# Margen transparente alrededor del panel para que no se recorte al hacer zoom.
PANEL_ANCHO, MARGEN = 940, 60


def panel(alto):
    img = Image.new("RGBA", (PANEL_ANCHO + 2 * MARGEN, alto + 2 * MARGEN), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([MARGEN, MARGEN, MARGEN + PANEL_ANCHO - 1, MARGEN + alto - 1],
                        radius=36, fill=(255, 255, 255, 18))
    return img, d


def pie_rojo(d, texto, y):
    """Franja roja al pie del panel; devuelve la altura que ocupa."""
    fnt = fuente(36)
    lineas = partir(texto, fnt, PANEL_ANCHO - 140, d)
    alto = 46 * len(lineas) + 40
    x0, x1 = MARGEN + 40, MARGEN + PANEL_ANCHO - 40
    d.rounded_rectangle([x0, y, x1, y + alto], radius=18, fill=ROJO)
    for i, linea in enumerate(lineas):
        d.text(((x0 + x1) / 2, y + 20 + 46 * i + 23), linea, font=fnt, fill=BLANCO, anchor="mm")
    return alto


def imagen_barras(datos):
    barras, maximo = datos["barras"], datos.get("maximo") or max(b["valor"] for b in datos["barras"])
    formato = datos.get("formato", "{valor}")
    alto, hueco = 96, 40
    h = 140 + len(barras) * (alto + hueco) - hueco
    pie = datos.get("pie")
    if pie:
        h += 110
    img, d = panel(h)
    fnt_t, fnt_v = fuente(44), fuente(52)
    x0, x_max = MARGEN + 220, MARGEN + PANEL_ANCHO - 160
    y = MARGEN + 70
    for barra in barras:
        destacada = barra.get("destacada", False)
        largo = (x_max - x0) * barra["valor"] / maximo
        d.text((x0 - 25, y + alto / 2), barra["etiqueta"], font=fnt_t,
               fill=BLANCO if destacada else GRIS, anchor="rm")
        d.rounded_rectangle([x0, y, x0 + largo, y + alto], radius=14,
                            fill=ROJO if destacada else AZUL_BARRA)
        d.text((x0 + largo + 20, y + alto / 2), formato.format(valor=barra["valor"]), font=fnt_v,
               fill=BLANCO, anchor="lm")
        y += alto + hueco
    if pie:
        pie_rojo(d, pie, y - hueco + 40)
    return img


def imagen_lista(datos):
    """Filas con un punto de color a la izquierda, nombre en blanco y estado debajo."""
    fnt_n, fnt_e = fuente(44), fuente(36, negrita=False)
    x_texto = MARGEN + 110
    ancho_texto = PANEL_ANCHO - 110 - 50
    medida = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    filas = []
    for fila in datos["filas"]:
        nombre = partir(fila["nombre"], fnt_n, ancho_texto, medida)
        estado = partir(fila["estado"], fnt_e, ancho_texto, medida)
        filas.append((fila, nombre, estado, 54 * len(nombre) + 8 + 46 * len(estado)))
    hueco = 56
    h = 100 + sum(f[3] for f in filas) + hueco * (len(filas) - 1)
    pie = datos.get("pie")
    if pie:
        h += 50 + 46 * len(partir(pie, fuente(36), PANEL_ANCHO - 140, medida)) + 40
    img, d = panel(h)
    y = MARGEN + 50
    for i, (fila, nombre, estado, alto) in enumerate(filas):
        if i:
            linea_y = y - hueco / 2
            d.line([(MARGEN + 50, linea_y), (MARGEN + PANEL_ANCHO - 50, linea_y)],
                   fill=(255, 255, 255, 30), width=2)
        color = COLORES.get(fila.get("color", "gris"), GRIS)
        cy = y + 27
        d.ellipse([MARGEN + 50, cy - 17, MARGEN + 84, cy + 17], fill=color)
        for j, linea in enumerate(nombre):
            d.text((x_texto, y + 54 * j + 27), linea, font=fnt_n, fill=BLANCO, anchor="lm")
        ye = y + 54 * len(nombre) + 8
        for j, linea in enumerate(estado):
            d.text((x_texto, ye + 46 * j + 23), linea, font=fnt_e, fill=GRIS_CLARO, anchor="lm")
        y += alto + hueco
    if pie:
        pie_rojo(d, pie, y - hueco + 50)
    return img


def imagen_foto(datos):
    """Foto de la noticia con esquinas redondeadas dentro del panel."""
    fuente_img = Image.open(datos["ruta"]).convert("RGB")
    ancho = PANEL_ANCHO - 60
    # Entre apaisada 8:3 (las de categoría) y cuadrada; si es más alta, se recorta al centro,
    # salvo que el json permita más ("proporcion_max", por ejemplo 1.8 para carteles verticales).
    proporcion = min(max(fuente_img.height / fuente_img.width, 0.375), datos.get("proporcion_max", 1.0))
    alto = round(ancho * proporcion)
    foto = ImageOps.fit(fuente_img, (ancho, alto), Image.LANCZOS)
    mascara = Image.new("L", (ancho, alto), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, ancho - 1, alto - 1], radius=26, fill=255)
    pie = datos.get("pie")
    medida = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    # Texto opcional bajo la foto (por ejemplo, el resumen de la noticia), como mucho 5 líneas
    fnt_t = fuente(38, negrita=False)
    lineas = partir(datos["texto"], fnt_t, PANEL_ANCHO - 100, medida) if datos.get("texto") else []
    if len(lineas) > 5:
        lineas = lineas[:5]
        lineas[-1] = lineas[-1].rstrip(" ,.;:") + "…"
    h = 60 + alto + (30 + 52 * len(lineas) if lineas else 0)
    if pie:
        h += 30 + 46 * len(partir(pie, fuente(36), PANEL_ANCHO - 140, medida)) + 40
    img, d = panel(h)
    img.paste(foto, (MARGEN + 30, MARGEN + 30), mascara)
    y = MARGEN + 30 + alto
    if lineas:
        y += 30
        for i, linea in enumerate(lineas):
            d.text((MARGEN + 50, y + 52 * i + 26), linea, font=fnt_t, fill=GRIS_CLARO, anchor="lm")
        y += 52 * len(lineas)
    if pie:
        pie_rojo(d, pie, y + 30)
    return img


def imagen_central(datos, alto_disponible):
    tipos = {"barras": imagen_barras, "lista": imagen_lista, "foto": imagen_foto}
    img = tipos[datos["tipo"]](datos)
    # Que el panel quepa también al final del zoom; si no, se reduce entero.
    alto_panel = (img.height - 2 * MARGEN) * ZOOM_FINAL + 2 * MARGEN
    if alto_panel > alto_disponible:
        k = alto_disponible / alto_panel
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    return img


def subtitulos(textos, tramos):
    capas = []
    for frase in textos:
        capa = Image.new("RGBA", (ANCHO, ALTO_SUBTITULOS), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        tamano = 58  # las frases largas bajan de tamaño para no pasar de 4 líneas
        while True:
            fnt = fuente(tamano)
            lineas = partir(frase, fnt, ANCHO - 160, d)
            if len(lineas) <= 4 or tamano <= 44:
                break
            tamano -= 2
        alto_linea = int(tamano * 1.28)
        total = alto_linea * len(lineas)
        y0 = (ALTO_SUBTITULOS - total) / 2
        ancho = max(d.textlength(l, font=fnt) for l in lineas)
        d.rounded_rectangle([(ANCHO - ancho) / 2 - 36, y0 - 24, (ANCHO + ancho) / 2 + 36,
                             y0 + total + 24], radius=22, fill=(0, 0, 0, 190))
        for i, linea in enumerate(lineas):
            d.text((ANCHO / 2, y0 + alto_linea * i + alto_linea / 2), linea, font=fnt,
                   fill=BLANCO, anchor="mm")
        capas.append(capa)
    return list(zip(tramos, capas))


def cargar_noticia(ruta):
    with open(ruta, encoding="utf-8") as f:
        noticia = json.load(f)
    frases = []
    for frase in noticia["frases"]:
        if isinstance(frase, str):  # una frase suelta vale para voz y subtítulo
            frase = {"hablado": frase}
        hablado = frase.get("hablado") or frase["subtitulo"]
        frases.append({"hablado": hablado, "subtitulo": frase.get("subtitulo") or hablado})
    noticia["frases"] = frases
    return noticia


def main(ruta_json, salida):
    noticia = cargar_noticia(ruta_json)
    habladas = [f["hablado"] for f in noticia["frases"]]
    textos = [f["subtitulo"] for f in noticia["frases"]]
    carpeta = os.path.dirname(os.path.abspath(salida))
    os.makedirs(carpeta, exist_ok=True)
    voz, tramos, duracion = generar_audio(carpeta, habladas)
    audio = mezclar(carpeta, voz, generar_fondo(carpeta, duracion))
    print(f"Duración: {duracion:.2f} s", flush=True)
    for (a, b), frase in zip(tramos, textos):
        print(f"  {a:6.2f} → {b:6.2f}  {frase}")

    datos = noticia["imagen"]
    base, y_libre = fondo_fijo(noticia["titular"], datos.get("titulo"))
    # Hueco entre el titular y los subtítulos, sin contar el margen transparente.
    hueco_arriba, hueco_abajo = y_libre + 10, Y_SUBTITULOS + 20
    graf = imagen_central(datos, hueco_abajo - hueco_arriba + 2 * MARGEN)
    gw, gh = graf.size
    gx, gy = (ANCHO - gw) // 2, int((hueco_arriba + hueco_abajo - gh) / 2)
    subs = subtitulos(textos, tramos)
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
                frame.paste(capa, (0, Y_SUBTITULOS), capa)
                break
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falló")
    print(f"Vídeo listo: {salida}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 scripts/video_noticia.py videos/<nombre>.json [salida.mp4]")
    nombre = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else f"salida/{nombre}.mp4")
