/* Script de minhas_reservas.html */
(function () {
    var layout = document.getElementById("layout");
    var painel = document.getElementById("painel");
    var fundo = document.getElementById("fundo");
    var cards = document.querySelectorAll(".nc-res-card");
    var ativo = null;

    function el(id) { return document.getElementById(id); }

    function abrir(card) {
        var d = card.dataset;
        el("p-codigo").textContent = d.codigo;
        el("p-veiculo").textContent = d.veiculo;
        el("p-placa").textContent = d.placa;
        el("p-categoria").textContent = d.categoria ? " · " + d.categoria : "";
        el("p-retirada").textContent = d.retirada;
        el("p-devolucao").textContent = d.devolucao;
        el("p-dias").textContent = d.dias;
        el("p-total").textContent = d.total;
        el("p-diaria").textContent = d.diaria;

        var status = el("p-status");
        status.textContent = d.statusRotulo;
        status.className = "nc-badge " + d.statusClasse;

        var img = el("p-img");
        if (d.img) { img.src = d.img; img.hidden = false; } else { img.hidden = true; }

        var form = el("p-cancelar");
        form.hidden = !d.cancelavel;
        form.action = d.cancelarUrl;

        cards.forEach(function (c) { c.classList.toggle("sel", c === card); });
        layout.classList.add("aberto");
        painel.hidden = false;
        fundo.hidden = false;
        ativo = card;
        el("p-fechar").focus();
    }

    function fechar() {
        painel.hidden = true;
        fundo.hidden = true;
        layout.classList.remove("aberto");
        cards.forEach(function (c) { c.classList.remove("sel"); });
        if (ativo) ativo.focus();
        ativo = null;
    }

    cards.forEach(function (card) {
        card.addEventListener("click", function () { abrir(card); });
        card.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir(card); }
        });
    });
    el("p-fechar").addEventListener("click", fechar);
    fundo.addEventListener("click", fechar);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !painel.hidden) fechar();
    });
    el("p-cancelar").addEventListener("submit", function (e) {
        if (!confirm("Deseja realmente solicitar o cancelamento desta reserva?")) e.preventDefault();
    });
})();
