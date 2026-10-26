from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Reserva, Veiculo


def index(request):
  # Busca todos os veículos cadastrados no banco de dados para exibir no catálogo
  veiculos = Veiculo.objects.all()
  contexto = {'veiculos': veiculos}
  return render(request, 'locacao/index.html', contexto)


def detalhe_veiculo(request, veiculo_id):
  # Busca o veículo específico ou retorna 404 se não existir
  veiculo = get_object_or_404(Veiculo, id=veiculo_id)

  if request.method == 'POST':
    nome_cliente = request.POST.get('nome_cliente')
    email_cliente = request.POST.get('email_cliente')
    data_retirada = request.POST.get('data_retirada')
    data_devolucao = request.POST.get('data_devolucao')

    # Validação do período de locação
    d1 = datetime.strptime(data_retirada, '%Y-%m-%d')
    d2 = datetime.strptime(data_devolucao, '%Y-%m-%d')
    dias = (d2 - d1).days

    if dias <= 0:
      return render(
          request,
          'locacao/detalhe_veiculo.html',
          {
              'veiculo': veiculo,
              'erro': (
                  'A data de devolução deve ser posterior à data de retirada.'
              ),
          },
      )

    # Cálculo automático do valor total baseado nas diárias do veículo
    valor_total = dias * veiculo.diaria

    # Cria e salva a reserva no banco de dados vinculando ao usuário logado (se houver)
    Reserva.objects.create(
        veiculo=veiculo,
        cliente=request.user if request.user.is_authenticated else None,
        nome_cliente=nome_cliente,
        email_cliente=email_cliente,
        data_retirada=data_retirada,
        data_devolucao=data_devolucao,
        valor_total=valor_total,
        status='Pendente',
    )

    return render(
        request,
        'locacao/detalhe_veiculo.html',
        {
            'veiculo': veiculo,
            'sucesso': 'Reserva realizada com sucesso! Status: Pendente.',
        },
    )

  return render(request, 'locacao/detalhe_veiculo.html', {'veiculo': veiculo})


@login_required(login_url='login')
def minhas_reservas(request):
  # Exibe apenas as reservas associadas ao cliente logado no momento
  reservas = Reserva.objects.filter(cliente=request.user).order_by(
      '-data_criacao'
  )
  return render(request, 'locacao/minhas_reservas.html', {'reservas': reservas})