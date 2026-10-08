// api/sitemap.js
// Mapa del sitio con todas las noticias, para Google Search Console.
// Dirección: https://diariocolchonero.com/api/sitemap
const supabase = require("../lib/supabase");

const SITIO = "https://diariocolchonero.com";

module.exports = async function handler(req, res) {
  const { data, error } = await supabase
    .from("noticias")
    .select("id, publicado_en")
    .eq("oculta", false)
    .order("publicado_en", { ascending: false })
    .limit(5000);

  if (error) {
    return res.status(500).send("Error generando el sitemap");
  }

  const fijas = [
    "/",
    "/categoria.html?cat=liga", "/categoria.html?cat=champions", "/categoria.html?cat=previa",
    "/categoria.html?cat=fichajes", "/categoria.html?cat=filial", "/categoria.html?cat=femenino",
    "/categoria.html?cat=clasificacion", "/categoria.html?cat=clasificacion-champions",
    "/categoria.html?cat=calendario-liga", "/categoria.html?cat=calendario-champions",
    "/sobre-nosotros.html", "/contacto.html", "/privacidad.html", "/cookies.html", "/aviso-legal.html",
  ].map((p) => `  <url><loc>${SITIO}${p.replace(/&/g, "&amp;")}</loc></url>`);

  const noticias = (data || []).map((n) => {
    const lastmod = n.publicado_en ? `<lastmod>${new Date(n.publicado_en).toISOString()}</lastmod>` : "";
    return `  <url><loc>${SITIO}/api/noticia?id=${n.id}</loc>${lastmod}</url>`;
  });

  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${[...fijas, ...noticias].join("\n")}\n</urlset>\n`;

  res.setHeader("Content-Type", "application/xml; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=3600");
  return res.status(200).send(xml);
};
