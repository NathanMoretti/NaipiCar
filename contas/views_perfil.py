from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms_perfil import PerfilForm


@login_required(login_url="login")
@require_POST
def editar_perfil(request):
    """Recebe o pop-up de Editar Perfil e responde em JSON (o pop-up mostra os erros nos campos)."""
    form = PerfilForm(request.POST, request.FILES, user=request.user)

    if not form.is_valid():
        erros = {campo: list(mensagens) for campo, mensagens in form.errors.items()}
        return JsonResponse({"ok": False, "erros": erros}, status=400)

    usuario = form.save()
    if form.cleaned_data.get("password1"):
        # Trocar a senha encerraria a sessão; isto mantém o cliente logado
        update_session_auth_hash(request, usuario)

    messages.success(request, "Perfil atualizado com sucesso.")
    return JsonResponse({"ok": True})
