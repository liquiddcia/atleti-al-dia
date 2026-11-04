"""Plató vertical para Shorts (1080x1920): el presentador en el estudio arriba y, debajo,
un panel con las imágenes de la noticia, que van cambiando.

Uso: python3 scripts/plato/vertical.py videos/<nombre>.json salida/<nombre>-vertical.mp4
En el json, "plato": {"paneles": [{"ruta": ..., "titulo": ..., "sub": ..., "frases": N}, ...]}
reparte las frases entre los paneles por orden."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.join(AQUI, "..", "..")
sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import demo, plato_render as pr, secuencia as SQ
from estudio import extender, K, T
import video_noticia as vn

W, H, FPS = 1080, 1920, 30
ROJO, BLANCO, AMARILLO = (203, 53, 36), (255, 255, 255), (255, 214, 0)
A_ALTO = 1000                          # zona del presentador (arriba)
B = (40, 1020, 1040, 1470)             # panel de imágenes (dentro de la zona segura de los Shorts)
# Recorte del plató alrededor del presentador, en px de la imagen original (con la extensión T)
VENTANA = (450, 142, 1235, 869)    # incluye el logo y el nombre enteros

def panel(info):
    x0, y0, x1, y1 = B; w, h = x1 - x0, y1 - y0
    if info.get("completa"):  # la imagen ocupa el panel entero, con borde rojo
        foto = ImageOps.fit(Image.open(info["ruta"]).convert("RGB"), (w, h), Image.LANCZOS).convert("RGBA")
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=255)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); im.paste(foto, (0, 0), m)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], 26, outline=ROJO + (255,), width=6)
        return im
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 28, fill=(16, 20, 38, 235), outline=(203, 53, 36, 255), width=4)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([30, 40, 430, 440], fill=info.get("brillo", (203, 53, 36)) + (130,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))
    foto = Image.open(info["ruta"]).convert("RGBA")
    alto = h - 20; foto = foto.resize((round(foto.width * alto / foto.height), alto), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], 28, fill=255)
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0)); capa.alpha_composite(foto, (max(250 - foto.width // 2, 10), h - alto))
    capa.putalpha(Image.fromarray(np.minimum(np.asarray(capa.getchannel("A")), np.asarray(mask))))
    im.alpha_composite(capa)
    d = ImageDraw.Draw(im); tx = 520
    d.text((tx, 120), info["sub"], font=vn.fuente(38, negrita=False), fill=(205, 212, 225), anchor="lm")
    lineas = vn.partir(info["titulo"], vn.fuente(66), w - tx - 30, d)
    for i, l in enumerate(lineas):
        d.text((tx, 200 + 78 * i), l, font=vn.fuente(66), fill=BLANCO, anchor="lm")
    etq = info.get("etiqueta")
    if etq:
        f = vn.fuente(44); tw = d.textlength(etq, font=f)
        y = 200 + 78 * len(lineas) + 30
        d.rounded_rectangle([tx, y, tx + tw + 50, y + 74], 18, fill=info.get("color", ROJO))
        d.text((tx + 25, y + 37), etq, font=f, fill=BLANCO if info.get("color", ROJO) != AMARILLO else (30, 20, 10), anchor="lm")
    return im

def render(noticia, paneles, tramos, voz_wav, salida, audio_final):
    lienzo = extender(os.path.join(RAIZ, "videos", "plato", "fondos", "escudo_centro.png"))
    pres = pr.Presentador()
    # Fondo del vertical: el plató desenfocado y oscurecido
    fondo = lienzo.resize((W, round(lienzo.height * W / lienzo.width))).resize((W, H)).filter(ImageFilter.GaussianBlur(25))
    fondo = Image.blend(fondo, Image.new("RGB", (W, H), (6, 8, 18)), 0.55).convert("RGBA")
    imgs = [panel(p) for p in paneles]
    # rótulo del titular (bajo el presentador)
    rotulo = Image.new("RGBA", (W, 130), (0, 0, 0, 0)); dr = ImageDraw.Draw(rotulo)
    dr.rectangle([0, 0, W, 130], fill=(0, 0, 0, 170)); dr.rectangle([0, 0, 18, 130], fill=ROJO)
    tit, tam = " ".join(noticia["titular"]), 56
    while tam > 30 and dr.textlength(tit, font=vn.fuente(tam)) > W - 48 - 30: tam -= 2   # que el titular quepa entero
    dr.text((48, 65), tit, font=vn.fuente(tam), fill=BLANCO, anchor="lm")
    dur = tramos[-1][1]; n = int(round(dur * FPS))
    boca = pr.envolvente(voz_wav, n)
    rng = np.random.default_rng(7); parpados = np.zeros(n); t_sig = 2.0
    while t_sig < dur:
        f = int(t_sig * FPS)
        for k, v in enumerate((0.6, 1.0, 1.0, 0.6)):
            if f + k < n: parpados[f + k] = v
        t_sig += rng.uniform(2.8, 5.5)
    # Una sola postura todo el vídeo: sin cortes ni cambios de imagen del presentador
    pose = noticia.get("plato", {}).get("pose", "f01")
    plan = [(0.0, pose, 0)]
    proc = subprocess.Popen([pr.FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-i", audio_final, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", salida], stdin=subprocess.PIPE)
    vx0, vy0, vx1, vy1 = VENTANA
    for f in range(n):
        t = f / FPS
        k_pose, encuadre, t_pose = SQ.en_limpio(plan, t)
        # Corte de cámara en cada cambio de postura: plano medio o primer plano, con deriva lenta
        z = 1.0 + 0.04 * t / dur          # acercamiento muy lento, sin cortar el logo ni el nombre
        cx, cy = (vx0 + vx1) / 2, (vy0 + vy1) / 2 - (25 if encuadre else 0); hw, hh = (vx1 - vx0) / 2 / z, (vy1 - vy0) / 2 / z
        box = tuple(int(round(c * K)) for c in (cx - hw, cy - hh, cx + hw, cy + hh))
        base = lienzo.crop(box).convert("RGBA")
        b = int(round(boca[f] * (pr.NIVELES - 1))); p = parpados[f]
        dx = 1.5 * K * math.sin(2 * math.pi * 0.17 * t); dy = 1.5 * K * math.sin(2 * math.pi * 0.23 * t)
        corte_y = (pr.PLANOS["centro"]["apoyo"] + T) * K - box[1]
        def con_pres(k):
            esc, sx, sy = pres.colocar("centro", k); im = pres.sprite("centro", k, b, p)
            px, py = int(sx + dx - box[0]), int(sy + dy - box[1])
            capa = Image.new("RGBA", base.size, (0, 0, 0, 0))
            capa.alpha_composite(im, (max(px, 0), max(py, 0)), (max(-px, 0), max(-py, 0)))
            if corte_y < capa.height: capa.paste((0, 0, 0, 0), (0, int(max(corte_y, 0)), capa.width, capa.height))
            o = base.copy(); o.alpha_composite(capa); return o
        arriba = con_pres(k_pose)
        frame = fondo.copy()
        frame.alpha_composite(arriba.resize((W, A_ALTO), Image.BILINEAR), (0, 0))
        sombra = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        for i in range(60): ImageDraw.Draw(sombra).line([(0, i), (W, i)], fill=(0, 0, 0, int(140 * i / 60)))
        frame.alpha_composite(sombra, (0, A_ALTO - 60))
        frame.alpha_composite(rotulo, (0, A_ALTO - 190))
        # panel actual con fundido entre imágenes y ligero acercamiento
        j = max(i for i, x in enumerate(tramos) if x[0] <= t)
        ini, fin = tramos[j][0], tramos[j][1]
        def pan(i, tt):
            im = imgs[i]; zz = 1 + 0.03 * (tt - tramos[i][0]) / (tramos[i][1] - tramos[i][0])
            w2, h2 = round(im.width * zz), round(im.height * zz)
            return im.resize((w2, h2), Image.BILINEAR), (B[0] - (w2 - im.width) // 2, B[1] - (h2 - im.height) // 2)
        FUND = 0.5
        if j > 0 and t - ini < FUND:
            a_, pa = pan(j - 1, t); frame.alpha_composite(a_, pa)
            b_, pb = pan(j, t); b_ = b_.copy(); b_.putalpha(b_.getchannel("A").point(lambda v, x=(t - ini) / FUND: int(v * x)))
            frame.alpha_composite(b_, pb)
        else:
            a_, pa = pan(j, t); frame.alpha_composite(a_, pa)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close(); proc.wait()

def main(ruta_json, salida):
    from nombres import aplicar
    n = aplicar(json.load(open(ruta_json, encoding="utf-8")))
    paneles = n["plato"]["paneles"]
    global A_ALTO, B, VENTANA
    if all(p.get("completa") for p in paneles):
        A_ALTO, B, VENTANA = 800, (40, 818, 1040, 1480), (450, 215, 1235, 796)
    for p in paneles:
        if not os.path.isabs(p["ruta"]): p["ruta"] = os.path.join(RAIZ, p["ruta"])
        if "brillo" in p: p["brillo"] = tuple(p["brillo"])
        if "color" in p: p["color"] = tuple(p["color"])
    frases = [f["hablado"] if isinstance(f, dict) else f for f in n["frases"]]
    if n.get("suscribete", True):  # cierre con la portada del canal
        import suscribete
        paneles = paneles[:-1] + [dict(paneles[-1], frases=len(frases) - sum(p["frases"] for p in paneles[:-1])),
                                  {"ruta": suscribete.imagen(os.path.join(os.path.dirname(os.path.abspath(salida)), "plato_tmp"), B[2] - B[0], B[3] - B[1]),
                                   "completa": True, "frases": 1}]
        frases.append(suscribete.FRASE)
    guion, i = [], 0
    for k, p in enumerate(paneles):
        for _ in range(p["frases"] if k < len(paneles) - 1 else len(frases) - i):
            guion.append(("centro", k, frases[i])); i += 1
    demo.GUION = guion
    demo.main(salida, render=lambda tr, voz, sal, fin: render(n, paneles, tr, voz, sal, fin))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
