// Agrupa las noticias nuevas que cuentan lo mismo (mismo hecho, o la misma persona hablando en el
// mismo acto: rueda de prensa, entrevista...) para publicarlas como UNA sola noticia, y detecta las
// que solo repiten algo ya publicado. Si falla la llamada, cada noticia queda sola (no se rompe nada).

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const MODEL = "claude-haiku-4-5-20251001";

async function agruparNoticias(items, recientes = []) {
  const solas = items.map((_, i) => [i]);
  if (items.length < 1) return { grupos: [], repetidas: [] };

  const lista = items
    .map((it, i) => `${i}. [${it.fuente}] ${it.titulo} — ${(it.resumenOriginal || "").slice(0, 220)}`)
    .join("\n");
  const ya = recientes.slice(0, 25).map((t) => "- " + t).join("\n") || "(ninguno)";

  const prompt = `Tienes una lista numerada de noticias nuevas sobre el Atlético de Madrid y una lista de titulares ya publicados en la web.

Tu trabajo:
1. GRUPOS: junta en un mismo grupo las noticias nuevas que cuenten lo mismo o casi lo mismo: el mismo hecho o un hecho muy parecido, el mismo tema o rumor aunque lo enfoquen distinto, la misma persona hablando en el mismo acto (rueda de prensa, entrevista, comparecencia, declaraciones) aunque cada noticia recoja una parte o una opinión distinta, o varias partes de una misma entrevista. Ante la duda entre juntar o no, júntalas. Solo las dejas separadas si de verdad tratan de asuntos distintos (otro día u otro tema sin relación).
2. REPETIDAS: indica los números de las noticias nuevas que repiten algo que YA está en los titulares ya publicados o que hablan de casi lo mismo (misma persona y mismo acto, mismo hecho o mismo tema), salvo que aporten un dato nuevo importante. Ante la duda, márcalas como repetidas.

Cada número de la lista nueva debe aparecer en exactamente un grupo. Responde SOLO con un JSON, sin texto ni backticks, así:
{"grupos": [[0, 2], [1], [3]], "repetidas": [3]}

Noticias nuevas:
${lista}

Titulares ya publicados:
${ya}`;

  try {
    const r = await fetch(ANTHROPIC_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({ model: MODEL, max_tokens: 600, messages: [{ role: "user", content: prompt }] }),
    });
    if (!r.ok) throw new Error("API " + r.status);
    const datos = await r.json();
    const texto = datos.content.map((b) => b.text || "").join("");
    const json = JSON.parse(texto.replace(/```json|```/g, "").trim());

    const usados = new Set();
    const grupos = [];
    for (const g of Array.isArray(json.grupos) ? json.grupos : []) {
      const limpio = (Array.isArray(g) ? g : []).filter(
        (n) => Number.isInteger(n) && n >= 0 && n < items.length && !usados.has(n)
      );
      limpio.forEach((n) => usados.add(n));
      if (limpio.length) grupos.push(limpio);
    }
    items.forEach((_, i) => { if (!usados.has(i)) grupos.push([i]); });

    const repetidas = (Array.isArray(json.repetidas) ? json.repetidas : []).filter(
      (n) => Number.isInteger(n) && n >= 0 && n < items.length
    );
    return { grupos, repetidas };
  } catch (e) {
    console.error("Error agrupando noticias:", e.message);
    return { grupos: solas, repetidas: [] };
  }
}

module.exports = { agruparNoticias };
