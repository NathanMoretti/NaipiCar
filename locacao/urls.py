from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'veiculo/<int:veiculo_id>/',
        views.detalhe_veiculo,
        name='detalhe_veiculo',
    ),
    path('minhas-reservas/', views.minhas_reservas, name='minhas_reservas'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='locacao/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
]