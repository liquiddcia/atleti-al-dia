"""Cierre de los vídeos del plató: la portada del canal y «Suscríbete a nuestro canal de YouTube»."""
import os
from PIL import Image, ImageEnhance, ImageFilter
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
FRASE = "Si eres del Atleti, suscríbete: cada día te contamos lo último del equipo."
FRASE_MEDIO = "Y si eres del Atleti, suscríbete: cada día te contamos lo último del equipo."
CANAL = os.path.join(RAIZ, "videos", "imagenes", "canal-diario-colchonero.jpg")

def imagen(carpeta, w=1920, h=1272):
    """La portada entera sobre un fondo hecho con ella misma, ampliada y desenfocada.
    Tiene la proporción de la pantalla del plató, así ocupa toda la pantalla sin recortar el texto."""
    canal = Image.open(CANAL).convert("RGB")
    fondo = canal.resize((round(canal.width * h / canal.height), h)).crop((0, 0, w, h)).filter(ImageFilter.GaussianBlur(30))
    fondo = ImageEnhance.Brightness(fondo).enhance(0.5)
    c2 = canal.copy(); c2.thumbnail((w, h), Image.LANCZOS)
    fondo.paste(c2, ((w - c2.width) // 2, (h - c2.height) // 2))
    os.makedirs(carpeta, exist_ok=True); ruta = os.path.join(carpeta, "suscribete.png"); fondo.save(ruta)
    return ruta
