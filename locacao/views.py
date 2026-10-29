from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Min
from django.shortcuts import get_object_or_404, render

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


def detalhe_veiculo(request, veiculo_id):
    # Busca o veículo específico ou retorna 404 se não existir
    veiculo = get_object_or_404(Veiculo, id=veiculo_id)
    contexto = {"veiculo": veiculo}

    if request.method == "POST":
        nome_cliente = request.POST.get("nome_cliente")
        email_cliente = request.POST.get("email_cliente")
        data_retirada = request.POST.get("data_retirada")
        data_devolucao = request.POST.get("data_devolucao")

        # Validação do período de locação
        try:
            d1 = datetime.strptime(data_retirada, "%Y-%m-%d").date()
            d2 = datetime.strptime(data_devolucao, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            contexto["erro"] = "Informe datas válidas."
            return render(request, "locacao/detalhe_veiculo.html", contexto)

        dias = (d2 - d1).days

        if d1 < date.today():
            contexto["erro"] = "A data de retirada não pode ser no passado."
            return render(request, "locacao/detalhe_veiculo.html", contexto)

        if dias <= 0:
            contexto["erro"] = (
                "A data de devolução deve ser posterior à data de retirada."
            )
            return render(request, "locacao/detalhe_veiculo.html", contexto)

        # Impede reservar um veículo já ocupado no período
        ocupado = (
            Reserva.objects.filter(
                veiculo=veiculo, data_retirada__lte=d2, data_devolucao__gte=d1
            )
            .exclude(status="Cancelada")
            .exists()
        )
        if ocupado:
            contexto["erro"] = "Este veículo já está reservado nesse período."
            return render(request, "locacao/detalhe_veiculo.html", contexto)

        # Cálculo automático do valor total baseado nas diárias do veículo
        valor_total = dias * veiculo.diaria

        # Cria e salva a reserva vinculando ao usuário logado (se houver)
        Reserva.objects.create(
            veiculo=veiculo,
            cliente=request.user if request.user.is_authenticated else None,
            nome_cliente=nome_cliente,
            email_cliente=email_cliente,
            data_retirada=d1,
            data_devolucao=d2,
            valor_total=valor_total,
            status="Pendente",
        )

        contexto["sucesso"] = "Reserva realizada com sucesso! Status: Pendente."

    return render(request, "locacao/detalhe_veiculo.html", contexto)


@login_required(login_url="login")
def minhas_reservas(request):
    # Exibe apenas as reservas associadas ao cliente logado no momento
    reservas = Reserva.objects.filter(cliente=request.user).order_by("-data_criacao")
    return render(request, "locacao/minhas_reservas.html", {"reservas": reservas})