const supabase = require("../lib/supabase");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Método no permitido" });
  }

  const { id, accion } = req.body || {};
  if (!id || !["dar", "quitar", "vista"].includes(accion)) {
    return res.status(400).json({ error: "Faltan datos (id, accion)" });
  }

  // "vista": suma una apertura de la noticia (no tiene que ver con los me gusta)
  if (accion === "vista") {
    const { data: fila, error: errorFila } = await supabase
      .from("noticias")
      .select("vistas")
      .eq("id", id)
      .single();
    if (errorFila || !fila) {
      return res.status(404).json({ error: "Noticia no encontrada" });
    }
    const { error: errorVista } = await supabase
      .from("noticias")
      .update({ vistas: (fila.vistas || 0) + 1 })
      .eq("id", id);
    if (errorVista) {
      return res.status(500).json({ error: errorVista.message });
    }
    return res.status(200).json({ ok: true });
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
