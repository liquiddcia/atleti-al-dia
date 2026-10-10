// lib/previa.js
// Previa propia de cada partido del Atlético, hecha con datos (no reescrita de otro medio):
//   - cómo llegan los dos equipos (sus últimos 5 partidos)
//   - cómo están en la clasificación
//   - los últimos enfrentamientos entre ambos
//   - un análisis y las claves, redactados por la IA SOLO a partir de esos datos
//     y de las noticias que ya hemos publicado en la web.
// Los números los pone el código, no la IA, así que no puede equivocarse con ellos.
// La llama api/partido.js el día antes de cada partido. Si la IA falla, se publica
// igualmente la previa con los datos y un texto de entrada sencillo.

const supabase = require("./supabase");
const { MODEL } = require("./reescribir");

const API = "https://api.football-data.org/v4";
const ID_ATLETI = 78;
const COMPETICIONES = { PD: "LaLiga", CL: "Champions League", CDR: "Copa del Rey", SC: "Supercopa" };

function esAtleti(equipo) {
  const n = String((equipo && (equipo.name || equipo.shortName)) || "").toLowerCase();
  return Boolean(equipo && (equipo.id === ID_ATLETI || n.includes("atl")));
}

function nombre(equipo) {
  return esAtleti(equipo) ? "Atlético de Madrid" : (equipo.shortName || equipo.name);
}

function competicion(m) {
  return COMPETICIONES[m.competition && m.competition.code] || (m.competition && m.competition.name) || "";
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Madrid" });
}

function plural(n, uno, varios) {
  return `${n} ${n === 1 ? uno : varios}`;
}

async function pedir(ruta) {
  const r = await fetch(`${API}${ruta}`, { headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY } });
  if (!r.ok) throw new Error(`football-data.org respondió ${r.status} en ${ruta}`);
  return r.json();
}

function terminado(m) {
  return m && m.status === "FINISHED" && m.score && m.score.fullTime &&
    m.score.fullTime.home != null && m.score.fullTime.away != null;
}

// Resume una lista de partidos terminados vistos desde un equipo (por su id).
// Devuelve los más recientes primero.
function resumirPartidos(partidos, idEquipo, maximo = 5) {
  const lista = (partidos || [])
    .filter(terminado)
    .filter((m) => (m.homeTeam && m.homeTeam.id === idEquipo) || (m.awayTeam && m.awayTeam.id === idEquipo))
    .sort((a, b) => new Date(b.utcDate) - new Date(a.utcDate))
    .slice(0, maximo)
    .map((m) => {
      const local = m.homeTeam.id === idEquipo;
      const gf = local ? m.score.fullTime.home : m.score.fullTime.away;
      const gc = local ? m.score.fullTime.away : m.score.fullTime.home;
      return {
        fecha: m.utcDate,
        competicion: competicion(m),
        marcador: `${nombre(m.homeTeam)} ${m.score.fullTime.home}-${m.score.fullTime.away} ${nombre(m.awayTeam)}`,
        resultado: gf > gc ? "V" : gf === gc ? "E" : "D",
        gf,
        gc,
      };
    });

  const cuenta = (r) => lista.filter((p) => p.resultado === r).length;
  return {
    partidos: lista,
    racha: lista.map((p) => p.resultado).join("-"),
    victorias: cuenta("V"),
    empates: cuenta("E"),
    derrotas: cuenta("D"),
    golesFavor: lista.reduce((s, p) => s + p.gf, 0),
    golesContra: lista.reduce((s, p) => s + p.gc, 0),
  };
}

function filaClasificacion(tabla, equipo) {
  if (!Array.isArray(tabla)) return null;
  const buscado = String(equipo.shortName || equipo.name || "").toLowerCase();
  const fila = tabla.find((f) => {
    const n = String(f.equipo || "").toLowerCase();
    return esAtleti(equipo) ? n.includes("atl") : n === buscado;
  });
  return fila || null;
}

// ---- Texto de cada bloque de datos ----

function lineasForma(f) {
  if (!f.partidos.length) return [];
  return [
    `- Últimos ${f.partidos.length} partidos: ${f.racha} (${plural(f.victorias, "victoria", "victorias")}, ${plural(f.empates, "empate", "empates")} y ${plural(f.derrotas, "derrota", "derrotas")}; ${plural(f.golesFavor, "gol", "goles")} a favor y ${f.golesContra} en contra)`,
    ...f.partidos.map((p) => `- ${fechaCorta(p.fecha)}${p.competicion ? ` · ${p.competicion}` : ""}: ${p.marcador}`),
  ];
}

function lineaClasificacion(nombreEquipo, f) {
  return `- ${nombreEquipo}: ${f.posicion}.º con ${plural(f.pts, "punto", "puntos")} en ${plural(f.pj, "partido", "partidos")} (${plural(f.pg, "victoria", "victorias")}, ${plural(f.pe, "empate", "empates")} y ${plural(f.pp, "derrota", "derrotas")}; ${f.gf} goles a favor y ${f.gc} en contra)`;
}

