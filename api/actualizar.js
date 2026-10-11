const Parser = require("rss-parser");
const supabase = require("../lib/supabase");
const fuentes = require("../lib/fuentes");
const { reescribirNoticia } = require("../lib/reescribir");
const { actualizarClasificaciones } = require("../lib/clasificacion");
const { publicarEnTelegram } = require("../lib/telegram");
const { publicarBorradores, avisarBorradores } = require("../lib/borradores");

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
const MAX_NOTICIAS = 6;
// Modo revisión: las noticias nuevas quedan como borradores ocultos hasta que las apruebes
// en /admin.html (o se publican solas pasada 1 hora). Para desactivarlo, pon la variable
// MODO_REVISION=0 en Vercel.
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

    const yaGuardados = new Set((existentes || []).map((n) => n.titulo_original));

    // Titulares de las últimas noticias, para no repetir el mismo tema
    const { data: recientesBD } = await supabase
      .from("noticias")
      .select("titular")
      .order("id", { ascending: false })
      .limit(40);
    const recientes = (recientesBD || []).map((n) => n.titular);

    let descartadasYaGuardadas = 0;
    let descartadasAntiguas = 0;
    let descartadasParecidas = 0;
    const aceptados = [];
    const candidatos = unicos.filter((it) => {
      if (yaGuardados.has(it.titulo.toLowerCase().slice(0, 40))) { descartadasYaGuardadas++; return false; }
      if (esMuyAntigua(it.publicado)) { descartadasAntiguas++; return false; }
      // Descarta si se parece a una noticia reciente o a otra de esta misma tanda
      if (recientes.some((t) => sonParecidos(it.titulo, t)) || aceptados.some((t) => sonParecidos(it.titulo, t))) {
        descartadasParecidas++;
        return false;
      }
      aceptados.push(it.titulo);
      return true;
    });
    const nuevos = candidatos.slice(0, MAX_NOTICIAS);

    const contexto = await partidosYaJugados();

    const reescritas = await Promise.all(
      nuevos.map(async (item) => {
        const resultado = await reescribirNoticia({ ...item, recientes, contexto });
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
    let borradores = 0;
    if (filas.length > 0) {
      const ahoraISO = new Date().toISOString();
      const filasAGuardar = MODO_REVISION
        ? filas.map((f) => ({ ...f, oculta: true, borrador: true, borrador_desde: ahoraISO }))
        : filas;
      const { data: guardadas, error } = await supabase
        .from("noticias")
        .insert(filasAGuardar)
        .select("id, categoria, titular, resumen");
      if (error) throw error;
      if (MODO_REVISION) {
        borradores = (guardadas || []).length;
        await avisarBorradores(guardadas || []).catch((e) =>
          console.error("Error avisando de borradores:", e.message)
        );
      } else {
        enviadasTelegram = await publicarEnTelegram(guardadas || []);
      }
    }

    // Publica los borradores que llevan más de 1 hora sin revisar
    let autopublicadas = 0;
    try {
      autopublicadas = (await publicarBorradores({ soloAntiguos: true })).publicadas;
    } catch (e) {
      console.error("Error autopublicando borradores:", e.message);
    }

    return res.status(200).json({
      ok: true,
      total: filas.length,
      enviadasTelegram,
      borradores,
      autopublicadas,
      encontrados: unicos.length,
      yaGuardadosEnBD: yaGuardados.size,
      nuevosTrasFiltro: nuevos.length,
      descartadasYaGuardadas,
      descartadasAntiguas,
      descartadasParecidas,
      pendientesPorLimite: candidatos.length - nuevos.length,
      leidasPorLaIA: nuevos.length,
      descartadasPorLaIA: nuevos.length - filas.length,
      guardadasEnBD: filas.length,
      errorConsulta: errorExistentes ? errorExistentes.message : null,
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
