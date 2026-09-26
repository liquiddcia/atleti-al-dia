// lib/supabase.js
// Cliente de Supabase para el servidor. Usa la Service Role Key,
// que tiene permiso de escritura y nunca debe exponerse en el frontend.

const { createClient } = require("@supabase/supabase-js");

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

module.exports = supabase;