function lineasAntecedentes(h, rivalNombre) {
  if (!h.partidos.length) return [];
  return [
    `- Últimos ${plural(h.partidos.length, "enfrentamiento", "enfrentamientos")}: ${plural(h.victorias, "victoria", "victorias")} del Atlético de Madrid, ${plural(h.empates, "empate", "empates")} y ${plural(h.derrotas, "victoria", "victorias")} de su rival (${rivalNombre})`,
    ...h.partidos.map((p) => `- ${fechaCorta(p.fecha)}${p.competicion ? ` · ${p.competicion}` : ""}: ${p.marcador}`),
  ];
}

// ---- Redacción con la IA (solo el texto; los datos ya están calculados) ----

async function redactar(datos, titularesRecientes) {
  const prompt = `Eres el redactor de "Diario Colchonero", una web de noticias del Atlético de Madrid.
Escribe la previa de un partido usando ÚNICAMENTE los datos que te doy. Reglas estrictas:
- No inventes nada: ni alineaciones, ni lesionados, ni sancionados, ni declaraciones, ni fichajes, ni estadísticas
  que no estén en los datos. Si un dato no aparece, no lo menciones.
- Puedes apoyarte en las "noticias recientes" (titulares ya publicados en nuestra web) solo para dar contexto,
  y solo si el titular lo dice de forma clara.
- No des un pronóstico de resultado como si fuera un hecho. Puedes valorar quién llega mejor según los datos.
- Tono de prensa deportiva, cercano al aficionado rojiblanco pero sin exagerar. Español de España.
- No repitas las listas de resultados una por una: ya se muestran en la página. Interprétalas.

Datos del partido (JSON):
${JSON.stringify(datos, null, 1)}

Noticias recientes de nuestra web:
${titularesRecientes.map((t) => "- " + t).join("\n") || "(ninguna)"}

Devuelve SOLO un JSON, sin texto adicional ni backticks, con este formato:
{"titular": "máx 90 caracteres, que nombre a los dos equipos",
 "resumen": "1-2 frases, máx 160 caracteres",
 "entrada": "un párrafo de 50-70 palabras que presente el partido: rival, competición, día y hora, y qué hay en juego según la clasificación",
 "analisis": ["párrafo de 70-90 palabras sobre cómo llega el Atlético", "párrafo de 70-90 palabras sobre cómo llega el rival", "párrafo de 60-80 palabras sobre los antecedentes y qué partido cabe esperar"],
 "claves": ["tres claves del partido, cada una en una frase de 15-25 palabras basada en los datos", "...", "..."]}`;

  const respuesta = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({ model: MODEL, max_tokens: 1500, messages: [{ role: "user", content: prompt }] }),
    signal: AbortSignal.timeout(40000),
  });
  if (!respuesta.ok) throw new Error(`Error de la API de Anthropic: ${respuesta.status}`);

  const json = await respuesta.json();
  const texto = json.content.map((b) => b.text || "").join("");
  const r = JSON.parse(texto.replace(/```json|```/g, "").trim());
  if (!r.titular || !r.resumen || !r.entrada) throw new Error("La IA devolvió una previa incompleta");
  return r;
}

// ---- Montaje de la previa completa ----

function montarPrevia({ m, formaAtleti, formaRival, filaAtleti, filaRival, antecedentes, texto }) {
  const local = nombre(m.homeTeam);
  const visitante = nombre(m.awayTeam);
  const rival = esAtleti(m.homeTeam) ? m.awayTeam : m.homeTeam;
  const rivalNombre = nombre(rival);
  const comp = competicion(m);
  const f = new Date(m.utcDate);
  const dia = f.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long", timeZone: "Europe/Madrid" });
  const hora = f.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid" });
  const jornada = m.matchday && m.competition && m.competition.code === "PD" ? `, jornada ${m.matchday}` : "";

  const t = texto || {};
  const titular = String(t.titular || `Previa ${local} - ${visitante}: así llegan los dos equipos`).slice(0, 110);
  const resumen = String(t.resumen || `El Atlético de Madrid se mide a ${rivalNombre} el ${dia} a las ${hora}h. Rachas, clasificación y antecedentes.`).slice(0, 200);
  const entrada = t.entrada ||
    `El Atlético de Madrid ${esAtleti(m.homeTeam) ? "recibe a" : "visita a"} ${rivalNombre} el ${dia} a las ${hora}h (hora de España)${comp ? `, en partido de ${comp}${jornada}` : ""}. Repasamos cómo llegan los dos equipos, su situación en la clasificación y los últimos enfrentamientos entre ambos.`;

  const lineas = [entrada];
  lineas.push("## El partido");
  lineas.push(`- ${local} - ${visitante}`);
  lineas.push(`- ${dia.charAt(0).toUpperCase() + dia.slice(1)}, ${hora}h (hora de España)`);
  if (comp) lineas.push(`- ${comp}${jornada}`);

  const la = lineasForma(formaAtleti);
  if (la.length) lineas.push("## Así llega el Atlético de Madrid", ...la);
  const lr = lineasForma(formaRival);
  if (lr.length) lineas.push(`## Así llega el rival: ${rivalNombre}`, ...lr);

  if (filaAtleti || filaRival) {
    lineas.push("## La clasificación");
    if (filaAtleti) lineas.push(lineaClasificacion("Atlético de Madrid", filaAtleti));
    if (filaRival) lineas.push(lineaClasificacion(rivalNombre, filaRival));
  }

  const lh = lineasAntecedentes(antecedentes, rivalNombre);
  if (lh.length) lineas.push("## Los antecedentes", ...lh);

  const analisis = (Array.isArray(t.analisis) ? t.analisis : []).map((p) => String(p || "").trim()).filter(Boolean);
  if (analisis.length) lineas.push("## El análisis", ...analisis);
  const claves = (Array.isArray(t.claves) ? t.claves : []).map((p) => String(p || "").trim()).filter(Boolean);
  if (claves.length) lineas.push("## Las claves del partido", ...claves.map((c) => `- ${c}`));

  lineas.push("Previa elaborada por Diario Colchonero a partir de los resultados y la clasificación oficiales (datos de football-data.org).");

  // Dentro de un párrafo no puede haber saltos de línea: cada línea es un párrafo
  const cuerpo = lineas.map((l) => String(l).replace(/\s*\n+\s*/g, " ").trim()).join("\n");
  return { titular, resumen, cuerpo };
}

