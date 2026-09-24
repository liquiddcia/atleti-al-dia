// Fuentes RSS que se rastrean en busca de noticias del Atlético de Madrid.
// Google News RSS ya agrega decenas de medios (Marca, AS, Mundo Deportivo, ESPN, etc.)
// filtrando por el término de búsqueda, así que es la fuente principal y más fiable.
// Puedes añadir feeds RSS propios de un medio concreto si tienen uno público.

module.exports = [
  {
    nombre: "Google News — Atlético de Madrid",
    url: "https://news.google.com/rss/search?q=%22Atl%C3%A9tico%20de%20Madrid%22%20when:1d&hl=es-419&gl=ES&ceid=ES:es-419",
  },
  {
    nombre: "Google News — Simeone",
    url: "https://news.google.com/rss/search?q=Simeone%20Atl%C3%A9tico&hl=es-419&gl=ES&ceid=ES:es-419",
  },
  // Ejemplo de cómo añadir el feed propio de un medio si lo tiene disponible:
  // { nombre: "AS - Atlético", url: "https://as.com/rss/futbol/equipos/atletico.xml" },
];
