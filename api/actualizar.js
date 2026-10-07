const Parser = require("rss-parser");
const supabase = require("../lib/supabase");
const fuentes = require("../lib/fuentes");
const { reescribirNoticia } = require("../lib/reescribir");
const { actualizarClasificaciones } = require("../lib/clasificacion");
const { publicarEnTelegram } = require("../lib/telegram");

const parser = new Parser();
const MAX_NOTICIAS = 12;

function corregirCategoria(texto, categoriaIA) {
  const t = texto.toLowerCase();
  const esFemenino = ["femenino", "liga f", "jenni hermoso", "maite zubieta", "lola gallardo"].some((k) =>
    t.includes(k)
  );
  if (esFemenino) return "femenino";
  const esFilial = ["atlético madrileño", "atletico madrileño", "filial"].some((k) => t.includes(k));
  if (esFilial) return "filial";
  return categoriaIA;
}

module.exports = async function handler(req, res) {
  const secreto = req.headers.authorization;
  if (secreto !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }

  try {
    // No bloqueante para las noticias: si falla, se registra pero no interrumpe el resto
    await actualizarClasificaciones().catch((e) =>
      console.error("Error actualizando clasificaciones:", e.message)
    );

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

    // Trae todos los títulos ya guardados y compara en memoria
    const { data: existentes, error: errorExistentes } = await supabase
      .from("noticias")
      .select("titulo_original");

    if (errorExistentes) {
      console.error("Error consultando duplicados:", errorExistentes);
    }

    const yaGuardados = new Set((existentes || []).map((n) => n.titulo_original));

    const nuevos = unicos
      .filter((it) => !yaGuardados.has(it.titulo.toLowerCase().slice(0, 40)))
      .slice(0, MAX_NOTICIAS);

    const reescritas = await Promise.all(
      nuevos.map(async (item) => {
        const resultado = await reescribirNoticia(item);
        if (!resultado || resultado.descartar) return null;
        return {
          categoria: corregirCategoria(
            `${item.titulo} ${item.resumenOriginal} ${resultado.titular} ${resultado.resumen}`,
            resultado.categoria
          ),
          titular: resultado.titular,
          resumen: resultado.resumen,
          cuerpo: resultado.cuerpo,
          fuentes: item.fuente,
          enlace_original: item.enlace,
          titulo_original: item.titulo.toLowerCase().slice(0, 40),
          publicado_en: item.publicado
            ? new Date(item.publicado).toISOString()
            : new Date().toISOString(),
        };
      })
    );

    const filas = reescritas.filter(Boolean);

    let enviadasTelegram = 0;
    if (filas.length > 0) {
      const { data: guardadas, error } = await supabase
        .from("noticias")
        .insert(filas)
        .select("id, categoria, titular, resumen");
      if (error) throw error;
      enviadasTelegram = await publicarEnTelegram(guardadas || []);
    }

    return res.status(200).json({
      ok: true,
      total: filas.length,
      enviadasTelegram,
      encontrados: unicos.length,
      yaGuardadosEnBD: yaGuardados.size,
      nuevosTrasFiltro: nuevos.length,
      errorConsulta: errorExistentes ? errorExistentes.message : null,
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
