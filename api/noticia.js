// api/noticia.js
// Página propia de cada noticia, generada en el servidor para que Google lea el
// texto completo. Dirección pública:
//   https://diariocolchonero.com/noticia/339-titular-de-la-noticia
// (vercel.json redirige /noticia/... a esta función). Las direcciones antiguas
// (/api/noticia?id=339) siguen funcionando: saltan solas a la nueva.
const supabase = require("../lib/supabase");
const { SITIO, rutaNoticia, urlNoticia } = require("../lib/url");
const {
  WHATSAPP, TELEGRAM, esc, etiqueta, imagenCategoria, fechaLarga, formatearCuerpo, pagina, paginaError,
} = require("../lib/plantilla");

function idYoutube(url) {
  const m = String(url || "").match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/))([A-Za-z0-9_-]{11})/
  );
  return m ? m[1] : null;
}

// Enlace discreto a la información original. Las noticias propias (resultados,
// previas con datos) no llevan fuente externa.
function fuenteHtml(n) {
  const enlace = String(n.enlace_original || "");
  if (!/^https?:\/\//.test(enlace) || enlace.startsWith(SITIO)) return "";
  const medio = String(n.fuentes || "").trim();
  const esMedio = medio && !/^google news/i.test(medio) && medio !== "Diario Colchonero";
  const texto = esMedio ? `Fuente: <a href="${esc(enlace)}" target="_blank" rel="noopener nofollow">${esc(medio)}</a>`
    : `<a href="${esc(enlace)}" target="_blank" rel="noopener nofollow">Ver la información original</a>`;
  return `<p class="fuente">${texto}</p>`;
}

// Me gusta, compartir y comentarios (lo mismo que hace la ventana de la portada)
function scriptInteraccion(n) {
  return `<script>
(function(){
  var ID = ${Number(n.id)};
  function likeados(){ try { return JSON.parse(localStorage.getItem("atleti_likes") || "[]"); } catch(e){ return []; } }
  function guardar(a){ try { localStorage.setItem("atleti_likes", JSON.stringify(a)); } catch(e){} }
  var btn = document.getElementById("btn-like");
  if (likeados().indexOf(ID) >= 0) btn.classList.add("activo");
  btn.addEventListener("click", function(){
    var lista = likeados(), ya = lista.indexOf(ID) >= 0;
    fetch("/api/like", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ id: ID, accion: ya ? "quitar" : "dar" }) })
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (typeof d.likes !== "number") return;
        guardar(ya ? lista.filter(function(x){ return x !== ID; }) : lista.concat([ID]));
        btn.textContent = "❤ " + d.likes;
        btn.classList.toggle("activo", !ya);
      }).catch(function(){});
  });

  document.getElementById("btn-compartir").addEventListener("click", function(){
    var url = location.origin + location.pathname, titulo = document.querySelector("h1").textContent;
    if (navigator.share) navigator.share({ title: titulo, text: titulo + " — Diario Colchonero", url: url }).catch(function(){});
    else if (navigator.clipboard) navigator.clipboard.writeText(url).then(function(){ alert("Enlace copiado al portapapeles"); }).catch(function(){ prompt("Copia este enlace:", url); });
    else prompt("Copia este enlace:", url);
  });

  var cont = document.getElementById("comentarios-lista");
  function fecha(iso){ return iso ? new Date(iso).toLocaleString("es-ES", { day:"numeric", month:"long", hour:"2-digit", minute:"2-digit" }) : ""; }
  function cargar(){
    fetch("/api/comentarios?noticia_id=" + ID).then(function(r){ return r.json(); }).then(function(d){
      var lista = d.comentarios || [];
      cont.textContent = "";
      if (!lista.length){ var p = document.createElement("p"); p.className = "aviso"; p.textContent = "Sé el primero en comentar."; cont.appendChild(p); return; }
      lista.forEach(function(c){
        var div = document.createElement("div"); div.className = "comentario";
        var b = document.createElement("b"); b.textContent = c.nombre;
        var s = document.createElement("span"); s.textContent = fecha(c.creado_en);
        var p = document.createElement("p"); p.textContent = c.texto;
        div.appendChild(b); div.appendChild(s); div.appendChild(p); cont.appendChild(div);
      });
    }).catch(function(){ cont.innerHTML = '<p class="aviso">No se pudieron cargar los comentarios.</p>'; });
  }
  cargar();

  document.getElementById("comentar").addEventListener("submit", function(e){
    e.preventDefault();
    var nombre = document.getElementById("c-nombre").value.trim(), campo = document.getElementById("c-texto"), texto = campo.value.trim();
    if (!nombre || !texto) return;
    var ultimo = 0; try { ultimo = Number(localStorage.getItem("atleti_ultimo_comentario") || 0); } catch(e){}
    if (Date.now() - ultimo < 20000){ alert("Espera unos segundos antes de comentar de nuevo."); return; }
    fetch("/api/comentarios", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ noticia_id: ID, nombre: nombre, texto: texto }) })
      .then(function(r){ if (!r.ok) throw new Error(); try { localStorage.setItem("atleti_ultimo_comentario", String(Date.now())); } catch(e){} campo.value = ""; cargar(); })
      .catch(function(){ alert("No se pudo enviar el comentario. Inténtalo de nuevo."); });
  });
})();
</script>`;
}

module.exports = async function handler(req, res) {
  const q = req.query || {};
  const slugPedido = q.slug ? String(q.slug) : "";
  const id = parseInt(slugPedido || q.id, 10);
  if (!id) return paginaError(res, 404, "Noticia no encontrada");

  const { data, error } = await supabase
    .from("noticias")
    .select("id, categoria, titular, resumen, cuerpo, publicado_en, likes, imagen_url, video_url, fuentes, enlace_original")
    .eq("id", id)
    .eq("oculta", false)
    .maybeSingle();

  if (error) return paginaError(res, 500, "No se pudo cargar la noticia");
  if (!data) return paginaError(res, 404, "Noticia no encontrada");

  // Dirección antigua (/api/noticia?id=…): salta a la dirección limpia
  if (!slugPedido) {
    res.setHeader("Cache-Control", "s-maxage=86400");
    return res.redirect(301, rutaNoticia(data));
  }

  // Otras noticias de la misma sección, para seguir leyendo (y para que Google las encuentre)
  const { data: otras } = await supabase
    .from("noticias")
    .select("id, categoria, titular, publicado_en")
    .eq("categoria", data.categoria)
    .eq("oculta", false)
    .neq("id", data.id)
    .order("publicado_en", { ascending: false })
    .limit(6);

  const url = urlNoticia(data);
  const nombreCat = etiqueta(data.categoria);
  const urlCat = `/categoria.html?cat=${encodeURIComponent(data.categoria)}`;
  const imagenSocial = `${SITIO}/og-image.jpg`;
  const foto = data.imagen_url || imagenCategoria(data.categoria);
  const descripcion = String(data.resumen || "").slice(0, 200);
  const vid = idYoutube(data.video_url);

  const jsonld = [
    {
      "@context": "https://schema.org",
      "@type": "NewsArticle",
      headline: data.titular,
      description: descripcion,
      image: [data.imagen_url || imagenSocial],
      datePublished: data.publicado_en,
      dateModified: data.publicado_en,
      articleSection: nombreCat,
      mainEntityOfPage: url,
      author: { "@type": "Organization", name: "Redacción Diario Colchonero", url: `${SITIO}/sobre-nosotros.html` },
      publisher: {
        "@type": "Organization", name: "Diario Colchonero", url: SITIO,
        logo: { "@type": "ImageObject", url: `${SITIO}/logo.png` },
      },
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Portada", item: SITIO + "/" },
        { "@type": "ListItem", position: 2, name: nombreCat, item: SITIO + urlCat },
        { "@type": "ListItem", position: 3, name: data.titular, item: url },
      ],
    },
  ];

  const cabeza = `<meta property="og:site_name" content="Diario Colchonero">
<meta property="og:type" content="article">
<meta property="og:locale" content="es_ES">
<meta property="og:title" content="${esc(data.titular)}">
<meta property="og:description" content="${esc(descripcion)}">
<meta property="og:url" content="${esc(url)}">
<meta property="og:image" content="${esc(data.imagen_url || imagenSocial)}">
<meta property="article:published_time" content="${esc(data.publicado_en || "")}">
<meta property="article:section" content="${esc(nombreCat)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(data.titular)}">
<meta name="twitter:description" content="${esc(descripcion)}">
<meta name="twitter:image" content="${esc(data.imagen_url || imagenSocial)}">
<script type="application/ld+json">${JSON.stringify(jsonld).replace(/</g, "\\u003c")}</script>`;

  const relacionadas = (otras || []).length
    ? `<section class="bloque"><h2>Más noticias de ${esc(nombreCat)}</h2><ul class="lista">${otras
        .map((o) => `<li><p class="meta">${esc(fechaLarga(o.publicado_en))}</p><a href="${esc(rutaNoticia(o))}">${esc(o.titular)}</a></li>`)
        .join("")}</ul></section>`
    : "";

  const contenido = `
    <p class="migas"><a href="/">Portada</a> › <a href="${esc(urlCat)}">${esc(nombreCat)}</a></p>
    <article>
      <a class="tag" href="${esc(urlCat)}">${esc(nombreCat)}</a>
      <h1>${esc(data.titular)}</h1>
      <p class="firma">Por <a href="/sobre-nosotros.html">Redacción Diario Colchonero</a> · <time datetime="${esc(data.publicado_en || "")}">${esc(fechaLarga(data.publicado_en))}</time></p>
      <img class="foto" src="${esc(foto)}" alt="${esc(nombreCat)} · Diario Colchonero" width="1280" height="480"${data.imagen_url ? ` onerror="this.onerror=null;this.src='${esc(imagenCategoria(data.categoria))}'"` : ""}>
      ${data.resumen && data.cuerpo ? `<p class="entradilla">${esc(data.resumen)}</p>` : ""}
      <div class="cuerpo">${formatearCuerpo(data.cuerpo || data.resumen)}</div>
      ${vid ? `<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/${vid}" title="Vídeo" loading="lazy" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>` : ""}
      ${fuenteHtml(data)}
    </article>
    <div class="acciones">
      <button class="btn b-like" id="btn-like" type="button">❤ ${Number(data.likes) || 0}</button>
      <button class="btn b-comp" id="btn-compartir" type="button">Compartir</button>
      <a class="btn b-wa" href="${WHATSAPP}" target="_blank" rel="noopener">Canal de WhatsApp</a>
      <a class="btn b-tg" href="${TELEGRAM}" target="_blank" rel="noopener">Canal de Telegram</a>
    </div>
    ${relacionadas}
    <section class="bloque">
      <h2>Comentarios</h2>
      <div id="comentarios-lista"><p class="aviso">Cargando comentarios…</p></div>
      <form class="comentar" id="comentar">
        <input type="text" id="c-nombre" placeholder="Tu nombre" maxlength="40" required>
        <textarea id="c-texto" placeholder="Escribe un comentario…" maxlength="500" required></textarea>
        <button class="btn" type="submit">Publicar</button>
      </form>
    </section>`;

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=600");
  return res.status(200).send(
    pagina({
      titulo: `${data.titular} | Diario Colchonero`,
      descripcion,
      canonica: url,
      cabeza,
      contenido,
      activa: data.categoria,
      scripts: scriptInteraccion(data),
    })
  );
};
