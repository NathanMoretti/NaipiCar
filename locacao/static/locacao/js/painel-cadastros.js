/* Script de painel/cadastros.html (usa as funções de painel.js) */
(function () {
    var modal = document.getElementById("modal");
    var form = document.getElementById("m-form");
    var iniciais = JSON.parse(JSON.parse(document.getElementById("dados-iniciais").textContent));
    var singular = modal.dataset.singular;

    var $ = Painel.$;

    function preencher(valores) {
        Object.keys(iniciais).forEach(function (nome) {
            var campo = $("id_" + nome);
            if (!campo) return;
            var v = valores[nome];
            campo.value = (v === null || v === undefined) ? "" : v;
        });
        modal.querySelectorAll(".erro-campo, .pl-alerta").forEach(function (e) { e.remove(); });
    }

    $("btn-novo").addEventListener("click", function () {
        preencher(iniciais);
        form.action = modal.dataset.urlNovo;
        $("m-titulo").textContent = "Cadastrar " + singular;
        $("m-enviar").textContent = "Cadastrar";
        modal.showModal();
    });

    document.querySelectorAll(".js-editar").forEach(function (botao) {
        botao.addEventListener("click", function () {
            var linha = botao.closest("tr");
            preencher(JSON.parse(linha.dataset.valores));
            form.action = linha.dataset.urlEditar;
            $("m-titulo").textContent = "Editar " + singular;
            $("m-enviar").textContent = "Salvar alterações";
            modal.showModal();
        });
    });

    Painel.confirmarExclusao(".js-excluir", function (nome) {
        return "Excluir " + nome + "? Essa ação não pode ser desfeita.";
    });

    Painel.ligarModal(modal, ["m-fechar", "m-cancelar"]);

    Painel.abrirSeTemErro(modal);
})();
