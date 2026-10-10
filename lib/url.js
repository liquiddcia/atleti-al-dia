// lib/url.js
// Direcciones "limpias" de las noticias, por ejemplo:
//   https://diariocolchonero.com/noticia/385-simeone-ironico-sobre-el-paron
// El número del principio es el id de la noticia; el resto es solo para que la
// dirección se entienda (y para Google). Si el titular cambia, el id sigue valiendo.

const SITIO = "https://diariocolchonero.com";

function slug(texto) {
  const limpio = String(texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (limpio.length <= 80) return limpio;
  // Corta por una palabra completa, sin dejar un guion colgando
  return limpio.slice(0, 80).replace(/-[^-]*$/, "");
}

function rutaNoticia(n) {
  const s = slug(n.titular);
  return `/noticia/${n.id}${s ? "-" + s : ""}`;
}

function urlNoticia(n) {
  return SITIO + rutaNoticia(n);
}

module.exports = { SITIO, slug, rutaNoticia, urlNoticia };
