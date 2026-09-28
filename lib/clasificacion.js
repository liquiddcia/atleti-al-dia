// lib/clasificacion.js
// Descarga la clasificación de LaLiga y de la fase de liga de la Champions
// desde football-data.org y la guarda en Supabase, para que el frontend
// no tenga que llamar a una API externa directamente ni exponer la clave.

const supabase = require("./supabase");

const FOOTBALL_DATA_URL = "https://api.football-data.org/v4";

async function obtenerClasificacion(codigoCompeticion) {
  const respuesta = await fetch(`${FOOTBALL_DATA_URL}/competitions/${codigoCompeticion}/standings`, {
    headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY },
  });

  if (!respuesta.ok) {
    throw new Error(`football-data.org respondió ${respuesta.status} para ${codigoCompeticion}`);
  }

  const datos = await respuesta.json();
  const tabla = (datos.standings || []).find((s) => s.type === "TOTAL");
  if (!tabla) return [];

  return tabla.table.map((fila) => ({
    posicion: fila.position,
    equipo: fila.team.shortName || fila.team.name,
    pj: fila.playedGames,
    pg: fila.won,
    pe: fila.draw,
    pp: fila.lost,
    gf: fila.goalsFor,
    gc: fila.goalsAgainst,
    dg: fila.goalDifference,
    pts: fila.points,
  }));
}

async function actualizarClasificaciones() {
  if (!process.env.FOOTBALL_DATA_API_KEY) {
    console.warn("FOOTBALL_DATA_API_KEY no configurada: se omite la actualización de clasificaciones");
    return;
  }

  const competiciones = [
    { clave: "liga", codigo: "PD" },
    { clave: "champions", codigo: "CL" },
  ];

  for (const { clave, codigo } of competiciones) {
    try {
      const tabla = await obtenerClasificacion(codigo);
      if (!tabla.length) continue;

      const { error } = await supabase
        .from("clasificaciones")
        .upsert({ competicion: clave, datos: tabla, actualizado_en: new Date().toISOString() });

      if (error) console.error(`Error guardando clasificación de ${clave}:`, error.message);
    } catch (e) {
      console.error(`Error obteniendo clasificación de ${clave}:`, e.message);
    }
  }
}

module.exports = { actualizarClasificaciones };
