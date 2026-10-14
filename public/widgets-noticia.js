// widgets-noticia.js
// Convierte marcas especiales del texto de una noticia en escudos y tabla de clasificación.
//   [[cartel:78,66]]                      -> escudos de los dos equipos (ids de football-data.org)
//   [[tabla-champions:atl,manchester]]    -> tabla de la Champions solo con esos equipos (datos en directo)
(function () {
  var css = ".wn-cartel{display:flex;align-items:center;justify-content:center;gap:18px;margin:6px 0 14px}" +
    ".wn-cartel img{width:84px;height:84px;object-fit:contain}" +
    ".wn-cartel span{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:26px;color:#55565C}" +
    ".wn-tabla{overflow-x:auto;border:1px solid rgba(20,21,26,.13);margin:0 0 14px}" +
    ".wn-tabla table{width:100%;border-collapse:collapse;font-family:'Barlow Condensed',sans-serif;min-width:380px}" +
    ".wn-tabla th{font-size:12px;text-transform:uppercase;color:#55565C;padding:8px 6px;border-bottom:2px solid #14151A;text-align:center}" +
    ".wn-tabla td{font-size:15px;font-weight:600;text-align:center;padding:8px 6px;border-bottom:1px solid rgba(20,21,26,.13)}" +
    ".wn-tabla th:nth-child(2),.wn-tabla td:nth-child(2){text-align:left}" +
    ".wn-tabla td .e{display:inline-flex;align-items:center;gap:8px;font-weight:700}" +
    ".wn-tabla td .e img{width:22px;height:22px;object-fit:contain}" +
    ".wn-tabla tr.dest{background:rgba(210,18,46,.07)}.wn-tabla td.pts{font-weight:800}" +
    ".wn-nota{font-size:13px;color:#55565C;margin:-8px 0 14px}.wn-estado{color:#55565C}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  var MARCAS = new RegExp("[" + String.fromCharCode(768) + "-" + String.fromCharCode(879) + "]", "g");
  function norm(s) { return String(s || "").toLowerCase().normalize("NFD").replace(MARCAS, ""); }
  function esc(t) { return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function esAtleti(n) { return norm(n).indexOf("atletico") >= 0 || norm(n).indexOf("atleti") >= 0; }

  var cache = null;
  function datos() {
    if (!cache) cache = fetch("/api/clasificacion").then(function (r) { return r.json(); }).catch(function () { return null; });
    return cache;
  }

  function tablaHTML(filas) {
    var cuerpo = filas.map(function (f) {
      var img = f.escudo ? '<img src="' + esc(f.escudo) + '" alt="" onerror="this.style.display=\'none\'">' : "";
      var nombre = esAtleti(f.equipo) ? "Atlético de Madrid" : f.equipo;
      return '<tr' + (esAtleti(f.equipo) ? ' class="dest"' : "") + "><td>" + f.posicion + ".º</td><td><span class=\"e\">" + img + esc(nombre) +
        "</span></td><td>" + f.pj + "</td><td>" + f.pg + "</td><td>" + f.pe + "</td><td>" + f.pp + "</td><td>" + f.gf + "</td><td>" + f.gc + '</td><td class="pts">' + f.pts + "</td></tr>";
    }).join("");
    return '<div class="wn-tabla"><table><thead><tr><th>Pos.</th><th>Equipo</th><th>PJ</th><th>PG</th><th>PE</th><th>PP</th><th>GF</th><th>GC</th><th>Pts</th></tr></thead><tbody>' +
      cuerpo + '</tbody></table></div><div class="wn-nota">Clasificación de la fase de liga de la Champions League. Se actualiza sola.</div>';
  }

  function hidratar(el) {
    el.querySelectorAll("p").forEach(function (p) {
      var t = p.textContent.trim(), m;
      if ((m = t.match(/^\[\[cartel:(\d+),(\d+)\]\]$/))) {
        var d = document.createElement("div"); d.className = "wn-cartel";
        d.innerHTML = '<img src="https://crests.football-data.org/' + m[1] + '.png" alt="" onerror="this.style.visibility=\'hidden\'"><span>VS</span><img src="https://crests.football-data.org/' + m[2] + '.png" alt="" onerror="this.style.visibility=\'hidden\'">';
        p.replaceWith(d);
      } else if ((m = t.match(/^\[\[tabla-champions:(.+)\]\]$/))) {
        var claves = m[1].split(",").map(function (c) { return norm(c).trim(); }).filter(Boolean);
        var slot = document.createElement("div"); slot.className = "wn-estado"; slot.textContent = "Cargando clasificación…";
        p.replaceWith(slot);
        datos().then(function (dt) {
          var tabla = (dt && dt.champions && dt.champions.tabla) || [];
          var filas = tabla.filter(function (f) { var n = norm(f.equipo); return claves.some(function (c) { return n.indexOf(c) >= 0; }); })
            .sort(function (a, b) { return a.posicion - b.posicion; });
          if (!filas.length) { slot.textContent = "Clasificación no disponible todavía."; return; }
          slot.className = ""; slot.innerHTML = tablaHTML(filas);
        });
      }
    });
  }

  // Cuenta una apertura por noticia y sesion (para saber que noticias se leen mas)
  function contarVista() {
    try {
      var b = document.getElementById("modal-like");
      var id = b && b.dataset.likeId;
      if (!id) return;
      var clave = "atleti_vistas";
      var vistas = JSON.parse(sessionStorage.getItem(clave) || "[]");
      if (vistas.indexOf(id) >= 0) return;
      vistas.push(id);
      sessionStorage.setItem(clave, JSON.stringify(vistas));
      fetch("/api/like", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(id), accion: "vista" })
      }).catch(function () {});
    } catch (e) {}
  }

  function iniciar() {
    var el = document.getElementById("modal-cuerpo");
    if (!el) return;
    new MutationObserver(function () { hidratar(el); contarVista(); }).observe(el, { childList: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
