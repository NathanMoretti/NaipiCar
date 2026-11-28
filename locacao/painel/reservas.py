"""Painel: lista de reservas, nova reserva (balcão) e mudança de situação."""
import re
from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from ..apoio import destino_seguro, paginar
from ..forms import ReservaPainelForm
from ..models import Reserva
from ..regras import ReservaInvalida, criar_reserva
from .comum import ROTULOS_SITUACAO, TRANSICOES, Status, cpf_oculto, reais, rotulo_situacao, somente_admin

def _contexto_reservas(request, form=None):
    hoje = timezone.localdate()
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
        lista = lista.filter(status=Status.PENDENTE)
    elif situacao == "confirmada":
        lista = lista.filter(status=Status.CONFIRMADA, data_devolucao__gte=hoje)
    elif situacao == "atrasado":
        lista = lista.filter(status=Status.CONFIRMADA, data_devolucao__lt=hoje)
    elif situacao == "concluida":
        lista = lista.filter(status=Status.CONCLUIDA)
    elif situacao == "cancelada":
        lista = lista.filter(status=Status.CANCELADA)

    if periodo == "hoje":
        lista = lista.filter(Q(data_retirada=hoje) | Q(data_devolucao=hoje))
    elif periodo == "semana":
        lista = lista.filter(data_retirada__gte=hoje, data_retirada__lte=hoje + timedelta(days=7))
    elif periodo == "mes":
        lista = lista.filter(data_retirada__year=hoje.year, data_retirada__month=hoje.month)

    paginacao = paginar(request, lista, 5)
    pagina = paginacao["pagina"]
    itens = list(pagina.object_list)
    for r in itens:
        r.dias = max((r.data_devolucao - r.data_retirada).days, 1)
        r.diaria_calculada = r.valor_total / r.dias
        r.rotulo, r.classe = rotulo_situacao(r, hoje)
        r.cpf = getattr(r.cliente, "cpf", "") if r.cliente else ""
        r.cpf_oculto = cpf_oculto(r.cpf)
        r.opcoes = "|".join(TRANSICOES.get(r.status, [r.status]))

    todas = Reserva.objects

    # Pop-up "Nova reserva": abre sozinho quando houve erro ou quando vem do cadastro de cliente
    abrir_nova = form is not None or request.GET.get("nova") == "1"
    if form is None:
        form = ReservaPainelForm(initial={"cliente": request.GET.get("cliente") or None})

    return {
        "form_reserva": form,
        "abrir_nova": abrir_nova,
        "diarias_veiculos": {str(v.id): float(v.diaria) for v in form.fields["veiculo"].queryset},
        "reservas": itens,
        **paginacao,
        "filtro": {"q": q, "situacao": situacao, "periodo": periodo},
        "stats": {
            "total": todas.count(),
            "analise": todas.filter(status=Status.PENDENTE).count(),
            "reservadas": todas.filter(status=Status.CONFIRMADA, data_devolucao__gte=hoje).count(),
            "atrasadas": todas.filter(status=Status.CONFIRMADA, data_devolucao__lt=hoje).count(),
            "concluidas": todas.filter(status=Status.CONCLUIDA).count(),
        },
        "rotulos": {k: v[0] for k, v in ROTULOS_SITUACAO.items()},
    }


@somente_admin
def reservas_painel(request):
    return render(request, "locacao/painel/reservas.html", _contexto_reservas(request))


@somente_admin
@require_POST
def reserva_nova(request):
    """Reserva criada pelo administrador (cliente no balcão). Segue as mesmas regras do site."""
    form = ReservaPainelForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        try:
            reserva = criar_reserva(
                d["veiculo"].id, d["cliente"], d["data_retirada"], d["data_devolucao"], status=d["status"])
        except ReservaInvalida as erro:
            form.add_error(None, str(erro))
        else:
            messages.success(
                request,
                f"Reserva RES-{reserva.id:04d} criada para {reserva.nome_cliente}: "
                f"{reserva.veiculo.modelo}, {reais(reserva.valor_total)}.",
            )
            return redirect("painel_reservas")
    return render(request, "locacao/painel/reservas.html", _contexto_reservas(request, form))


@somente_admin
@require_POST
def reserva_situacao(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    novo = request.POST.get("status", "")
    destino = destino_seguro(request, "painel_reservas")

    if novo not in TRANSICOES.get(reserva.status, []):
        messages.error(request, "Não é possível mudar a reserva para essa situação.")
    elif novo == reserva.status:
        messages.info(request, "Nenhuma alteração feita.")
    else:
        reserva.status = novo
        reserva.save(update_fields=["status"])
        messages.success(request, f"Reserva RES-{reserva.id:04d} atualizada para {ROTULOS_SITUACAO[novo][0]}.")
    return redirect(destino)
