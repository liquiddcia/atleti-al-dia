// Llama a la API de Claude para reescribir cada noticia con voz propia,
// a partir únicamente del titular + resumen que da el feed RSS (nunca copiamos
// el artículo original completo).

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";

// Revisa docs.claude.com/en/docs/about-claude/models para el id de modelo
// más reciente si este ya no está disponible cuando despliegues esto.
const MODEL = "claude-sonnet-5";

async function reescribirNoticia({ titulo, resumenOriginal, fuente }) {
  const prompt = `Eres el redactor de "Atleti al Día", una web de noticias del Atlético de Madrid.
Te doy el titular y el resumen de una noticia tal como la publicó un medio. Tu trabajo:

1. Escribe un titular propio (máx 90 caracteres), directo, sin sensacionalismo.
2. Escribe un resumen corto de 1-2 frases para la tarjeta de portada (máx 160 caracteres).
3. Escribe el cuerpo completo de la noticia: 2-3 párrafos cortos, con tus propias palabras.
   Nunca copies frases textuales del original ni menciones el nombre del medio original.
4. Clasifícala en una categoría: "liga", "champions", "fichajes" o "previa".

Devuelve SOLO un JSON con este formato, sin texto adicional ni backticks:
{"titular": "...", "resumen": "...", "cuerpo": "...", "categoria": "..."}

Titular original: ${titulo}
Resumen original: ${resumenOriginal}
Medio original: ${fuente}`;

  const respuesta = await fetch(ANTHROPIC_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": process.env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 400,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!respuesta.ok) {
    throw new Error(`Error de la API de Anthropic: ${respuesta.status}`);
  }

  const datos = await respuesta.json();
  const texto = datos.content.map((b) => b.text || "").join("");

  try {
    return JSON.parse(texto.replace(/```json|```/g, "").trim());
  } catch (e) {
    // Si el modelo no devolvió JSON limpio, se descarta esta noticia
    // en vez de romper toda la actualización.
    return null;
  }
}

module.exports =
