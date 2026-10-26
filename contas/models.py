from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from .validators import formatar_cpf


class Address(models.Model):
    """Tabela address do dicionário de dados."""
    street = models.CharField('rua', max_length=100)
    number = models.CharField('número', max_length=10)
    complement = models.CharField('complemento', max_length=50, blank=True)
    neighborhood = models.CharField('bairro', max_length=60)
    city = models.CharField('cidade', max_length=60)
    state = models.CharField('estado', max_length=2)
    zip_code = models.CharField('CEP', max_length=9)

    class Meta:
        db_table = 'address'
        verbose_name = 'endereço'
        verbose_name_plural = 'endereços'

    def __str__(self):
        return f'{self.street}, {self.number} - {self.city}/{self.state}'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        if 'address' not in extra and 'address_id' not in extra:
            # Contas criadas pelo terminal (createsuperuser) recebem um endereço provisório.
            extra['address'] = Address.objects.create(
                street='-', number='-', neighborhood='-', city='-', state='--', zip_code='-')
        if 'cpf' in extra:
            extra['cpf'] = formatar_cpf(extra['cpf'])
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)  # guarda só o hash (RNF01)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('profile_type', User.ADMIN)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    """Tabela user do dicionário de dados (clientes e administradores)."""
    USER = 1
    ADMIN = 2
    PROFILE_CHOICES = [(USER, 'Cliente'), (ADMIN, 'Administrador')]

    ACTIVE, INACTIVE, PENDING, BLOCKED = 'ACTIVE', 'INACTIVE', 'PENDING', 'BLOCKED'
    STATUS_CHOICES = [
        (ACTIVE, 'Ativo'), (INACTIVE, 'Inativo'), (PENDING, 'Pendente'), (BLOCKED, 'Bloqueado'),
    ]

    address = models.ForeignKey(Address, on_delete=models.PROTECT, verbose_name='endereço')
    first_name = models.CharField('nome', max_length=50)
    last_name = models.CharField('sobrenome', max_length=50)
    cpf = models.CharField('CPF', max_length=14, unique=True)
    email = models.EmailField('e-mail', max_length=70, unique=True)
    phone = models.CharField('telefone', max_length=20)
    # A coluna no banco se chama password_hash (como no dicionário).
    password = models.CharField('senha', max_length=255, db_column='password_hash')
    profile_photo = models.ImageField(
        'foto de perfil', upload_to='perfis/', max_length=255,
        null=True, blank=True, db_column='profile_photo_url')
    profile_type = models.IntegerField('perfil', choices=PROFILE_CHOICES, default=USER)
    status = models.CharField('situação', max_length=10, choices=STATUS_CHOICES, default=ACTIVE)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'cpf', 'phone']

    class Meta:
        db_table = 'user'
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.first_name

    # --- Integração com o login e o /admin/ do Django ---------------------
    @property
    def is_active(self):
        return self.status == self.ACTIVE

    @property
    def is_admin_profile(self):
        return self.profile_type == self.ADMIN

    @property
    def is_staff(self):
        return self.is_active and self.is_admin_profile

    @property
    def is_superuser(self):
        return self.is_staff

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
