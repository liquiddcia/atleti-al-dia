// api/partido.js
// Avisos automáticos de partido en el canal de Telegram:
//   1) Un aviso cuando falta como máximo 1 hora para el partido del Atleti.
//   2) Un aviso en el descanso con el marcador (y una noticia en la web con el marcador y los goles, si la fuente los da).
//   3) Un aviso con el resultado cuando el partido termina (y una noticia con el resultado en la web).
// Además refresca la clasificación y el calendario cada 30 minutos en horas de partidos.
// Lo llama cron-job.org cada 5 minutos (con la cabecera Authorization: Bearer CRON_SECRET).
// Variables de entorno: FOOTBALL_DATA_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CRON_SECRET.
// Para no repetir avisos guarda los partidos ya avisados en la tabla "clasificaciones"
// (fila "avisos_partido"), así que no hace falta crear ninguna tabla nueva.

const supabase = require("../lib/supabase");
const { actualizarClasificaciones } = require("../lib/clasificacion");

const SITIO = "https://diariocolchonero.com";
const IMAGEN_AVISO = `${SITIO}/banner.jpg`; // imagen que acompaña a los avisos
const API = "https://api.football-data.org/v4";
const MINUTOS_PREVIA = 70; // avisa cuando faltan entre 0 y 70 minutos
const HORAS_MAX_FINAL = 8; // no avisa de resultados de partidos de hace más de 8 horas

const COMPETICIONES = {
  PD: "LaLiga",
  CL: "Champions League",
  CDR: "Copa del Rey",
  SC: "Supercopa",
};

function esc(t) {
  return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function esAtleti(equipo) {
  const n = String((equipo && (equipo.name || equipo.shortName)) || "").toLowerCase();
  return equipo && (equipo.id === 78 || n.includes("atl"));
}

function nombre(equipo) {
  return esAtleti(equipo) ? "Atlético de Madrid" : (equipo.shortName || equipo.name);
}

function dia(fecha) {
  return fecha.toISOString().slice(0, 10);
}

async function enviarTelegram(texto) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chat) throw new Error("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID");

  // Primero intenta enviarlo con la imagen del banner; si falla, lo manda solo como texto
  try {
    const rf = await fetch(`https://api.telegram.org/bot${token}/sendPhoto`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chat, photo: IMAGEN_AVISO, caption: texto, parse_mode: "HTML" }),
    });
    if (rf.ok) return;
    console.error("sendPhoto falló:", rf.status, (await rf.text()).slice(0, 200));
  } catch (e) {
    console.error("sendPhoto error:", e.message);
  }

  const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text: texto, parse_mode: "HTML", disable_web_page_preview: true }),
  });
  if (!r.ok) {
    const detalle = await r.text();
    throw new Error(`Telegram ${r.status}: ${detalle.slice(0, 200)}`);
  }
}

function mensajePrevia(m) {
  const comp = COMPETICIONES[m.competition && m.competition.code] || (m.competition && m.competition.name) || "";
  const hora = new Date(m.utcDate).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid" });
  return (
    `⚽ <b>¡El Atleti juega en menos de una hora!</b>\n\n` +
    `${esc(nombre(m.homeTeam))} - ${esc(nombre(m.awayTeam))}\n` +
    `🕒 ${hora}h (hora de España)${comp ? ` · ${esc(comp)}` : ""}\n\n` +
    `🔴⚪ Previa y noticias: <a href="${SITIO}">diariocolchonero.com</a>`
  );
}

