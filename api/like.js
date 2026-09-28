const supabase = require("../lib/supabase");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Método no permitido" });
  }

  const { id, accion } = req.body || {};
  if (!id || !["dar", "quitar"].includes(accion)) {
    return res.status(400).json({ error: "Faltan datos (id, accion)" });
  }

  const { data: actual, error: errorLectura } = await supabase
    .from("noticias")
    .select("likes")
    .eq("id", id)
    .single();

  if (errorLectura || !actual) {
    return res.status(404).json({ error: "Noticia no encontrada" });
  }

  const nuevoValor = Math.max(0, (actual.likes || 0) + (accion === "dar" ? 1 : -1));

  const { error: errorEscritura } = await supabase
    .from("noticias")
    .update({ likes: nuevoValor })
    .eq("id", id);

  if (errorEscritura) {
    return res.status(500).json({ error: errorEscritura.message });
  }

  return res.status(200).json({ ok: true, likes: nuevoValor });
};
