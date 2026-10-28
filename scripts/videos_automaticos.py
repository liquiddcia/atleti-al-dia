"""Vídeos automáticos de Diario Colchonero.

  python3 scripts/videos_automaticos.py diario   -> un vídeo por cada una de las noticias
                                                    más importantes de las últimas 24 h
                                                    que aún no tienen vídeo
  python3 scripts/videos_automaticos.py resumen  -> un vídeo con el resumen del día

Lee las noticias de Supabase, pide el guion a Claude (claude-haiku-4-5), genera el vídeo
con scripts/video_noticia.py y lo envía por Telegram al chat privado (nunca al canal).

Variables de entorno (secretos de GitHub): SUPABASE_URL, SUPABASE_SERVICE_KEY,
ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN y TELEGRAM_RESUMEN_CHAT_ID.
Opcionales: CANTIDAD (por defecto 3) y SIN_ENVIAR=true para generar sin enviar ni marcar.

Para no repetir vídeos, la tabla noticias necesita esta columna (una sola vez):
  alter table noticias add column if not exists video_hecho_en timestamptz;
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_noticia  # noqa: E402

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SALIDA = os.path.join(RAIZ, "salida", "auto")
SITIO = "https://diariocolchonero.com"
MADRID = ZoneInfo("Europe/Madrid")
MODELO = "claude-haiku-4-5"
SQL_COLUMNA = "alter table noticias add column if not exists video_hecho_en timestamptz;"

ETIQUETAS = {
    "liga": "LIGA", "champions": "CHAMPIONS", "previa": "PREVIA", "fichajes": "MERCADO",
    "clasificacion": "CLASIFICACIÓN", "filial": "FILIAL", "femenino": "FEMENINO",
}
IMAGEN_CATEGORIA = {
    "liga": "liga.png", "champions": "champions.png", "previa": "previa.png",
    "fichajes": "mercado.png", "clasificacion": "clasificacion.png",
    "filial": "filial.png", "femenino": "femenino.png",
}
# Orden de importancia por categoría; el resto va detrás.
PRIORIDAD = {"liga": 0, "champions": 1, "fichajes": 2}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


class ColumnaSinCrear(Exception):
    pass


# ---------------------------------------------------------------- Supabase

def supabase(metodo, ruta, parametros=None, cuerpo=None):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + ruta
    if parametros:
        url += "?" + urllib.parse.urlencode(parametros, safe="*,.():")
    clave = os.environ["SUPABASE_SERVICE_KEY"]
    cabeceras = {"apikey": clave, "Authorization": f"Bearer {clave}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"}
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            texto = r.read().decode()
    except urllib.error.HTTPError as e:
        detalle = e.read().decode()[:500]
        if "video_hecho_en" in detalle:
            raise ColumnaSinCrear(detalle) from None
        raise RuntimeError(f"Supabase {e.code}: {detalle}") from None
    return json.loads(texto) if texto else None


def noticias_sin_video():
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).isoformat()
    campos = "id,categoria,titular,resumen,cuerpo,fuentes,imagen_url,likes,publicado_en"
    base = {"select": campos, "oculta": "eq.false", "publicado_en": f"gte.{desde}",
            "order": "publicado_en.desc", "limit": "60"}
    try:
        return supabase("GET", "noticias", {**base, "video_hecho_en": "is.null"}), True
    except ColumnaSinCrear:
        print(f"::warning::Falta la columna video_hecho_en. Ejecuta en Supabase: {SQL_COLUMNA}")
        return supabase("GET", "noticias", base), False


def importancia(n):
    """Primero las que reúnen varias fuentes; luego liga, champions, fichajes y el resto."""
    varias = len([f for f in str(n.get("fuentes") or "").split(",") if f.strip()]) > 1
    return (0 if varias else 1, PRIORIDAD.get(n.get("categoria"), 3),
            -(n.get("likes") or 0), _negar_fecha(n.get("publicado_en")))


def _negar_fecha(iso):
    try:
        return -dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def marcar_hecha(noticia_id):
    supabase("PATCH", "noticias", {"id": f"eq.{int(noticia_id)}"},
             {"video_hecho_en": dt.datetime.now(dt.timezone.utc).isoformat()})


def noticias_resumen():
    """Igual que api/resumen.js: primero los resultados de partido, luego las más votadas."""
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).isoformat()
    campos = "id,categoria,titular,resumen,likes,publicado_en"
    comun = {"select": campos, "oculta": "eq.false", "publicado_en": f"gte.{desde}"}
    resultados = supabase("GET", "noticias", {**comun, "titulo_original": "like.final partido *",
                                              "order": "publicado_en.desc", "limit": "2"})
    populares = supabase("GET", "noticias", {**comun, "order": "likes.desc,publicado_en.desc",
                                             "limit": "6"})
    vistos, lista = set(), []
    for n in (resultados or []) + (populares or []):
        if n["id"] not in vistos:
            vistos.add(n["id"])
            lista.append(n)
    return lista[:6]


# ---------------------------------------------------------------- Claude

REGLAS_GUION = """Reglas del guion:
- Español de España, tono de noticiario deportivo, frases cortas y claras para leer en voz alta
  (como mucho 22 palabras cada una).
