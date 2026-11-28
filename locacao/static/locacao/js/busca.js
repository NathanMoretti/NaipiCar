/* Script de _busca.html */
(function () {
    var retirada = document.getElementById("retirada");
    var devolucao = document.getElementById("devolucao");
    var mais = document.getElementById("btn-mais");
    var painel = document.getElementById("avancado");

    // Se preencher uma das datas, a outra passa a ser obrigatória; a devolução não pode ser antes da retirada
    function sincronizar() {
        var alguma = !!(retirada.value || devolucao.value);
        retirada.required = alguma;
        devolucao.required = alguma;
        if (retirada.value) devolucao.min = retirada.value;
        if (devolucao.value && retirada.value && devolucao.value < retirada.value) devolucao.value = retirada.value;
    }
    retirada.addEventListener("change", sincronizar);
    devolucao.addEventListener("change", sincronizar);
    sincronizar();

    mais.addEventListener("click", function () {
        var aberto = painel.hidden;
        painel.hidden = !aberto;
        mais.setAttribute("aria-expanded", aberto ? "true" : "false");
    });
})();
