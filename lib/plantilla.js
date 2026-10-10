// lib/plantilla.js
// Piezas comunes de las páginas que se generan en el servidor (la de cada noticia
// y la hemeroteca): cabecera con el menú, pie, estilos y formato del texto.
// Al generarse en el servidor, Google y el resto de buscadores leen el texto
// completo sin tener que ejecutar JavaScript.

const { SITIO } = require("./url");

const ETIQUETAS = {
  liga: "Liga", champions: "Champions", previa: "Previa", fichajes: "Mercado",
  clasificacion: "Clasificación", filial: "Filial", femenino: "Femenino",
};

const IMAGENES = {
  liga: "/imagenes/liga.jpg", champions: "/imagenes/champions.jpg", previa: "/imagenes/previa.jpg",
  fichajes: "/imagenes/mercado.jpg", clasificacion: "/imagenes/clasificacion.jpg",
  filial: "/imagenes/filial.jpg", femenino: "/imagenes/femenino.jpg",
};

const WHATSAPP = "https://whatsapp.com/channel/0029VbDayGCF1YlZa2aj5j0J";
const TELEGRAM = "https://t.me/diariocolchonero";

function esc(t) {
  return String(t == null ? "" : t)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function etiqueta(cat) {
  return ETIQUETAS[cat] || cat || "";
}

function imagenCategoria(cat) {
  return IMAGENES[cat] || IMAGENES.liga;
}

function fechaLarga(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-ES", {
    day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid",
  });
}

