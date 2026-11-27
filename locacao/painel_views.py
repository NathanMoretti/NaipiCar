import json
import re
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Sum
from django.forms.models import model_to_dict
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from contas.models import User

from .forms import (
    CategoriaClasseForm,
    CategoriaForm,
    ClasseCarroForm,
    MarcaForm,
    ModeloCarroForm,
    VeiculoForm,
)
from .models import Categoria, CategoriaClasse, ClasseCarro, Marca, ModeloCarro, Reserva, Veiculo

def somente_admin(view):
    """Só administradores (is_staff) entram.

    Quem não está logado vai para o login. Quem está logado como cliente volta para
    o site com um aviso (sem isso, o login devolvia o cliente ao painel, em loop).
    """

    @wraps(view)
    def interna(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), resolve_url("login"))
        if not request.user.is_staff:
            messages.error(request, "Você não tem permissão para acessar o painel.")
            return redirect("index")
        return view(request, *args, **kwargs)

    return interna

TEMPLATE_VEICULOS = "locacao/painel/veiculos.html"


def _ids_reservados():
    """Veículos com reserva Pendente/Confirmada cobrindo o dia de hoje."""
    hoje = date.today()
    return set(
        Reserva.objects.filter(
            status__in=["Pendente", "Confirmada"],
            data_retirada__lte=hoje,
            data_devolucao__gte=hoje,
        ).values_list("veiculo_id", flat=True)
    )


def _contexto_veiculos(request, form=None, modal=None):
    reservados = _ids_reservados()

    lista = Veiculo.objects.select_related(
        "modelo__marca", "categoria_classe__categoria", "categoria_classe__classe"
    ).order_by("-id")

    q = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria", "")
    status = request.GET.get("status", "")

    if q:
        lista = lista.filter(
            Q(modelo__nome__icontains=q)
            | Q(modelo__marca__nome__icontains=q)
            | Q(placa__icontains=q)
        )
    if categoria:
        lista = lista.filter(categoria_classe__categoria_id=categoria)
    if status == "indisponivel":
        lista = lista.filter(disponivel=False)
    elif status == "reservado":
        lista = lista.filter(disponivel=True, id__in=reservados)
    elif status == "disponivel":
        lista = lista.filter(disponivel=True).exclude(id__in=reservados)

    pagina = Paginator(lista, 5).get_page(request.GET.get("page"))
    itens = list(pagina.object_list)
    for v in itens:
        if not v.disponivel:
            v.situacao, v.classe = "Indisponível", "indisponivel"
        elif v.id in reservados:
            v.situacao, v.classe = "Reservado", "reservado"
        else:
            v.situacao, v.classe = "Disponível", "disponivel"

    total = Veiculo.objects.count()
    indisponiveis = Veiculo.objects.filter(disponivel=False).count()
    n_reservados = Veiculo.objects.filter(disponivel=True, id__in=reservados).count()

    params = request.GET.copy()
    params.pop("page", None)

    return {
        "veiculos": itens,
        "pagina": pagina,
        "paginas": list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
        "reticencias": pagina.paginator.ELLIPSIS,
        "querystring": params.urlencode(),
        "filtro": {"q": q, "categoria": categoria, "status": status},
        "categorias": Categoria.objects.all(),
        "stats": {
            "total": total,
            "disponiveis": total - indisponiveis - n_reservados,
            "reservados": n_reservados,
            "indisponiveis": indisponiveis,
        },
        "diarias": {str(cc.id): float(cc.daily_rate) for cc in CategoriaClasse.objects.all()},
        "form": form or VeiculoForm(),
        "modal": modal,
    }


@somente_admin
def veiculos_painel(request):
    """Lista os veículos e, em POST, cadastra um novo."""
    if request.method == "POST":
        form = VeiculoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo cadastrado com sucesso.")
            return redirect("painel_veiculos")
        modal = {
            "titulo": "Cadastrar Veículo",
            "botao": "Cadastrar Veículo",
            "acao": reverse("painel_veiculos"),
        }
        return render(request, TEMPLATE_VEICULOS, _contexto_veiculos(request, form, modal))

    return render(request, TEMPLATE_VEICULOS, _contexto_veiculos(request))


