from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render, resolve_url

from .forms import CadastroForm, LoginForm


class NaipiLoginView(LoginView):
    """RF02: login por e-mail; administradores vão para o painel, clientes para o catálogo."""
    template_name = 'locacao/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return resolve_url('/admin/' if self.request.user.is_staff else 'index')


def cadastro(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Conta criada com sucesso! Entre com o seu e-mail e senha.')
        return redirect('login')
    return render(request, 'contas/cadastro.html', {'form': form})


def termos(request):
    return render(request, 'contas/termos.html')
