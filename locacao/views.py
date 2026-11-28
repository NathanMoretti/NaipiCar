from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from .apoio import destino_seguro, paginar
from .models import Categoria, Marca, Reserva, Veiculo
from .regras import ReservaInvalida, criar_reserva

Status = Reserva.Status


def _faixa(valores):
    """'5' quando todos iguais, ou '4 a 7' quando variam."""
    menor, maior = min(valores), max(valores)
    return str(menor) if menor == maior else f"{menor} a {maior}"


def _opcoes_busca():
    """Listas usadas no formulário de busca (home e catálogo)."""
    try:
        motorizacoes = [(v, r) for v, r in Veiculo._meta.get_field("motorizacao").choices if v]
    except FieldDoesNotExist:
        motorizacoes = []
    disponiveis = Veiculo.objects.filter(disponivel=True)
    return {
        # Só aparecem categorias e marcas que já têm veículo disponível cadastrado
        "todas_categorias": Categoria.objects.filter(
            id__in=disponiveis.values("categoria_classe__categoria_id")
        ).order_by("nome"),
        "marcas": Marca.objects.filter(id__in=disponiveis.values("modelo__marca_id")).order_by("nome"),
        "motorizacoes": motorizacoes,
    }


def index(request):
    """Página inicial: cada categoria aparece sozinha assim que tem um veículo disponível cadastrado."""
    categorias = []
    for cat in Categoria.objects.order_by("nome"):
        lista = list(
            Veiculo.objects.filter(categoria_classe__categoria=cat, disponivel=True)
            .select_related("modelo", "categoria_classe")
            .order_by("-id")
        )
        if not lista:
            continue  # categoria sem veículo cadastrado não aparece
        com_foto = next((v for v in lista if v.imagem), None)  # usa a foto do carro mais recente que tiver
        categorias.append({
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "assentos": _faixa([v.modelo.assentos for v in lista]),
            "malas": _faixa([v.modelo.malas for v in lista]),
            "imagem": com_foto.imagem if com_foto else None,
            "preco_minimo": min(v.categoria_classe.daily_rate for v in lista),
            "quantidade": len(lista),
        })
    return render(request, "locacao/index.html", {"categorias": categorias, **_opcoes_busca()})


ORDENACOES = {
    "nome": ("modelo__marca__nome", "modelo__nome"),
    "preco_asc": ("categoria_classe__daily_rate", "modelo__nome"),
    "preco_desc": ("-categoria_classe__daily_rate", "modelo__nome"),
    "ano_desc": ("-ano", "modelo__nome"),
    "assentos_desc": ("-modelo__assentos", "modelo__nome"),
}


def _inteiro(valor):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def veiculos(request):
    """Catálogo com filtros: período livre, categoria, marca, motorização, assentos, malas, preço e texto."""
    opcoes = _opcoes_busca()
    get = request.GET
    lista = Veiculo.objects.select_related("modelo__marca", "categoria_classe__categoria")

    categoria = get.get("categoria", "")
    marca = get.get("marca", "")
    motorizacao = get.get("motorizacao", "")
    assentos = _inteiro(get.get("assentos"))
    malas = _inteiro(get.get("malas"))
    q = get.get("q", "").strip()
    ordem = get.get("ordem", "nome")
    incluir_indisponiveis = get.get("todos") == "1"
    try:
        preco_max = Decimal(get.get("preco_max", "").strip().replace(",", "."))
        if not preco_max.is_finite() or preco_max <= 0:
            preco_max = None
    except InvalidOperation:
        preco_max = None

    if categoria.isdigit():
        lista = lista.filter(categoria_classe__categoria_id=categoria)
    if marca.isdigit():
        lista = lista.filter(modelo__marca_id=marca)
    if motorizacao in dict(opcoes["motorizacoes"]):
        lista = lista.filter(motorizacao=motorizacao)
    if assentos:
        lista = lista.filter(modelo__assentos__gte=assentos)
    if malas:
        lista = lista.filter(modelo__malas__gte=malas)
    if preco_max is not None:
        lista = lista.filter(categoria_classe__daily_rate__lte=preco_max)
    for termo in q.split():  # cada palavra precisa aparecer na marca ou no modelo
        lista = lista.filter(Q(modelo__nome__icontains=termo) | Q(modelo__marca__nome__icontains=termo))
    if not incluir_indisponiveis:
        lista = lista.filter(disponivel=True)

    retirada = get.get("retirada")
    devolucao = get.get("devolucao")
    if retirada and devolucao and retirada <= devolucao:
        ocupados = (
            Reserva.objects.filter(data_retirada__lte=devolucao, data_devolucao__gte=retirada)
            .exclude(status=Status.CANCELADA)
            .values_list("veiculo_id", flat=True)
        )
        lista = lista.exclude(id__in=ocupados)

    lista = lista.order_by(*ORDENACOES.get(ordem, ORDENACOES["nome"]))
    paginacao = paginar(request, lista, 9)
    pagina = paginacao["pagina"]

    avancados = [bool(marca), bool(motorizacao), bool(assentos), bool(malas), preco_max is not None,
                 bool(q), ordem in ORDENACOES and ordem != "nome", incluir_indisponiveis]

    return render(request, "locacao/veiculos.html", {
        **opcoes,
        "veiculos": list(pagina.object_list),
        **paginacao,
        "filtro": {
            "retirada": retirada or "",
            "devolucao": devolucao or "",
            "categoria": categoria,
            "marca": marca,
            "motorizacao": motorizacao,
            "assentos": str(assentos or ""),
            "malas": str(malas or ""),
            "preco_max": get.get("preco_max", "") if preco_max is not None else "",
            "q": q,
            "ordem": ordem if ordem in ORDENACOES else "nome",
            "todos": incluir_indisponiveis,
            "n_avancados": sum(avancados),
            "avancado": any(avancados),
            "ativo": any(avancados) or bool(retirada or devolucao or categoria),
        },
    })


