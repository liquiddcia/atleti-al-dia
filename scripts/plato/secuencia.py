"""Presentador animado con fotogramas consecutivos (videos/plato/secuencia).

Los fotogramas se alinean por los ojos para que no den saltos, y cada gesto recorre
su lista de fotogramas fundiendo uno con el siguiente."""
import json, os, random
from PIL import Image

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DIR = os.path.join(RAIZ, "videos", "plato", "secuencia")
PASO = 0.2  # segundos por fotograma dentro de un gesto

# Gestos: lista de (fotograma, segundos que se mantiene; 0 = solo de paso)
GESTOS = {
    "reposo":  [("f01", 0)],
    "explica": [("f01", 0), ("f02", 0), ("f03", 0), ("f04", 0.5), ("f03", 0), ("f04", 0.6),
                ("f08", 0), ("f10", 0), ("f11", 0), ("f12", 0)],
    "senala":  [("f01", 0), ("f02", 0), ("f05", 0), ("f06", 1.2), ("f07", 0), ("f08", 0),
                ("f10", 0), ("f11", 0), ("f12", 0)],
    "manos":   [("f12", 0), ("f11", 0), ("f10", 0.4), ("f11", 0), ("f12", 0), ("f01", 0)],
}

def cargar():
    marcas = json.load(open(os.path.join(DIR, "marcas.json")))
    imgs = {k: Image.open(os.path.join(DIR, k + ".png")).convert("RGBA") for k in marcas}
    return imgs, marcas

def duracion(gesto):
    return sum(PASO + h for _, h in GESTOS[gesto])

def plan(tramos, semilla=3):
    """Lista de claves (t, fotograma) para todo el vídeo."""
    rnd = random.Random(semilla); claves = []
    for i, (ini, fin, plano, slide) in enumerate(tramos):
        t = ini
        cola = ["senala"] if plano == "pantalla" else (["reposo"] if i == 0 else [])
        while t < fin - 0.3:
            g = cola.pop(0) if cola else rnd.choice(["explica", "explica", "manos", "reposo"])
            if g == "reposo":
                d = min(rnd.uniform(1.2, 2.5), fin - t)
                claves += [(t, "f01"), (t + d - 0.01, "f01")]; t += d; continue
            if t + duracion(g) > fin:
                claves += [(t, "f01"), (fin - 0.01, "f01")]; break
            for k, hold in GESTOS[g]:
                claves.append((t, k)); t += PASO
                if hold: claves.append((t + hold - PASO, k)); t += hold
            # pausa entre gestos
            d = min(rnd.uniform(0.6, 1.6), max(fin - t, 0))
            if d > 0: claves += [(t, "f01"), (t + d - 0.01, "f01")]; t += d
    claves.sort(key=lambda c: c[0])
    return claves

def en(claves, t):
    """(fotograma A, fotograma B, mezcla 0..1) en el instante t."""
    if t <= claves[0][0]: return claves[0][1], claves[0][1], 0.0
    for (t0, a), (t1, b) in zip(claves, claves[1:]):
        if t0 <= t < t1:
            u = (t - t0) / max(t1 - t0, 1e-6)
            return a, b, u * u * (3 - 2 * u)
    return claves[-1][1], claves[-1][1], 0.0

# --- Modo limpio: posturas quietas que cambian con un corte de cámara (sin fundidos de manos) ---
POSTURAS_LIMPIAS = ["f01", "f04", "f12", "f08", "f01", "f03", "f12"]

def plan_limpio(tramos, semilla=5):
    """Lista de (inicio, fotograma, encuadre); el encuadre alterna plano medio y primer plano."""
    rnd = random.Random(semilla); out = []; i = 0; encuadre = 0
    dur = tramos[-1][1]; t = 0.0
    while t < dur:
        d = rnd.uniform(2.6, 4.2)
        out.append((t, POSTURAS_LIMPIAS[i % len(POSTURAS_LIMPIAS)], encuadre))
        i += 1; encuadre = 1 - encuadre; t += d
    return out

def en_limpio(plan, t):
    j = max(k for k, x in enumerate(plan) if x[0] <= t)
    return plan[j][1], plan[j][2], t - plan[j][0]
