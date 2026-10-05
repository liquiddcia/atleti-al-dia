const supabase = require("../lib/supabase");
const { imagenJugador } = require("../lib/jugadores");

module.exports = async function handler(req, res) {
  const { data, error } = await supabase
    .from("noticias")
    .select("id, categoria, titular, resumen, cuerpo, publicado_en, likes, imagen_url")
    .eq("oculta", false)
    .order("publicado_en", { ascending: false })
    .limit(60);

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  const noticias = (data || []).map((n) => ({
    id: n.id,
    categoria: n.categoria,
    titular: n.titular,
    resumen: n.resumen,
    cuerpo: n.cuerpo,
    publicado_en: n.publicado_en,
    likes: n.likes || 0,
    // Prioridad: imagen puesta a mano > imagen del jugador mencionado > (el frontend usa la de la categoría)
    imagen_url: n.imagen_url || imagenJugador(n.titular, n.resumen) || null,
  }));

  res.setHeader("Cache-Control", "s-maxage=300");
  return res.status(200).json({
    actualizado: data && data[0] ? data[0].publicado_en : null,
    noticias,
  });
};