function mensajeFinal(m) {
  const comp = COMPETICIONES[m.competition && m.competition.code] || (m.competition && m.competition.name) || "";
  const gl = m.score.fullTime.home;
  const gv = m.score.fullTime.away;
  const atletiLocal = esAtleti(m.homeTeam);
  const gAtleti = atletiLocal ? gl : gv;
  const gRival = atletiLocal ? gv : gl;
  const icono = gAtleti > gRival ? "✅" : gAtleti === gRival ? "🤝" : "❌";
  const titulo = gAtleti > gRival ? "¡Victoria del Atleti!" : gAtleti === gRival ? "Empate del Atleti" : "Derrota del Atleti";
  return (
    `${icono} <b>FINAL${comp ? ` · ${esc(comp)}` : ""}</b>\n\n` +
    `${esc(nombre(m.homeTeam))} <b>${gl} - ${gv}</b> ${esc(nombre(m.awayTeam))}\n` +
    `${titulo}\n\n` +
    `📰 Todas las noticias: <a href="${SITIO}">diariocolchonero.com</a>`
  );
}

// Goles del partido (si la fuente de datos los devuelve; en caso contrario, lista vacía)
async function golesDelPartido(id) {
  try {
    const r = await fetch(`${API}/matches/${id}`, { headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY } });
    if (!r.ok) return [];
    const d = await r.json();
    return (Array.isArray(d.goals) ? d.goals : [])
      .filter((g) => g && g.scorer && g.scorer.name && g.minute != null)
      .map((g) => ({
        minuto: g.injuryTime ? `${g.minute}+${g.injuryTime}` : `${g.minute}`,
        jugador: g.scorer.name,
        equipo: g.team && (g.team.shortName || g.team.name) ? (g.team.shortName || g.team.name) : "",
      }));
  } catch (e) {
    console.error("Error pidiendo goles:", e.message);
    return [];
  }
}

function marcadorDescanso(m) {
  const s = m.score || {};
  const ht = s.halfTime && s.halfTime.home != null && s.halfTime.away != null ? s.halfTime : s.fullTime;
  return { gl: ht ? ht.home : null, gv: ht ? ht.away : null };
}

function mensajeDescanso(m, goles) {
  const comp = COMPETICIONES[m.competition && m.competition.code] || (m.competition && m.competition.name) || "";
  const { gl, gv } = marcadorDescanso(m);
  const marcador = gl != null && gv != null ? `<b>${gl} - ${gv}</b>` : "-";
  const lineaGoles = goles.length
    ? `\n\n⚽ Goles:\n` + goles.map((g) => `${esc(g.minuto)}' ${esc(g.jugador)}${g.equipo ? ` (${esc(g.equipo)})` : ""}`).join("\n")
    : "";
  return (
    `⏸ <b>DESCANSO${comp ? ` · ${esc(comp)}` : ""}</b>\n\n` +
    `${esc(nombre(m.homeTeam))} ${marcador} ${esc(nombre(m.awayTeam))}` +
    lineaGoles +
    `\n\n📰 Sigue el partido y las noticias: <a href="${SITIO}">diariocolchonero.com</a>`
  );
}

// Noticia del descanso en la web, solo con datos del partido (sin IA)
async function guardarNoticiaDescanso(m, goles) {
  const clave = `descanso partido ${m.id}`;
  const { data: ya } = await supabase.from("noticias").select("id").eq("titulo_original", clave).maybeSingle();
  if (ya) return false;

  const compNombre = COMPETICIONES[m.competition && m.competition.code] || (m.competition && m.competition.name) || "";
  const { gl, gv } = marcadorDescanso(m);
  if (gl == null || gv == null) return false;
  const local = nombre(m.homeTeam);
  const visitante = nombre(m.awayTeam);

  const titular = `Descanso: ${local} ${gl}-${gv} ${visitante}`;
  const resumen = `Al descanso del partido${compNombre ? ` de ${compNombre}` : ""}, el marcador es ${local} ${gl}-${gv} ${visitante}.`;
  const parrafos = [`Se llega al descanso con el marcador ${local} ${gl}-${gv} ${visitante}${compNombre ? ` en ${compNombre}` : ""}.`];
  if (goles.length) {
    parrafos.push("Goles hasta ahora: " + goles.map((g) => `${g.minuto}' ${g.jugador}${g.equipo ? ` (${g.equipo})` : ""}`).join("; ") + ".");
  } else if (gl + gv === 0) {
    parrafos.push("De momento no se han marcado goles.");
  }
  parrafos.push("El resultado final se publicará en una noticia aparte cuando termine el partido.");

  const { error } = await supabase.from("noticias").insert({
    categoria: m.competition && m.competition.code === "CL" ? "champions" : "liga",
    titular,
    resumen,
    cuerpo: parrafos.join("\n"),
    fuentes: "Diario Colchonero",
    enlace_original: SITIO,
    titulo_original: clave,
    publicado_en: new Date().toISOString(),
  });
  if (error) {
    console.error("Error guardando noticia del descanso:", error.message);
    return false;
  }
  return true;
}

