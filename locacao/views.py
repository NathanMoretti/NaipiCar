from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Categoria, Marca, Reserva, Veiculo


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
            .exclude(status="Cancelada")
            .values_list("veiculo_id", flat=True)
        )
        lista = lista.exclude(id__in=ocupados)

    lista = lista.order_by(*ORDENACOES.get(ordem, ORDENACOES["nome"]))
    pagina = Paginator(lista, 9).get_page(get.get("page"))

    avancados = [bool(marca), bool(motorizacao), bool(assentos), bool(malas), preco_max is not None,
                 bool(q), ordem in ORDENACOES and ordem != "nome", incluir_indisponiveis]
    params = get.copy()
    params.pop("page", None)

    return render(request, "locacao/veiculos.html", {
        **opcoes,
        "veiculos": list(pagina.object_list),
        "pagina": pagina,
        "paginas": list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
        "reticencias": pagina.paginator.ELLIPSIS,
        "querystring": params.urlencode(),
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


def _destino_voltar(request):
    """Volta para a página de onde o cliente veio (só endereços do próprio site)."""
    destino = request.POST.get("voltar", "")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return destino
    return reverse("veiculos")


@login_required(login_url="login")
@require_POST
def reservar_veiculo(request, veiculo_id):
    """Cria a reserva com os dados da conta do cliente logado."""
    get_object_or_404(Veiculo, id=veiculo_id)
    voltar = _destino_voltar(request)

    try:
        d1 = datetime.strptime(request.POST.get("data_retirada", ""), "%Y-%m-%d").date()
        d2 = datetime.strptime(request.POST.get("data_devolucao", ""), "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Informe datas válidas.")
        return redirect(voltar)

    dias = (d2 - d1).days

    # Verificar o período e gravar a reserva precisam acontecer "de uma vez só".
    # O select_for_update() trava a linha do veículo até o fim da transação: se dois
    # clientes pedirem o mesmo carro ao mesmo tempo, o segundo espera o primeiro terminar
    # e então já enxerga a reserva dele, evitando duas reservas no mesmo período.
    with transaction.atomic():
        veiculo = Veiculo.objects.select_for_update().get(id=veiculo_id)

        if not veiculo.disponivel:
            erro = "Este veículo está indisponível no momento."
        elif not veiculo.diaria:
            erro = "Este veículo ainda não tem diária cadastrada."
        elif d1 < date.today():
            erro = "A data de retirada não pode ser no passado."
        elif dias <= 0:
            erro = "A data de devolução deve ser posterior à data de retirada."
        elif Reserva.objects.filter(
            veiculo=veiculo, data_retirada__lte=d2, data_devolucao__gte=d1
        ).exclude(status="Cancelada").exists():
            erro = "Este veículo já está reservado nesse período."
        else:
            erro = None
            usuario = request.user
            nome = getattr(usuario, "full_name", None) or f"{usuario.first_name} {usuario.last_name}".strip()
            Reserva.objects.create(
                veiculo=veiculo,
                cliente=usuario,
                nome_cliente=nome,
                email_cliente=usuario.email,
                data_retirada=d1,
                data_devolucao=d2,
                valor_total=dias * veiculo.diaria,
                status="Pendente",
            )

    if erro:
        messages.error(request, erro)
        return redirect(voltar)

    messages.success(request, "Reserva solicitada! Acompanhe a situação em Minhas Reservas.")
    return redirect("minhas_reservas")


# Como cada situação do banco aparece para o cliente: (texto, classe CSS)
ROTULOS_STATUS = {
    "Pendente": ("Em análise", "pendente"),
    "Confirmada": ("Reservada", "confirmada"),
    "Concluída": ("Concluída", "concluida"),
    "Cancelada": ("Cancelada", "cancelada"),
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
        lista = lista.filter(status__in=["Pendente", "Confirmada"])
    elif aba == "historico":
        lista = lista.filter(status__in=["Concluída", "Cancelada"])
    else:
        aba = "todas"

    pagina = Paginator(lista, 6).get_page(request.GET.get("page"))
    itens = list(pagina.object_list)
    hoje = date.today()
    for r in itens:
        r.dias = max((r.data_devolucao - r.data_retirada).days, 1)
        r.diaria_calculada = r.valor_total / r.dias
        r.rotulo, r.classe = ROTULOS_STATUS.get(r.status, (r.status, "concluida"))
        r.cancelavel = r.status in ("Pendente", "Confirmada") and r.data_retirada >= hoje

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
    if reserva.status in ("Pendente", "Confirmada") and reserva.data_retirada >= date.today():
        reserva.status = "Cancelada"
        reserva.save(update_fields=["status"])
        messages.success(request, f"Reserva RES-{reserva.id:04d} cancelada.")
    else:
        messages.error(request, "Esta reserva não pode mais ser cancelada.")
    return redirect("minhas_reservas")