// Convierte el texto de una noticia en HTML. Cada línea es un párrafo, y además:
//   "## Título"  -> un subtítulo
//   "- texto"    -> un punto de una lista
// (los subtítulos y las listas los usan las previas con datos).
function formatearCuerpo(texto) {
  const lineas = String(texto || "").split(/\n+/).map((l) => l.trim()).filter(Boolean);
  const html = [];
  let lista = [];
  const cerrarLista = () => {
    if (lista.length) {
      html.push(`<ul>${lista.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>`);
      lista = [];
    }
  };
  for (const l of lineas) {
    if (/^- /.test(l)) {
      lista.push(l.slice(2));
      continue;
    }
    cerrarLista();
    if (/^## /.test(l)) html.push(`<h2>${esc(l.slice(3))}</h2>`);
    else html.push(`<p>${esc(l)}</p>`);
  }
  cerrarLista();
  return html.join("");
}

const CSS = `
  :root{--red:#D2122E;--red-dark:#9A0B21;--ink:#14151A;--cream:#F5F3EE;--paper:#fff;--navy:#10203D;--grey:#55565C;--line:rgba(20,21,26,.13)}
  *{box-sizing:border-box}
  body{margin:0;background:var(--cream);color:var(--ink);font-family:'Barlow',Arial,sans-serif}
  a{color:inherit}
  .top{background:var(--navy);border-bottom:5px solid var(--red);padding:14px 20px;text-align:center}
  .top a{color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:28px;text-transform:uppercase;text-decoration:none;letter-spacing:.02em}
  .nav{background:var(--paper);border-bottom:1px solid var(--line);overflow-x:auto;white-space:nowrap;text-align:center}
  .nav a{display:inline-block;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:14px;letter-spacing:.03em;text-transform:uppercase;text-decoration:none;padding:11px 12px}
  .nav a:hover,.nav a.activo{color:var(--red-dark)}
  main{max-width:720px;margin:0 auto;padding:22px 20px 40px}
  .migas{font-family:'Barlow Condensed',sans-serif;font-size:13.5px;color:var(--grey);margin:0 0 12px}
  .migas a{text-decoration:none}
  .migas a:hover{text-decoration:underline}
  .tag{display:inline-block;background:var(--red);color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;padding:4px 10px 5px;border-radius:2px;text-decoration:none}
  h1{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:clamp(28px,5vw,40px);line-height:1.05;text-transform:uppercase;margin:12px 0 8px}
  .firma{font-family:'Barlow Condensed',sans-serif;font-size:14.5px;color:var(--grey);margin:0 0 16px}
  .firma a{color:var(--ink);font-weight:600;text-decoration:none}
  .foto{width:100%;height:auto;display:block;margin:0 0 20px;border-radius:3px;background:var(--navy)}
  .entradilla{font-size:19px;line-height:1.5;font-weight:600;margin:0 0 16px}
  .cuerpo p{font-size:18px;line-height:1.65;margin:0 0 14px;color:#22232b}
  .cuerpo h2{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:24px;text-transform:uppercase;margin:26px 0 10px;padding-left:10px;border-left:5px solid var(--red)}
  .cuerpo ul{margin:0 0 16px;padding-left:22px}
  .cuerpo li{font-size:17px;line-height:1.55;margin:0 0 6px;color:#22232b}
  .video{position:relative;aspect-ratio:16/9;background:#000;margin:8px 0 18px}
  .video iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
  .fuente{font-size:14px;color:var(--grey);margin:18px 0 0;padding-top:12px;border-top:1px solid var(--line)}
  .fuente a{color:var(--red-dark)}
  .acciones{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 6px}
  .btn{display:inline-block;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:15px;padding:9px 18px;border-radius:24px;text-decoration:none;color:#fff;border:0;cursor:pointer}
  .b-like{background:var(--paper);color:var(--ink);border:1.5px solid var(--line)}
  .b-like.activo{background:var(--red);color:#fff;border-color:var(--red)}
  .b-comp{background:var(--navy)}.b-wa{background:#25D366}.b-tg{background:#229ED9}
  .bloque{margin-top:34px;padding-top:6px;border-top:3px solid var(--ink)}
  .bloque h2{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:22px;text-transform:uppercase;margin:12px 0 10px}
  .lista{list-style:none;margin:0;padding:0}
  .lista li{padding:12px 0;border-bottom:1px solid var(--line)}
  .lista a{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:20px;line-height:1.15;text-decoration:none}
  .lista a:hover{color:var(--red-dark)}
  .lista .meta{font-family:'Barlow Condensed',sans-serif;font-size:13px;color:var(--grey);margin:0 0 3px}
  .lista .meta b{color:var(--red-dark);text-transform:uppercase;font-weight:700}
  .lista p{font-size:15px;line-height:1.45;color:var(--grey);margin:4px 0 0}
  .comentario{padding:10px 0;border-bottom:1px solid var(--line)}
  .comentario b{font-size:15px}
  .comentario span{font-size:12.5px;color:var(--grey);margin-left:8px}
  .comentario p{margin:4px 0 0;font-size:15.5px;line-height:1.5}
  .aviso{font-size:15px;color:var(--grey);margin:8px 0}
  form.comentar{display:grid;gap:8px;margin-top:14px}
  form.comentar input,form.comentar textarea{font:inherit;font-size:16px;padding:10px 12px;border:1px solid var(--line);border-radius:4px;background:var(--paper);width:100%}
  form.comentar textarea{min-height:90px;resize:vertical}
  form.comentar button{justify-self:start;background:var(--red)}
  .paginas{display:flex;justify-content:space-between;gap:12px;margin:24px 0 0;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:16px}
  .paginas a{color:var(--red-dark);text-decoration:none}
  footer{max-width:720px;margin:0 auto;text-align:center;font-size:13px;color:var(--grey);padding:16px 20px 44px;border-top:1px solid var(--line)}
  footer p{margin:6px 0}
`;

const MENU = [
  ["/", "Portada"],
  ["/categoria.html?cat=liga", "Liga", "liga"],
  ["/categoria.html?cat=champions", "Champions", "champions"],
  ["/categoria.html?cat=previa", "Previa", "previa"],
  ["/categoria.html?cat=fichajes", "Mercado", "fichajes"],
  ["/categoria.html?cat=filial", "Filial", "filial"],
  ["/categoria.html?cat=femenino", "Femenino", "femenino"],
  ["/categoria.html?cat=clasificacion", "Clasificación"],
  ["/categoria.html?cat=calendario-liga", "Calendario"],
];

// Devuelve la página HTML completa.
//   titulo, descripcion, canonica: datos para Google y para compartir
//   cabeza: etiquetas extra para el <head> (Open Graph, datos estructurados…)
//   contenido: lo que va dentro de <main>
//   activa: categoría que se resalta en el menú
//   scripts: código extra al final de la página
function pagina({ titulo, descripcion, canonica, cabeza = "", contenido, activa = "", scripts = "", indexar = true }) {
  const menu = MENU.map(([href, texto, cat]) =>
    `<a href="${esc(href)}"${cat && cat === activa ? ' class="activo"' : ""}>${esc(texto)}</a>`
  ).join("");

  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(titulo)}</title>
<meta name="description" content="${esc(descripcion)}">
${indexar ? "" : '<meta name="robots" content="noindex">\n'}${canonica ? `<link rel="canonical" href="${esc(canonica)}">\n` : ""}${cabeza}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&family=Barlow+Condensed:wght@600;700;800&display=swap" rel="stylesheet">
<style>${CSS}</style>
</head>
<body>
  <div class="top"><a href="/">Diario Colchonero</a></div>
  <nav class="nav" aria-label="Secciones">${menu}</nav>
  <main>${contenido}</main>
  <footer>
    <p>Diario Colchonero · Independiente, no afiliado al Atlético de Madrid.</p>
    <p>📲 Síguenos: <a href="${WHATSAPP}" target="_blank" rel="noopener">Canal de WhatsApp</a> · <a href="${TELEGRAM}" target="_blank" rel="noopener">Canal de Telegram</a></p>
    <p><a href="/noticias">Todas las noticias</a> · <a href="/sobre-nosotros.html">Quiénes somos</a> · <a href="/privacidad.html">Privacidad</a> · <a href="/cookies.html">Cookies</a> · <a href="/aviso-legal.html">Aviso legal</a> · <a href="/contacto.html">Contacto</a></p>
  </footer>
  ${scripts}
  <script defer src="/_vercel/insights/script.js"></script>
</body>
</html>`;
}

function paginaError(res, codigo, mensaje) {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  return res.status(codigo).send(
    pagina({
      titulo: `${mensaje} | Diario Colchonero`,
      descripcion: mensaje,
      indexar: false,
      contenido: `<h1>${esc(mensaje)}</h1><p class="aviso"><a href="/">Volver a la portada de Diario Colchonero</a></p>`,
    })
  );
}

module.exports = {
  SITIO, WHATSAPP, TELEGRAM, esc, etiqueta, imagenCategoria, fechaLarga, formatearCuerpo, pagina, paginaError,
};
