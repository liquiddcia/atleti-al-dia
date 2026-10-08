// api/limpiar.js
// Busca noticias repetidas sobre el mismo tema y las oculta (no las borra).
// Por defecto SOLO MUESTRA lo que ocultaría (prueba en seco). Para ocultarlas de verdad:
//   /api/limpiar?aplicar=1
// Opcional: /api/limpiar?max=300  (cuántas noticias recientes revisar, por defecto 300)
// Se llama con la cabecera Authorization: Bearer CRON_SECRET (por ejemplo desde cron-job.org).
// De cada grupo de noticias repetidas se queda la más antigua (la que ya se envió a Telegram,
// así sus enlaces compartidos siguen funcionando). Las demás se marcan como ocultas.

const supabase = require("../lib/supabase");

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
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9ñ\s]/g, " ");
  const vacias = new Set([...PALABRAS_VACIAS].map((p) => p.normalize("NFD").replace(/[\u0300-\u036f]/g, "")));
  return new Set(limpio.split(/\s+/).filter((w) => w.length > 3 && !vacias.has(w)));
}

// Mismo criterio que el filtro de api/actualizar.js: al menos 3 palabras clave en común
// y que sean el 60 % o más del titular más corto.
function sonParecidos(a, b) {
  const A = palabrasClave(a);
  const B = palabrasClave(b);
  if (!A.size || !B.size) return false;
  let comunes = 0;
  A.forEach((w) => { if (B.has(w)) comunes++; });
  return comunes >= 3 && comunes / Math.min(A.size, B.size) >= 0.6;
}

module.exports = async function handler(req, res) {
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }

  try {
    const aplicar = req.query && req.query.aplicar === "1";
    const max = Math.min(parseInt(req.query && req.query.max, 10) || 300, 1000);

    const { data, error } = await supabase
      .from("noticias")
      .select("id, titular, likes, categoria")
      .eq("oculta", false)
      .order("id", { ascending: false })
      .limit(max);
    if (error) throw error;

    // De la más antigua a la más reciente: la primera de cada tema es la que se queda
    const noticias = (data || []).slice().sort((a, b) => a.id - b.id);
    const grupos = []; // { conservar: noticia, repetidas: [noticia] }

    for (const n of noticias) {
      const grupo = grupos.find((g) => sonParecidos(g.conservar.titular, n.titular));
      if (grupo) {
        grupo.repetidas.push(n);
      } else {
        grupos.push({ conservar: n, repetidas: [] });
      }
    }

    const conRepetidas = grupos.filter((g) => g.repetidas.length > 0);
    const idsAOcultar = conRepetidas.flatMap((g) => g.repetidas.map((x) => x.id));

    if (aplicar && idsAOcultar.length > 0) {
      const { error: errorUpdate } = await supabase
        .from("noticias")
        .update({ oculta: true })
        .in("id", idsAOcultar);
      if (errorUpdate) throw errorUpdate;
    }

    return res.status(200).json({
      ok: true,
      modo: aplicar ? "APLICADO: noticias ocultadas" : "PRUEBA EN SECO: no se ha ocultado nada (añade ?aplicar=1)",
      revisadas: noticias.length,
      gruposConRepetidas: conRepetidas.length,
      ocultadas: idsAOcultar.length,
      ids: idsAOcultar.sort((a, b) => a - b),
      detalle: conRepetidas.map((g) => ({
        conservo: `${g.conservar.id} · ${g.conservar.titular}`,
        oculto: g.repetidas.map((x) => `${x.id} · ${x.titular}`),
      })),
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
