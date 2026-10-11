// lib/borradores.js
// Modo revisión: las noticias nuevas se guardan como borradores ocultos (borrador = true,
// oculta = true). Se publican cuando las apruebas en /admin.html, o solas pasada
// 1 hora si no las has revisado.
// Columnas necesarias en la tabla "noticias": borrador (boolean) y borrador_desde (timestamptz).

const supabase = require("./supabase");
const { publicarEnTelegram } = require("./telegram");

const SITIO = "https://diariocolchonero.com";
const HORAS_AUTOPUBLICAR = 1;

// Publica borradores: los ids indicados, o todos; con soloAntiguos solo los que llevan
// más de HORAS_AUTOPUBLICAR sin revisar. Después los envía al canal de Telegram.
async function publicarBorradores({ ids = null, soloAntiguos = false } = {}) {
  let consulta = supabase
    .from("noticias")
    .update({ oculta: false, borrador: false })
    .eq("borrador", true);
  if (ids) consulta = consulta.in("id", ids);
  if (soloAntiguos) {
    consulta = consulta.lte("borrador_desde", new Date(Date.now() - HORAS_AUTOPUBLICAR * 3600 * 1000).toISOString());
  }
  const { data, error } = await consulta.select("id, categoria, titular, resumen");
  if (error) throw error;

  const publicadas = data || [];
  let enviadasTelegram = 0;
  if (publicadas.length) enviadasTelegram = await publicarEnTelegram(publicadas);
  return { publicadas: publicadas.length, enviadasTelegram };
}

// Avisa en tu Telegram privado de que hay borradores por revisar
async function avisarBorradores(noticias) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.TELEGRAM_RESUMEN_CHAT_ID;
  if (!token || !chat || !noticias.length) return false;

  const lineas = noticias.slice(0, 15).map((n, i) => `${i + 1}. ${n.titular}`);
  const texto =
    `📝 ${noticias.length} noticia${noticias.length === 1 ? "" : "s"} por revisar\n\n` +
    lineas.join("\n") +
    `\n\nSi no las revisas, se publican solas en ${HORAS_AUTOPUBLICAR} h.\n` +
    `👉 ${SITIO}/admin.html`;

  const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text: texto, disable_web_page_preview: true }),
  });
  if (!r.ok) throw new Error(`Telegram ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return true;
}

module.exports = { publicarBorradores, avisarBorradores, HORAS_AUTOPUBLICAR };
