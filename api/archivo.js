// api/archivo.js
// Hemeroteca: lista de todas las noticias publicadas, de la más reciente a la más
// antigua, con enlaces normales a cada una. Dirección pública:
//   https://diariocolchonero.com/noticias        (y /noticias?p=2, ?p=3…)
// Sirve a los lectores para encontrar noticias antiguas y a Google para llegar
// a todas sin depender del JavaScript de la portada.
const supabase = require("../lib/supabase");
const { SITIO, rutaNoticia } = require("../lib/url");
const { esc, etiqueta, fechaLarga, pagina, paginaError } = require("../lib/plantilla");

const POR_PAGINA = 40;

module.exports = async function handler(req, res) {
  const p = Math.max(1, parseInt(req.query && req.query.p, 10) || 1);
  const desde = (p - 1) * POR_PAGINA;

  // Pide una de más para saber si hay página siguiente
  const { data, error } = await supabase
    .from("noticias")
    .select("id, categoria, titular, resumen, publicado_en")
    .eq("oculta", false)
    .order("publicado_en", { ascending: false })
    .range(desde, desde + POR_PAGINA);

  if (error) return paginaError(res, 500, "No se pudieron cargar las noticias");

  const filas = data || [];
  const haySiguiente = filas.length > POR_PAGINA;
  const noticias = filas.slice(0, POR_PAGINA);
  if (!noticias.length && p > 1) return paginaError(res, 404, "Página no encontrada");

  const lista = noticias
    .map(
      (n) => `<li>
        <p class="meta"><b>${esc(etiqueta(n.categoria))}</b> · ${esc(fechaLarga(n.publicado_en))}</p>
        <a href="${esc(rutaNoticia(n))}">${esc(n.titular)}</a>
        ${n.resumen ? `<p>${esc(n.resumen)}</p>` : ""}
      </li>`
    )
    .join("");

  const anterior = p > 1 ? `<a href="/noticias${p > 2 ? `?p=${p - 1}` : ""}">← Más recientes</a>` : "<span></span>";
  const siguiente = haySiguiente ? `<a href="/noticias?p=${p + 1}">Más antiguas →</a>` : "<span></span>";

  const contenido = `
    <p class="migas"><a href="/">Portada</a> › Todas las noticias</p>
    <h1>Todas las noticias del Atlético de Madrid</h1>
    <p class="firma">Hemeroteca de Diario Colchonero${p > 1 ? ` · Página ${p}` : ""}</p>
    ${noticias.length ? `<ul class="lista">${lista}</ul>` : '<p class="aviso">Todavía no hay noticias publicadas.</p>'}
    <div class="paginas">${anterior}${siguiente}</div>`;

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=600, stale-while-revalidate=1200");
  return res.status(200).send(
    pagina({
      titulo: `Todas las noticias del Atlético de Madrid${p > 1 ? ` – Página ${p}` : ""} | Diario Colchonero`,
      descripcion: "Hemeroteca de Diario Colchonero: todas las noticias del Atlético de Madrid, de la más reciente a la más antigua.",
      canonica: `${SITIO}/noticias${p > 1 ? `?p=${p}` : ""}`,
      contenido,
    })
  );
};
