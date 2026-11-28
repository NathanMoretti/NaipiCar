"""Painel: lista de usuários, cadastro pelo administrador e mudança de perfil/situação."""
import json

from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils import timezone

from contas.forms import UsuarioPainelForm
from contas.forms_senha import enviar_link_criar_senha
from contas.models import User

from ..apoio import destino_seguro, paginar
from ..models import Reserva
from .comum import cpf_oculto, rotulo_situacao, somente_admin

SITUACOES_USUARIO = {
    User.ACTIVE: ("Ativo", "ativo"),
    User.INACTIVE: ("Inativo", "inativo"),
    User.PENDING: ("Pendente", "pendente"),
    User.BLOCKED: ("Bloqueado", "bloqueado"),
}


def _contexto_usuarios(request, form=None):
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

    paginacao = paginar(request, lista, 6)
    pagina = paginacao["pagina"]
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
            rotulo, _ = rotulo_situacao(r, timezone.localdate())
            recentes[r.cliente_id].append({
                "codigo": f"RES-{r.id:04d}",
                "veiculo": str(r.veiculo.modelo),
                "periodo": f"{r.data_retirada:%d/%m/%Y} → {r.data_devolucao:%d/%m/%Y}",
                "situacao": rotulo,
            })

    for u in itens:
        u.rotulo, u.classe = SITUACOES_USUARIO.get(u.status, (u.status, "inativo"))
        u.eh_admin = u.profile_type == User.ADMIN
        u.cpf_oculto = cpf_oculto(u.cpf)
        u.n_reservas = totais.get(u.id, 0)
        u.eu = u.pk == request.user.pk
        u.endereco_texto = str(u.address) if u.address_id else "—"
        u.recentes = json.dumps(recentes.get(u.id, []), cls=DjangoJSONEncoder)


    # Pop-up "Novo usuário": abre sozinho quando houve erro ou quando vem da Nova reserva
    para_reserva = request.POST.get("para_reserva") == "1" or request.GET.get("para") == "reserva"
    abrir_novo = form is not None or request.GET.get("novo") == "1"

    return {
        "form_usuario": form or UsuarioPainelForm(),
        "abrir_novo": abrir_novo,
        "para_reserva": para_reserva,
        "usuarios": itens,
        **paginacao,
        "filtro": {"q": q, "perfil": perfil, "situacao": situacao},
        "stats": {
            "total": User.objects.count(),
            "clientes": User.objects.filter(profile_type=User.USER).count(),
            "admins": User.objects.filter(profile_type=User.ADMIN).count(),
            "inativos": User.objects.exclude(status=User.ACTIVE).count(),
        },
        "ADMIN": User.ADMIN,
        "USER": User.USER,
    }


@somente_admin
def usuarios_painel(request):
    return render(request, "locacao/painel/usuarios.html", _contexto_usuarios(request))


@somente_admin
@require_POST
def usuario_novo(request):
    """Cadastro feito pelo administrador. A conta nasce sem senha e a pessoa recebe o link por e-mail."""
    form = UsuarioPainelForm(request.POST)
    if not form.is_valid():
        return render(request, "locacao/painel/usuarios.html", _contexto_usuarios(request, form))

    usuario = form.save()
    try:
        enviar_link_criar_senha(request, usuario)
        messages.success(
            request, f"Conta de {usuario.full_name} criada. Enviamos para {usuario.email} o link para criar a senha.")
    except Exception:  # falha no servidor de e-mail não pode desfazer o cadastro
        messages.warning(
            request,
            f"Conta de {usuario.full_name} criada, mas não foi possível enviar o e-mail. "
            "Peça para a pessoa usar \"Esqueci minha senha\" na tela de login.",
        )

    if request.POST.get("para_reserva") == "1" and usuario.profile_type == User.USER:
        # Volta para a Nova reserva com o cliente recém-cadastrado já escolhido
        return redirect(f"{reverse('painel_reservas')}?nova=1&cliente={usuario.pk}")
    return redirect("painel_usuarios")


@somente_admin
@require_POST
def usuario_atualizar(request, pk):
    alvo = get_object_or_404(User, pk=pk)
    destino = destino_seguro(request, "painel_usuarios")

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
