"""Painel: cadastro, edição e exclusão de veículos."""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils import timezone

from ..forms import VeiculoForm
from ..models import Categoria, CategoriaClasse, Reserva, Veiculo
from ..apoio import paginar
from .comum import somente_admin

TEMPLATE_VEICULOS = "locacao/painel/veiculos.html"


def ids_reservados():
    """Veículos com reserva Pendente/Confirmada cobrindo o dia de hoje."""
    hoje = timezone.localdate()
    return set(
        Reserva.objects.filter(
            status__in=Reserva.EM_ABERTO,
            data_retirada__lte=hoje,
            data_devolucao__gte=hoje,
        ).values_list("veiculo_id", flat=True)
    )


def _contexto_veiculos(request, form=None, modal=None):
    reservados = ids_reservados()

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

    paginacao = paginar(request, lista, 5)
    pagina = paginacao["pagina"]
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


    return {
        "veiculos": itens,
        **paginacao,
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
                status__in=Reserva.EM_ABERTO,
                data_devolucao__gte=timezone.localdate(),
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
