// api/noticia.js
// Página propia de cada noticia (con título, descripción e imagen propios para
// Google y para las vistas previas de WhatsApp/Telegram).
// Se usa así: https://diariocolchonero.com/api/noticia?id=339
const supabase = require("../lib/supabase");

const SITIO = "https://diariocolchonero.com";
const ETIQUETAS = {
  liga: "Liga", champions: "Champions", previa: "Previa", fichajes: "Mercado",
  clasificacion: "Clasificación", filial: "Filial", femenino: "Femenino",
};

function esc(t) {
  return String(t == null ? "" : t)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Texto escapado, pero deja pasar solo negrita y salto de línea
function escConFormato(t) {
  return esc(t).replace(/&lt;(\/?)b&gt;/g, "<$1b>").replace(/&lt;br&gt;/g, "<br>");
}

const MARCAS = new RegExp("[" + String.fromCharCode(768) + "-" + String.fromCharCode(879) + "]", "g");

function quitarTildes(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(MARCAS, "");
}

function htmlTabla(tabla, claves) {
  const ks = String(claves).split(",").map((c) => quitarTildes(c).trim()).filter(Boolean);
  const filas = (tabla || [])
    .filter((f) => ks.some((k) => quitarTildes(f.equipo).includes(k)))
    .sort((a, b) => a.posicion - b.posicion);
  if (!filas.length) return `<p>Clasificación no disponible todavía.</p>`;
  const cuerpo = filas
    .map((f) => {
      const atleti = quitarTildes(f.equipo).includes("atletico");
      const img = f.escudo ? `<img src="${esc(f.escudo)}" alt="">` : "";
      return `<tr${atleti ? ' class="dest"' : ""}><td>${esc(f.posicion)}.º</td><td><span class="e">${img}${esc(atleti ? "Atlético de Madrid" : f.equipo)}</span></td><td>${esc(f.pj)}</td><td>${esc(f.pg)}</td><td>${esc(f.pe)}</td><td>${esc(f.pp)}</td><td>${esc(f.gf)}</td><td>${esc(f.gc)}</td><td class="pts">${esc(f.pts)}</td></tr>`;
    })
    .join("");
  return `<div class="wn-tabla"><table><thead><tr><th>Pos.</th><th>Equipo</th><th>PJ</th><th>PG</th><th>PE</th><th>PP</th><th>GF</th><th>GC</th><th>Pts</th></tr></thead><tbody>${cuerpo}</tbody></table></div><div class="wn-nota">Clasificación de la fase de liga de la Champions League.</div>`;
}

function idYoutube(url) {
  const m = String(url || "").match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/))([A-Za-z0-9_-]{11})/
  );
  return m ? m[1] : null;
}

function paginaError(res, codigo, mensaje) {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  return res.status(codigo).send(
    `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(mensaje)} | Diario Colchonero</title><meta name="robots" content="noindex"></head><body style="font-family:Arial,sans-serif;text-align:center;padding:60px 20px"><h1>${esc(mensaje)}</h1><p><a href="${SITIO}">Volver a Diario Colchonero</a></p></body></html>`
  );
}

