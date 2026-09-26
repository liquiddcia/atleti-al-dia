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

    const vistos = new Set();
    const unicos = items.filter((it) => {
      const clave = it.titulo.toLowerCase().slice(0, 40);
      if (vistos.has(clave)) return false;
      vistos.add(clave);
      return true;
    });

    const enlaces = unicos.map((it) => it.enlace).filter(Boolean);
    const { data: existentes } = await supabase
      .from("noticias")
      .select("enlace_original")
      .in("enlace_original", enlaces);
    const yaGuardados = new Set((existentes || []).map((n) => n.enlace_original));

    const nuevos = unicos.filter((it) => !yaGuardados.has(it.enlace)).slice(0, MAX_NOTICIAS);

    const filas = [];
    for (const item of nuevos) {
      const resultado = await reescribirNoticia(item);
      if (resultado) {
        filas.push({
          categoria: resultado.categoria,
          titular: resultado.titular,
          resumen: resultado.resumen,
          cuerpo: resultado.cuerpo,
          fuentes: item.fuente,
          enlace_original: item.enlace,
          publicado_en: item.publicado
            ? new Date(item.publicado).toISOString()
            : new Date().toISOString(),
        });
      }
    }

    if (filas.length > 0) {
      const { error } = await supabase.from("noticias").insert(filas);
      if (error) throw error;
    }

    return res.status(200).json({ ok: true, total: filas.length });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
