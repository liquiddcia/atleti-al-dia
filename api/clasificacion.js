// api/clasificacion.js
//   GET                -> clasificaciones y calendario guardados en Supabase
//   GET ?vivo=1        -> el partido del Atleti que se está jugando (o que va a empezar / acaba de terminar),
//                         con su marcador. Solo consulta la fuente de datos cuando hay un partido cerca,
//                         y guarda la respuesta unos segundos para no pasarse del límite de peticiones.
const supabase = require("../lib/supabase");

const API = "https://api.football-data.org/v4";
const ID_ATLETI = 78;
const ANTES_MIN = 40; // desde 40 minutos antes del inicio
const DESPUES_HORAS = 4; // hasta 4 horas después del inicio
const CACHE_MS = 45 * 1000;

let cacheVivo = { t: 0, valor: null };

function esAtleti(equipo) {
  const n = String((equipo && (equipo.name || equipo.shortName)) || "").toLowerCase();
  return !!equipo && (equipo.id === ID_ATLETI || n.includes("atl"));
}

function dibujarEquipo(equipo) {
  const atleti = esAtleti(equipo);
  return {
    nombre: atleti ? "Atlético de Madrid" : (equipo.shortName || equipo.name),
    escudo: atleti ? "https://crests.football-data.org/78.png" : (equipo.crest || ""),
  };
}

function diaISO(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

async function pedir(ruta) {
  const r = await fetch(`${API}${ruta}`, { headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY } });
  if (!r.ok) throw new Error(`football-data ${r.status}`);
  return r.json();
}

async function golesDelPartido(id) {
  try {
    const d = await pedir(`/matches/${id}`);
    return (Array.isArray(d.goals) ? d.goals : [])
      .filter((g) => g && g.scorer && g.scorer.name && g.minute != null)
      .map((g) => ({
        minuto: g.injuryTime ? `${g.minute}+${g.injuryTime}` : `${g.minute}`,
        jugador: g.scorer.name,
        equipo: g.team && (g.team.shortName || g.team.name) ? (g.team.shortName || g.team.name) : "",
      }));
  } catch (e) {
    return [];
  }
}

async function calcularPartidoVivo() {
  if (!process.env.FOOTBALL_DATA_API_KEY) return null;
  const ahora = Date.now();

  // 1) Mira en Supabase (gratis) si hay algún partido cerca; si no, no se molesta a la fuente de datos
  const { data: fila } = await supabase
    .from("clasificaciones")
    .select("datos")
    .eq("competicion", "calendario")
    .maybeSingle();
  const tabla = Array.isArray(fila && fila.datos) ? fila.datos : [];
  const hayCerca = tabla.some((p) => {
    const t = new Date(p.fecha).getTime();
    return ahora - t > -ANTES_MIN * 60000 && ahora - t < DESPUES_HORAS * 3600000;
  });
  if (!hayCerca) return null;

  // 2) Pide a la fuente de datos los partidos de ayer a mañana
  const lista = await pedir(
    `/teams/${ID_ATLETI}/matches?dateFrom=${diaISO(ahora - 86400000)}&dateTo=${diaISO(ahora + 86400000)}`
  );
  const partidos = Array.isArray(lista.matches) ? lista.matches : [];
  const m = partidos.find((p) => {
    if (p.status === "POSTPONED" || p.status === "CANCELLED") return false;
    const t = new Date(p.utcDate).getTime();
    return ahora - t > -ANTES_MIN * 60000 && ahora - t < DESPUES_HORAS * 3600000;
  });
  if (!m) return null;

  const enJuego = m.status === "IN_PLAY" || m.status === "PAUSED" || m.status === "LIVE";
  const ft = (m.score && m.score.fullTime) || {};
  const ht = (m.score && m.score.halfTime) || {};
  let gl = ft.home != null ? ft.home : ht.home;
  let gv = ft.away != null ? ft.away : ht.away;
  if (gl == null) gl = enJuego || m.status === "FINISHED" ? 0 : null;
  if (gv == null) gv = enJuego || m.status === "FINISHED" ? 0 : null;

  const hayGoles = (gl || 0) + (gv || 0) > 0;
  const goles = hayGoles ? await golesDelPartido(m.id) : [];

  return {
    id: m.id,
    estado: m.status,
    inicio: m.utcDate,
    competicion: ({ PD: "LaLiga", CL: "Champions League", CDR: "Copa del Rey", SC: "Supercopa" })[m.competition && m.competition.code] || (m.competition && m.competition.name) || "",
    local: dibujarEquipo(m.homeTeam),
    visitante: dibujarEquipo(m.awayTeam),
    golesLocal: gl,
    golesVisitante: gv,
    minuto: m.minute != null ? m.minute : null,
    extra: m.injuryTime != null ? m.injuryTime : null,
    goles,
  };
}

async function partidoVivo() {
  if (Date.now() - cacheVivo.t < CACHE_MS) return cacheVivo.valor;
  let valor = null;
  try {
    valor = await calcularPartidoVivo();
  } catch (e) {
    console.error("Error en marcador en vivo:", e.message);
    valor = cacheVivo.valor; // si falla, se queda con lo último que había
  }
  cacheVivo = { t: Date.now(), valor };
  return valor;
}

module.exports = async function handler(req, res) {
  if (req.query && req.query.vivo) {
    const partido = await partidoVivo();
    res.setHeader("Cache-Control", "s-maxage=30, stale-while-revalidate=30");
    return res.status(200).json({ ok: true, partido });
  }

  const { data, error } = await supabase
    .from("clasificaciones")
    .select("competicion, datos, actualizado_en");

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  const resultado = {};
  (data || []).forEach((fila) => {
    resultado[fila.competicion] = { tabla: fila.datos, actualizado_en: fila.actualizado_en };
  });

  res.setHeader("Cache-Control", "s-maxage=300");
  return res.status(200).json(resultado);
};