- "hablado" es lo que dice la voz: TODOS los números escritos con letras ("veinticinco",
  "dos a uno", "el minuto noventa"). Las temporadas tipo 2012-13 pueden quedarse así.
- "subtitulo" es el mismo texto, con los números en cifras ("25", "2-1", "el minuto 90").
- No inventes nada que no esté en el texto. No menciones medios ni fuentes.
- La última frase termina con "Esto es Diario Colchonero."
- "titular": el titular del vídeo en MAYÚSCULAS, partido en exactamente 2 líneas de como mucho
  20 caracteres cada una.
Devuelve SOLO un JSON, sin backticks ni texto adicional."""


def claude(prompt):
    cuerpo = json.dumps({"model": MODELO, "max_tokens": 1500,
                         "messages": [{"role": "user", "content": prompt}]}).encode()
    peticion = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=cuerpo, method="POST",
        headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    try:
        with urllib.request.urlopen(peticion, timeout=90) as r:
            datos = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Anthropic {e.code}: {e.read().decode()[:300]}") from None
    texto = "".join(b.get("text", "") for b in datos.get("content", []))
    texto = re.sub(r"```(?:json)?", "", texto).strip()
    return json.loads(texto[texto.find("{"):texto.rfind("}") + 1])


def validar_guion(g, minimo=5, maximo=6):
    titular = g.get("titular")
    if isinstance(titular, str):  # si llega en una línea, se parte por la mitad de las palabras
        palabras = titular.split()
        mitad = (len(palabras) + 1) // 2
        titular = [" ".join(palabras[:mitad]), " ".join(palabras[mitad:])]
    if not titular or not all(isinstance(l, str) and l.strip() for l in titular):
        raise ValueError("titular vacío")
    frases = [f for f in g.get("frases", []) if f.get("hablado") and f.get("subtitulo")]
    if not minimo <= len(frases) <= maximo:
        raise ValueError(f"{len(frases)} frases (se esperaban {minimo}-{maximo})")
    return [l.strip().upper() for l in titular][:3], frases


def guion_noticia(n):
    prompt = f"""Convierte esta noticia del Atlético de Madrid en el guion de un vídeo vertical de
unos 35 segundos: entre 5 y 6 frases que cuenten lo esencial de principio a fin.

{REGLAS_GUION}
Formato: {{"titular": ["LÍNEA 1", "LÍNEA 2"], "frases": [{{"hablado": "...", "subtitulo": "..."}}]}}

Titular: {n['titular']}
Resumen: {n.get('resumen') or ''}
Cuerpo:
{n.get('cuerpo') or ''}"""
    return pedir_guion(prompt)


def guion_resumen(noticias):
    lista = "\n".join(f"{i + 1}. [{n.get('categoria')}] {n['titular']}: {n.get('resumen') or ''}"
                      for i, n in enumerate(noticias))
    prompt = f"""Con estas noticias del Atlético de Madrid de hoy, escribe el guion de un vídeo vertical
de unos 40 segundos que resuma el día: 6 frases. La primera presenta el resumen del día; las
siguientes cuentan las noticias por orden de importancia (las primeras son las más importantes);
la última despide.

{REGLAS_GUION}
Además, "puntos": para cada una de las {min(len(noticias), 5)} primeras noticias, en el mismo orden,
un titular muy corto (como mucho 38 caracteres, sin punto final).
Formato: {{"titular": ["LÍNEA 1", "LÍNEA 2"], "frases": [{{"hablado": "...", "subtitulo": "..."}}],
"puntos": ["...", "..."]}}

