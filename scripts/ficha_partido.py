"""Ficha de partido para los post partido (estilo marcador + estadísticas + línea de goles + onces).

ficha(datos, salida, W=1920, H=1272) dibuja la ficha. 'datos' es un dict:
  fecha, jornada, estadio
  local / visitante: {nombre, escudo, goles, formacion, once: [[portero], [defensas...], ...]}
      cada jugador es "Nombre" o "Nombre|Sustituto 56'"
  stats: {"tiros": [l, v], "a_puerta": [...], "paradas": [...], "fueras": [...], "posesion": [...],
          "corners": [...], "faltas": [...], "amarillas": [...], "rojas": [...]}
  goles: [{"min": 62, "equipo": "local"|"visitante", "jugador": "Nombre"}]
  duracion: 90 (o 95 si hubo descuento largo)"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_noticia as v

ROJO, AMARILLO, BLANCO, GRIS = (203, 53, 36), (255, 214, 0), (255, 255, 255), (190, 198, 214)
OSCURO, TARJETA, VERDE = (14, 16, 34), (30, 34, 58), (40, 170, 90)

def F(t, n=True): return v.fuente(t, negrita=n)

def _escudo(im, ruta, cx, cy, alto):
    e = Image.open(ruta).convert("RGBA"); e.thumbnail((alto, alto), Image.LANCZOS)
    im.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))

def _barras(d, x, y, w, h, a, b, col_a, col_b):
    tot = (a + b) or 1
    for k, (val, col) in enumerate(((a, col_a), (b, col_b))):
        bh = int(h * val / max(a, b, 1))
        bx = x + k * (w // 2 + 6)
        d.rectangle([bx, y + h - bh, bx + w // 2 - 6, y + h], fill=col)

def _anillo(d, cx, cy, r, frac, col):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(70, 76, 100), width=14)
    if frac > 0:
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * frac, fill=col, width=14)

def ficha(datos, salida, W=1920, H=1272):
    L, V = datos["local"], datos["visitante"]; st = datos["stats"]
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H): d.line([(0, y), (W, y)], fill=(int(12 + 14 * y / H), int(16 + 12 * y / H), int(32 + 16 * y / H)))
    im = im.convert("RGBA"); d = ImageDraw.Draw(im)
    # cabecera
    d.text((60, 45), datos.get("fecha", ""), font=F(36, False), fill=GRIS, anchor="lm")
    d.text((W / 2, 45), datos.get("jornada", ""), font=F(38), fill=BLANCO, anchor="mm")
    d.text((W - 60, 45), datos.get("estadio", ""), font=F(36, False), fill=GRIS, anchor="rm")
    # marcador
    d.rounded_rectangle([60, 85, W - 60, 250], 28, fill=(245, 245, 245))
    d.text((W / 2 - 330, 167), L["nombre"].upper(), font=F(62), fill=(20, 20, 30), anchor="rm")
    _escudo(im, L["escudo"], W / 2 - 250, 167, 140); d = ImageDraw.Draw(im)
    for k, g in enumerate((L["goles"], V["goles"])):
        cx = W / 2 - 110 + k * 220
        d.rounded_rectangle([cx - 70, 100, cx + 70, 235], 18, fill=BLANCO, outline=(200, 200, 205), width=3)
        d.text((cx, 167), str(g), font=F(110), fill=(20, 20, 30), anchor="mm")
    d.text((W / 2, 167), "FINAL", font=F(30), fill=ROJO, anchor="mm")
    _escudo(im, V["escudo"], W / 2 + 250, 167, 140); d = ImageDraw.Draw(im)
    d.text((W / 2 + 330, 167), V["nombre"].upper(), font=F(62), fill=(20, 20, 30), anchor="lm")
    # bloques de estadísticas
    bloques = [("TIROS", [("Tiros", "tiros"), ("A puerta", "a_puerta"), ("Paradas", "paradas")]),
               ("GENERALES", [("Fueras de juego", "fueras"), ("Posesión", "posesion"), ("Córners", "corners")]),
               ("DISCIPLINA", [("Faltas", "faltas"), ("Amarillas", "amarillas"), ("Rojas", "rojas")])]
    bw = (W - 120 - 2 * 30) / 3
    for i, (tit, items) in enumerate(bloques):
        x0 = 60 + i * (bw + 30); y0 = 270; y1 = 620
        d.rounded_rectangle([x0, y0, x0 + bw, y1], 24, fill=TARJETA, outline=(70, 76, 100), width=3)
        d.text((x0 + bw / 2, y0 + 38), tit, font=F(40), fill=AMARILLO, anchor="mm")
        for j, (nom, clave) in enumerate(items):
            a, b = st.get(clave, ["-", "-"])
            cx = x0 + bw * (j + 0.5) / 3
            if clave == "posesion":
                _anillo(d, cx, y0 + 165, 66, (a or 0) / 100, VERDE)
                d.text((cx, y0 + 165), f"{a}%", font=F(36), fill=BLANCO, anchor="mm")
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                _barras(d, cx - 55, y0 + 90, 110, 140, a, b, VERDE, (150, 156, 175))
            d.text((cx, y0 + 268), nom, font=F(26 if len(nom) > 10 else 30, False), fill=GRIS, anchor="mm")
            d.text((cx, y0 + 315), f"{a} | {b}", font=F(40), fill=BLANCO, anchor="mm")
    # línea de goles
    ty = 705; tx0, tx1 = 260, W - 260; dur = datos.get("duracion", 90)
    d.line([(tx0, ty), (tx1, ty)], fill=VERDE, width=14)
    d.ellipse([(tx0 + tx1) / 2 - 26, ty - 26, (tx0 + tx1) / 2 + 26, ty + 26], fill=TARJETA, outline=VERDE, width=4)
    d.text(((tx0 + tx1) / 2, ty), "2.ª", font=F(26), fill=BLANCO, anchor="mm")
    d.rounded_rectangle([tx1 - 10, ty - 30, tx1 + 90, ty + 30], 30, fill=TARJETA, outline=VERDE, width=4)
    d.text((tx1 + 40, ty), "FIN", font=F(28), fill=BLANCO, anchor="mm")
    _escudo(im, L["escudo"], 150, ty - 38, 60); _escudo(im, V["escudo"], 150, ty + 38, 60); d = ImageDraw.Draw(im)
    etiquetas = {True: [], False: []}
    for g in datos.get("goles", []):
        x = tx0 + (tx1 - tx0) * min(g["min"], dur) / dur
        arriba = g["equipo"] == "local"
        yy = ty - 30 if arriba else ty + 30
        d.ellipse([x - 16, yy - 16, x + 16, yy + 16], fill=BLANCO, outline=(20, 20, 30), width=3)
        d.text((x, yy), "⚽", font=F(10), fill=BLANCO, anchor="mm")
        t = f"{g['jugador']} {g['min']}'"
        etiquetas[arriba].append([x, d.textlength(t, font=F(28)), t, yy + (-34 if arriba else 34)])
    for lista in etiquetas.values():   # separa las etiquetas de goles muy seguidos
        lista.sort()
        for _ in range(10):
            for a, b in zip(lista, lista[1:]):
                hueco = (a[0] + a[1] / 2 + 24) - (b[0] - b[1] / 2)
                if hueco > 0: a[0] -= hueco / 2; b[0] += hueco / 2
        for x, _, t, y in lista:
            d.text((x, y), t, font=F(28), fill=BLANCO, anchor="mm")
    # campo con los onces
    cy0, cy1 = 800, H - 25
    d.rounded_rectangle([60, cy0, W - 60, cy1], 24, fill=(28, 96, 52))
    d.rounded_rectangle([60, cy0, W - 60, cy1], 24, outline=(200, 230, 200), width=3)
    d.line([(W / 2, cy0), (W / 2, cy1)], fill=(200, 230, 200), width=3)
    d.ellipse([W / 2 - 110, (cy0 + cy1) / 2 - 110, W / 2 + 110, (cy0 + cy1) / 2 + 110], outline=(200, 230, 200), width=3)
    for eq, lado in ((L, -1), (V, 1)):
        fx = W / 2 + lado * (W / 2 - 150)
        d.rounded_rectangle([fx - 70, cy0 + 14, fx + 70, cy0 + 56], 12, fill=TARJETA)
        d.text((fx, cy0 + 35), eq.get("formacion", ""), font=F(30), fill=BLANCO, anchor="mm")
        lineas = eq.get("once", [])
        n = len(lineas)
        for i, linea in enumerate(lineas):
            x = W / 2 + lado * ((W / 2 - 110) - (W / 2 - 220) * i / max(n - 1, 1))
            for j, jug in enumerate(linea):
                y = cy0 + (cy1 - cy0) * (j + 1) / (len(linea) + 1)
                nombre, _, sust = jug.partition("|")
                d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=ROJO if lado < 0 else (240, 240, 240), outline=BLANCO, width=3)
                d.text((x, y + 30), nombre, font=F(26), fill=BLANCO, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))
                if sust:
                    d.text((x, y + 60), "↔ " + sust, font=F(21, False), fill=(220, 230, 220), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
    im.convert("RGB").save(salida)
    return salida
