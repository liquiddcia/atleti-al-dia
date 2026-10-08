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
    .select("id, categoria, titular, resumen, cuerpo, publicado_en, imagen_url, video_url")
    .eq("id", id)
    .eq("oculta", false)
    .maybeSingle();

  if (error) return paginaError(res, 500, "No se pudo cargar la noticia");
  if (!data) return paginaError(res, 404, "Noticia no encontrada");

  const url = `${SITIO}/api/noticia?id=${data.id}`;
  const etiqueta = ETIQUETAS[data.categoria] || data.categoria;
  const imagen = data.imagen_url && /^https:\/\//.test(data.imagen_url) ? data.imagen_url : `${SITIO}/og-image.jpg`;
  const descripcion = String(data.resumen || "").slice(0, 200);
  const fecha = data.publicado_en ? new Date(data.publicado_en) : null;
  const fechaTxt = fecha
    ? fecha.toLocaleString("es-ES", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid" })
    : "";
  const parrafos = String(data.cuerpo || data.resumen || "")
    .split(/\n+/)
    .filter((p) => p.trim())
    .map((p) => `<p>${esc(p)}</p>`)
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
<script type="application/ld+json">${JSON.stringify(jsonld).replace(/</g, "\\u003c")}</script>
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
      <a class="btn b-tg" href="https://t.me/diariocolchonero" target="_blank" rel="noopener">Canal de Telegram</a>
    </div>
    <p><a href="${SITIO}">← Todas las noticias del Atlético de Madrid</a></p>
  </main>
  <footer>Diario Colchonero · Independiente, no afiliado al Atlético de Madrid. · <a href="${SITIO}/privacidad.html">Privacidad</a> · <a href="${SITIO}/aviso-legal.html">Aviso legal</a></footer>
  <script defer src="/_vercel/insights/script.js"></script>
</body>
</html>`;

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=600");
  return res.status(200).send(html);
};
