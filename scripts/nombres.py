"""Cómo se nombra a cada jugador en los vídeos (voz, subtítulos e imágenes).

Se aplica a todos los textos antes de generar cada vídeo, así que basta con añadir
aquí una línea para cambiar un nombre en todos los vídeos futuros."""
import re

NOMBRES = {
    "Jan Oblak": "Oblak",
}

# Cómo debe PRONUNCIAR la voz algunos nombres (solo afecta a lo que se dice, no a lo que se escribe)
PRONUNCIACION = {
    "Raphinha": "Rafiña",
    "Aston Villa": "Aston Vila",
    "Hancko": "Janco",
    "Lookman": "Lukman",
}

def pronunciar(texto):
    if not isinstance(texto, str):
        return texto
    for escrito, dicho in PRONUNCIACION.items():
        texto = re.sub(rf"\b{re.escape(escrito)}\b", dicho, texto, flags=re.IGNORECASE)
    return texto

def nombres(texto):
    if not isinstance(texto, str):
        return texto
    for largo, corto in NOMBRES.items():
        texto = re.sub(rf"\b{re.escape(largo.upper())}\b", corto.upper(), texto)
        texto = re.sub(rf"\b{re.escape(largo)}\b", corto, texto, flags=re.IGNORECASE)
    return texto

def aplicar(obj):
    """Aplica nombres() a todos los textos de un dict/lista (por ejemplo, el json de una noticia)."""
    if isinstance(obj, dict):
        return {k: (v if k in ("ruta", "tipo", "color", "brillo") else aplicar(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [aplicar(x) for x in obj]
    return nombres(obj)
