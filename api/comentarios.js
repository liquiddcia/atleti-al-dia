const supabase = require("../lib/supabase");

module.exports = async function handler(req, res) {
  if (req.method === "GET") {
    const { noticia_id } = req.query;
    if (!noticia_id) {
      return res.status(400).json({ error: "Falta noticia_id" });
    }

    const { data, error } = await supabase
      .from("comentarios")
      .select("id, nombre, texto, creado_en")
      .eq("noticia_id", noticia_id)
      .order("creado_en", { ascending: false });

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json({ comentarios: data || [] });
  }

  if (req.method === "POST") {
    const { noticia_id, nombre, texto } = req.body || {};
    if (!noticia_id || !nombre || !texto) {
      return res.status(400).json({ error: "Faltan datos" });
    }

    const nombreLimpio = String(nombre).trim().slice(0, 40);
    const textoLimpio = String(texto).trim().slice(0, 500);
    if (!nombreLimpio || !textoLimpio) {
      return res.status(400).json({ error: "Nombre o comentario vacío" });
    }

    const { data, error } = await supabase
      .from("comentarios")
      .insert({ noticia_id, nombre: nombreLimpio, texto: textoLimpio })
      .select("id, nombre, texto, creado_en")
      .single();

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json({ comentario: data });
  }

  return res.status(405).json({ error: "Método no permitido" });
};
