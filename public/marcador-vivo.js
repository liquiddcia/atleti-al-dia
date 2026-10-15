// marcador-vivo.js
// Muestra en la portada el marcador del Atleti mientras se juega el partido
// (y un rato antes y después). Se actualiza solo. Los datos vienen de /api/clasificacion?vivo=1
(function () {
  var caja = null;
  var temporizador = null;

  function ponerEstilos() {
    var s = document.createElement("style");
    s.textContent =
      "#marcador-vivo{background:#10203D;color:#fff;border-top:4px solid #D2122E;margin:0 0 22px;padding:14px 18px 12px;font-family:'Barlow Condensed',Arial,sans-serif}" +
      "#marcador-vivo .mv-estado{display:inline-block;background:#D2122E;color:#fff;font-weight:700;font-size:13px;letter-spacing:.04em;text-transform:uppercase;padding:3px 10px 4px;border-radius:2px}" +
      "#marcador-vivo .mv-estado.fin{background:#55565C}" +
      "#marcador-vivo .mv-estado.pronto{background:#C79A3C;color:#1c1608}" +
      "#marcador-vivo .mv-comp{margin-left:10px;font-size:13px;opacity:.8}" +
      "#marcador-vivo .mv-fila{display:flex;align-items:center;justify-content:center;gap:16px;padding:10px 0 4px}" +
      "#marcador-vivo .mv-eq{display:flex;align-items:center;gap:10px;flex:1;font-weight:700;font-size:19px;text-transform:uppercase}" +
      "#marcador-vivo .mv-eq.vis{justify-content:flex-start}" +
      "#marcador-vivo .mv-eq.loc{justify-content:flex-end;text-align:right}" +
      "#marcador-vivo .mv-eq img{width:40px;height:40px;object-fit:contain;flex:none}" +
      "#marcador-vivo .mv-num{font-weight:800;font-size:38px;line-height:1;min-width:92px;text-align:center;white-space:nowrap}" +
      "#marcador-vivo .mv-goles{margin:8px 0 0;padding:8px 0 0;border-top:1px solid rgba(255,255,255,.18);font-size:14px;text-align:center;line-height:1.5}" +
      "#marcador-vivo .mv-nota{margin:8px 0 0;font-size:12px;opacity:.65;text-align:center}" +
      "@media (max-width:560px){#marcador-vivo .mv-eq{font-size:15px;flex-direction:column;gap:4px;text-align:center}#marcador-vivo .mv-eq.loc{flex-direction:column-reverse}#marcador-vivo .mv-num{font-size:30px;min-width:70px}}";
    document.head.appendChild(s);
  }

  function crearCaja() {
    var main = document.querySelector("main");
    if (!main) return null;
    var d = document.createElement("div");
    d.id = "marcador-vivo";
    d.style.display = "none";
    main.insertBefore(d, main.firstChild);
    return d;
  }

  function elem(tag, clase, texto) {
    var e = document.createElement(tag);
    if (clase) e.className = clase;
    if (texto != null) e.textContent = texto;
    return e;
  }

  function equipo(e, clase) {
    var d = elem("div", "mv-eq " + clase);
    var img = document.createElement("img");
    img.src = e.escudo || "";
    img.alt = "";
    img.onerror = function () { img.style.display = "none"; };
    var nombre = elem("span", null, e.nombre);
    if (clase === "loc") { d.appendChild(nombre); d.appendChild(img); }
    else { d.appendChild(img); d.appendChild(nombre); }
    return d;
  }

  function pintar(p) {
    if (!p) { caja.style.display = "none"; caja.textContent = ""; return; }
    var etiqueta, clase = "";
    if (p.estado === "IN_PLAY" || p.estado === "LIVE") etiqueta = "🔴 En directo";
    else if (p.estado === "PAUSED") etiqueta = "⏸ Descanso";
    else if (p.estado === "FINISHED") { etiqueta = "Final"; clase = " fin"; }
    else {
      var mins = Math.max(0, Math.round((new Date(p.inicio).getTime() - Date.now()) / 60000));
      etiqueta = mins > 0 ? "Empieza en " + mins + " min" : "A punto de empezar";
      clase = " pronto";
    }

    caja.textContent = "";
    var cab = elem("div");
    cab.appendChild(elem("span", "mv-estado" + clase, etiqueta));
    if (p.competicion) cab.appendChild(elem("span", "mv-comp", p.competicion));
    caja.appendChild(cab);

    var fila = elem("div", "mv-fila");
    fila.appendChild(equipo(p.local, "loc"));
    var marcador = p.golesLocal != null && p.golesVisitante != null ? p.golesLocal + " - " + p.golesVisitante : "vs";
    fila.appendChild(elem("div", "mv-num", marcador));
    fila.appendChild(equipo(p.visitante, "vis"));
    caja.appendChild(fila);

    if (p.goles && p.goles.length) {
      var g = elem("div", "mv-goles");
      p.goles.forEach(function (x, i) {
        if (i) g.appendChild(document.createElement("br"));
        g.appendChild(document.createTextNode("⚽ " + x.minuto + "' " + x.jugador + (x.equipo ? " (" + x.equipo + ")" : "")));
      });
      caja.appendChild(g);
    }
    caja.appendChild(elem("p", "mv-nota", "Marcador con posible retraso de unos minutos · se actualiza solo"));
    caja.style.display = "block";
  }

  function siguiente(p) {
    var ms = 5 * 60 * 1000;
    if (p && (p.estado === "IN_PLAY" || p.estado === "LIVE" || p.estado === "PAUSED")) ms = 60 * 1000;
    else if (p && p.estado !== "FINISHED") ms = 60 * 1000;
    clearTimeout(temporizador);
    temporizador = setTimeout(cargar, ms);
  }

  function cargar() {
    if (document.hidden) { siguiente(null); return; }
    fetch("/api/clasificacion?vivo=1")
      .then(function (r) { return r.json(); })
      .then(function (d) { pintar(d && d.partido); siguiente(d && d.partido); })
      .catch(function () { siguiente(null); });
  }

  function iniciar() {
    ponerEstilos();
    caja = crearCaja();
    if (caja) cargar();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
