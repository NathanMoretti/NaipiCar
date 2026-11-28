/* Script de base.html */
// Fecha o menu do usuário ao clicar fora ou apertar Esc
(function () {
    var menu = document.getElementById("menu-usuario");
    if (!menu) return;
    document.addEventListener("click", function (e) { if (!menu.contains(e.target)) menu.removeAttribute("open"); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") menu.removeAttribute("open"); });
})();
