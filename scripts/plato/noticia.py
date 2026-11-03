"""Vídeo de una noticia (videos/<nombre>.json) presentado en el plató, en horizontal.

La primera frase la dice el presentador en plano general; el resto, con la imagen de la
noticia en la pantalla. Uso: python3 scripts/plato/noticia.py videos/<nombre>.json salida/x.mp4"""
import json, os, sys
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.join(AQUI, "..", "..")
sys.path.insert(0, AQUI)
import demo, plato_render as pr

def main(ruta_json, salida):
    n = json.load(open(ruta_json, encoding="utf-8"))
    img = n["imagen"]["ruta"]
    img = img if os.path.isabs(img) else os.path.join(RAIZ, img)
    # La pantalla del plató es 16:9: se centra la imagen de la noticia sobre fondo oscuro
    from PIL import Image
    tmp = os.path.join(os.path.dirname(os.path.abspath(salida)), "plato_tmp"); os.makedirs(tmp, exist_ok=True)
    src = Image.open(img).convert("RGB"); lienzo = Image.new("RGB", (1920, 1080), (14, 18, 34))
    src.thumbnail((1920, 1080), Image.LANCZOS); lienzo.paste(src, ((1920 - src.width) // 2, (1080 - src.height) // 2))
    slide = os.path.join(tmp, "pantalla.png"); lienzo.save(slide)
    frases = [f["hablado"] if isinstance(f, dict) else f for f in n["frases"]]
    demo.GUION = [("centro", None, frases[0])] + [("pantalla", slide, f) for f in frases[1:]]
    # Las frases seguidas con la misma imagen forman un solo tramo de pantalla
    demo.main(salida)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
