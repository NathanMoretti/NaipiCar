from django.contrib.auth import views as auth_views
from django.urls import path
from contas import views as contas_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'veiculo/<int:veiculo_id>/',
        views.detalhe_veiculo,
        name='detalhe_veiculo',
    ),
    path('minhas-reservas/', views.minhas_reservas, name='minhas_reservas'),
    path('cadastro/', contas_views.cadastro, name='cadastro'),
    path('termos/', contas_views.termos, name='termos'),
    path('login/', contas_views.NaipiLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
]