"""Piezas comunes para los paneles (1920x1272) y portadas de los vídeos del plató."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_noticia as v, estadio

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
REC = R + "videos/imagenes/recortes/"
ESC = R + "public/escudos/"
ATM = ESC + "escudoB.png"
W, H = 1920, 1272
ROJO, AMARILLO, BLANCO, GRIS, VERDE = (203, 53, 36), (255, 214, 0), (255, 255, 255), (190, 198, 214), (40, 170, 90)
CARD = (30, 34, 58)

def F(t, n=True): return v.fuente(t, negrita=n)

def base(titulo, sub):
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H): d.line([(0, y), (W, y)], fill=(int(14 + 10 * y / H), int(16 + 6 * y / H), int(34 + 14 * y / H)))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([-300, -300, 900, 800], fill=(203, 53, 36, 90))
    im = im.convert("RGBA"); im.alpha_composite(g.filter(ImageFilter.GaussianBlur(160))); d = ImageDraw.Draw(im)
    d.rectangle([80, 90, 96, 230], fill=ROJO)
    d.text((130, 140), titulo, font=F(96), fill=BLANCO, anchor="lm")
    d.text((132, 222), sub, font=F(46, False), fill=GRIS, anchor="lm")
    return im, d

def esc(im, ruta, cx, cy, alto):
    e = Image.open(ruta).convert("RGBA"); e.thumbnail((alto, alto), Image.LANCZOS)
    im.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))

def jugador(im, ruta, cx, alto, glow, base_y=H):
    j = Image.open(ruta).convert("RGBA"); j = j.resize((round(j.width * alto / j.height), alto), Image.LANCZOS)
    h = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(h).ellipse([cx - 340, base_y - alto * 0.95, cx + 340, base_y - alto * 0.1], fill=glow + (120,))
    im.alpha_composite(h.filter(ImageFilter.GaussianBlur(80)))
    im.alpha_composite(j, (int(cx - j.width / 2), base_y - alto))

def ajustar(d, t, tam, ancho, negrita=True):
    while d.textlength(t, font=F(tam, negrita)) > ancho: tam -= 2
    return F(tam, negrita)

def tarjetas(d, x, filas, ancho=1000, y0=330, alto=170, paso=205):
    for k, (n, t) in enumerate(filas):
        y = y0 + k * paso
        d.rounded_rectangle([x, y, x + ancho, y + alto], 26, fill=CARD, outline=ROJO, width=4)
        tx = x + 40
        if n:
            d.text((tx, y + alto / 2), n, font=F(76), fill=AMARILLO, anchor="lm"); tx += d.textlength(n, font=F(76)) + 30
        d.text((tx, y + alto / 2), t, font=ajustar(d, t, 50, x + ancho - 30 - tx), fill=BLANCO, anchor="lm")

def borde(d, xy, t, f, col, b=12): d.text(xy, t, font=f, fill=col, anchor="mm", stroke_width=b, stroke_fill=(0, 0, 0))

# --- portadas con fondo de estadio ---
def jugador_luz(lienzo, ruta, cx, base_y, alto):
    j = Image.open(ruta).convert("RGBA"); j = j.resize((round(j.width * alto / j.height), alto), Image.LANCZOS)
    aa = np.asarray(j.getchannel("A"), dtype=np.float32); n = int(alto * 0.22)
    aa[-n:] *= np.linspace(1, 0, n)[:, None] ** 1.2
    j.putalpha(Image.fromarray(aa.astype(np.uint8)))
    sh = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([cx - j.width * 0.45, base_y - 40, cx + j.width * 0.45, base_y + 40], fill=(0, 0, 0, 180))
    lienzo.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
    a = j.getchannel("A")
    glow = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    col = Image.new("RGBA", j.size, (255, 60, 50, 0)); col.putalpha(a.filter(ImageFilter.GaussianBlur(40)))
    glow.alpha_composite(col, (int(cx - j.width / 2), base_y - alto)); lienzo.alpha_composite(glow)
    lienzo.alpha_composite(ImageEnhance.Contrast(j).enhance(1.12), (int(cx - j.width / 2), base_y - alto))

def esc_halo(im, ruta, cx, cy, alto):
    e = Image.open(ruta).convert("RGBA"); e.thumbnail((alto, alto), Image.LANCZOS)
    h = Image.new("RGBA", im.size, (0, 0, 0, 0)); a = e.getchannel("A").filter(ImageFilter.GaussianBlur(18))
    g = Image.new("RGBA", e.size, (255, 255, 255, 0)); g.putalpha(a.point(lambda p: int(p * 0.7)))
    h.alpha_composite(g, (int(cx - e.width / 2), int(cy - e.height / 2))); im.alpha_composite(h)
    im.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))

def humo_delante(im, y0, intensidad=0.35):
    Wi, Hi = im.size
    rng = np.random.default_rng(3); r = estadio._ruido(Hi // 4, Wi // 4, 300, rng)
    r = np.asarray(Image.fromarray((r * 255).astype(np.uint8)).resize((Wi, Hi), Image.BILINEAR), np.float32) / 255
    yy = np.arange(Hi)[:, None]; m = np.clip((yy - y0) / (Hi - y0), 0, 1) * (r ** 2) * intensidad
    capa = Image.new("RGBA", (Wi, Hi), (230, 230, 240, 0)); capa.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    im.alpha_composite(capa)

def logo(im, cx, y, lado):
    d = ImageDraw.Draw(im)
    lg = Image.open(v.LOGO).convert("RGB").resize((lado, lado), Image.LANCZOS)
    ml = Image.new("L", (lado, lado), 0); ImageDraw.Draw(ml).ellipse([0, 0, lado - 1, lado - 1], fill=255)
    d.ellipse([cx - lado / 2 - 4, y - 4, cx + lado / 2 + 4, y + lado + 4], fill=ROJO); im.paste(lg, (int(cx - lado / 2), y), ml)
