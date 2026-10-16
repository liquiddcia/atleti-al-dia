// lib/leerarticulo.js
// Abre el enlace original de una noticia y devuelve el texto del artículo (recortado),
// para que la IA tenga los nombres y los datos que el titular de Google News no trae.
// Es solo una fuente de datos: la IA reescribe con sus palabras, nunca se copia ni se publica el texto.
// Si algo falla (enlace que no abre, medio que bloquea, página de pago...) devuelve "" y la
// noticia se escribe como hasta ahora, solo con el titular y el resumen.

const MAX_CARACTERES = 5000;
const TIEMPO_MAX_MS = 8000;
const NAVEGADOR =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

function idDeGoogle(enlace) {
  const m = /news\.google\.com\/(?:rss\/)?(?:articles|read)\/([^?/#]+)/.exec(String(enlace || ""));
  return m ? m[1] : null;
}

// Los enlaces antiguos de Google News llevan la dirección real escrita dentro del propio código
function decodificarLocal(id) {
  try {
    const b64 = id.replace(/-/g, "+").replace(/_/g, "/");
    let s = Buffer.from(b64, "base64").toString("latin1");
    if (s.startsWith("\x08\x13\x22")) s = s.slice(3);
    if (s.endsWith("\xd2\x01\x00")) s = s.slice(0, -3);
    const largo = s.charCodeAt(0);
    s = largo >= 0x80 ? s.slice(2, largo + 1) : s.slice(1, largo + 1);
    return /^https?:\/\//.test(s) ? s : null;
  } catch (e) {
    return null;
  }
}

// Los enlaces nuevos hay que preguntárselos a Google
async function decodificarRemoto(id, senal) {
  const pagina = await fetch(`https://news.google.com/rss/articles/${id}?hl=en-US&gl=US&ceid=US:en`, {
    headers: { "User-Agent": NAVEGADOR },
    signal: senal,
  });
  if (!pagina.ok) return null;
  const html = await pagina.text();
  const firma = /data-n-a-sg="([^"]+)"/.exec(html);
  const marca = /data-n-a-ts="([^"]+)"/.exec(html);
  if (!firma || !marca) return null;

  const peticion = [
    "garturlreq",
    [["X", "X", ["X", "X"], null, null, 1, 1, "US:en", null, 1, null, null, null, null, null, 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, null, 0, 0, null, 0],
    id,
    Number(marca[1]),
    firma[1],
  ];
  const cuerpo = "f.req=" + encodeURIComponent(JSON.stringify([[["Fbv4je", JSON.stringify(peticion), null, "generic"]]]));
  const r = await fetch("https://news.google.com/_/DotsSplashUi/data/batchexecute", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", "User-Agent": NAVEGADOR },
    body: cuerpo,
    signal: senal,
  });
  if (!r.ok) return null;
  const texto = await r.text();
  const trozo = texto.split("\n\n")[1];
  if (!trozo) return null;
  const url = JSON.parse(JSON.parse(trozo)[0][2])[1];
  return /^https?:\/\//.test(url) ? url : null;
}

async function direccionReal(enlace, senal) {
  const id = idDeGoogle(enlace);
  if (!id) return enlace;
  return decodificarLocal(id) || (await decodificarRemoto(id, senal));
}

function limpiarEntidades(t) {
  return t
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCharCode(parseInt(n, 16)));
}

function textoDeHtml(html) {
  let h = html
    .replace(/<(script|style|noscript|nav|header|footer|aside|form|figure|iframe|svg)[\s\S]*?<\/\1>/gi, " ")
    .replace(/<!--[\s\S]*?-->/g, " ");
  const art = /<article[\s\S]*?<\/article>/i.exec(h);
  if (art) h = art[0];

  const parrafos = [];
  const vistos = new Set();
  const re = /<p[\s>][\s\S]*?<\/p>/gi;
  let m;
  while ((m = re.exec(h))) {
    const p = limpiarEntidades(m[0].replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim();
    if (p.length < 60 || vistos.has(p)) continue;
    vistos.add(p);
    parrafos.push(p);
  }
  let texto = parrafos.join("\n");

  if (texto.length < 200) {
    const d = /<meta[^>]+(?:property|name)=["'](?:og:description|description)["'][^>]+content=["']([^"']+)["']/i.exec(html);
    if (d) texto = limpiarEntidades(d[1]).trim();
  }
  return texto.slice(0, MAX_CARACTERES);
}

async function leerArticulo(enlace) {
  const control = new AbortController();
  const reloj = setTimeout(() => control.abort(), TIEMPO_MAX_MS);
  try {
    const url = await direccionReal(enlace, control.signal);
    if (!url || /news\.google\.com|consent\.google/.test(url)) return "";
    const r = await fetch(url, {
      headers: { "User-Agent": NAVEGADOR, "Accept-Language": "es-ES,es;q=0.9", Accept: "text/html" },
      redirect: "follow",
      signal: control.signal,
    });
    if (!r.ok) return "";
    if (!String(r.headers.get("content-type") || "").includes("html")) return "";
    const html = (await r.text()).slice(0, 1500000);
    return textoDeHtml(html);
  } catch (e) {
    return "";
  } finally {
    clearTimeout(reloj);
  }
}

module.exports = { leerArticulo, textoDeHtml, decodificarLocal, idDeGoogle };