@somente_admin
@require_POST
def veiculo_editar(request, pk):
    veiculo = get_object_or_404(Veiculo, pk=pk)
    form = VeiculoForm(request.POST, request.FILES, instance=veiculo)
    if form.is_valid():
        form.save()
        messages.success(request, "Veículo atualizado com sucesso.")
        if not veiculo.disponivel:
            abertas = Reserva.objects.filter(
                veiculo=veiculo,
                status__in=["Pendente", "Confirmada"],
                data_devolucao__gte=date.today(),
            ).count()
            if abertas:
                messages.warning(
                    request,
                    f"Atenção: o veículo está indisponível, mas ainda tem {abertas} "
                    f"reserva{'s' if abertas > 1 else ''} em aberto.",
                )
        return redirect("painel_veiculos")
    modal = {
        "titulo": "Editar Veículo",
        "botao": "Editar Veículo",
        "acao": reverse("painel_veiculo_editar", args=[pk]),
    }
    return render(request, TEMPLATE_VEICULOS, _contexto_veiculos(request, form, modal))


@somente_admin
@require_POST
def veiculo_excluir(request, pk):
    veiculo = get_object_or_404(Veiculo, pk=pk)
    # O banco também bloqueia (on_delete=PROTECT); aqui mostramos uma mensagem amigável
    if Reserva.objects.filter(veiculo=veiculo).exists():
        messages.error(
            request,
            "Este veículo tem reservas registradas e não pode ser excluído. "
            "Marque-o como indisponível.",
        )
    else:
        nome = str(veiculo.modelo)
        veiculo.delete()
        messages.success(request, f"Veículo {nome} excluído.")
    return redirect("painel_veiculos")


# ---------------------------------------------------------------------------
# Situação das reservas
# ---------------------------------------------------------------------------
# "Atrasado" não existe no banco: é calculado (reserva Confirmada com devolução vencida).
ROTULOS_SITUACAO = {
    "Pendente": ("Em análise", "pendente"),
    "Confirmada": ("Reservado", "confirmada"),
    "Concluída": ("Concluído", "concluida"),
    "Cancelada": ("Cancelado", "cancelada"),
}

# Para qual situação cada reserva pode ser alterada pelo administrador
TRANSICOES = {
    "Pendente": ["Pendente", "Confirmada", "Cancelada"],
    "Confirmada": ["Confirmada", "Concluída", "Cancelada"],
    "Concluída": ["Concluída"],
    "Cancelada": ["Cancelada"],
}


def _situacao(reserva, hoje):
    if reserva.status == "Confirmada" and reserva.data_devolucao < hoje:
        return "Atrasado", "atrasado"
    return ROTULOS_SITUACAO.get(reserva.status, (reserva.status, "concluida"))


def _cpf_oculto(cpf):
    cpf = cpf or ""
    return f"{cpf[:3]}.***.***-**" if cpf else "—"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
PERIODOS = [
    ("hoje", "Hoje"), ("7d", "Últimos 7 dias"), ("30d", "Últimos 30 dias"), ("mes", "Este mês"),
    ("mes_anterior", "Mês anterior"), ("ano", "Este ano"), ("personalizado", "Personalizado"),
]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _ultimo_dia(d):
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _intervalo(request, hoje):
    """Período escolhido no dashboard: devolve (chave, inicio, fim)."""
    chave = request.GET.get("periodo", "30d")
    if chave not in dict(PERIODOS):
        chave = "30d"
    ini = fim = None
    if chave == "hoje":
        ini = fim = hoje
    elif chave == "7d":
        ini, fim = hoje - timedelta(days=6), hoje
    elif chave == "mes":
        ini = hoje.replace(day=1)
        fim = _ultimo_dia(ini)
    elif chave == "mes_anterior":
        fim = hoje.replace(day=1) - timedelta(days=1)
        ini = fim.replace(day=1)
    elif chave == "ano":
        ini, fim = date(hoje.year, 1, 1), date(hoje.year, 12, 31)
    elif chave == "personalizado":
        try:
            ini = date.fromisoformat(request.GET.get("de", ""))
            fim = date.fromisoformat(request.GET.get("ate", ""))
        except ValueError:
            ini = fim = None
        if ini is None or fim < ini or (fim - ini).days > 366:
            chave, ini, fim = "30d", None, None
    if ini is None:
        ini, fim = hoje - timedelta(days=29), hoje
    return chave, ini, fim


def _variacao(atual, anterior):
    """Variação percentual em relação ao período anterior (None quando não há base de comparação)."""
    if not anterior:
        return None
    return round((atual - anterior) * 100 / anterior)


