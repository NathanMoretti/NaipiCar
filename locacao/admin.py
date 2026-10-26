from django.contrib import admin
from .models import Categoria, Marca, ModeloCarro, Reserva, Veiculo, ClasseCarro, CategoriaClasse

# Registra os modelos no painel administrativo do Django
admin.site.register(Marca)
admin.site.register(ModeloCarro)
admin.site.register(ClasseCarro)
admin.site.register(Categoria)
admin.site.register(CategoriaClasse)
admin.site.register(Veiculo)
admin.site.register(Reserva)