/* Script de painel/veiculos.html (usa as funções de painel.js) */
(function () {
    var modal = document.getElementById("modal-veiculo");
    var form = document.getElementById("v-form");
    var diarias = JSON.parse(document.getElementById("dados-diarias").textContent);
    var URL_NOVO = modal.dataset.urlNovo;

    var $ = Painel.$, reais = Painel.reais;

    function atualizarDiaria() {
        var id = $("id_categoria_classe").value;
        $("v-diaria").value = reais(diarias[id] || 0);
    }

    function mostrarPrevia(url) {
        var img = $("v-previa");
        if (url) { img.src = url; img.hidden = false; $("v-zona-texto").hidden = true; }
        else { img.removeAttribute("src"); img.hidden = true; $("v-zona-texto").hidden = false; }
    }

    function limparErros() {
        modal.querySelectorAll(".erro-campo:not(#v-diaria-dica), .pl-alerta").forEach(function (e) { e.remove(); });
    }

    function abrirNovo() {
        limparErros();
        form.action = URL_NOVO;
        $("v-titulo").textContent = "Cadastrar Veículo";
        $("v-enviar").textContent = "Cadastrar Veículo";
        ["id_modelo", "id_placa", "id_categoria_classe", "id_ano"].forEach(function (id) { $(id).value = ""; });
        $("id_quilometragem").value = 0;
        $("id_motorizacao").selectedIndex = 0;
        $("id_disponivel").value = "True";
        $("id_imagem").value = "";
        mostrarPrevia("");
        atualizarDiaria();
        modal.showModal();
    }

    function abrirEdicao(linha) {
        var d = linha.dataset;
        limparErros();
        form.action = d.editarUrl;
        $("v-titulo").textContent = "Editar Veículo";
        $("v-enviar").textContent = "Editar Veículo";
        $("id_modelo").value = d.modelo;
        $("id_placa").value = d.placa;
        $("id_categoria_classe").value = d.categoria;
        $("id_ano").value = d.ano;
        $("id_quilometragem").value = d.km;
        $("id_motorizacao").value = d.motor;
        $("id_disponivel").value = d.disponivel;
        $("id_imagem").value = "";
        mostrarPrevia(d.img);
        atualizarDiaria();
        modal.showModal();
    }

    $("btn-novo").addEventListener("click", abrirNovo);
    document.querySelectorAll(".js-editar").forEach(function (b) {
        b.addEventListener("click", function () { abrirEdicao(b.closest("tr")); });
    });
    Painel.confirmarExclusao(".js-excluir", function (nome) {
        return "Excluir o veículo " + nome + "? Essa ação não pode ser desfeita.";
    });

    Painel.ligarModal(modal, ["v-fechar", "v-cancelar"]);

    $("id_categoria_classe").addEventListener("change", atualizarDiaria);

    // Foto: pré-visualização, arrastar e soltar
    var zona = $("zona"), arquivo = $("id_imagem");
    arquivo.addEventListener("change", function () {
        var f = arquivo.files[0];
        if (!f) return;
        if (f.size > 5 * 1024 * 1024) { alert("A foto deve ter no máximo 5MB."); arquivo.value = ""; return; }
        var leitor = new FileReader();
        leitor.onload = function (e) { mostrarPrevia(e.target.result); };
        leitor.readAsDataURL(f);
    });
    ["dragenter", "dragover"].forEach(function (nome) {
        zona.addEventListener(nome, function (e) { e.preventDefault(); zona.classList.add("arrastando"); });
    });
    ["dragleave", "drop"].forEach(function (nome) {
        zona.addEventListener(nome, function () { zona.classList.remove("arrastando"); });
    });
    zona.addEventListener("drop", function (e) {
        e.preventDefault();
        if (e.dataTransfer.files.length) { arquivo.files = e.dataTransfer.files; arquivo.dispatchEvent(new Event("change")); }
    });

    // Filtros: aplica ao trocar categoria ou status
    Painel.enviarAoMudar(["f-categoria", "f-status"]);

    atualizarDiaria();
    Painel.abrirSeTemErro(modal);
})();
