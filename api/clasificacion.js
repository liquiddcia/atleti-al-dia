const supabase = require("../lib/supabase");

module.exports = async function handler(req, res) {
  const { data, error } = await supabase
    .from("clasificaciones")
    .select("competicion, datos, actualizado_en");

  if (error) {
    return res.status(500).json({ error: error.message });
  }

  const resultado = {};
  (data || []).forEach((fila) => {
    resultado[fila.competicion] = { tabla: fila.datos, actualizado_en: fila.actualizado_en };
  });

  res.setHeader("Cache-Control", "s-maxage=300");
  return res.status(200).json(resultado);
};
