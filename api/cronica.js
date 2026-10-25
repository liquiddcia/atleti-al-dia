const Parser = require("rss-parser");
const supabase = require("../lib/supabase");
const fuentes = require("../lib/fuentes");
const { leerArticulo } = require("../lib/leerarticulo");
const { avisarBorradores } = require("../lib/borradores");
const { publicarEnTelegram } = require("../lib/telegram");

// Crónica larga del partido: cuando termina un partido del Atlético, junta las crónicas que han
// publicado los medios y escribe UNA crónica propia de 800-1.200 palabras. Solo se hace una vez por
// partido (se apunta en titulo_original como "cronica:ID"). cron-job.org puede llamarla cada 20-30 min.
const MODEL = "claude-haiku-4-5-20251001";
const parser = new Parser();
const MODO_REVISION = process.env.MODO_REVISION !== "0";

const sinTildes = (t) => String(t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

// Trozos del nombre del rival para reconocerlo en los titulares ("Deportivo", "depor"...)
function trozosRival(equipo) {
  const base = [equipo.shortName, equipo.name].map(sinTildes).join(" ");
  const palabras = base.split(/[^a-z0-9ñ]+/).filter((w) => w.length >= 5 && !["atletico", "madrid", "club", "futbol"].includes(w));
  const trozos = new Set();
  palabras.forEach((w) => { trozos.add(w); trozos.add(w.slice(0, 5)); });
  return [...trozos];
}

module.exports = async function handler(req, res) {
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }
  try {
    if (!process.env.FOOTBALL_DATA_API_KEY) return res.status(200).json({ ok: true, motivo: "falta FOOTBALL_DATA_API_KEY" });
    const rehacer = req.query && req.query.rehacer === "1";
    const dia = (d) => d.toISOString().slice(0, 10);
    const ahora = Date.now();
    const r = await fetch(
      `https://api.football-data.org/v4/teams/78/matches?dateFrom=${dia(new Date(ahora - 2 * 86400000))}&dateTo=${dia(new Date(ahora + 86400000))}`,
      { headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY } }
    );
    if (!r.ok) return res.status(200).json({ ok: true, motivo: "football-data " + r.status });
    const d = await r.json();
    // Partidos terminados en las últimas 36 horas
    const terminados = (d.matches || []).filter(
      (m) => m.status === "FINISHED" && m.score && m.score.fullTime && m.score.fullTime.home != null &&
        ahora - new Date(m.utcDate).getTime() < 36 * 3600 * 1000
    );
    if (!terminados.length) return res.status(200).json({ ok: true, motivo: "ningún partido terminado en las últimas 36 h" });

    const resultado = [];
    for (const m of terminados) {
      const clave = `cronica:${m.id}`;
      if (!rehacer) {
        const { data: ya } = await supabase.from("noticias").select("id").eq("titulo_original", clave).limit(1);
        if (ya && ya.length) { resultado.push({ partido: m.id, motivo: "ya tiene crónica" }); continue; }
      }
      const rival = m.homeTeam.id === 78 ? m.awayTeam : m.homeTeam;
      const trozos = trozosRival(rival);
      const inicio = new Date(m.utcDate).getTime();

      // Busca en las fuentes los artículos posteriores al final del partido que hablan de él
      const feeds = await Promise.allSettled(fuentes.map((f) => parser.parseURL(f.url)));
      const candidatos = [];
      feeds.forEach((fe, i) => {
        if (fe.status !== "fulfilled") return;
        for (const it of fe.value.items.slice(0, 15)) {
          const t = sinTildes(it.title);
          const pub = new Date(it.isoDate || it.pubDate || 0).getTime();
          if (!pub || pub < inicio + 100 * 60000) continue; // solo lo publicado tras el pitido final
          if (!trozos.some((z) => t.includes(z))) continue;
          if (/en directo|minuto a minuto|rueda de prensa|alineacion|once confirmado|previa|convocatoria|en vivo/.test(t)) continue;
          candidatos.push({ titulo: it.title, enlace: it.link, fuente: fuentes[i].nombre, resumen: (it.contentSnippet || "").slice(0, 400) });
        }
      });
      const vistosC = new Set();
      const elegidos = candidatos.filter((c) => { const k = sinTildes(c.titulo).slice(0, 40); if (vistosC.has(k)) return false; vistosC.add(k); return true; }).slice(0, 5);
      const textos = await Promise.all(elegidos.map((c) => leerArticulo(c.enlace)));
      const fuentesTexto = elegidos
        .map((c, i) => ({ c, t: textos[i] }))
        .filter((x) => x.t && x.t.length > 600);
      if (!fuentesTexto.length) { resultado.push({ partido: m.id, motivo: "aún no hay crónicas legibles", candidatos: elegidos.map((c) => c.titulo) }); continue; }

      const local = m.homeTeam.shortName || m.homeTeam.name;
      const visitante = m.awayTeam.shortName || m.awayTeam.name;
      const marcador = `${local} ${m.score.fullTime.home}-${m.score.fullTime.away} ${visitante}`;
      const fecha = new Date(m.utcDate).toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", timeZone: "Europe/Madrid" });
      const comp = (m.competition && m.competition.name) || "";
      const prompt = `Eres el redactor de una web de noticias del Atlético de Madrid. Escribe LA CRÓNICA COMPLETA del partido, con voz propia, a partir de los textos de varios medios que te doy. No escribas el nombre de la web ni de ningún medio.

Datos oficiales del partido: ${marcador}. ${comp}. Jugado el ${fecha}.

Reglas:
- Usa SOLO datos que estén en los textos o en los datos oficiales (goleadores, minutos, cambios, tarjetas, declaraciones, jugadas). No inventes nada. Si los textos no dicen un dato, no lo menciones ni digas que falta.
- Si los textos se contradicen, quédate con lo que cuadra con el marcador oficial.
- Nunca copies frases textuales, ni siquiera declaraciones entre comillas: cuéntalas con tus palabras.
- Extensión del cuerpo: entre 800 y 1.200 palabras, en párrafos cortos (6 a 10 párrafos), con orden cronológico: contexto y once inicial, primera parte, goles y jugadas clave, segunda parte y cambios, final del partido y valoración, declaraciones y lo que viene después.
- Titular propio de máximo 90 caracteres, directo, sin sensacionalismo. Resumen de 1-2 frases de máximo 160 caracteres.

Devuelve SOLO un JSON, sin texto adicional ni backticks:
{"titular": "...", "resumen": "...", "cuerpo": "..."}

Textos de los medios:
${fuentesTexto.map((x, i) => `--- Texto ${i + 1} ---\n${x.t.slice(0, 5000)}`).join("\n\n")}`;

      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-api-key": process.env.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01" },
        body: JSON.stringify({ model: MODEL, max_tokens: 4000, messages: [{ role: "user", content: prompt }] }),
      });
      if (!resp.ok) { resultado.push({ partido: m.id, motivo: "API " + resp.status }); continue; }
      const datos = await resp.json();
      const txt = datos.content.map((b) => b.text || "").join("");
      let nota;
      try { nota = JSON.parse(txt.replace(/```json|```/g, "").trim()); } catch (e) { resultado.push({ partido: m.id, motivo: "respuesta no válida" }); continue; }
      if (!nota || !nota.cuerpo) { resultado.push({ partido: m.id, motivo: "sin cuerpo" }); continue; }

      const fila = {
        categoria: m.competition && m.competition.code === "CL" ? "champions" : "liga",
        titular: nota.titular,
        resumen: nota.resumen,
        cuerpo: nota.cuerpo,
        fuentes: [...new Set(fuentesTexto.map((x) => x.c.fuente))].join(", "),
        enlace_original: fuentesTexto[0].c.enlace,
        titulo_original: clave,
        publicado_en: new Date().toISOString(),
      };
      let guardada;
      if (MODO_REVISION) {
        const { data, error } = await supabase.from("noticias")
          .insert({ ...fila, oculta: true, borrador: true, borrador_desde: new Date().toISOString() })
          .select("id, categoria, titular, resumen");
        if (error) throw error;
        guardada = data;
        try { await avisarBorradores(data || []); } catch (e) { console.error("Error avisando de borradores:", e.message); }
      } else {
        const { data, error } = await supabase.from("noticias").insert(fila).select("id, categoria, titular, resumen");
        if (error) throw error;
        guardada = data;
        await publicarEnTelegram(data || []);
      }
      resultado.push({ partido: m.id, marcador, creada: guardada && guardada[0] && guardada[0].id, palabras: String(nota.cuerpo).split(/\s+/).length, textosUsados: fuentesTexto.length });
    }
    return res.status(200).json({ ok: true, resultado });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
