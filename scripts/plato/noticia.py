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
    slide = img
    frases = [f["hablado"] if isinstance(f, dict) else f for f in n["frases"]]
    # Frases grabadas por el autor: {"audio": "videos/voz/xxx.m4a", "subtitulo": "..."} en lugar de "hablado"
    frases = [demo.AUDIO + (f["audio"] if os.path.isabs(f["audio"]) else os.path.join(RAIZ, f["audio"]))
              if isinstance(f, dict) and f.get("audio") else x for f, x in zip(n["frases"], frases)]
    paneles = n.get("plato", {}).get("paneles")
    if paneles:  # varias imágenes: cada una ocupa la pantalla durante sus frases
        de_frase = []
        for k, p in enumerate(paneles):
            de_frase += [k] * p["frases"]
        rutas = []
        for k, p in enumerate(paneles):
            r = p["ruta"] if os.path.isabs(p["ruta"]) else os.path.join(RAIZ, p["ruta"])
            rutas.append(r)
        demo.GUION = [("centro", None, frases[0])] + [("pantalla", rutas[de_frase[i]], frases[i]) for i in range(1, len(frases))]
    else:
        demo.GUION = [("centro", None, frases[0])] + [("pantalla", slide, f) for f in frases[1:]]
    modo = n.get("suscribete", True)
    if modo:  # portada del canal con «Suscríbete…»: al final o, con "suscribete": "medio", también a mitad
        import suscribete
        sus = suscribete.imagen(tmp)
        if modo == "medio":
            k = len(demo.GUION) // 2   # se pone en el primer cambio de imagen a partir de la mitad
            while k < len(demo.GUION) - 1 and demo.GUION[k][1] == demo.GUION[k - 1][1]: k += 1
            demo.GUION.insert(k, ("pantalla", sus, suscribete.FRASE_MEDIO))
            demo.GUION.append(("pantalla", sus, demo.PAUSA))
        else:
            demo.GUION.append(("pantalla", sus, suscribete.FRASE))
    demo.HUECO = float(n.get("hueco", demo.HUECO)); demo.VELOCIDAD = n.get("velocidad", demo.VELOCIDAD)
    portada = n.get("portada_horizontal")
    destino = salida
    if portada: salida = salida.replace(".mp4", "_sin_portada.mp4")
    # Las frases seguidas con la misma imagen forman un solo tramo de pantalla
    demo.main(salida)
    if portada:
        import portada as port
        port.poner(portada if os.path.isabs(portada) else os.path.join(RAIZ, portada), salida, destino, pr.W, pr.H,
                   float(n.get("portada_segundos", 1.0)), pr.FPS)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