// Guarda en la web una noticia con el resultado final (sin IA, solo con datos del partido),
// para que los días de partido siempre haya una noticia del resultado en la portada y en el resumen.
async function guardarNoticiaResultado(m) {
  const clave = `final partido ${m.id}`;
  const { data: ya } = await supabase.from("noticias").select("id").eq("titulo_original", clave).maybeSingle();
  if (ya) return false;

  const compNombre = COMPETICIONES[m.competition && m.competition.code] || (m.competition && m.competition.name) || "";
  const gl = m.score.fullTime.home;
  const gv = m.score.fullTime.away;
  const atletiLocal = esAtleti(m.homeTeam);
  const gAtleti = atletiLocal ? gl : gv;
  const gRival = atletiLocal ? gv : gl;
  const local = nombre(m.homeTeam);
  const visitante = nombre(m.awayTeam);
  const rival = atletiLocal ? visitante : local;
  const resultado = gAtleti > gRival ? "victoria rojiblanca" : gAtleti === gRival ? "reparto de puntos" : "derrota rojiblanca";
  const verbo = gAtleti > gRival ? "ganó" : gAtleti === gRival ? "empató" : "perdió";
  const fecha = new Date(m.utcDate).toLocaleDateString("es-ES", { day: "numeric", month: "long", timeZone: "Europe/Madrid" });

  const titular = `${local} ${gl}-${gv} ${visitante}: ${resultado}`;
  const resumen = `Final del partido${compNombre ? ` de ${compNombre}` : ""}: ${local} ${gl}-${gv} ${visitante}.`;
  const cuerpo =
    `El Atlético de Madrid ${verbo} ante ${rival} en el partido${compNombre ? ` de ${compNombre}` : ""} disputado el ${fecha}. El resultado final fue ${local} ${gl}-${gv} ${visitante}.\n` +
    `La clasificación y el calendario de la web se actualizan automáticamente tras el partido. Aquí iremos publicando las reacciones y la información posterior.`;

  const { error } = await supabase.from("noticias").insert({
    categoria: m.competition && m.competition.code === "CL" ? "champions" : "liga",
    titular,
    resumen,
    cuerpo,
    fuentes: "Diario Colchonero",
    enlace_original: SITIO,
    titulo_original: clave,
    publicado_en: new Date().toISOString(),
  });
  if (error) {
    console.error("Error guardando noticia del resultado:", error.message);
    return false;
  }
  return true;
}

// Refresca la clasificación y el calendario cada 30 minutos durante las horas de partidos
// (de 13:00 a 02:00, hora de España), para que reflejen también los partidos de otros equipos.
const MINUTOS_REFRESCO_CLASIFICACION = 30;

async function refrescarClasificacionSiToca() {
  const hora = Number(
    new Intl.DateTimeFormat("en-GB", { hour: "numeric", hourCycle: "h23", timeZone: "Europe/Madrid" }).format(new Date())
  );
  if (hora >= 2 && hora < 13) return false;

  const { data: fila } = await supabase
    .from("clasificaciones")
    .select("actualizado_en")
    .eq("competicion", "liga")
    .maybeSingle();
  const ultima = fila && fila.actualizado_en ? new Date(fila.actualizado_en).getTime() : 0;
  if (Date.now() - ultima < MINUTOS_REFRESCO_CLASIFICACION * 60000) return false;

  await actualizarClasificaciones();
  return true;
}

