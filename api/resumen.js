// api/resumen.js
// Envía a tu Telegram privado un resumen con las noticias más importantes de las
// últimas 24 horas, en texto plano (los enlaces se ven al reenviarlo a WhatsApp).
// Lo llama cron-job.org cada día a las 21:00.
// Variables de entorno: TELEGRAM_BOT_TOKEN y TELEGRAM_RESUMEN_CHAT_ID (tu id numérico).

const supabase = require("../lib/supabase");

const SITIO = "https://diariocolchonero.com";
const MAX_NOTICIAS = 6;

function construirMensaje(noticias) {
  const lineas = noticias.map(
    (n, i) =>
      `${i + 1}. ${n.titular}\n${SITIO}/categoria.html?n=${n.id}`
  );
  return (
    `📰 LO MÁS IMPORTANTE DEL ATLETI HOY\n\n` +
    lineas.join("\n\n") +
    `\n\n🔴⚪ Todas las noticias en ${SITIO}\n📲 Telegram: t.me/diariocolchonero\n📲 WhatsApp: https://whatsapp.com/channel/0029VbDayGCF1YlZa2aj5j0J`
  );
}

module.exports = async function handler(req, res) {
  const secreto = req.headers.authorization;
  if (secreto !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: "No autorizado" });
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.TELEGRAM_RESUMEN_CHAT_ID;
  if (!token || !chat) {
    return res.status(500).json({ error: "Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_RESUMEN_CHAT_ID" });
  }

  try {
    const desde = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    // Los días de partido, la noticia del resultado va siempre la primera del resumen
    const { data: resultados } = await supabase
      .from("noticias")
      .select("id, categoria, titular, likes, publicado_en")
      .eq("oculta", false)
      .gte("publicado_en", desde)
      .like("titulo_original", "final partido %")
      .order("publicado_en", { ascending: false })
      .limit(2);

    const { data: populares, error } = await supabase
      .from("noticias")
      .select("id, categoria, titular, likes, publicado_en")
      .eq("oculta", false)
      .gte("publicado_en", desde)
      .order("likes", { ascending: false })
      .order("publicado_en", { ascending: false })
      .limit(MAX_NOTICIAS);

    if (error) throw error;

    const vistos = new Set();
    const data = [...(resultados || []), ...(populares || [])]
      .filter((n) => (vistos.has(n.id) ? false : (vistos.add(n.id), true)))
      .slice(0, MAX_NOTICIAS);

    if (!data || data.length === 0) {
      return res.status(200).json({ ok: true, enviado: false, motivo: "Sin noticias en las últimas 24 horas" });
    }

    const respuesta = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chat,
        text: construirMensaje(data),
        disable_web_page_preview: true,
      }),
    });

    if (!respuesta.ok) {
      const detalle = await respuesta.text();
      throw new Error(`Telegram ${respuesta.status}: ${detalle.slice(0, 200)}`);
    }

    return res.status(200).json({ ok: true, enviado: true, noticias: data.length });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
};
