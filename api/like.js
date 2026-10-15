// api/like.js  (une "me gusta / lecturas" y "comentarios" en una sola función)
//   POST /api/like        {id, accion: dar|quitar|vista}   -> me gusta y lecturas
//   GET  /api/comentarios?noticia_id=ID                    -> lista de comentarios
//   POST /api/comentarios {noticia_id, nombre, texto}      -> añade un comentario
// /api/comentarios se redirige aquí desde vercel.json (la dirección pública no cambia).
const supabase = require("../lib/supabase");

async function comentarios(req, res) {
  if (req.method === "GET") {
    const { noticia_id } = req.query || {};
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
}

async function likes(req, res) {
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
}

module.exports = async function handler(req, res) {
  const body = req.body || {};
  // Es de comentarios si viene de la redirección (?tipo=comentarios), si es un GET,
  // o si el cuerpo trae noticia_id y no una acción de me gusta
  const esComentarios =
    (req.query && req.query.tipo === "comentarios") ||
    req.method === "GET" ||
    (body.noticia_id && !body.accion);
  return esComentarios ? comentarios(req, res) : likes(req, res);
};
