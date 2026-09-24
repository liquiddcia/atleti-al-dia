// lib/fuentes.js
// Lista de medios de los que recogemos noticias del Atlético de Madrid.
// Usamos el buscador RSS de Google News filtrado por cada medio ("site:dominio.com"),
// así no dependemos de que cada periódico tenga su propio feed RSS.

const medios = [
  // --- General ---
  { nombre: "Google News – Atlético de Madrid", url: "https://news.google.com/rss/search?q=%22Atl%C3%A9tico%20de%20Madrid%22&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Google News – Simeone", url: "https://news.google.com/rss/search?q=Simeone%20Atl%C3%A9tico&hl=es&gl=ES&ceid=ES:es" },

  // --- Web oficial ---
  { nombre: "Web oficial Atlético de Madrid", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:atleticodemadrid.com&hl=es&gl=ES&ceid=ES:es" },

  // --- Prensa deportiva nacional ---
  { nombre: "Marca", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:marca.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "AS", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:as.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Mundo Deportivo", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:mundodeportivo.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "El Desmarque", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:eldesmarque.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Estadio Deportivo", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:estadiodeportivo.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "OKDiario Deportes", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:okdiario.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Relevo", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:relevo.com&hl=es&gl=ES&ceid=ES:es" },

  // --- Generalistas con sección de deportes ---
  { nombre: "El País", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:elpais.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "El Mundo", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:elmundo.es&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "ABC", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:abc.es&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "20minutos", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:20minutos.es&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Telemadrid", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:telemadrid.es&hl=es&gl=ES&ceid=ES:es" },

  // --- Radio y TV ---
  { nombre: "Cadena SER", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:cadenaser.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "COPE", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:cope.es&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Onda Cero", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:ondacero.es&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "El Chiringuito", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:elchiringuitotv.com&hl=es&gl=ES&ceid=ES:es" },

  // --- Fichajes y rumores ---
  { nombre: "Fichajes.net", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:fichajes.net&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Tribuna.com", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:tribuna.com&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Transfermarkt", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:transfermarkt.es&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Fabrizio Romano", url: "https://news.google.com/rss/search?q=Fabrizio+Romano+Atl%C3%A9tico+de+Madrid&hl=es&gl=ES&ceid=ES:es" },

  // --- Blogs y medios de aficionados ---
  { nombre: "Atleti & Co", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:atleticodemadrid.blog&hl=es&gl=ES&ceid=ES:es" },
  { nombre: "Esto es Atleti", url: "https://news.google.com/rss/search?q=Atl%C3%A9tico+de+Madrid+site:estoesatleti.es&hl=es&gl=ES&ceid=ES:es" },

  // --- En inglés ---
  { nombre: "Into the Calderón", url: "https://news.google.com/rss/search?q=Atletico+Madrid+site:intothecalderon.com&hl=en&gl=US&ceid=US:en" },
  { nombre: "Football España", url: "https://news.google.com/rss/search?q=Atletico+Madrid+site:footballespana.net&hl=en&gl=US&ceid=US:en" },
  { nombre: "The Athletic", url: "https://news.google.com/rss/search?q=Atletico+Madrid+site:theathletic.com&hl=en&gl=US&ceid=US:en" },
  { nombre: "ESPN", url: "https://news.google.com/rss/search?q=Atletico+Madrid+site:espn.com&hl=en&gl=US&ceid=US:en" },
  { nombre: "Sky Sports", url: "https://news.google.com/rss/search?q=Atletico+Madrid+site:skysports.com&hl=en&gl=US&ceid=US:en" },
];

module.exports = medios;