@somente_admin
def dashboard(request):
    hoje = date.today()
    chave, ini, fim = _intervalo(request, hoje)
    dias = (fim - ini).days + 1
    ant_fim = ini - timedelta(days=1)
    ant_ini = ant_fim - timedelta(days=dias - 1)

    categoria_id = request.GET.get("categoria", "")
    if not categoria_id.isdigit():
        categoria_id = ""

    def da_categoria(qs):
        return qs.filter(veiculo__categoria_classe__categoria_id=categoria_id) if categoria_id else qs

    reservas = Reserva.objects.select_related(
        "veiculo__modelo__marca", "veiculo__categoria_classe__categoria", "cliente"
    )
    no_periodo = da_categoria(reservas.filter(data_retirada__range=(ini, fim)))
    validas = no_periodo.exclude(status="Cancelada")
    anteriores = da_categoria(reservas.filter(data_retirada__range=(ant_ini, ant_fim))).exclude(status="Cancelada")

    # --- Indicadores do período (reservas com retirada no período) -----------
    n_reservas = validas.count()
    receita = validas.aggregate(t=Sum("valor_total"))["t"] or 0
    n_ant = anteriores.count()
    receita_ant = anteriores.aggregate(t=Sum("valor_total"))["t"] or 0
    ticket = receita / n_reservas if n_reservas else 0
    ticket_ant = receita_ant / n_ant if n_ant else 0
    total_com_cancel = no_periodo.count()
    canceladas = no_periodo.filter(status="Cancelada").count()
    taxa_cancel = round(canceladas * 100 / total_com_cancel) if total_com_cancel else 0

    # --- Ocupação: dias de veículo alugados ÷ dias disponíveis no período ----
    frota = Veiculo.objects.filter(disponivel=True)
    if categoria_id:
        frota = frota.filter(categoria_classe__categoria_id=categoria_id)
    n_frota = frota.count()
    frota_por_categoria = {
        l["categoria_classe__categoria_id"]: l["n"]
        for l in Veiculo.objects.filter(disponivel=True)
        .values("categoria_classe__categoria_id").annotate(n=Count("id"))
    }
    sobrepostas = da_categoria(
        reservas.filter(data_retirada__lte=fim, data_devolucao__gte=ini)
    ).exclude(status="Cancelada")
    dias_ocupados, ocupados_por_categoria = 0, {}
    for r in sobrepostas:
        d = max((min(r.data_devolucao, fim + timedelta(days=1)) - max(r.data_retirada, ini)).days, 0)
        dias_ocupados += d
        cid = r.veiculo.categoria_classe.categoria_id if r.veiculo.categoria_classe_id else None
        ocupados_por_categoria[cid] = ocupados_por_categoria.get(cid, 0) + d
    capacidade = n_frota * dias
    ocupacao = min(100, round(dias_ocupados * 100 / capacidade)) if capacidade else 0

    ocupados_hoje = frota.filter(id__in=_ids_reservados()).count()

    cartoes = [
        {"rotulo": "Receita estimada", "valor": _reais(receita), "var": _variacao(receita, receita_ant),
         "nota": "reservas com retirada no período"},
        {"rotulo": "Reservas", "valor": n_reservas, "var": _variacao(n_reservas, n_ant),
         "nota": "sem contar as canceladas"},
        {"rotulo": "Ticket médio", "valor": _reais(ticket), "var": _variacao(ticket, ticket_ant),
         "nota": "valor médio por reserva"},
        {"rotulo": "Taxa de ocupação", "valor": f"{ocupacao}%", "var": None,
         "nota": f"{dias_ocupados} de {capacidade} dias de veículo"},
        {"rotulo": "Taxa de cancelamento", "valor": f"{taxa_cancel}%", "var": None,
         "nota": f"{canceladas} de {total_com_cancel} reservas"},
        {"rotulo": "Frota hoje", "valor": f"{ocupados_hoje} de {n_frota}", "var": None,
         "nota": "veículos reservados agora"},
    ]

    # --- Gráficos: por dia (períodos até 31 dias) ou por mês -------------------
    por_dia = dias <= 31
    baldes = {}
    for r in validas:
        chave_b = r.data_retirada if por_dia else r.data_retirada.replace(day=1)
        b = baldes.setdefault(chave_b, {"reservas": 0, "receita": 0})
        b["reservas"] += 1
        b["receita"] += r.valor_total
    serie, cursor = [], (ini if por_dia else ini.replace(day=1))
    while cursor <= fim:
        b = baldes.get(cursor, {"reservas": 0, "receita": 0})
        rotulo = f"{cursor:%d/%m}" if por_dia else f"{MESES[cursor.month - 1]}/{cursor:%y}"
        serie.append({"rotulo": rotulo, "reservas": b["reservas"], "receita": b["receita"]})
        cursor = cursor + timedelta(days=1) if por_dia else _ultimo_dia(cursor) + timedelta(days=1)
    maior_receita = max((b["receita"] for b in serie), default=0) or 1
    maior_reservas = max((b["reservas"] for b in serie), default=0) or 1
    passo = max(1, len(serie) // 8)
    for i, b in enumerate(serie):
        b["h_receita"] = max(round(b["receita"] * 100 / maior_receita), 2) if b["receita"] else 0
        b["h_reservas"] = max(round(b["reservas"] * 100 / maior_reservas), 2) if b["reservas"] else 0
        b["receita_txt"] = _reais(b["receita"])
        b["mostrar"] = i % passo == 0

    # --- Reservas por situação -------------------------------------------------
    contagem = {l["status"]: l["n"] for l in no_periodo.order_by().values("status").annotate(n=Count("id"))}
    atrasadas_periodo = no_periodo.filter(status="Confirmada", data_devolucao__lt=hoje).count()
    situacoes = [
        ("Em análise", "pendente", contagem.get("Pendente", 0)),
        ("Reservado", "confirmada", contagem.get("Confirmada", 0) - atrasadas_periodo),
        ("Atrasado", "atrasado", atrasadas_periodo),
        ("Concluído", "concluida", contagem.get("Concluída", 0)),
        ("Cancelado", "cancelada", contagem.get("Cancelada", 0)),
    ]
    situacoes = [
        {"rotulo": r, "classe": c, "n": n, "pct": round(n * 100 / total_com_cancel) if total_com_cancel else 0}
        for r, c, n in situacoes
    ]

    # --- Desempenho por categoria ---------------------------------------------
    por_categoria = {}
    for r in validas:
        cc = r.veiculo.categoria_classe
        cid = cc.categoria_id if cc else None
        c = por_categoria.setdefault(cid, {"nome": cc.categoria.nome if cc else "Sem categoria", "n": 0, "receita": 0})
        c["n"] += 1
        c["receita"] += r.valor_total
    categorias = []
    for cid, c in por_categoria.items():
        cap = frota_por_categoria.get(cid, 0) * dias
        c["ocupacao"] = min(100, round(ocupados_por_categoria.get(cid, 0) * 100 / cap)) if cap else 0
        c["pct"] = round(c["n"] * 100 / n_reservas) if n_reservas else 0
        c["receita_txt"] = _reais(c["receita"])
        categorias.append(c)
    categorias.sort(key=lambda c: -c["n"])

    # --- Rankings -----------------------------------------------------------------
    top_veiculos = [
        {"nome": f'{l["veiculo__modelo__marca__nome"]} {l["veiculo__modelo__nome"]}',
         "placa": l["veiculo__placa"] or "sem placa", "n": l["n"], "receita_txt": _reais(l["total"])}
        for l in validas.order_by().values(
            "veiculo_id", "veiculo__modelo__marca__nome", "veiculo__modelo__nome", "veiculo__placa"
        ).annotate(n=Count("id"), total=Sum("valor_total")).order_by("-n", "-total")[:5]
    ]
    top_clientes = [
        {"nome": l["nome_cliente"], "n": l["n"], "receita_txt": _reais(l["total"])}
        for l in validas.exclude(cliente=None).order_by().values("cliente_id", "nome_cliente")
        .annotate(n=Count("id"), total=Sum("valor_total")).order_by("-n", "-total")[:5]
    ]

    # --- Atenção, radar do dia e agenda (não dependem do período) ------------------
    pendentes = Reserva.objects.filter(status="Pendente").count()
    atrasos = Reserva.objects.filter(status="Confirmada", data_devolucao__lt=hoje).count()

    def linha(r, acao, classe, status):
        placa = r.veiculo.placa or "sem placa"
        return {"cliente": r.nome_cliente, "veiculo": f"{r.veiculo.modelo} ({placa})",
                "acao": acao, "classe": classe, "status": status}

    radar = [linha(r, "Atrasado", "atrasado", "Atrasado")
             for r in reservas.filter(status="Confirmada", data_devolucao__lt=hoje).order_by("data_devolucao")]
    radar += [linha(r, "Retirada", "retirada", "Aguardando" if r.status == "Confirmada" else "Em análise")
              for r in reservas.filter(data_retirada=hoje, status__in=["Pendente", "Confirmada"])]
    radar += [linha(r, "Devolução", "devolucao", "No prazo")
              for r in reservas.filter(data_devolucao=hoje, status="Confirmada")]

    agenda = {}
    limite = hoje + timedelta(days=7)
    for r in reservas.filter(data_retirada__gt=hoje, data_retirada__lte=limite, status__in=["Pendente", "Confirmada"]):
        agenda.setdefault(r.data_retirada, []).append(linha(r, "Retirada", "retirada", ""))
    for r in reservas.filter(data_devolucao__gt=hoje, data_devolucao__lte=limite, status="Confirmada"):
        agenda.setdefault(r.data_devolucao, []).append(linha(r, "Devolução", "devolucao", ""))
    agenda_lista = [{"data": d, "itens": agenda[d]} for d in sorted(agenda)]

    return render(request, "locacao/painel/dashboard.html", {
        "hoje": hoje,
        "periodos": PERIODOS,
        "chave": chave,
        "ini": ini, "fim": fim, "dias": dias, "ant_ini": ant_ini, "ant_fim": ant_fim,
        "categoria_id": categoria_id,
        "todas_categorias": Categoria.objects.order_by("nome"),
        "cartoes": cartoes,
        "serie": serie,
        "por_dia": por_dia,
        "situacoes": situacoes,
        "categorias": categorias,
        "top_veiculos": top_veiculos,
        "top_clientes": top_clientes,
        "pendentes": pendentes,
        "atrasos": atrasos,
        "radar": radar[:8],
        "total_radar": len(radar),
        "agenda": agenda_lista,
    })


# ---------------------------------------------------------------------------
# Reservas
# ---------------------------------------------------------------------------
@somente_admin
def reservas_painel(request):
    hoje = date.today()
    lista = Reserva.objects.select_related(
        "cliente", "veiculo__modelo__marca", "veiculo__categoria_classe__categoria"
    ).order_by("-id")

    q = request.GET.get("q", "").strip()
    situacao = request.GET.get("situacao", "")
    periodo = request.GET.get("periodo", "")

    if q:
        filtro = (
            Q(nome_cliente__icontains=q) | Q(email_cliente__icontains=q)
            | Q(veiculo__placa__icontains=q) | Q(veiculo__modelo__nome__icontains=q)
            | Q(veiculo__modelo__marca__nome__icontains=q)
        )
        codigo = re.match(r"^(?:res-?)?(\d+)$", q, re.IGNORECASE)  # "RES-1048" ou "1048"
        if codigo:
            filtro |= Q(id=int(codigo.group(1)))
        lista = lista.filter(filtro)

    if situacao == "pendente":
        lista = lista.filter(status="Pendente")
    elif situacao == "confirmada":
        lista = lista.filter(status="Confirmada", data_devolucao__gte=hoje)
    elif situacao == "atrasado":
        lista = lista.filter(status="Confirmada", data_devolucao__lt=hoje)
    elif situacao == "concluida":
        lista = lista.filter(status="Concluída")
    elif situacao == "cancelada":
        lista = lista.filter(status="Cancelada")

    if periodo == "hoje":
        lista = lista.filter(Q(data_retirada=hoje) | Q(data_devolucao=hoje))
    elif periodo == "semana":
        lista = lista.filter(data_retirada__gte=hoje, data_retirada__lte=hoje + timedelta(days=7))
    elif periodo == "mes":
        lista = lista.filter(data_retirada__year=hoje.year, data_retirada__month=hoje.month)

    pagina = Paginator(lista, 5).get_page(request.GET.get("page"))
    itens = list(pagina.object_list)
    for r in itens:
        r.dias = max((r.data_devolucao - r.data_retirada).days, 1)
        r.diaria_calculada = r.valor_total / r.dias
        r.rotulo, r.classe = _situacao(r, hoje)
        r.cpf = getattr(r.cliente, "cpf", "") if r.cliente else ""
        r.cpf_oculto = _cpf_oculto(r.cpf)
        r.opcoes = "|".join(TRANSICOES.get(r.status, [r.status]))

    todas = Reserva.objects
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "locacao/painel/reservas.html", {
        "reservas": itens,
        "pagina": pagina,
        "paginas": list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
        "reticencias": pagina.paginator.ELLIPSIS,
        "querystring": params.urlencode(),
        "filtro": {"q": q, "situacao": situacao, "periodo": periodo},
        "stats": {
            "total": todas.count(),
            "analise": todas.filter(status="Pendente").count(),
            "reservadas": todas.filter(status="Confirmada", data_devolucao__gte=hoje).count(),
            "atrasadas": todas.filter(status="Confirmada", data_devolucao__lt=hoje).count(),
            "concluidas": todas.filter(status="Concluída").count(),
        },
        "rotulos": {k: v[0] for k, v in ROTULOS_SITUACAO.items()},
    })


