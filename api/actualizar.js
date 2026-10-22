const Parser = require("rss-parser");
const supabase = require("../lib/supabase");
const fuentes = require("../lib/fuentes");
const { reescribirNoticia } = require("../lib/reescribir");
const { leerArticulo } = require("../lib/leerarticulo");
const { agruparNoticias } = require("../lib/agrupar");
const { actualizarClasificaciones } = require("../lib/clasificacion");
const { publicarEnTelegram } = require("../lib/telegram");
const { avisarBorradores } = require("../lib/borradores");

const parser = new Parser();
const MAX_HORAS_ANTIGUEDAD = 48; // no se publican noticias cuyo medio las publicó hace más de 48 horas

function esMuyAntigua(publicado) {
  const t = publicado ? new Date(publicado).getTime() : NaN;
  return !isNaN(t) && Date.now() - t > MAX_HORAS_ANTIGUEDAD * 3600 * 1000;
}

// Partidos del Atlético ya terminados en los últimos días, para que la IA no publique
// previas de partidos que ya se han jugado.
async function partidosYaJugados() {
  if (!process.env.FOOTBALL_DATA_API_KEY) return "";
  try {
    const dia = (d) => d.toISOString().slice(0, 10);
    const ahora = Date.now();
    const r = await fetch(
      `https://api.football-data.org/v4/teams/78/matches?dateFrom=${dia(new Date(ahora - 5 * 86400000))}&dateTo=${dia(new Date(ahora + 86400000))}`,
      { headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY } }
    );
    if (!r.ok) return "";
    const d = await r.json();
    return (d.matches || [])
      .filter((m) => m.status === "FINISHED" && m.score && m.score.fullTime && m.score.fullTime.home != null)
      .map((m) => {
        const fecha = new Date(m.utcDate).toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", timeZone: "Europe/Madrid" });
        const comp = (m.competition && m.competition.name) || "";
        return `- ${fecha}: ${m.homeTeam.shortName || m.homeTeam.name} ${m.score.fullTime.home}-${m.score.fullTime.away} ${m.awayTeam.shortName || m.awayTeam.name}${comp ? ` (${comp})` : ""}`;
      })
      .join("\n");
  } catch (e) {
    console.error("Error pidiendo partidos jugados:", e.message);
    return "";
  }
}
const MAX_NOTICIAS = 6; // máximo de noticias publicadas por tanda (ya agrupadas)
const MAX_CANDIDATAS = 12; // máximo de noticias nuevas que se estudian para agrupar
// Modo revisión: las noticias nuevas quedan como borradores hasta que las apruebas en /admin.html
// (o se publican solas pasada 1 hora). Para volver a publicar directo: MODO_REVISION=0 en Vercel.
const MODO_REVISION = process.env.MODO_REVISION !== "0";

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

    // Una noticia unida guarda varias claves separadas por "||" (una por cada original)
    const yaGuardados = new Set();
    (existentes || []).forEach((n) => {
      String(n.titulo_original || "").split("||").forEach((k) => yaGuardados.add(k));
    });

    // Titulares de los últimos 7 días (no solo de hoy), para no repetir el mismo tema
    const { data: recientesBD } = await supabase
      .from("noticias")
      .select("titular")
      .gte("publicado_en", new Date(Date.now() - 7 * 86400000).toISOString())
      .order("id", { ascending: false })
      .limit(100);
    const recientes = (recientesBD || []).map((n) => n.titular);

    const aceptados = [];
    const nuevos = unicos
      .filter((it) => !yaGuardados.has(it.titulo.toLowerCase().slice(0, 40)))
      .filter((it) => !esMuyAntigua(it.publicado))
      .filter((it) => {
        // Descarta si se parece a una noticia reciente o a otra de esta misma tanda
        if (recientes.some((t) => sonParecidos(it.titulo, t))) return false;
        if (aceptados.some((t) => sonParecidos(it.titulo, t))) return false;
        aceptados.push(it.titulo);
        return true;
      })
      .slice(0, MAX_CANDIDATAS);

    // Agrupa las que cuentan lo mismo (misma persona en el mismo acto, misma entrevista...)
    // para publicar UNA sola noticia, y quita las que solo repiten algo ya publicado.
    const { grupos, repetidas } = await agruparNoticias(nuevos, recientes);
    const sinRepetidas = new Set(repetidas);
    const gruposFinales = grupos
      .map((g) => g.filter((i) => !sinRepetidas.has(i)).map((i) => nuevos[i]))
      .filter((g) => g.length > 0)
      .slice(0, MAX_NOTICIAS);

    const contexto = await partidosYaJugados();

    let articulosLeidos = 0;
    const descartadasIA = []; // titulares que la IA descarta al reescribir (para revisarlas)
    const reescritas = await Promise.all(
      gruposFinales.map(async (grupo) => {
        // Lee los artículos originales (si se puede) para que la IA tenga nombres y datos completos
        const textos = await Promise.all(grupo.map((it) => leerArticulo(it.enlace)));
        textos.forEach((t) => { if (t) articulosLeidos++; });
        const item = grupo[0];
        const varias = grupo.length > 1;
        const resumenOriginal = varias
          ? grupo.map((it) => `[${it.fuente}] ${it.titulo}: ${it.resumenOriginal}`).join("\n")
          : item.resumenOriginal;
        const textoArticulo = varias
          ? textos.map((t, i) => (t ? `--- Texto ${i + 1} (${grupo[i].fuente}) ---\n${t.slice(0, 3000)}` : "")).filter(Boolean).join("\n\n")
          : textos[0];
        const resultado = await reescribirNoticia({ ...item, resumenOriginal, recientes, contexto, textoArticulo, varias });
        if (!resultado || resultado.descartar) { descartadasIA.push(item.titulo); return null; }
        const nombresFuentes = [...new Set(grupo.map((it) => it.fuente))].join(", ");
        return {
          categoria: corregirCategoria(
            `${grupo.map((it) => `${it.titulo} ${it.resumenOriginal}`).join(" ")} ${resultado.titular} ${resultado.resumen}`,
            resultado.categoria
          ),
          titular: resultado.titular,
          resumen: resultado.resumen,
          cuerpo: resultado.cuerpo,
          fuentes: nombresFuentes,
          enlace_original: item.enlace,
          // una clave por cada original, para no volver a procesar ninguno
          titulo_original: grupo.map((it) => it.titulo.toLowerCase().slice(0, 40)).join("||"),
          publicado_en: item.publicado
            ? new Date(item.publicado).toISOString()
            : new Date().toISOString(),
        };
      })
    );

    const filas = reescritas.filter(Boolean);

    let enviadasTelegram = 0;
    let borradores = 0;
    if (filas.length > 0) {
      if (MODO_REVISION) {
        const ahoraISO = new Date().toISOString();
        const { data: guardadas, error } = await supabase
          .from("noticias")
          .insert(filas.map((f) => ({ ...f, oculta: true, borrador: true, borrador_desde: ahoraISO })))
          .select("id, categoria, titular, resumen");
        if (error) throw error;
        borradores = (guardadas || []).length;
        try { await avisarBorradores(guardadas || []); } catch (e) { console.error("Error avisando de borradores:", e.message); }
      } else {
        const { data: guardadas, error } = await supabase
          .from("noticias")
          .insert(filas)
          .select("id, categoria, titular, resumen");
        if (error) throw error;
        enviadasTelegram = await publicarEnTelegram(guardadas || []);
      }
    }

    return res.status(200).json({
      ok: true,
      total: filas.length,
      enviadasTelegram,
      borradores,
      encontrados: unicos.length,
      yaGuardadosEnBD: yaGuardados.size,
      nuevosTrasFiltro: nuevos.length,
      gruposUnidos: gruposFinales.filter((g) => g.length > 1).length,
      repetidasDescartadas: repetidas.length,
      titularesRepetidos: repetidas.map((i) => nuevos[i] && nuevos[i].titulo),
      titularesDescartadosIA: descartadasIA,
      articulosLeidos,
      errorConsulta: errorExistentes ? errorExistentes.message : null,
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
