// lib/telegram.js
// Publica cada noticia nueva en el canal de Telegram de Diario Colchonero.
// Necesita dos variables de entorno en Vercel:
//   TELEGRAM_BOT_TOKEN  -> el token que da @BotFather
//   TELEGRAM_CHAT_ID    -> el canal, por ejemplo @diariocolchonero
// Si faltan, no hace nada (la web sigue funcionando igual).

const SITIO = "https://diariocolchonero.com";

function escapar(texto) {
  return String(texto || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function enviarNoticia(noticia) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chat) return false;

  const enlace = `${SITIO}/categoria.html?cat=${encodeURIComponent(noticia.categoria)}&n=${noticia.id}`;
  const texto =
    `<b>${escapar(noticia.titular)}</b>\n\n` +
    `${escapar(noticia.resumen)}\n\n` +
    `👉 <a href="${enlace}">Leer la noticia completa</a>`;

  const respuesta = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chat,
      text: texto,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });

  if (!respuesta.ok) {
    const detalle = await respuesta.text();
    throw new Error(`Telegram ${respuesta.status}: ${detalle.slice(0, 200)}`);
  }
  return true;
}

// Envía las noticias una a una (de la más antigua a la más reciente) sin
// interrumpir nunca la actualización si Telegram falla.
async function publicarEnTelegram(noticias) {
  let enviadas = 0;
  const ordenadas = [...noticias].sort((a, b) => a.id - b.id);
  for (const noticia of ordenadas) {
    try {
      if (await enviarNoticia(noticia)) enviadas++;
    } catch (e) {
      console.error("Error enviando a Telegram:", e.message);
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return enviadas;
}

module.exports = { publicarEnTelegram };
