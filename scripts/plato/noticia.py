"""Vídeo de una noticia (videos/<nombre>.json) presentado en el plató, en horizontal.

La primera frase la dice el presentador en plano general; el resto, con la imagen de la
noticia en la pantalla. Uso: python3 scripts/plato/noticia.py videos/<nombre>.json salida/x.mp4"""
import json, os, sys
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.join(AQUI, "..", "..")
sys.path.insert(0, AQUI)
import demo, plato_render as pr

def main(ruta_json, salida):
    sys.path.insert(0, os.path.join(RAIZ, "scripts")); from nombres import aplicar
    n = aplicar(json.load(open(ruta_json, encoding="utf-8")))
    img = n["imagen"]["ruta"]
    img = img if os.path.isabs(img) else os.path.join(RAIZ, img)
    # La pantalla del plató es 16:9: se centra la imagen de la noticia sobre fondo oscuro
    from PIL import Image
    tmp = os.path.join(os.path.dirname(os.path.abspath(salida)), "plato_tmp"); os.makedirs(tmp, exist_ok=True)
    src = Image.open(img).convert("RGB"); lienzo = Image.new("RGB", (1920, 1080), (14, 18, 34))
    src.thumbnail((1920, 1080), Image.LANCZOS); lienzo.paste(src, ((1920 - src.width) // 2, (1080 - src.height) // 2))
    slide = os.path.join(tmp, "pantalla.png"); lienzo.save(slide)
    frases = [f["hablado"] if isinstance(f, dict) else f for f in n["frases"]]
    paneles = n.get("plato", {}).get("paneles")
    if paneles:  # varias imágenes: cada una ocupa la pantalla durante sus frases
        de_frase = []
        for k, p in enumerate(paneles):
            de_frase += [k] * p["frases"]
        rutas = []
        for k, p in enumerate(paneles):
            r = p["ruta"] if os.path.isabs(p["ruta"]) else os.path.join(RAIZ, p["ruta"])
            src = Image.open(r).convert("RGB"); lz = Image.new("RGB", (1920, 1080), (14, 18, 34))
            src.thumbnail((1920, 1080), Image.LANCZOS); lz.paste(src, ((1920 - src.width) // 2, (1080 - src.height) // 2))
            rutas.append(os.path.join(tmp, f"pantalla{k}.png")); lz.save(rutas[-1])
        demo.GUION = [("centro", None, frases[0])] + [("pantalla", rutas[de_frase[i]], frases[i]) for i in range(1, len(frases))]
    else:
        demo.GUION = [("centro", None, frases[0])] + [("pantalla", slide, f) for f in frases[1:]]
    # Las frases seguidas con la misma imagen forman un solo tramo de pantalla
    demo.main(salida)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
