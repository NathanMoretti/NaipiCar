/* Script de painel/reservas.html (usa as funções de painel.js) */
// Painel lateral com os detalhes da reserva
(function () {
    var $ = Painel.$;
    var ROTULOS = { "Pendente": "Em análise", "Confirmada": "Reservado", "Concluída": "Concluído", "Cancelada": "Cancelado" };

    function preencher(d) {
        $("p-codigo").textContent = d.codigo;
        $("p-cliente").textContent = d.cliente;
        $("p-cpf").textContent = d.cpf;
        $("p-email").textContent = d.email;
        $("p-veiculo").textContent = d.veiculo;
        $("p-detalhe-veiculo").textContent = d.detalheVeiculo;
        $("p-retirada").textContent = d.retirada;
        $("p-devolucao").textContent = d.devolucao;
        $("p-dias").textContent = d.dias;
        $("p-total").textContent = d.total;
        $("p-diaria").textContent = d.diaria;

        var badge = $("p-badge");
        badge.textContent = d.rotulo;
        badge.className = "badge " + d.classe;

        var img = $("p-img");
        if (d.img) { img.src = d.img; img.hidden = false; } else { img.hidden = true; }

        // Só aparecem as situações para as quais esta reserva pode avançar
        var select = $("p-status");
        select.innerHTML = "";
        d.opcoes.split("|").forEach(function (valor) {
            var op = document.createElement("option");
            op.value = valor;
            op.textContent = ROTULOS[valor] || valor;
            if (valor === d.status) op.selected = true;
            select.appendChild(op);
        });
        var final = d.opcoes.split("|").length === 1;
        select.disabled = final;
        $("p-salvar").hidden = final;
        $("p-nota").textContent = final
            ? "Esta reserva já foi finalizada e não pode mais ser alterada."
            : (d.rotulo === "Atrasado" ? "Esta reserva está atrasada. Marque como Concluído quando o veículo for devolvido." : "");
        $("p-form").action = d.url;
    }

    Painel.painelLateral(document.querySelectorAll("tbody tr[data-codigo]"), preencher);

    // Cancelar a reserva pede confirmação
    $("p-form").addEventListener("submit", function (e) {
        if ($("p-status").value === "Cancelada" && !confirm("Cancelar esta reserva? Essa ação não pode ser desfeita.")) e.preventDefault();
    });

    Painel.enviarAoMudar(["f-situacao", "f-periodo"]);
})();

// Pop-up "Nova reserva"
(function () {
    var modal = document.getElementById("modal-nova");
    var diarias = JSON.parse(document.getElementById("dados-diarias").textContent);
    var $ = Painel.$, reais = Painel.reais;
    var cliente = $("id_cliente"), veiculo = $("id_veiculo");
    var retirada = $("id_data_retirada"), devolucao = $("id_data_devolucao");

    // Prévia do valor: o valor de verdade é calculado no servidor ao salvar
    function atualizarResumo() {
        var diaria = diarias[veiculo.value];
        var d1 = retirada.value && new Date(retirada.value + "T00:00:00");
        var d2 = devolucao.value && new Date(devolucao.value + "T00:00:00");
        var dias = d1 && d2 ? Math.round((d2 - d1) / 86400000) : 0;
        if (!diaria || dias <= 0) {
            $("n-dias").textContent = dias < 0 || (d1 && d2 && dias === 0)
                ? "A devolução deve ser depois da retirada" : "Escolha o veículo e as datas";
            $("n-total").textContent = reais(0);
            return;
        }
        $("n-dias").textContent = dias + " diária" + (dias > 1 ? "s" : "") + " × " + reais(diaria);
        $("n-total").textContent = reais(dias * diaria);
    }

    // Filtro da lista de clientes (nome, CPF ou e-mail)
    $("n-busca").addEventListener("input", function () {
        var termo = this.value.trim().toLowerCase();
        Array.prototype.forEach.call(cliente.options, function (op) {
            if (!op.value) return;
            op.hidden = termo && op.textContent.toLowerCase().indexOf(termo) === -1;
        });
        var visiveis = Array.prototype.filter.call(cliente.options, function (op) { return op.value && !op.hidden; });
        if (visiveis.length === 1) cliente.value = visiveis[0].value;
    });

    retirada.addEventListener("change", function () {
        if (retirada.value) devolucao.min = retirada.value;
        atualizarResumo();
    });
    [veiculo, devolucao].forEach(function (el) { el.addEventListener("change", atualizarResumo); });

    $("btn-nova").addEventListener("click", function () { modal.showModal(); });
    Painel.ligarModal(modal, ["n-fechar", "n-cancelar"]);

    atualizarResumo();
    Painel.abrirSeTemErro(modal);
})();