Noticias:
{lista}"""
    return pedir_guion(prompt, minimo=5, maximo=7, puntos=True)


def pedir_guion(prompt, minimo=5, maximo=6, puntos=False):
    ultimo = None
    for intento in range(3):
        try:
            g = claude(prompt)
            titular, frases = validar_guion(g, minimo, maximo)
            if puntos and not g.get("puntos"):
                raise ValueError("faltan los puntos")
            return titular, frases, g.get("puntos") or []
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            ultimo = e
            print(f"  Guion no válido (intento {intento + 1}): {e}", flush=True)
    raise RuntimeError(f"Claude no devolvió un guion válido: {ultimo}")


# ---------------------------------------------------------------- imagen

def imagen_para(n, carpeta):
    """La imagen_url de la noticia si se puede descargar; si no, la de su categoría."""
    url = (n.get("imagen_url") or "").strip()
    if url:
        if url.startswith("/"):
            local = os.path.join(RAIZ, "public", url.lstrip("/"))
            if os.path.isfile(local):
                return local
            url = SITIO + url
        try:
            destino = os.path.join(carpeta, f"foto-{n['id']}")
            peticion = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(peticion, timeout=20) as r, open(destino, "wb") as f:
                f.write(r.read(15 * 1024 * 1024))
            from PIL import Image
            with Image.open(destino) as im:
                im.verify()
            return destino
        except Exception as e:  # cualquier fallo: se usa la imagen de la categoría
            print(f"  No se pudo usar imagen_url ({e}); uso la de la categoría", flush=True)
    nombre = IMAGEN_CATEGORIA.get(n.get("categoria"))
    ruta = os.path.join(RAIZ, "public", "imagenes", nombre) if nombre else ""
    return ruta if os.path.isfile(ruta) else os.path.join(RAIZ, "public", "og-image.jpg")


def fecha_larga(iso=None):
    d = (dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")) if iso
         else dt.datetime.now(dt.timezone.utc)).astimezone(MADRID)
    return f"{d.day} DE {MESES[d.month - 1].upper()}"


# ---------------------------------------------------------------- Telegram

def enviar_telegram(video, pie):
    if os.environ.get("SIN_ENVIAR", "").lower() == "true":
        print("  SIN_ENVIAR=true: no se envía a Telegram", flush=True)
        return False
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_RESUMEN_CHAT_ID"]  # chat privado, nunca el canal público
    # El token va en un archivo de configuración de curl para que no salga en la línea de órdenes.
    config = os.path.join(SALIDA, ".curl-telegram")
    with open(config, "w") as f:
        f.write(f'url = "https://api.telegram.org/bot{token}/sendVideo"\n')
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", "300", "-K", config,
             "-F", f"chat_id={chat}", "-F", f"caption={pie[:1000]}",
             "-F", "supports_streaming=true", "-F", "width=1080", "-F", "height=1920",
             "-F", f"video=@{video};type=video/mp4"],
            capture_output=True, text=True)
    finally:
        os.remove(config)
    try:
        respuesta = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        respuesta = {}
    if r.returncode != 0 or not respuesta.get("ok"):
        detalle = respuesta.get("description") or r.stderr.strip() or "respuesta vacía"
        raise RuntimeError(f"Telegram no aceptó el vídeo: {detalle.replace(token, '***')}")
    return True


# ---------------------------------------------------------------- vídeos

def renderizar(nombre, titular, frases, imagen):
    ruta_json = os.path.join(SALIDA, f"{nombre}.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump({"titular": titular, "frases": frases, "imagen": imagen}, f,
                  ensure_ascii=False, indent=2)
    video = os.path.join(SALIDA, f"{nombre}.mp4")
    video_noticia.main(ruta_json, video)
    return video


def diario():
    cantidad = int(os.environ.get("CANTIDAD") or 3)
    noticias, hay_columna = noticias_sin_video()
    print(f"Noticias de las últimas 24 h sin vídeo: {len(noticias)}", flush=True)
    elegidas = sorted(noticias, key=importancia)[:cantidad]
    fallos = 0
    for n in elegidas:
        print(f"\n▶ [{n['id']}] ({n.get('categoria')}, fuentes: {n.get('fuentes')}) {n['titular']}",
              flush=True)
        try:
            titular, frases, _ = guion_noticia(n)
            for f in frases:
                print(f"  · {f['subtitulo']}", flush=True)
            imagen = {"tipo": "foto", "ruta": imagen_para(n, SALIDA), "texto": n.get("resumen"),
                      "titulo": f"{ETIQUETAS.get(n.get('categoria'), 'ATLÉTICO')} · "
                                f"{fecha_larga(n.get('publicado_en'))}"}
            video = renderizar(f"noticia-{n['id']}", titular, frases, imagen)
            if enviar_telegram(video, n["titular"]) and hay_columna:
                marcar_hecha(n["id"])
                print("  Enviado y marcado como hecho", flush=True)
        except Exception as e:
            fallos += 1
            print(f"::error::Noticia {n['id']}: {e}", flush=True)
    if not hay_columna:
        print(f"::error::No se ha marcado ninguna noticia. Crea la columna en Supabase: {SQL_COLUMNA}")
        return 1
    return 1 if fallos else 0


def resumen():
    noticias = noticias_resumen()
    print(f"Noticias para el resumen: {len(noticias)}", flush=True)
    if not noticias:
        print("Sin noticias en las últimas 24 horas: no hay vídeo de resumen")
        return 0
    titular, frases, puntos = guion_resumen(noticias)
    for f in frases:
        print(f"  · {f['subtitulo']}", flush=True)
    filas = [{"nombre": p, "estado": ETIQUETAS.get(n.get("categoria"), "").capitalize(),
              "color": "rojo"} for p, n in zip(puntos, noticias[:5])]
    imagen = {"tipo": "lista", "titulo": f"RESUMEN · {fecha_larga()}", "filas": filas}
    hoy = dt.datetime.now(MADRID).strftime("%Y-%m-%d")
    video = renderizar(f"resumen-{hoy}", titular, frases, imagen)
    enviar_telegram(video, f"Resumen del día · {fecha_larga().capitalize()}\n"
                           f"{' '.join(titular).capitalize()}")
    return 0


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo not in ("diario", "resumen"):
        sys.exit("Uso: python3 scripts/videos_automaticos.py diario|resumen")
    os.makedirs(SALIDA, exist_ok=True)
    sys.exit(diario() if modo == "diario" else resumen())
