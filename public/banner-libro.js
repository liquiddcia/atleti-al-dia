/* Banner del libro «Sombras de Aranjuez»: se inyecta en todas las páginas públicas. */
(function () {
  if (document.querySelector(".lib")) return;
  var css = "\n.lib{position:fixed;z-index:900;font-family:'Barlow Condensed',sans-serif;text-decoration:none;color:#fff}\n.lib img{display:block;width:100%;height:auto;border-radius:6px}\n.lib .lib-pub{font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.7;display:block}\n.lib .lib-btn{display:block;background:#D2122E;color:#fff;font-weight:700;font-size:18px;text-align:center;padding:9px 6px;border-radius:4px;text-transform:uppercase;letter-spacing:.03em}\n.lib:hover .lib-btn{background:#9A0B21}\n@media (min-width:1540px){.lib{right:14px;top:50%;transform:translateY(-50%);width:210px;background:#14151A;padding:8px;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.45)}.lib .lib-btn{margin-top:8px}.lib .lib-txt{display:block;margin-top:8px;text-align:center;font-size:15px;line-height:1.15}}\n@media (max-width:1539px){.lib{left:0;right:0;bottom:0;display:flex;align-items:center;gap:12px;background:#14151A;padding:6px 12px;box-shadow:0 -3px 14px rgba(0,0,0,.4)}.lib img{width:46px;flex:none}.lib .lib-txt{flex:1;line-height:1.15;font-size:15px}.lib .lib-btn{flex:none;font-size:16px;padding:9px 14px}body{padding-bottom:64px}}\n";
  var html = "<a class=\"lib\" href=\"https://link.amazon/B0fJgu9jY\" target=\"_blank\" rel=\"sponsored noopener noreferrer\" aria-label=\"Comprar Sombras de Aranjuez en Amazon\">\n<img src=\"/libro-sombras-aranjuez.jpg\" alt=\"Sombras de Aranjuez, libro de Daniel Santiago Sanz García\" loading=\"lazy\">\n<span class=\"lib-txt\"><span class=\"lib-pub\">Publicidad</span><b>Sombras de Aranjuez</b><br>Ya disponible en Amazon</span>\n<span class=\"lib-btn\">Cómpralo ya</span>\n</a>";
  function poner() {
    if (document.querySelector(".lib")) return;
    var st = document.createElement("style");
    st.textContent = css;
    document.head.appendChild(st);
    var caja = document.createElement("div");
    caja.innerHTML = html;
    document.body.appendChild(caja.firstChild);
  }
  if (document.body) poner();
  else document.addEventListener("DOMContentLoaded", poner);
})();
