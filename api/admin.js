// api/admin.js
// Panel de revisión de borradores (lo usa /admin.html). Necesita la cabecera
// Authorization: Bearer CRON_SECRET (la clave que escribes al entrar en el panel).
//   GET                                   -> lista los borradores pendientes
//   POST { accion: "guardar",   id, campos }   -> guarda los cambios de un borrador
//   POST { accion: "publicar",  id, campos? }  -> guarda (si hay cambios) y publica un borrador
//   POST { accion: "descartar", id }           -> descarta un borrador (queda oculto para siempre)
//   POST { accion: "publicarTodas" }           -> publica todos los borradores
//   GET ?resumen=1                        -> devuelve el texto del resumen del día, listo para pegar en WhatsApp

const supabase = require("../lib/supabase");
const { publicarBorradores, HORAS_AUTOPUBLICAR } = require("../lib/borradores");

const SITIO = "https://diariocolchonero.com";
const MAX_RESUMEN = 6;

// Mismo resumen que se envía a las 21:00 por Telegram: el resultado del partido primero
// (si lo hay) y después las noticias más votadas de las últimas 24 horas.
async function textoResumen() {
  const desde = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const { data: resultados } = await supabase
    .from("noticias")
    .select("id, titular")
    .eq("oculta", false)
    .gte("publicado_en", desde)
    .like("titulo_original", "final partido %")
    .order("publicado_en", { ascending: false })
    .limit(2);
  const { data: populares, error } = await supabase
    .from("noticias")
    .select("id, titular")
    .eq("oculta", false)
    .gte("publicado_en", desde)
    .order("likes", { ascending: false })
    .order("publicado_en", { ascending: false })
    .limit(MAX_RESUMEN);
  if (error) throw error;

  const vistos = new Set();
  const lista = [...(resultados || []), ...(populares || [])]
    .filter((n) => (vistos.has(n.id) ? false : (vistos.add(n.id), true)))
    .slice(0, MAX_RESUMEN);
  if (!lista.length) return "";

  const lineas = lista.map((n, i) => `${i + 1}. ${n.titular}\n${SITIO}/api/noticia?id=${n.id}`);
  return (
    `📰 LO MÁS IMPORTANTE DEL ATLETI HOY\n\n` +
    lineas.join("\n\n") +
    `\n\n🔴⚪ Todas las noticias en ${SITIO}\n📲 Telegram: t.me/diariocolchonero`
  );
}

const CAMPOS_EDITABLES = ["titular", "resumen", "cuerpo", "imagen_url", "video_url"];

function limpiarCampos(campos) {
  const salida = {};
  if (!campos || typeof campos !== "object") return salida;
  for (const c of CAMPOS_EDITABLES) {
    if (typeof campos[c] !== "string") continue;
    const v = campos[c].trim();
    if (c === "imagen_url" || c === "video_url") salida[c] = v || null;
    else if (v) salida[c] = v;
  }
  return salida;
}

async function guardarCambios(id, campos) {
  const cambios = limpiarCampos(campos);
  if (!Object.keys(cambios).length) return;
  const { error } = await supabase.from("noticias").update(cambios).eq("id", id).eq("borrador", true);
  if (error) throw error;
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "Clave incorrecta" });
  }

  try {
    if (req.method === "GET" && req.query && req.query.resumen) {
      return res.status(200).json({ ok: true, texto: await textoResumen() });
    }

    if (req.method === "GET") {
      const { data, error } = await supabase
        .from("noticias")
        .select("id, categoria, titular, resumen, cuerpo, imagen_url, video_url, fuentes, enlace_original, borrador_desde")
        .eq("borrador", true)
        .order("id", { ascending: false });
      if (error) throw error;
      return res.status(200).json({ ok: true, horasAutopublicar: HORAS_AUTOPUBLICAR, borradores: data || [] });
    }

    if (req.method !== "POST") return res.status(405).json({ error: "Método no permitido" });

    const cuerpo = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
    const accion = cuerpo.accion;
    const id = parseInt(cuerpo.id, 10);

    if (accion === "guardar") {
      if (!id) return res.status(400).json({ error: "Falta id" });
      await guardarCambios(id, cuerpo.campos);
      return res.status(200).json({ ok: true });
    }

    if (accion === "publicar") {
      if (!id) return res.status(400).json({ error: "Falta id" });
      await guardarCambios(id, cuerpo.campos);
      const r = await publicarBorradores({ ids: [id] });
      return res.status(200).json({ ok: true, ...r });
    }

    if (accion === "descartar") {
      if (!id) return res.status(400).json({ error: "Falta id" });
      const { error } = await supabase.from("noticias").update({ borrador: false }).eq("id", id).eq("borrador", true);
      if (error) throw error;
      return res.status(200).json({ ok: true });
    }

    if (accion === "publicarTodas") {
      const r = await publicarBorradores({});
      return res.status(200).json({ ok: true, ...r });
    }

    return res.status(400).json({ error: "Acción no válida" });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