module.exports = async function handler(req, res) {
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }
  if (!process.env.FOOTBALL_DATA_API_KEY) {
    return res.status(500).json({ error: "Falta FOOTBALL_DATA_API_KEY" });
  }

  try {
    const ahora = Date.now();
    const desde = dia(new Date(ahora - 24 * 3600 * 1000));
    const hasta = dia(new Date(ahora + 48 * 3600 * 1000));
    const r = await fetch(`${API}/teams/78/matches?dateFrom=${desde}&dateTo=${hasta}`, {
      headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY },
    });
    if (!r.ok) throw new Error(`football-data.org respondió ${r.status}`);
    const datos = await r.json();
    const partidos = datos.matches || [];

    // Partidos ya avisados
    const { data: fila } = await supabase
      .from("clasificaciones")
      .select("datos")
      .eq("competicion", "avisos_partido")
      .maybeSingle();
    const estado = (fila && fila.datos) || {};
    const previa = Array.isArray(estado.previa) ? estado.previa : [];
    const final = Array.isArray(estado.final) ? estado.final : [];
    const descanso = Array.isArray(estado.descanso) ? estado.descanso : [];

    const enviados = [];
    let hayFinal = false;

    for (const m of partidos) {
      const minutos = (new Date(m.utcDate).getTime() - ahora) / 60000;

      // 1) Aviso previo: falta como máximo 1 hora y todavía no ha empezado
      if (["TIMED", "SCHEDULED"].includes(m.status) && minutos > 0 && minutos <= MINUTOS_PREVIA && !previa.includes(m.id)) {
        await enviarTelegram(mensajePrevia(m));
        previa.push(m.id);
        enviados.push(`previa ${m.id}`);
      }

      // 2) Aviso del descanso: el partido está en el descanso
      if (m.status === "PAUSED" && !descanso.includes(m.id)) {
        const goles = await golesDelPartido(m.id);
        await enviarTelegram(mensajeDescanso(m, goles));
        descanso.push(m.id);
        enviados.push(`descanso ${m.id}`);
        if (await guardarNoticiaDescanso(m, goles)) enviados.push(`noticia descanso ${m.id}`);
      }

      // 3) Aviso de resultado: terminado, con marcador y reciente
      const horasDesde = -minutos / 60;
      if (
        m.status === "FINISHED" &&
        m.score && m.score.fullTime && m.score.fullTime.home != null && m.score.fullTime.away != null &&
        horasDesde <= HORAS_MAX_FINAL &&
        !final.includes(m.id)
      ) {
        await enviarTelegram(mensajeFinal(m));
        final.push(m.id);
        hayFinal = true;
        enviados.push(`final ${m.id}`);
        if (await guardarNoticiaResultado(m)) enviados.push(`noticia ${m.id}`);
      }
    }

    if (enviados.length) {
      const { error } = await supabase.from("clasificaciones").upsert({
        competicion: "avisos_partido",
        datos: { previa: previa.slice(-20), descanso: descanso.slice(-20), final: final.slice(-20) },
        actualizado_en: new Date().toISOString(),
      });
      if (error) console.error("Error guardando avisos_partido:", error.message);
    }

    // Al terminar un partido, refresca clasificación y calendario de la web
    if (hayFinal) {
      try { await actualizarClasificaciones(); } catch (e) { console.error("Error refrescando clasificaciones:", e.message); }
    }

    // Si no se ha refrescado ya por un final de partido, refresca de vez en cuando
    let clasificacionRefrescada = hayFinal;
    if (!hayFinal) {
      try { clasificacionRefrescada = await refrescarClasificacionSiToca(); } catch (e) { console.error("Error refrescando clasificaciones:", e.message); }
    }

    return res.status(200).json({ ok: true, partidos: partidos.length, enviados, clasificacionRefrescada });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
