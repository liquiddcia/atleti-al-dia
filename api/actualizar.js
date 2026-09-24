const Parser = require("rss-parser");
const { kv } = require("@vercel/kv");
const fuentes = require("../lib/fuentes");
const { reescribirNoticia } = require("../lib/reescribir");

const parser = new Parser();
const MAX_NOTICIAS = 12;

module.exports = async function handler(req, res) {
  // Protege el endpoint: solo Vercel Cron (o tú, a mano) puede dispararlo.
  const secreto = req.headers.authorization;
  if (secreto !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }

  try {
    const items = [];
    for (const fuente of fuentes) {
      const feed = await parser.parseURL(fuente.url);
      for (const item of feed.items.slice(0, 8)) {
        items.push({
          titulo: item.title,
          resumenOriginal: (item.contentSnippet || "").slice(0, 500),
          enlace: item.link,
          fuente: fuente.nombre,
          publicado: item.isoDate || item.pubDate,
        });
      }
    }

    // Quita duplicados por titular muy parecido (varios medios cubren lo mismo)
    const vistos = new Set();
    const unicos = items.filter((it) => {
      const clave = it.titulo.toLowerCase().slice(0, 40);
      if (vistos.has(clave)) return false;
      vistos.add(clave);
      return true;
    });

    const reescritas = [];
    for (const item of unicos.slice(0, MAX_NOTICIAS)) {
      const resultado = await reescribirNoticia(item);
      if (resultado) {
        reescritas.push({
          ...resultado,
          enlaceOriginal: item.enlace,
          fuenteOriginal: item.fuente,
          publicado: item.publicado,
        });
      }
    }

    await kv.set("noticias-atleti", {
      actualizado: new Date().toISOString(),
      noticias: reescritas,
    });

    return res.status(200).json({ ok: true, total: reescritas.length });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