module.exports = async function handler(req, res) {
  const id = parseInt(req.query && req.query.id, 10);
  if (!id) return paginaError(res, 404, "Noticia no encontrada");

  const { data, error } = await supabase
    .from("noticias")
    .select("id, categoria, titular, resumen, cuerpo, publicado_en, imagen_url, video_url, vistas")
    .eq("id", id)
    .eq("oculta", false)
    .maybeSingle();

  if (error) return paginaError(res, 500, "No se pudo cargar la noticia");
  if (!data) return paginaError(res, 404, "Noticia no encontrada");


  const url = `${SITIO}/api/noticia?id=${data.id}`;
  const etiqueta = ETIQUETAS[data.categoria] || data.categoria;
  const imagen = `${SITIO}/og-image.jpg`;
  const descripcion = String(data.resumen || "").slice(0, 200);
  const fecha = data.publicado_en ? new Date(data.publicado_en) : null;
  const fechaTxt = fecha
    ? fecha.toLocaleString("es-ES", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid" })
    : "";
  const lineas = String(data.cuerpo || data.resumen || "").split(/\n+/).filter((p) => p.trim());

  // Solo si la noticia lleva una tabla, se leen las clasificaciones
  let tablaChampions = [];
  if (lineas.some((l) => /^\[\[tabla-champions:/.test(l.trim()))) {
    const { data: fila } = await supabase
      .from("clasificaciones")
      .select("datos")
      .eq("competicion", "champions")
      .maybeSingle();
    tablaChampions = (fila && fila.datos) || [];
  }

  const parrafos = lineas
    .map((p) => {
      const t = p.trim();
      let m = t.match(/^\[\[cartel:(\d+),(\d+)\]\]$/) || t.match(/^<img[^>]*crests\.football-data\.org\/(\d+)\.png[^>]*>.*crests\.football-data\.org\/(\d+)\.png[^>]*>$/);
      if (m) {
        return `<div class="wn-cartel"><img src="https://crests.football-data.org/${m[1]}.png" alt=""><span>VS</span><img src="https://crests.football-data.org/${m[2]}.png" alt=""></div>`;
      }
      m = t.match(/^\[\[tabla-champions:(.+)\]\]$/);
      if (m) return htmlTabla(tablaChampions, m[1]);
      return `<p>${escConFormato(p)}</p>`;
    })
    .join("");
  const vid = idYoutube(data.video_url);
  const videoHtml = vid
    ? `<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/${vid}" title="Vídeo" loading="lazy" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`
    : "";

  const jsonld = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: data.titular,
    description: descripcion,
    image: [imagen],
    datePublished: data.publicado_en,
    mainEntityOfPage: url,
    publisher: { "@type": "Organization", name: "Diario Colchonero", url: SITIO },
  };

  const html = `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(data.titular)} | Diario Colchonero</title>
<meta name="description" content="${esc(descripcion)}">
<link rel="canonical" href="${url}">
<meta property="og:site_name" content="Diario Colchonero">
<meta property="og:type" content="article">
<meta property="og:locale" content="es_ES">
<meta property="og:title" content="${esc(data.titular)}">
<meta property="og:description" content="${esc(descripcion)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${esc(imagen)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(data.titular)}">
<meta name="twitter:description" content="${esc(descripcion)}">
<meta name="twitter:image" content="${esc(imagen)}">
<script type="application/ld+json">${JSON.stringify(jsonld).replace(/</g, String.fromCharCode(92) + "u003c")}</script>
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&family=Barlow+Condensed:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  body{margin:0;background:#F5F3EE;color:#14151A;font-family:'Barlow',Arial,sans-serif}
  .top{background:#10203D;border-bottom:5px solid #D2122E;padding:14px 20px;text-align:center}
  .top a{color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:26px;text-transform:uppercase;text-decoration:none;letter-spacing:.02em}
  main{max-width:700px;margin:0 auto;padding:24px 20px 50px}
  .tag{display:inline-block;background:#D2122E;color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;padding:4px 10px 5px;border-radius:2px;text-decoration:none}
  h1{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:clamp(28px,5vw,40px);line-height:1.05;text-transform:uppercase;margin:12px 0 8px}
  .fecha{font-family:'Barlow Condensed',sans-serif;font-size:14px;color:#55565C;margin:0 0 18px}
  .cuerpo p{font-size:18px;line-height:1.65;margin:0 0 14px;color:#22232b}
  .video{position:relative;aspect-ratio:16/9;background:#000;margin:8px 0 18px}
  .video iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
  .botones{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0}
  .btn{display:inline-block;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:15px;padding:10px 18px;border-radius:24px;text-decoration:none;color:#fff}
  .b-web{background:#D2122E}.b-wa{background:#25D366}.b-tg{background:#229ED9}
  .wn-cartel{display:flex;align-items:center;justify-content:center;gap:18px;margin:6px 0 14px}
  .wn-cartel img{width:84px;height:84px;object-fit:contain}
  .wn-cartel span{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:26px;color:#55565C}
  .wn-tabla{overflow-x:auto;border:1px solid rgba(20,21,26,.13);margin:0 0 14px}
  .wn-tabla table{width:100%;border-collapse:collapse;font-family:'Barlow Condensed',sans-serif;min-width:380px}
  .wn-tabla th{font-size:12px;text-transform:uppercase;color:#55565C;padding:8px 6px;border-bottom:2px solid #14151A;text-align:center}
  .wn-tabla td{font-size:15px;font-weight:600;text-align:center;padding:8px 6px;border-bottom:1px solid rgba(20,21,26,.13)}
  .wn-tabla th:nth-child(2),.wn-tabla td:nth-child(2){text-align:left}
  .wn-tabla td .e{display:inline-flex;align-items:center;gap:8px;font-weight:700}
  .wn-tabla td .e img{width:22px;height:22px;object-fit:contain}
  .wn-tabla tr.dest{background:rgba(210,18,46,.07)}.wn-tabla td.pts{font-weight:800}
  .wn-nota{font-size:13px;color:#55565C;margin:-8px 0 14px}
  footer{text-align:center;font-size:13px;color:#55565C;padding:0 20px 40px}
  footer a{color:#55565C}
</style>
</head>
<body>
  <div class="top"><a href="${SITIO}">Diario Colchonero</a></div>
  <main>
    <a class="tag" href="${SITIO}/categoria.html?cat=${esc(data.categoria)}">${esc(etiqueta)}</a>
    <h1>${esc(data.titular)}</h1>
    <p class="fecha">${esc(fechaTxt)}</p>
    <div class="cuerpo">${parrafos}</div>
    ${videoHtml}
    <div class="botones">
      <a class="btn b-web" href="${SITIO}/categoria.html?cat=${esc(data.categoria)}&amp;n=${data.id}">Comentar y dar me gusta</a>
      <a class="btn b-wa" href="https://whatsapp.com/channel/0029VbDayGCF1YlZa2aj5j0J" target="_blank" rel="noopener">Canal de WhatsApp</a>
      <a class="btn b-wa" href="https://chat.whatsapp.com/HErvPhz36yoIuR97jbP0xG" target="_blank" rel="noopener">Grupo de WhatsApp</a>
      <a class="btn b-tg" href="https://t.me/diariocolchonero" target="_blank" rel="noopener">Canal de Telegram</a>
    </div>
    <p><a href="${SITIO}">← Todas las noticias del Atlético de Madrid</a></p>
  </main>
  <footer>Diario Colchonero · Independiente, no afiliado al Atlético de Madrid. · <a href="${SITIO}/privacidad.html">Privacidad</a> · <a href="${SITIO}/aviso-legal.html">Aviso legal</a></footer>
  <script>
  (function(){ try {
    if (/bot|crawl|spider|headless|preview/i.test(navigator.userAgent)) return;
    var id = ${data.id}, clave = "atleti_vistas";
    var v = JSON.parse(sessionStorage.getItem(clave) || "[]");
    if (v.indexOf(id) >= 0) return;
    v.push(id); sessionStorage.setItem(clave, JSON.stringify(v));
    fetch("/api/like", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: id, accion: "vista" }) }).catch(function(){});
  } catch (e) {} })();
  </script>
  <script defer src="/_vercel/insights/script.js"></script>
</body>
</html>`;

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=600");
  return res.status(200).send(html);
};
