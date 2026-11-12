from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Min
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Categoria, CategoriaClasse, Reserva, Veiculo


def index(request):
    """Página inicial: até 3 categorias com foto, especificações e preço mínimo."""
    categorias = []
    for cat in Categoria.objects.all():
        veiculo = (
            Veiculo.objects.filter(categoria_classe__categoria=cat, disponivel=True)
            .exclude(imagem="")
            .exclude(imagem__isnull=True)
            .select_related("modelo")
            .first()
        )
        if not veiculo:
            continue
        preco = CategoriaClasse.objects.filter(categoria=cat).aggregate(
            m=Min("daily_rate")
        )["m"]
        categorias.append({
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "assentos": veiculo.modelo.assentos,
            "malas": veiculo.modelo.malas,
            "imagem": veiculo.imagem,
            "preco_minimo": preco,
        })
    return render(request, "locacao/index.html", {
        "categorias": categorias[:3],
        "todas_categorias": Categoria.objects.all(),
    })


def veiculos(request):
    """Lista de veículos, com filtro por categoria e por período livre."""
    lista = Veiculo.objects.select_related(
        "modelo__marca", "categoria_classe__categoria"
    )

    categoria = request.GET.get("categoria")
    if categoria:
        lista = lista.filter(categoria_classe__categoria_id=categoria)

    retirada = request.GET.get("retirada")
    devolucao = request.GET.get("devolucao")
    if retirada and devolucao and retirada <= devolucao:
        ocupados = (
            Reserva.objects.filter(
                data_retirada__lte=devolucao, data_devolucao__gte=retirada
            )
            .exclude(status="Cancelada")
            .values_list("veiculo_id", flat=True)
        )
        lista = lista.exclude(id__in=ocupados)

    return render(request, "locacao/veiculos.html", {
        "veiculos": lista,
        "todas_categorias": Categoria.objects.all(),
        "filtro": {
            "retirada": retirada or "",
            "devolucao": devolucao or "",
            "categoria": categoria or "",
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
    veiculo = get_object_or_404(Veiculo, id=veiculo_id)
    voltar = _destino_voltar(request)

    try:
        d1 = datetime.strptime(request.POST.get("data_retirada", ""), "%Y-%m-%d").date()
        d2 = datetime.strptime(request.POST.get("data_devolucao", ""), "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Informe datas válidas.")
        return redirect(voltar)

    dias = (d2 - d1).days

    if not veiculo.disponivel:
        messages.error(request, "Este veículo está indisponível no momento.")
    elif not veiculo.diaria:
        messages.error(request, "Este veículo ainda não tem diária cadastrada.")
    elif d1 < date.today():
        messages.error(request, "A data de retirada não pode ser no passado.")
    elif dias <= 0:
        messages.error(request, "A data de devolução deve ser posterior à data de retirada.")
    elif Reserva.objects.filter(
        veiculo=veiculo, data_retirada__lte=d2, data_devolucao__gte=d1
    ).exclude(status="Cancelada").exists():
        messages.error(request, "Este veículo já está reservado nesse período.")
    else:
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
        messages.success(request, "Reserva solicitada! Acompanhe a situação em Minhas Reservas.")
        return redirect("minhas_reservas")

    return redirect(voltar)


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