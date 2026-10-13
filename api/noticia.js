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
    `<!doctype html><html
