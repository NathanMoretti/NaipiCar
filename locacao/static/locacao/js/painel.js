/* Funções usadas pelos scripts de várias telas do painel (carregado por painel/base_painel.html). */
window.Painel = (function () {
    function $(id) { return document.getElementById(id); }

    function reais(n) {
        return Number(n).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    }

    /* Pop-up (<dialog>): fecha pelos botões indicados e ao clicar fora da caixa. */
    function ligarModal(modal, idsFechar) {
        idsFechar.forEach(function (id) {
            $(id).addEventListener("click", function () { modal.close(); });
        });
        modal.addEventListener("click", function (e) { if (e.target === modal) modal.close(); });
    }

    /* Quando o servidor devolve o formulário com erro, o pop-up já abre mostrando os erros. */
    function abrirSeTemErro(modal) {
        if (modal.dataset.abrir) modal.showModal();
    }

    /* Filtros que se aplicam sozinhos ao trocar a opção (sem precisar clicar em Filtrar). */
    function enviarAoMudar(ids) {
        ids.forEach(function (id) {
            $(id).addEventListener("change", function () { this.form.submit(); });
        });
    }

    /* Pede confirmação antes de enviar os formulários de exclusão (data-nome = o que será excluído). */
    function confirmarExclusao(seletor, pergunta) {
        document.querySelectorAll(seletor).forEach(function (f) {
            f.addEventListener("submit", function (e) {
                if (!confirm(pergunta(f.dataset.nome))) e.preventDefault();
            });
        });
    }

    /* Painel lateral de detalhes (Reservas e Usuários): abre ao clicar (ou Enter) numa linha da tabela
       e fecha pelo X, Cancelar, clique no fundo ou Esc, devolvendo o foco para a linha. */
    function painelLateral(linhas, preencher) {
        var layout = $("layout"), painel = $("painel"), fundo = $("fundo");
        var ativa = null;

        function abrir(linha) {
            preencher(linha.dataset);
            linhas.forEach(function (l) { l.classList.toggle("sel", l === linha); });
            layout.classList.add("aberto");
            painel.hidden = false;
            fundo.hidden = false;
            ativa = linha;
            $("p-fechar").focus();
        }

        function fechar() {
            painel.hidden = true;
            fundo.hidden = true;
            layout.classList.remove("aberto");
            linhas.forEach(function (l) { l.classList.remove("sel"); });
            if (ativa) ativa.focus();
            ativa = null;
        }

        linhas.forEach(function (linha) {
            linha.addEventListener("click", function () { abrir(linha); });
            linha.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir(linha); }
            });
        });
        $("p-fechar").addEventListener("click", fechar);
        $("p-cancelar").addEventListener("click", fechar);
        fundo.addEventListener("click", fechar);
        document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !painel.hidden) fechar(); });

        return { linhaAtiva: function () { return ativa; } };
    }

    return {
        $: $,
        reais: reais,
        ligarModal: ligarModal,
        abrirSeTemErro: abrirSeTemErro,
        enviarAoMudar: enviarAoMudar,
        confirmarExclusao: confirmarExclusao,
        painelLateral: painelLateral,
    };
})();
