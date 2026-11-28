/* Script de veiculos.html */
(function () {
    var modal = document.getElementById("modal-veiculo");
    var form = document.getElementById("m-form");
    var diaria = 0;

    function el(id) { return document.getElementById(id); }
    function reais(n) { return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

    function atualizarTotal() {
        var r = el("m-retirada"), d = el("m-devolucao"), total = el("m-total");
        if (!r || !r.value || !d || !d.value) { if (total) total.textContent = "Escolha as datas para ver o valor total."; return; }
        var dias = Math.round((new Date(d.value) - new Date(r.value)) / 86400000);
        if (dias <= 0) { total.textContent = "A devolução deve ser depois da retirada."; return; }
        total.innerHTML = dias + " diária" + (dias > 1 ? "s" : "") + " × " + reais(diaria) + " = <strong>" + reais(dias * diaria) + "</strong>";
    }

    function abrir(card) {
        var d = card.dataset;
        diaria = parseFloat(d.diaria) || 0;
        el("m-titulo").textContent = d.modelo;
        el("m-modelo").textContent = d.modelo;
        el("m-categoria").textContent = d.categoria;
        el("m-ano").textContent = d.ano;
        el("m-motor").textContent = d.motor;
        el("m-assentos").textContent = d.assentos;
        el("m-malas").textContent = d.malas;
        el("m-diaria").textContent = reais(diaria);

        var disponivel = !!d.disponivel;
        el("m-situacao").textContent = disponivel ? "Disponível" : "Indisponível";
        el("m-bloco-reserva").hidden = !disponivel;
        el("m-indisponivel").hidden = disponivel;
        var enviar = el("m-enviar"), entrar = el("m-entrar");
        if (enviar) enviar.hidden = !disponivel;
        if (entrar) entrar.hidden = !disponivel;

        var img = el("m-img");
        if (d.img) { img.src = d.img; img.alt = d.modelo; img.hidden = false; el("m-sem-foto").hidden = true; }
        else { img.hidden = true; el("m-sem-foto").hidden = false; }

        if (form) { form.action = d.reservarUrl; atualizarTotal(); }
        document.body.classList.add("nc-modal-aberto");
        modal.showModal();
    }

    function fechar() { modal.close(); }

    document.querySelectorAll(".js-detalhes").forEach(function (botao) {
        botao.addEventListener("click", function () { abrir(botao.closest("article")); });
    });
    el("m-fechar").addEventListener("click", fechar);
    el("m-cancelar").addEventListener("click", fechar);
    // clicar fora da caixa (no fundo escuro) também fecha
    modal.addEventListener("click", function (e) { if (e.target === modal) fechar(); });
    modal.addEventListener("close", function () { document.body.classList.remove("nc-modal-aberto"); });

    if (form) {
        var r = el("m-retirada"), dv = el("m-devolucao");
        r.addEventListener("change", function () {
            dv.min = r.value;
            if (dv.value && dv.value < r.value) dv.value = r.value;
            atualizarTotal();
        });
        dv.addEventListener("change", atualizarTotal);
    }
})();
