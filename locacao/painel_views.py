from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import VeiculoForm
from .models import Categoria, CategoriaClasse, Reserva, Veiculo

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
    # A reserva é apagada junto com o veículo (CASCADE), então bloqueamos para não perder histórico
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