@login_required(login_url="login")
@require_POST
def reservar_veiculo(request, veiculo_id):
    """Cria a reserva com os dados da conta do cliente logado (regras em regras.py)."""
    get_object_or_404(Veiculo, id=veiculo_id)
    voltar = destino_seguro(request, "veiculos")

    try:
        d1 = datetime.strptime(request.POST.get("data_retirada", ""), "%Y-%m-%d").date()
        d2 = datetime.strptime(request.POST.get("data_devolucao", ""), "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Informe datas válidas.")
        return redirect(voltar)

    try:
        criar_reserva(veiculo_id, request.user, d1, d2, status=Status.PENDENTE)
    except ReservaInvalida as erro:
        messages.error(request, str(erro))
        return redirect(voltar)

    messages.success(request, "Reserva solicitada! Acompanhe a situação em Minhas Reservas.")
    return redirect("minhas_reservas")


# Como cada situação do banco aparece para o cliente: (texto, classe CSS)
ROTULOS_STATUS = {
    Status.PENDENTE: ("Em análise", "pendente"),
    Status.CONFIRMADA: ("Reservada", "confirmada"),
    Status.CONCLUIDA: ("Concluída", "concluida"),
    Status.CANCELADA: ("Cancelada", "cancelada"),
}


@login_required(login_url="login")
def minhas_reservas(request):
    # Exibe apenas as reservas associadas ao cliente logado no momento
    lista = (
        Reserva.objects.filter(cliente=request.user)
        .select_related("veiculo__modelo__marca", "veiculo__categoria_classe__categoria")
        .order_by("-data_criacao")
    )

    aba = request.GET.get("aba", "todas")
    if aba == "atuais":
        lista = lista.filter(status__in=Reserva.EM_ABERTO)
    elif aba == "historico":
        lista = lista.filter(status__in=Reserva.FINALIZADAS)
    else:
        aba = "todas"

    paginacao = paginar(request, lista, 6)
    pagina = paginacao["pagina"]
    itens = list(pagina.object_list)
    hoje = timezone.localdate()
    for r in itens:
        r.dias = max((r.data_devolucao - r.data_retirada).days, 1)
        r.diaria_calculada = r.valor_total / r.dias
        r.rotulo, r.classe = ROTULOS_STATUS.get(r.status, (r.status, "concluida"))
        r.cancelavel = r.status in Reserva.EM_ABERTO and r.data_retirada >= hoje

    return render(request, "locacao/minhas_reservas.html", {
        "reservas": itens,
        "pagina": pagina,
        "aba": aba,
    })


@login_required(login_url="login")
@require_POST
def cancelar_reserva(request, reserva_id):
    # Só o dono da reserva pode cancelar, e só antes da retirada
    reserva = get_object_or_404(Reserva, id=reserva_id, cliente=request.user)
    if reserva.status in Reserva.EM_ABERTO and reserva.data_retirada >= timezone.localdate():
        reserva.status = Status.CANCELADA
        reserva.save(update_fields=["status"])
        messages.success(request, f"Reserva RES-{reserva.id:04d} cancelada.")
    else:
        messages.error(request, "Esta reserva não pode mais ser cancelada.")
    return redirect("minhas_reservas")