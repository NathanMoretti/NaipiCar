/* Script de painel/dashboard.html */
(function () {
    var form = document.getElementById("form-filtros");
    var periodo = document.getElementById("f-periodo");
    var datas = document.getElementById("datas-personalizadas");
    var aplicar = document.getElementById("btn-aplicar");

    // Escolher um período pronto aplica na hora; "Personalizado" mostra as datas e espera o botão Aplicar
    periodo.addEventListener("change", function () {
        if (periodo.value === "personalizado") { datas.hidden = false; aplicar.hidden = false; }
        else { form.submit(); }
    });
    document.getElementById("f-categoria").addEventListener("change", function () { form.submit(); });

    // Escolha dos blocos visíveis: fica guardada neste navegador
    var CHAVE = "naipicar.dashboard.blocos";
    var caixas = document.querySelectorAll("[data-alternar]");
    var padrao = {};
    caixas.forEach(function (c) { padrao[c.dataset.alternar] = true; });

    function ler() {
        try { return Object.assign({}, padrao, JSON.parse(localStorage.getItem(CHAVE) || "{}")); }
        catch (e) { return Object.assign({}, padrao); }
    }
    function aplicarEscolha(estado) {
        caixas.forEach(function (c) { c.checked = estado[c.dataset.alternar] !== false; });
        document.querySelectorAll("[data-widget]").forEach(function (bloco) {
            bloco.hidden = estado[bloco.dataset.widget] === false;
        });
    }
    function salvar() {
        var estado = {};
        caixas.forEach(function (c) { estado[c.dataset.alternar] = c.checked; });
        try { localStorage.setItem(CHAVE, JSON.stringify(estado)); } catch (e) {}
        aplicarEscolha(estado);
    }
    caixas.forEach(function (c) { c.addEventListener("change", salvar); });
    document.getElementById("restaurar").addEventListener("click", function () {
        caixas.forEach(function (c) { c.checked = true; });
        salvar();
    });
    aplicarEscolha(ler());

    // Fecha o menu "Personalizar" ao clicar fora
    var menu = document.getElementById("personalizar");
    document.addEventListener("click", function (e) { if (!menu.contains(e.target)) menu.removeAttribute("open"); });
})();