@somente_admin
@require_POST
def reserva_situacao(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    novo = request.POST.get("status", "")
    destino = request.POST.get("voltar", "")
    if not (destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()})):
        destino = reverse("painel_reservas")

    if novo not in TRANSICOES.get(reserva.status, []):
        messages.error(request, "Não é possível mudar a reserva para essa situação.")
    elif novo == reserva.status:
        messages.info(request, "Nenhuma alteração feita.")
    else:
        reserva.status = novo
        reserva.save(update_fields=["status"])
        messages.success(request, f"Reserva RES-{reserva.id:04d} atualizada para {ROTULOS_SITUACAO[novo][0]}.")
    return redirect(destino)


# ---------------------------------------------------------------------------
# Cadastros: marcas, modelos, categorias, classes e diárias
# ---------------------------------------------------------------------------
def _reais(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


# Cada aba é descrita aqui; as views abaixo servem para todas elas.
CADASTROS = {
    "marcas": {
        "titulo": "Marcas", "singular": "marca", "artigo": "a",
        "model": Marca, "form": MarcaForm,
        "ordem": ["nome"], "relacionados": [], "busca": ["nome"],
        "colunas": ["Marca", "Modelos cadastrados"],
        "celulas": lambda o: [o.nome, ModeloCarro.objects.filter(marca=o).count()],
        "em_uso": lambda o: ModeloCarro.objects.filter(marca=o).exists(),
        "motivo": "Esta marca tem modelos cadastrados.",
    },
    "modelos": {
        "titulo": "Modelos", "singular": "modelo", "artigo": "o",
        "model": ModeloCarro, "form": ModeloCarroForm,
        "ordem": ["marca__nome", "nome"], "relacionados": ["marca"], "busca": ["nome", "marca__nome"],
        "colunas": ["Marca", "Modelo", "Assentos", "Malas", "Veículos"],
        "celulas": lambda o: [o.marca.nome, o.nome, getattr(o, "assentos", "—"), getattr(o, "malas", "—"),
                              Veiculo.objects.filter(modelo=o).count()],
        "em_uso": lambda o: Veiculo.objects.filter(modelo=o).exists(),
        "motivo": "Este modelo está em uso por veículos cadastrados.",
    },
    "categorias": {
        "titulo": "Categorias", "singular": "categoria", "artigo": "a",
        "model": Categoria, "form": CategoriaForm,
        "ordem": ["nome"], "relacionados": [], "busca": ["nome", "descricao"],
        "colunas": ["Categoria", "Descrição", "Diárias cadastradas"],
        "celulas": lambda o: [o.nome, o.descricao or "—", CategoriaClasse.objects.filter(categoria=o).count()],
        "em_uso": lambda o: CategoriaClasse.objects.filter(categoria=o).exists(),
        "motivo": "Esta categoria tem diárias cadastradas.",
    },
    "classes": {
        "titulo": "Classes", "singular": "classe", "artigo": "a",
        "model": ClasseCarro, "form": ClasseCarroForm,
        "ordem": ["nome"], "relacionados": [], "busca": ["nome"],
        "colunas": ["Classe", "Diárias cadastradas"],
        "celulas": lambda o: [o.nome, CategoriaClasse.objects.filter(classe=o).count()],
        "em_uso": lambda o: CategoriaClasse.objects.filter(classe=o).exists(),
        "motivo": "Esta classe tem diárias cadastradas.",
    },
    "diarias": {
        "titulo": "Diárias", "singular": "diária", "artigo": "a",
        "model": CategoriaClasse, "form": CategoriaClasseForm,
        "ordem": ["categoria__nome", "classe__nome"], "relacionados": ["categoria", "classe"],
        "busca": ["categoria__nome", "classe__nome"],
        "colunas": ["Categoria", "Classe", "Diária", "Veículos"],
        "celulas": lambda o: [o.categoria.nome, o.classe.nome, _reais(o.daily_rate),
                              Veiculo.objects.filter(categoria_classe=o).count()],
        "em_uso": lambda o: Veiculo.objects.filter(categoria_classe=o).exists(),
        "motivo": "Esta combinação está em uso por veículos cadastrados.",
    },
}


def _config(aba):
    if aba not in CADASTROS:
        raise Http404("Cadastro não encontrado.")
    return CADASTROS[aba]


def _contexto_cadastros(request, aba, form=None, modal=None):
    cfg = _config(aba)
    lista = cfg["model"].objects.all()
    if cfg["relacionados"]:
        lista = lista.select_related(*cfg["relacionados"])
    lista = lista.order_by(*cfg["ordem"])

    q = request.GET.get("q", "").strip()
    if q:
        filtro = Q()
        for campo in cfg["busca"]:
            filtro |= Q(**{f"{campo}__icontains": q})
        lista = lista.filter(filtro)

    pagina = Paginator(lista, 8).get_page(request.GET.get("page"))
    campos = cfg["form"]._meta.fields
    linhas = [
        {
            "celulas": cfg["celulas"](o),
            "nome": str(o),
            "json": json.dumps(model_to_dict(o, fields=campos), cls=DjangoJSONEncoder),
            "url_editar": reverse("painel_cadastro_editar", args=[aba, o.pk]),
            "url_excluir": reverse("painel_cadastro_excluir", args=[aba, o.pk]),
        }
        for o in pagina.object_list
    ]

    params = request.GET.copy()
    params.pop("page", None)
    vazio = cfg["form"]()

    return {
        "aba": aba,
        "cfg": cfg,
        "abas": [(chave, c["titulo"]) for chave, c in CADASTROS.items()],
        "linhas": linhas,
        "pagina": pagina,
        "paginas": list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
        "reticencias": pagina.paginator.ELLIPSIS,
        "querystring": params.urlencode(),
        "q": q,
        "form": form or vazio,
        "iniciais": json.dumps({n: vazio[n].value() for n in vazio.fields}, cls=DjangoJSONEncoder),
        "url_novo": reverse("painel_cadastros", args=[aba]),
        "modal": modal,
    }


@somente_admin
def cadastros_inicio(request):
    return redirect("painel_cadastros", aba="marcas")


@somente_admin
def cadastros(request, aba):
    """Lista a aba escolhida e, em POST, cadastra um novo registro."""
    cfg = _config(aba)
    if request.method == "POST":
        form = cfg["form"](request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{cfg['singular'].capitalize()} cadastrad{cfg['artigo']} com sucesso.")
            return redirect("painel_cadastros", aba=aba)
        modal = {"titulo": f"Cadastrar {cfg['singular']}", "botao": "Cadastrar", "acao": reverse("painel_cadastros", args=[aba])}
        return render(request, "locacao/painel/cadastros.html", _contexto_cadastros(request, aba, form, modal))
    return render(request, "locacao/painel/cadastros.html", _contexto_cadastros(request, aba))


@somente_admin
@require_POST
def cadastro_editar(request, aba, pk):
    cfg = _config(aba)
    objeto = get_object_or_404(cfg["model"], pk=pk)
    form = cfg["form"](request.POST, instance=objeto)
    if form.is_valid():
        form.save()
        messages.success(request, f"{cfg['singular'].capitalize()} atualizad{cfg['artigo']} com sucesso.")
        return redirect("painel_cadastros", aba=aba)
    modal = {"titulo": f"Editar {cfg['singular']}", "botao": "Salvar alterações",
             "acao": reverse("painel_cadastro_editar", args=[aba, pk])}
    return render(request, "locacao/painel/cadastros.html", _contexto_cadastros(request, aba, form, modal))


@somente_admin
@require_POST
def cadastro_excluir(request, aba, pk):
    cfg = _config(aba)
    objeto = get_object_or_404(cfg["model"], pk=pk)
    if cfg["em_uso"](objeto):
        messages.error(request, f"{cfg['motivo']} Remova ou altere esses registros antes de excluir.")
    else:
        nome = str(objeto)
        objeto.delete()
        messages.success(request, f"{nome} excluíd{cfg['artigo']}.")
    return redirect("painel_cadastros", aba=aba)


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------
SITUACOES_USUARIO = {
    User.ACTIVE: ("Ativo", "ativo"),
    User.INACTIVE: ("Inativo", "inativo"),
    User.PENDING: ("Pendente", "pendente"),
    User.BLOCKED: ("Bloqueado", "bloqueado"),
}


@somente_admin
def usuarios_painel(request):
    lista = User.objects.select_related("address").order_by("first_name", "last_name")

    q = request.GET.get("q", "").strip()
    perfil = request.GET.get("perfil", "")
    situacao = request.GET.get("situacao", "")

    for termo in q.split():  # cada palavra precisa aparecer em algum campo
        lista = lista.filter(
            Q(first_name__icontains=termo) | Q(last_name__icontains=termo)
            | Q(email__icontains=termo) | Q(cpf__icontains=termo) | Q(phone__icontains=termo)
        )
    if perfil == "cliente":
        lista = lista.filter(profile_type=User.USER)
    elif perfil == "admin":
        lista = lista.filter(profile_type=User.ADMIN)
    if situacao in SITUACOES_USUARIO:
        lista = lista.filter(status=situacao)

    pagina = Paginator(lista, 6).get_page(request.GET.get("page"))
    itens = list(pagina.object_list)
    ids = [u.id for u in itens]

    # Reservas dos usuários desta página (sem depender do nome da relação no modelo)
    totais = {
        linha["cliente_id"]: linha["n"]
        for linha in Reserva.objects.filter(cliente_id__in=ids).values("cliente_id").annotate(n=Count("id"))
    }
    recentes = {}
    for r in Reserva.objects.filter(cliente_id__in=ids).select_related("veiculo__modelo").order_by("-id"):
        if len(recentes.setdefault(r.cliente_id, [])) < 3:
            rotulo, _ = _situacao(r, date.today())
            recentes[r.cliente_id].append({
                "codigo": f"RES-{r.id:04d}",
                "veiculo": str(r.veiculo.modelo),
                "periodo": f"{r.data_retirada:%d/%m/%Y} → {r.data_devolucao:%d/%m/%Y}",
                "situacao": rotulo,
            })

    for u in itens:
        u.rotulo, u.classe = SITUACOES_USUARIO.get(u.status, (u.status, "inativo"))
        u.eh_admin = u.profile_type == User.ADMIN
        u.cpf_oculto = _cpf_oculto(u.cpf)
        u.n_reservas = totais.get(u.id, 0)
        u.eu = u.pk == request.user.pk
        u.endereco_texto = str(u.address) if u.address_id else "—"
        u.recentes = json.dumps(recentes.get(u.id, []), cls=DjangoJSONEncoder)

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "locacao/painel/usuarios.html", {
        "usuarios": itens,
        "pagina": pagina,
        "paginas": list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
        "reticencias": pagina.paginator.ELLIPSIS,
        "querystring": params.urlencode(),
        "filtro": {"q": q, "perfil": perfil, "situacao": situacao},
        "stats": {
            "total": User.objects.count(),
            "clientes": User.objects.filter(profile_type=User.USER).count(),
            "admins": User.objects.filter(profile_type=User.ADMIN).count(),
            "inativos": User.objects.exclude(status=User.ACTIVE).count(),
        },
        "ADMIN": User.ADMIN,
        "USER": User.USER,
    })


@somente_admin
@require_POST
def usuario_atualizar(request, pk):
    alvo = get_object_or_404(User, pk=pk)
    destino = request.POST.get("voltar", "")
    if not (destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()})):
        destino = reverse("painel_usuarios")

    status = request.POST.get("status", "")
    try:
        perfil = int(request.POST.get("perfil", ""))
    except ValueError:
        perfil = None

    if alvo.pk == request.user.pk:
        messages.error(request, "Você não pode alterar a sua própria conta por aqui. Use Editar perfil.")
    elif status not in SITUACOES_USUARIO or perfil not in (User.USER, User.ADMIN):
        messages.error(request, "Valores inválidos para a conta.")
    else:
        deixa_de_ser_admin_ativo = alvo.is_staff and (status != User.ACTIVE or perfil != User.ADMIN)
        outros_admins = User.objects.filter(profile_type=User.ADMIN, status=User.ACTIVE).exclude(pk=alvo.pk).count()
        if deixa_de_ser_admin_ativo and outros_admins == 0:
            messages.error(request, "Precisa existir pelo menos um administrador ativo.")
        elif status == alvo.status and perfil == alvo.profile_type:
            messages.info(request, "Nenhuma alteração feita.")
        else:
            alvo.status, alvo.profile_type = status, perfil
            alvo.save(update_fields=["status", "profile_type"])
            messages.success(request, f"Conta de {alvo.full_name} atualizada.")
    return redirect(destino)