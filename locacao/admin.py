from django.contrib import admin

from .models import (
    Categoria,
    CategoriaClasse,
    ClasseCarro,
    Marca,
    ModeloCarro,
    Reserva,
    Veiculo,
)

admin.site.register(Marca)
admin.site.register(ClasseCarro)
admin.site.register(Categoria)
admin.site.register(CategoriaClasse)


@admin.register(ModeloCarro)
class ModeloCarroAdmin(admin.ModelAdmin):
    list_display = ("marca", "nome", "assentos", "malas")
    list_filter = ("marca", "assentos")
    search_fields = ("nome", "marca__nome")
    list_editable = ("assentos", "malas")


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = (
        "modelo",
        "placa",
        "ano",
        "motorizacao",
        "categoria_classe",
        "disponivel",
    )
    list_filter = ("motorizacao", "disponivel", "categoria_classe")
    search_fields = ("placa", "modelo__nome", "modelo__marca__nome")


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "veiculo",
        "data_retirada",
        "data_devolucao",
        "valor_total",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("nome_cliente", "email_cliente", "veiculo__placa")