// Genera y guarda la previa de un partido. Devuelve la noticia guardada
// ({ id, categoria, titular, resumen }) o null si ya existía.
async function generarPrevia(m) {
  const clave = `previa partido ${m.id}`;
  const { data: ya } = await supabase.from("noticias").select("id").eq("titulo_original", clave).maybeSingle();
  if (ya) return null;

  const rival = esAtleti(m.homeTeam) ? m.awayTeam : m.homeTeam;

  // Datos de football-data.org: últimos partidos de cada equipo y enfrentamientos entre ambos
  const [pAtleti, pRival, h2h] = await Promise.all([
    pedir(`/teams/${ID_ATLETI}/matches?status=FINISHED`),
    pedir(`/teams/${rival.id}/matches?status=FINISHED`),
    pedir(`/matches/${m.id}/head2head?limit=10`).catch((e) => {
      console.error("Sin antecedentes:", e.message);
      return { matches: [] };
    }),
  ]);
  const formaAtleti = resumirPartidos(pAtleti.matches, ID_ATLETI);
  const formaRival = resumirPartidos(pRival.matches, rival.id);
  const antecedentes = resumirPartidos(h2h.matches, ID_ATLETI);

  // Clasificación ya guardada en la web (solo LaLiga y Champions)
  const codigo = m.competition && m.competition.code;
  const claveTabla = codigo === "PD" ? "liga" : codigo === "CL" ? "champions" : null;
  let filaAtleti = null;
  let filaRival = null;
  if (claveTabla) {
    const { data: fila } = await supabase.from("clasificaciones").select("datos").eq("competicion", claveTabla).maybeSingle();
    const tabla = fila && fila.datos;
    filaAtleti = filaClasificacion(tabla, { id: ID_ATLETI, name: "Atlético" });
    filaRival = filaClasificacion(tabla, rival);
  }

  // Titulares de los últimos 3 días, para que la IA tenga contexto de la actualidad
  const desde = new Date(Date.now() - 72 * 3600 * 1000).toISOString();
  const { data: recientes } = await supabase
    .from("noticias")
    .select("titular, resumen")
    .eq("oculta", false)
    .in("categoria", ["liga", "champions", "previa"])
    .gte("publicado_en", desde)
    .order("publicado_en", { ascending: false })
    .limit(15);
  const titulares = (recientes || []).map((n) => `${n.titular}. ${n.resumen || ""}`.trim());

  let texto = null;
  try {
    texto = await redactar(
      {
        partido: {
          local: nombre(m.homeTeam),
          visitante: nombre(m.awayTeam),
          competicion: competicion(m),
          jornada: m.matchday || null,
          fechaHoraEspana: new Date(m.utcDate).toLocaleString("es-ES", {
            weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid",
          }),
        },
        atletico: { ultimosPartidos: formaAtleti, clasificacion: filaAtleti },
        rival: { nombre: nombre(rival), ultimosPartidos: formaRival, clasificacion: filaRival },
        enfrentamientosAnteriores: antecedentes,
      },
      titulares
    );
  } catch (e) {
    console.error("La IA no pudo redactar la previa; se publica solo con datos:", e.message);
  }

  const previa = montarPrevia({ m, formaAtleti, formaRival, filaAtleti, filaRival, antecedentes, texto });

  const { data: guardada, error } = await supabase
    .from("noticias")
    .insert({
      categoria: "previa",
      titular: previa.titular,
      resumen: previa.resumen,
      cuerpo: previa.cuerpo,
      fuentes: "Diario Colchonero",
      enlace_original: "https://diariocolchonero.com",
      titulo_original: clave,
      publicado_en: new Date().toISOString(),
    })
    .select("id, categoria, titular, resumen")
    .single();
  if (error) throw new Error(`Error guardando la previa: ${error.message}`);
  return guardada;
}

module.exports = { generarPrevia, resumirPartidos, filaClasificacion, montarPrevia };
