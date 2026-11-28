/* Script de auth_base.html */
// Mostrar / ocultar senha
document.querySelectorAll(".olho").forEach(function (botao) {
    botao.addEventListener("click", function () {
        var campo = document.getElementById(botao.dataset.alvo);
        var mostrar = campo.type === "password";
        campo.type = mostrar ? "text" : "password";
        botao.querySelector("i").className = mostrar ? "bi bi-eye-slash" : "bi bi-eye";
        botao.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
    });
});
