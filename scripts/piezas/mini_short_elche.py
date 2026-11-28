"""Miniatura vertical viral del Short de la previa Elche - Atlético."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from paneles import *
ELC = ESC + "elche.png"
PW, PH = 1080, 1920
p = estadio.fondo(PW, PH, semilla=9, horizonte=0.45).convert("RGBA")
# mitad verde (Elche) / mitad roja (Atleti) con corte en diagonal
yy, xx = np.mgrid[0:PH, 0:PW]
lado = (xx - PW / 2) - (yy - PH / 2) * 0.18
for col, m in (((20, 150, 70), lado < 0), ((210, 25, 30), lado >= 0)):
    a = np.clip(np.where(m, 1, 0) * (0.5 - 0.25 * yy / PH), 0, 1)
    capa = Image.new("RGBA", (PW, PH), col + (0,)); capa.putalpha(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30)))
    p.alpha_composite(capa)
# rayo blanco en la diagonal
rayo = Image.new("RGBA", (PW, PH), (0, 0, 0, 0)); dr = ImageDraw.Draw(rayo)
x0, x1 = PW / 2 - PH / 2 * 0.18, PW / 2 + PH / 2 * 0.18
dr.line([(x0, 0), (x1, PH)], fill=(255, 255, 255, 200), width=10)
p.alpha_composite(rayo.filter(ImageFilter.GaussianBlur(6))); p.alpha_composite(rayo.filter(ImageFilter.GaussianBlur(1)))
# jugadores
jugador_luz(p, REC + "fer-nino.png", 280, 1260, 720, (60, 220, 110))
jugador_luz(p, REC + "julian.png", 810, 1260, 760)
humo_delante(p, 800, 0.5)
g = Image.new("RGBA", (PW, 760), (0, 0, 0, 0))
for i in range(760): ImageDraw.Draw(g).line([(0, i), (PW, i)], fill=(0, 0, 0, int(190 * min(1, i / 320))))
p.alpha_composite(g, (0, 1160))
# escudos y VS arriba
esc_halo(p, ELC, 230, 330, 300); esc_halo(p, ATM, 850, 330, 320)
d = ImageDraw.Draw(p)
borde(d, (PW / 2, 330), "VS", F(170), BLANCO, 14)
t = "PREVIA · SÁBADO 18:30"; an = d.textlength(t, font=F(44))
d.rounded_rectangle([(PW - an) / 2 - 30, 70, (PW + an) / 2 + 30, 145], 18, fill=(0, 0, 0, 200)); d.text((PW / 2, 108), t, font=F(44), fill=BLANCO, anchor="mm")
# ¡PROHIBIDO FALLAR! rojo con borde blanco y perfil negro
def gordo(xy, txt, tam):
    f = F(tam)
    d.text(xy, txt, font=f, fill=(0, 0, 0), anchor="mm", stroke_width=26, stroke_fill=(0, 0, 0))
    d.text(xy, txt, font=f, fill=BLANCO, anchor="mm", stroke_width=15, stroke_fill=BLANCO)
    d.text(xy, txt, font=f, fill=(225, 20, 25), anchor="mm")
tam = 190
while d.textlength("¡PROHIBIDO", font=F(tam)) > PW - 90: tam -= 4
gordo((PW / 2, 1370), "¡PROHIBIDO", tam)
gordo((PW / 2, 1560), "FALLAR!", tam + 20)
t = "SIN SØRLOTH EN ELCHE"; w = d.textlength(t, font=F(56))
d.rounded_rectangle([PW / 2 - w / 2 - 40, 1690, PW / 2 + w / 2 + 40, 1790], 26, fill=AMARILLO, outline=(0, 0, 0), width=5)
d.text((PW / 2, 1740), t, font=F(56), fill=(0, 0, 0), anchor="mm")
logo(p, PW / 2, 1815, 80)
p.convert("RGB").save(R + "entregas/miniatura-short-elche-prohibido-fallar.jpg", quality=93)
p.convert("RGB").save(R + "videos/imagenes/previa-elche/00_portada.jpg", quality=93)
