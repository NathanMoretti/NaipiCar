"""Painel: dashboard com indicadores, gráficos, radar do dia e agenda."""
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from ..models import Categoria, Reserva, Veiculo
from .comum import Status, reais, somente_admin
from .veiculos import ids_reservados

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
    hoje = timezone.localdate()
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
    validas = no_periodo.exclude(status=Status.CANCELADA)
    anteriores = da_categoria(reservas.filter(data_retirada__range=(ant_ini, ant_fim))).exclude(status=Status.CANCELADA)

    # --- Indicadores do período (reservas com retirada no período) -----------
    n_reservas = validas.count()
    receita = validas.aggregate(t=Sum("valor_total"))["t"] or 0
    n_ant = anteriores.count()
    receita_ant = anteriores.aggregate(t=Sum("valor_total"))["t"] or 0
    ticket = receita / n_reservas if n_reservas else 0
    ticket_ant = receita_ant / n_ant if n_ant else 0
    total_com_cancel = no_periodo.count()
    canceladas = no_periodo.filter(status=Status.CANCELADA).count()
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
    ).exclude(status=Status.CANCELADA)
    dias_ocupados, ocupados_por_categoria = 0, {}
    for r in sobrepostas:
        d = max((min(r.data_devolucao, fim + timedelta(days=1)) - max(r.data_retirada, ini)).days, 0)
        dias_ocupados += d
        cid = r.veiculo.categoria_classe.categoria_id if r.veiculo.categoria_classe_id else None
        ocupados_por_categoria[cid] = ocupados_por_categoria.get(cid, 0) + d
    capacidade = n_frota * dias
    ocupacao = min(100, round(dias_ocupados * 100 / capacidade)) if capacidade else 0

    ocupados_hoje = frota.filter(id__in=ids_reservados()).count()

    cartoes = [
        {"rotulo": "Receita estimada", "valor": reais(receita), "var": _variacao(receita, receita_ant),
         "nota": "reservas com retirada no período"},
        {"rotulo": "Reservas", "valor": n_reservas, "var": _variacao(n_reservas, n_ant),
         "nota": "sem contar as canceladas"},
        {"rotulo": "Ticket médio", "valor": reais(ticket), "var": _variacao(ticket, ticket_ant),
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
        b["receita_txt"] = reais(b["receita"])
        b["mostrar"] = i % passo == 0

    # --- Reservas por situação -------------------------------------------------
    contagem = {l["status"]: l["n"] for l in no_periodo.order_by().values("status").annotate(n=Count("id"))}
    atrasadas_periodo = no_periodo.filter(status=Status.CONFIRMADA, data_devolucao__lt=hoje).count()
    situacoes = [
        ("Em análise", "pendente", contagem.get(Status.PENDENTE, 0)),
        ("Reservado", "confirmada", contagem.get(Status.CONFIRMADA, 0) - atrasadas_periodo),
        ("Atrasado", "atrasado", atrasadas_periodo),
        ("Concluído", "concluida", contagem.get(Status.CONCLUIDA, 0)),
        ("Cancelado", "cancelada", contagem.get(Status.CANCELADA, 0)),
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
        c["receita_txt"] = reais(c["receita"])
        categorias.append(c)
    categorias.sort(key=lambda c: -c["n"])

    # --- Rankings -----------------------------------------------------------------
    top_veiculos = [
        {"nome": f'{l["veiculo__modelo__marca__nome"]} {l["veiculo__modelo__nome"]}',
         "placa": l["veiculo__placa"] or "sem placa", "n": l["n"], "receita_txt": reais(l["total"])}
        for l in validas.order_by().values(
            "veiculo_id", "veiculo__modelo__marca__nome", "veiculo__modelo__nome", "veiculo__placa"
        ).annotate(n=Count("id"), total=Sum("valor_total")).order_by("-n", "-total")[:5]
    ]
    top_clientes = [
        {"nome": l["nome_cliente"], "n": l["n"], "receita_txt": reais(l["total"])}
        for l in validas.exclude(cliente=None).order_by().values("cliente_id", "nome_cliente")
        .annotate(n=Count("id"), total=Sum("valor_total")).order_by("-n", "-total")[:5]
    ]

    # --- Atenção, radar do dia e agenda (não dependem do período) ------------------
    pendentes = Reserva.objects.filter(status=Status.PENDENTE).count()
    atrasos = Reserva.objects.filter(status=Status.CONFIRMADA, data_devolucao__lt=hoje).count()

    def linha(r, acao, classe, status):
        placa = r.veiculo.placa or "sem placa"
        return {"cliente": r.nome_cliente, "veiculo": f"{r.veiculo.modelo} ({placa})",
                "acao": acao, "classe": classe, "status": status}

    radar = [linha(r, "Atrasado", "atrasado", "Atrasado")
             for r in reservas.filter(status=Status.CONFIRMADA, data_devolucao__lt=hoje).order_by("data_devolucao")]
    radar += [linha(r, "Retirada", "retirada", "Aguardando" if r.status == Status.CONFIRMADA else "Em análise")
              for r in reservas.filter(data_retirada=hoje, status__in=Reserva.EM_ABERTO)]
    radar += [linha(r, "Devolução", "devolucao", "No prazo")
              for r in reservas.filter(data_devolucao=hoje, status=Status.CONFIRMADA)]

    agenda = {}
    limite = hoje + timedelta(days=7)
    for r in reservas.filter(data_retirada__gt=hoje, data_retirada__lte=limite, status__in=Reserva.EM_ABERTO):
        agenda.setdefault(r.data_retirada, []).append(linha(r, "Retirada", "retirada", ""))
    for r in reservas.filter(data_devolucao__gt=hoje, data_devolucao__lte=limite, status=Status.CONFIRMADA):
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
