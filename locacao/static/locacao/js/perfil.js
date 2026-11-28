/* Script de _perfil_modal.html */
(function () {
    var modal = document.getElementById("modal-perfil");
    var form = document.getElementById("pf-form");
    var previa = document.getElementById("pf-previa");
    var zonaTexto = document.getElementById("pf-zona-texto");
    var arquivo = document.getElementById("pf-foto");
    var original = previa.getAttribute("src");

    function limparErros() {
        form.querySelectorAll("[data-erro]").forEach(function (e) { e.textContent = ""; });
        form.querySelectorAll(".pf-campo.erro").forEach(function (e) { e.classList.remove("erro"); });
        var geral = document.getElementById("pf-geral");
        geral.hidden = true; geral.textContent = "";
    }

    function mostrarErros(erros) {
        var primeiro = null;
        Object.keys(erros).forEach(function (campo) {
            var texto = erros[campo].join(" ");
            var alvo = form.querySelector('[data-erro="' + campo + '"]');
            if (alvo) {
                alvo.textContent = texto;
                var caixa = alvo.parentElement.querySelector(".pf-campo");
                if (caixa) caixa.classList.add("erro");
                if (!primeiro) primeiro = alvo;
            } else {
                var geral = document.getElementById("pf-geral");
                geral.textContent += texto + " "; geral.hidden = false;
            }
        });
        if (primeiro) primeiro.scrollIntoView({ block: "center", behavior: "smooth" });
    }

    function abrir() {
        form.reset();
        limparErros();
        if (original) { previa.src = original; previa.hidden = false; zonaTexto.hidden = true; }
        modal.showModal();
    }

    document.querySelectorAll("[data-abrir-perfil]").forEach(function (b) {
        b.addEventListener("click", function () {
            var menu = b.closest("details"); if (menu) menu.removeAttribute("open");
            abrir();
        });
    });
    document.getElementById("pf-fechar").addEventListener("click", function () { modal.close(); });
    document.getElementById("pf-cancelar").addEventListener("click", function () { modal.close(); });
    modal.addEventListener("click", function (e) { if (e.target === modal) modal.close(); });

    // Mostrar / ocultar senha
    form.querySelectorAll(".pf-olho").forEach(function (b) {
        b.addEventListener("click", function () {
            var campo = document.getElementById(b.dataset.alvo);
            var mostrar = campo.type === "password";
            campo.type = mostrar ? "text" : "password";
            b.querySelector("i").className = mostrar ? "bi bi-eye-slash" : "bi bi-eye";
        });
    });

    // Foto: pré-visualização e arrastar e soltar
    var zona = document.getElementById("pf-zona");
    arquivo.addEventListener("change", function () {
        var f = arquivo.files[0];
        if (!f) return;
        if (f.size > 5 * 1024 * 1024) { alert("A foto deve ter no máximo 5MB."); arquivo.value = ""; return; }
        var leitor = new FileReader();
        leitor.onload = function (e) { previa.src = e.target.result; previa.hidden = false; zonaTexto.hidden = true; };
        leitor.readAsDataURL(f);
    });
    ["dragenter", "dragover"].forEach(function (n) { zona.addEventListener(n, function (e) { e.preventDefault(); zona.classList.add("arrastando"); }); });
    ["dragleave", "drop"].forEach(function (n) { zona.addEventListener(n, function () { zona.classList.remove("arrastando"); }); });
    zona.addEventListener("drop", function (e) {
        e.preventDefault();
        if (e.dataTransfer.files.length) { arquivo.files = e.dataTransfer.files; arquivo.dispatchEvent(new Event("change")); }
    });

    // Envio sem sair da página: os erros aparecem nos campos
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        limparErros();
        var botao = document.getElementById("pf-enviar");
        botao.disabled = true;
        fetch(form.action, { method: "POST", body: new FormData(form), headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); })
            .then(function (dados) {
                if (dados.ok) { location.reload(); return; }
                mostrarErros(dados.erros || {});
            })
            .catch(function () {
                var geral = document.getElementById("pf-geral");
                geral.textContent = "Não foi possível salvar agora. Tente novamente."; geral.hidden = false;
            })
            .then(function () { botao.disabled = false; });
    });
})();
