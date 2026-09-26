const Parser = require("rss-parser");
const supabase = require("../lib/supabase");
const fuentes = require("../lib/fuentes");
const { reescribirNoticia } = require("../lib/reescribir");

const parser = new Parser();
const MAX_NOTICIAS = 12;

module.exports = async function handler(req, res) {
  const secreto = req.headers.authorization;
  if (secreto !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }

  try {
    const resultados = await Promise.allSettled(
      fuentes.map((fuente) => parser.parseURL(fuente.url))
    );

    const items = [];
    resultados.forEach((resultado, i) => {
      if (resultado.status !== "fulfilled") return;
      const fuente = fuentes[i];
      for (const item of resultado.value.items.slice(0, 8)) {
        items.push({
          titulo: item.title,
          resumenOriginal: (item.contentSnippet || "").slice(0, 500),
          enlace: item.link,
          fuente: fuente.nombre,
          publicado: item.isoDate || item.pubDate,
        });
      }
    });

    const vistos = new Set();
    const unicos = items.filter((it) => {
      const clave = it.titulo.toLowerCase().slice(0, 40);
      if (vistos.has(clave)) return false;
      vistos.add(clave);
      return true;
    });

    // Trae los títulos guardados en los últimos 7 días y compara en memoria
