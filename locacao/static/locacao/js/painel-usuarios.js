/* Script de painel/usuarios.html (usa as funções de painel.js) */
// Painel lateral com os detalhes da conta
(function () {
    var $ = Painel.$;
    var ADMIN = $("layout").dataset.admin;

    function avatar(el, foto, inicial) {
        el.innerHTML = "";
        if (foto) { var img = document.createElement("img"); img.src = foto; img.alt = ""; el.appendChild(img); }
        else { el.textContent = inicial; }
    }

    function preencher(d) {
        avatar($("p-avatar"), d.foto, d.inicial);
        $("p-nome").textContent = d.nome;
        var pb = $("p-perfil-badge");
        pb.textContent = d.perfilRotulo;
        pb.className = "badge " + (d.perfil === ADMIN ? "admin" : "cliente");
        $("p-email").textContent = d.email;
        $("p-telefone").textContent = d.telefone;
        $("p-cpf").textContent = d.cpf;
        $("p-endereco").textContent = d.endereco;
        $("p-total").textContent = d.reservas;
        var badge = $("p-badge");
        badge.textContent = d.rotulo;
        badge.className = "badge " + d.classe;

        var lista = $("p-recentes");
        lista.innerHTML = "";
        var recentes = JSON.parse(d.recentes || "[]");
        if (!recentes.length) {
            var vazio = document.createElement("span");
            vazio.className = "linha suave"; vazio.textContent = "Nenhuma reserva.";
            lista.appendChild(vazio);
        }
        recentes.forEach(function (r) {
            var item = document.createElement("div");
            item.className = "res";
            var esq = document.createElement("div");
            var forte = document.createElement("strong"); forte.textContent = r.codigo + " · " + r.veiculo;
            var peq = document.createElement("small"); peq.textContent = r.periodo;
            esq.appendChild(forte); esq.appendChild(peq);
            var dir = document.createElement("span"); dir.className = "suave"; dir.textContent = r.situacao;
            item.appendChild(esq); item.appendChild(dir);
            lista.appendChild(item);
        });

        $("p-status").value = d.status;
        $("p-perfil").value = d.perfil;
        var eu = !!d.eu;
        $("p-status").disabled = eu;
        $("p-perfil").disabled = eu;
        $("p-salvar").hidden = eu;
        $("p-nota").textContent = eu
            ? "Esta é a sua conta. Para alterar seus dados, use Editar perfil no site."
            : "Inativo ou bloqueado impede o login. As reservas da pessoa continuam registradas.";
        $("p-form").action = d.url;
    }

    var painel = Painel.painelLateral(document.querySelectorAll("tbody tr[data-nome]"), preencher);

    // Promover a administrador ou bloquear pede confirmação
    $("p-form").addEventListener("submit", function (e) {
        var ativa = painel.linhaAtiva();
        var promove = $("p-perfil").value === ADMIN && ativa && ativa.dataset.perfil !== ADMIN;
        var bloqueia = $("p-status").value !== "ACTIVE" && ativa && ativa.dataset.status === "ACTIVE";
        var pergunta = promove ? "Dar acesso de administrador a esta pessoa?"
                     : bloqueia ? "Esta pessoa não conseguirá mais entrar na conta. Continuar?" : "";
        if (pergunta && !confirm(pergunta)) e.preventDefault();
    });

    Painel.enviarAoMudar(["f-perfil", "f-situacao"]);
})();

// Pop-up "Novo usuário"
(function () {
    var modal = Painel.$("modal-novo");
    Painel.$("btn-novo").addEventListener("click", function () { modal.showModal(); });
    Painel.ligarModal(modal, ["u-fechar", "u-cancelar"]);
    Painel.abrirSeTemErro(modal);
})();
