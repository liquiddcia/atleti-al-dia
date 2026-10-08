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

// ---- Detección de noticias repetidas sobre el mismo tema ----
const PALABRAS_VACIAS = new Set([
  "para", "pero", "como", "tras", "ante", "sobre", "entre", "desde", "hasta", "este", "esta", "esto",
  "estos", "estas", "sus", "con", "sin", "por", "los", "las", "del", "una", "uno", "unos", "unas",
  "que", "más", "mas", "muy", "ser", "han", "hay", "dos", "tres", "ver", "así", "asi", "ya",
  "atlético", "atletico", "madrid", "atleti", "club", "colchonero", "colchoneros", "rojiblanco",
  "rojiblancos", "equipo", "partido", "liga", "noticia", "última", "ultima", "hora", "oficial",
]);

function palabrasClave(texto) {
  const limpio = String(texto || "")
    .toLowerCase()
    .replace(/\s[-–|]\s[^-–|]+$/, "") // quita el " - Marca" del final de los titulares de Google News
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9ñ\s]/g, " ");
  const vacias = new Set([...PALABRAS_VACIAS].map((p) => p.normalize("NFD").replace(/[\u0300-\u036f]/g, "")));
  return new Set(limpio.split(/\s+/).filter((w) => w.length > 3 && !vacias.has(w)));
}

// Dos titulares hablan de lo mismo si comparten al menos 3 palabras clave
// y esas palabras son el 60 % o más del más corto de los dos.
function sonParecidos(a, b) {
  const A = palabrasClave(a);
  const B = palabrasClave(b);
  if (!A.size || !B.size) return false;
  let comunes = 0;
  A.forEach((w) => { if (B.has(w)) comunes++; });
  return comunes >= 3 && comunes / Math.min(A.size, B.size) >= 0.6;
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

    // Titulares de las últimas noticias, para no repetir el mismo tema
    const { data: recientesBD } = await supabase
      .from("noticias")
      .select("titular")
      .order("id", { ascending: false })
      .limit(40);
    const recientes = (recientesBD || []).map((n) => n.titular);

    const aceptados = [];
    const nuevos = unicos
      .filter((it) => !yaGuardados.has(it.titulo.toLowerCase().slice(0, 40)))
      .filter((it) => {
        // Descarta si se parece a una noticia reciente o a otra de esta misma tanda
        if (recientes.some((t) => sonParecidos(it.titulo, t))) return false;
        if (aceptados.some((t) => sonParecidos(it.titulo, t))) return false;
        aceptados.push(it.titulo);
        return true;
      })
      .slice(0, MAX_NOTICIAS);

    const reescritas = await Promise.all(
      nuevos.map(async (item) => {
        const resultado = await reescribirNoticia({ ...item, recientes });
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
