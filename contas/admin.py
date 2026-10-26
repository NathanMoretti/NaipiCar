from django.contrib import admin

from .models import Address, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'cpf', 'profile_type', 'status')
    list_filter = ('profile_type', 'status')
    search_fields = ('email', 'first_name', 'last_name', 'cpf')
    exclude = ('password', 'last_login')  # a senha só muda pelos fluxos normais

    def has_add_permission(self, request):
        return False  # contas novas são criadas pela tela de cadastro


admin.site.register(Address)
