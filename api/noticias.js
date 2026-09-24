const { kv } = require("@vercel/kv");

module.exports = async function handler(req, res) {
  const datos = (await kv.get("noticias-atleti")) || {
    actualizado: null,
    noticias: [],
  };
  res.setHeader("Cache-Control", "s-maxage=300"); // caché de 5 min en el borde
  return res.status(200).json(datos);
};
