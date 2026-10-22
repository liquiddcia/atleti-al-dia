// Llama a la API de Claude para reescribir cada noticia con voz propia,
// a partir del titular + resumen del feed RSS y, si se ha podido leer, del texto del artículo
// original (solo como fuente de datos: nunca se copia ni se publica el artículo original).

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";

// Revisa docs.claude.com/en/docs/about-claude/models para el id de modelo
// más reciente si este ya no está disponible cuando despliegues esto.
const MODEL = "claude-sonnet-5";

async function reescribirNoticia({ titulo, resumenOriginal, fuente, recientes = [], contexto = "", publicado = "", textoArticulo = "", varias = false }) {
  const ahoraTexto = new Date().toLocaleString("es-ES", {
    weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid",
  });
  const prompt = `Eres el redactor de una web de noticias del Atlético de Madrid. Nunca escribas el nombre de la web
ni el de ningún medio dentro del titular, el resumen o el cuerpo.
Fecha y hora actuales: ${ahoraTexto} (hora de España).
Fecha de publicación original de esta noticia: ${publicado || "desconocida"}.
Te doy el titular y el resumen de una noticia tal como la publicó un medio y, si está disponible, el
texto del artículo original. Sé estrictamente fiel a esos datos: no inventes, cambies ni mezcles
nombres de equipos, jugadores o resultados que no aparezcan en el titular, el resumen o el texto del
artículo. Si el titular alude a alguien sin nombrarlo (por ejemplo "un delantero" o "un central") y el
texto del artículo dice quién es, escribe su nombre. Si el texto no lo dice, no lo adivines, y tampoco escribas frases que afirmen que un dato no se ha dado o no se ha detallado (como "no se detallaron los nombres" o "no se han facilitado"): si no tienes el dato, simplemente no lo menciones. Si el contenido no trata claramente sobre el Atlético
de Madrid (por ejemplo, es sobre otro equipo o selección y solo lo menciona de pasada), responde
únicamente con: {"descartar": true}

Descarta también (responde {"descartar": true}) si cuenta el mismo hecho o rumor, o casi lo mismo, que
alguno de estos titulares ya publicados, sin aportar un dato nuevo importante. Si aporta información nueva
relevante (un dato, una declaración distinta, un desarrollo), no la descartes. Descarta también si es solo
otra parte, opinión o enfoque de una declaración, rueda de prensa o entrevista de la misma persona que ya
está cubierta en esos titulares, o si habla del mismo tema que uno de ellos.
Titulares ya publicados:
${recientes.slice(0, 100).map((t) => "- " + t).join("\n") || "(ninguno)"}

Partidos del Atlético que YA se han jugado recientemente (con su resultado):
${contexto || "(sin datos)"}
Descarta también (responde {"descartar": true}) si la noticia es una previa, una convocatoria, un anuncio
o un adelanto de alguno de esos partidos ya jugados, o si habla de ellos como si todavía no se hubieran
jugado. Si la noticia habla del resultado o de lo ocurrido en esos partidos, usa solo los datos reales de
arriba y del titular, sin inventar nada.

Si sí trata claramente sobre el Atlético de Madrid, tu trabajo:

1. Escribe un titular propio (máx 90 caracteres), directo, sin sensacionalismo.
2. Escribe un resumen corto de 1-2 frases para la tarjeta de portada (máx 160 caracteres).
3. Escribe el cuerpo completo de la noticia con tus propias palabras. Si hay texto del artículo,
   aprovecha sus datos (nombres, cifras, fechas, motivos, contexto) y escribe 3-4 párrafos cortos;
   si no lo hay, 2-3 párrafos cortos. Nunca copies frases textuales del original (ni siquiera
   declaraciones entre comillas: cuéntalas con tus palabras) ni menciones el nombre del medio original.
4. Clasifícala en una categoría, la que mejor encaje: "liga" (partidos y actualidad de LaLiga
   del primer equipo masculino), "champions" (Champions League), "previa" (análisis o previa de
   un próximo partido del primer equipo masculino), "fichajes" (mercado de fichajes), "clasificacion"
   (tabla, puestos, rachas del primer equipo masculino), "filial" (Atlético Madrileño, el equipo
   filial/segundo equipo) o "femenino" (Atlético de Madrid Femenino).
   IMPORTANTE: si la noticia trata sobre el Atlético de Madrid Femenino o la Liga F, clasifícala
   SIEMPRE como "femenino", aunque sea sobre un partido de liga o una previa. Si trata sobre el
   Atlético Madrileño (filial), clasifícala SIEMPRE como "filial", aunque sea sobre un partido de
   liga. Las categorías "liga", "previa" y "clasificacion" son EXCLUSIVAS del primer equipo masculino.

Devuelve SOLO un JSON con este formato, sin texto adicional ni backticks:
{"titular": "...", "resumen": "...", "cuerpo": "...", "categoria": "..."}

${varias ? `IMPORTANTE: lo que sigue reúne varias noticias de distintos medios sobre lo mismo (el mismo hecho, o la
misma persona hablando en el mismo acto o entrevista). Júntalo todo en UNA sola noticia completa, de 4-5
párrafos cortos, ordenada y sin repetir datos, con todos los temas que se tratan. No la dividas ni
menciones que viene de varias fuentes.
` : ""}Titular original: ${titulo}
Resumen original: ${resumenOriginal}
Medio original: ${fuente}
Texto del artículo original (solo como fuente de datos; no lo copies):
${textoArticulo || "(no disponible)"}`;

  const respuesta = await fetch(ANTHROPIC_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: varias ? 2000 : 1400,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!respuesta.ok) {
    const detalle = await respuesta.text();
    console.error(`Error de la API de Anthropic: ${respuesta.status}`, detalle);
    throw new Error(`Error de la API de Anthropic: ${respuesta.status}`);
  }

  const datos = await respuesta.json();
  const texto = datos.content.map((b) => b.text || "").join("");

  try {
    return JSON.parse(texto.replace(/```json|```/g, "").trim());
  } catch (e) {
    // Si el modelo no devolvió JSON limpio, se descarta esta noticia
    // en vez de romper toda la actualización.
    console.error("No se pudo parsear la respuesta de la IA:", texto);
    return null;
  }
}

module.exports = { reescribirNoticia };
