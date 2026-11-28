"""Paneles y portadas de la previa Elche - Atlético (LaLiga, jornada 14)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from paneles import *
OUT = R + "videos/imagenes/previa-elche/"; os.makedirs(OUT, exist_ok=True)
ELC = ESC + "elche.png"; VERDE_E = (30, 140, 70)

# 01 partido
im, d = base("ELCHE - ATLÉTICO", "LaLiga · Jornada 14")
esc(im, ELC, 480, 640, 420); esc(im, ATM, 1440, 640, 440); d = ImageDraw.Draw(im)
d.text((960, 640), "VS", font=F(170), fill=BLANCO, anchor="mm")
for k, t in enumerate(("Sábado 28 · 18:30", "Estadio Martínez Valero")):
    w = d.textlength(t, font=F(56)); y = 960 + k * 120
    d.rounded_rectangle([960 - w / 2 - 40, y - 50, 960 + w / 2 + 40, y + 50], 24, fill=ROJO if k == 0 else CARD)
    d.text((960, y), t, font=F(56), fill=BLANCO, anchor="mm")
im.convert("RGB").save(OUT + "01_partido.png")

# 02 cómo llega el Atleti
im, d = base("ASÍ LLEGA EL ATLETI", "LaLiga · tras 13 jornadas")
d.text((1640, 320), "PTS", font=F(44), fill=GRIS, anchor="mm")
filas = (("1", "Barcelona", "36", ESC + "barcelona.png"), ("2", "Real Madrid", "33", ESC + "real-madrid.png"), ("3", "Atlético", "31", ATM))
for k, (pos, nom, pts, e_) in enumerate(filas):
    y = 360 + k * 175
    d.rounded_rectangle([130, y, 1790, y + 150], 24, fill=CARD, outline=ROJO if e_ == ATM else (120, 128, 150), width=5 if e_ == ATM else 2)
    d.text((220, y + 75), pos, font=F(70), fill=AMARILLO, anchor="mm")
    esc(im, e_, 370, y + 75, 110); d = ImageDraw.Draw(im)
    d.text((470, y + 75), nom, font=F(62), fill=BLANCO, anchor="lm")
    d.text((1640, y + 75), pts, font=F(80), fill=AMARILLO if e_ == ATM else BLANCO, anchor="mm")
t = "Y viene de ganar 2-0 al Viking en Champions"; w = d.textlength(t, font=F(52))
d.rounded_rectangle([960 - w / 2 - 40, 1000, 960 + w / 2 + 40, 1120], 26, fill=ROJO); d.text((960, 1060), t, font=F(52), fill=BLANCO, anchor="mm")
im.convert("RGB").save(OUT + "02_llega.png")

# 03 cara a cara
im, d = base("CARA A CARA", "Últimos enfrentamientos")
for k, (l, r, a, b) in enumerate(((ELC, ATM, 3, 2), (ATM, ELC, 1, 1), (ELC, ATM, 0, 4), (ELC, ATM, 1, 0))):
    x = 160 + k * 410; y = 330
    d.rounded_rectangle([x, y, x + 370, y + 360], 30, fill=CARD, outline=(120, 128, 150), width=2)
    esc(im, l, x + 105, y + 110, 120); esc(im, r, x + 265, y + 110, 120); d = ImageDraw.Draw(im)
    d.text((x + 185, y + 270), f"{a}-{b}", font=F(96), fill=BLANCO, anchor="mm")
for k, (n, t, e_) in enumerate((("2", "victorias Elche", ELC), ("1", "empate", None), ("2", "victorias Atleti", ATM))):
    x = 160 + k * 547
    d.rounded_rectangle([x, 820, x + 500, 1060], 30, fill=CARD, outline=ROJO if e_ == ATM else (120, 128, 150), width=4)
    d.text((x + 250, 900), n, font=F(110), fill=AMARILLO, anchor="mm")
    d.text((x + 250, 1005), t, font=F(48), fill=BLANCO, anchor="mm")
im.convert("RGB").save(OUT + "03_cara.png")

# 04 bajas
im, d = base("LAS BAJAS", "Enfermería de los dos equipos")
for col, (e_, nombre, bajas) in enumerate(((ATM, "ATLÉTICO", [("Sørloth", "pantorrilla"), ("Cuti Romero", "muscular"), ("Lookman", "rodilla")]),
                                          (ELC, "ELCHE", [("Lemar", "isquiotibiales"), ("R. Sánchez", "ingle"), ("Boayar", "lesión"), ("Y. Santiago", "lesión"), ("Aguado", "duda · tobillo")]))):
    x = 110 + col * 870
    esc(im, e_, x + 70, 345, 100); d = ImageDraw.Draw(im)
    d.text((x + 150, 345), nombre, font=F(60), fill=BLANCO, anchor="lm")
    for k, (n, t) in enumerate(bajas):
        y = 430 + k * 155
        duda = t.startswith("duda")
        d.rounded_rectangle([x, y, x + 830, y + 135], 24, fill=CARD, outline=(230, 160, 30) if duda else ROJO, width=4)
        d.text((x + 40, y + 67), n, font=F(58), fill=BLANCO, anchor="lm")
        d.text((x + 800, y + 67), t, font=F(40, False), fill=(255, 200, 90) if duda else GRIS, anchor="rm")
im.convert("RGB").save(OUT + "04_bajas.png")

# 05 posible once
im, d = base("EL POSIBLE ONCE", "Sin Sørloth: ¿quién acompaña a Julián?")
lineas = [["Julián", "¿Giuliano o J. David?"], ["Kang-In Lee", "Koke", "Cardoso", "Baena"], ["Llorente", "Le Normand", "Hancko", "Grimaldo"], ["Oblak"]]
d.rounded_rectangle([110, 300, 1810, 1220], 30, fill=(28, 90, 50))
d.line([(110, 760), (1810, 760)], fill=(90, 160, 110), width=4); d.ellipse([860, 660, 1060, 860], outline=(90, 160, 110), width=4)
for k, fila in enumerate(lineas):
    y = 380 + k * 245
    for i, n in enumerate(fila):
        x = 110 + 1700 * (i + 1) / (len(fila) + 1)
        duda = n.startswith("¿")
        d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(230, 160, 30) if duda else ROJO, outline=BLANCO, width=4)
        d.text((x, y + 70), n, font=F(48 if not duda else 44), fill=AMARILLO if duda else BLANCO, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
im.convert("RGB").save(OUT + "05_once.png")

# 06 duelo
im, d = base("EL DUELO", "Fer Niño vs Julián · LaLiga esta temporada")
jugador(im, REC + "fer-nino.png", 420, 900, VERDE_E); jugador(im, REC + "julian.png", 1500, 900, ROJO); d = ImageDraw.Draw(im)
for k, (a, t, b) in enumerate((("6", "Goles", "1"), ("0", "Asistencias", "4"), ("13", "Partidos", "9"))):
    y = 430 + k * 220
    d.rounded_rectangle([700, y, 1220, y + 180], 26, fill=CARD, outline=ROJO, width=4)
    d.text((780, y + 90), a, font=F(90), fill=AMARILLO if int(a) > int(b) else BLANCO, anchor="mm")
    d.text((1140, y + 90), b, font=F(90), fill=AMARILLO if int(b) > int(a) else BLANCO, anchor="mm")
    d.text((960, y + 90), t, font=F(40, False), fill=GRIS, anchor="mm")
im.convert("RGB").save(OUT + "06_duelo.png")

# 07 árbitro
im, d = base("EL ÁRBITRO: QUINTERO", "Alejandro Quintero · 33 años")
for k, (n, t) in enumerate((("5,5", "tarjetas por partido"), ("28", "amarillas en 6 partidos"), ("5", "rojas esta temporada"), ("4", "penaltis pitados"))):
    x = 130 + (k % 2) * 850; y = 340 + (k // 2) * 300
    d.rounded_rectangle([x, y, x + 810, y + 260], 30, fill=CARD, outline=ROJO, width=4)
    d.text((x + 170, y + 130), n, font=F(120), fill=AMARILLO, anchor="mm")
    d.text((x + 330, y + 130), t, font=ajustar(d, t, 50, 450), fill=BLANCO, anchor="lm")
t = "Con el Atleti: 1 partido, victoria y 1 penalti en contra"; w = d.textlength(t, font=F(50))
d.rounded_rectangle([960 - w / 2 - 40, 1000, 960 + w / 2 + 40, 1120], 26, fill=ROJO); d.text((960, 1060), t, font=F(50), fill=BLANCO, anchor="mm")
im.convert("RGB").save(OUT + "07_arbitro.png")

# 08 el Elche
im, d = base("OJO AL ELCHE", "El equipo de Anselmi")
jugador(im, REC + "fer-nino.png", 1460, 960, VERDE_E); d = ImageDraw.Draw(im)
tarjetas(d, 110, [("4-4-2", "el sistema de Anselmi"), ("1-1", "último partido, ante el Levante"), ("6", "goles de Fer Niño, su killer"), ("4", "bajas y la duda de Aguado")], ancho=1000, y0=320, alto=190, paso=225)
im.convert("RGB").save(OUT + "08_elche.png")

# 09 pregunta
im, d = base("¿Y TÚ QUÉ DICES?", "Tu pronóstico")
esc(im, ELC, 520, 640, 380); esc(im, ATM, 1400, 640, 400); d = ImageDraw.Draw(im)
d.text((960, 640), "?-?", font=F(200), fill=BLANCO, anchor="mm")
d.rounded_rectangle([510, 1000, 1410, 1130], 26, fill=ROJO); d.text((960, 1065), "Os leo en comentarios", font=F(62), fill=BLANCO, anchor="mm")
im.convert("RGB").save(OUT + "09_pronostico.png")

# PORTADA vertical
PW, PH = 1080, 1920
p = estadio.fondo(PW, PH, semilla=5, horizonte=0.47).convert("RGBA")
jugador_luz(p, REC + "julian.png", 300, 1250, 760)
jugador_luz(p, REC + "fer-nino.png", 790, 1250, 740)
humo_delante(p, 700, 0.55)
g = Image.new("RGBA", (PW, 700), (0, 0, 0, 0))
for i in range(700): ImageDraw.Draw(g).line([(0, i), (PW, i)], fill=(0, 0, 0, int(175 * min(1, i / 300))))
p.alpha_composite(g, (0, 1220)); d = ImageDraw.Draw(p)
t = "PREVIA · LALIGA"; an = d.textlength(t, font=F(48))
d.rounded_rectangle([(PW - an) / 2 - 30, 120, (PW + an) / 2 + 30, 200], 18, fill=ROJO); d.text((PW / 2, 160), t, font=F(48), fill=BLANCO, anchor="mm")
esc_halo(p, ATM, 170, 1150, 170); esc_halo(p, ELC, 910, 1150, 170); d = ImageDraw.Draw(p)
borde(d, (PW / 2, 1330), "SIN SØRLOTH", F(118), BLANCO, 11)
borde(d, (PW / 2, 1480), "A ELCHE", F(150), AMARILLO, 12)
t = "Elche - Atlético · Sábado 18:30"; w = d.textlength(t, font=F(44))
d.rounded_rectangle([PW / 2 - w / 2 - 40, 1600, PW / 2 + w / 2 + 40, 1690], 24, fill=(0, 0, 0, 210)); d.text((PW / 2, 1645), t, font=F(44), fill=BLANCO, anchor="mm")
logo(p, PW / 2, 1760, 84)
p.convert("RGB").save(OUT + "00_portada.jpg", quality=92); p.convert("RGB").save(R + "entregas/miniatura-previa-elche.jpg", quality=92)

# PORTADA horizontal
W2, H2 = 1920, 1080
q = estadio.fondo(W2, H2, semilla=5, horizonte=0.56).convert("RGBA")
jugador_luz(q, REC + "julian.png", 330, 1080, 860)
jugador_luz(q, REC + "fer-nino.png", 780, 1080, 820)
humo_delante(q, 450, 0.5)
sh = Image.new("RGBA", (W2, H2), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
for i in range(900): ds.line([(1020 + i, 0), (1020 + i, H2)], fill=(0, 0, 0, int(130 * min(1, i / 260))))
q.alpha_composite(sh); d = ImageDraw.Draw(q)
d.rounded_rectangle([1110, 70, 1770, 160], 22, fill=ROJO); d.text((1440, 115), "PREVIA · LALIGA", font=F(56), fill=BLANCO, anchor="mm")
esc_halo(q, ELC, 1240, 320, 200); esc_halo(q, ATM, 1640, 320, 200); d = ImageDraw.Draw(q)
borde(d, (1440, 320), "VS", F(90), BLANCO, 7)
borde(d, (1440, 580), "SIN SØRLOTH", F(118), BLANCO)
borde(d, (1440, 740), "A ELCHE", F(160), AMARILLO)
d.rounded_rectangle([1070, 900, 1810, 1000], 22, fill=(0, 0, 0, 220)); d.text((1440, 950), "Bajas, once, duelo y árbitro", font=F(48), fill=BLANCO, anchor="mm")
q.convert("RGB").save(OUT + "00_portada_horizontal.jpg", quality=92); q.convert("RGB").save(R + "entregas/miniatura-previa-elche-larga.jpg", quality=92)
