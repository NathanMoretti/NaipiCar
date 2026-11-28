"""Painel: cadastros de marcas, modelos, categorias, classes e diárias (uma tela com abas)."""
import json

from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..apoio import paginar
from ..forms import CategoriaClasseForm, CategoriaForm, ClasseCarroForm, MarcaForm, ModeloCarroForm
from ..models import Categoria, CategoriaClasse, ClasseCarro, Marca, ModeloCarro, Veiculo
from .comum import reais, somente_admin

# Cada aba é descrita aqui; as views abaixo servem para todas elas.
CADASTROS = {
    "marcas": {
        "titulo": "Marcas", "singular": "marca", "artigo": "a",
        "model": Marca, "form": MarcaForm,
        "ordem": ["nome"], "relacionados": [], "busca": ["nome"],
        "colunas": ["Marca", "Modelos cadastrados"],
        "celulas": lambda o: [o.nome, ModeloCarro.objects.filter(marca=o).count()],
        "em_uso": lambda o: ModeloCarro.objects.filter(marca=o).exists(),
        "motivo": "Esta marca tem modelos cadastrados.",
    },
    "modelos": {
        "titulo": "Modelos", "singular": "modelo", "artigo": "o",
        "model": ModeloCarro, "form": ModeloCarroForm,
        "ordem": ["marca__nome", "nome"], "relacionados": ["marca"], "busca": ["nome", "marca__nome"],
        "colunas": ["Marca", "Modelo", "Assentos", "Malas", "Veículos"],
        "celulas": lambda o: [o.marca.nome, o.nome, getattr(o, "assentos", "—"), getattr(o, "malas", "—"),
                              Veiculo.objects.filter(modelo=o).count()],
        "em_uso": lambda o: Veiculo.objects.filter(modelo=o).exists(),
        "motivo": "Este modelo está em uso por veículos cadastrados.",
    },
    "categorias": {
        "titulo": "Categorias", "singular": "categoria", "artigo": "a",
        "model": Categoria, "form": CategoriaForm,
        "ordem": ["nome"], "relacionados": [], "busca": ["nome", "descricao"],
        "colunas": ["Categoria", "Descrição", "Diárias cadastradas"],
        "celulas": lambda o: [o.nome, o.descricao or "—", CategoriaClasse.objects.filter(categoria=o).count()],
        "em_uso": lambda o: CategoriaClasse.objects.filter(categoria=o).exists(),
        "motivo": "Esta categoria tem diárias cadastradas.",
    },
    "classes": {
        "titulo": "Classes", "singular": "classe", "artigo": "a",
        "model": ClasseCarro, "form": ClasseCarroForm,
        "ordem": ["nome"], "relacionados": [], "busca": ["nome"],
        "colunas": ["Classe", "Diárias cadastradas"],
        "celulas": lambda o: [o.nome, CategoriaClasse.objects.filter(classe=o).count()],
        "em_uso": lambda o: CategoriaClasse.objects.filter(classe=o).exists(),
        "motivo": "Esta classe tem diárias cadastradas.",
    },
    "diarias": {
        "titulo": "Diárias", "singular": "diária", "artigo": "a",
        "model": CategoriaClasse, "form": CategoriaClasseForm,
        "ordem": ["categoria__nome", "classe__nome"], "relacionados": ["categoria", "classe"],
        "busca": ["categoria__nome", "classe__nome"],
        "colunas": ["Categoria", "Classe", "Diária", "Veículos"],
        "celulas": lambda o: [o.categoria.nome, o.classe.nome, reais(o.daily_rate),
                              Veiculo.objects.filter(categoria_classe=o).count()],
        "em_uso": lambda o: Veiculo.objects.filter(categoria_classe=o).exists(),
        "motivo": "Esta combinação está em uso por veículos cadastrados.",
    },
}


def _config(aba):
    if aba not in CADASTROS:
        raise Http404("Cadastro não encontrado.")
    return CADASTROS[aba]


def _contexto_cadastros(request, aba, form=None, modal=None):
    cfg = _config(aba)
    lista = cfg["model"].objects.all()
    if cfg["relacionados"]:
        lista = lista.select_related(*cfg["relacionados"])
    lista = lista.order_by(*cfg["ordem"])

    q = request.GET.get("q", "").strip()
    if q:
        filtro = Q()
        for campo in cfg["busca"]:
            filtro |= Q(**{f"{campo}__icontains": q})
        lista = lista.filter(filtro)

    paginacao = paginar(request, lista, 8)
    pagina = paginacao["pagina"]
    campos = cfg["form"]._meta.fields
    linhas = [
        {
            "celulas": cfg["celulas"](o),
            "nome": str(o),
            "json": json.dumps(model_to_dict(o, fields=campos), cls=DjangoJSONEncoder),
            "url_editar": reverse("painel_cadastro_editar", args=[aba, o.pk]),
            "url_excluir": reverse("painel_cadastro_excluir", args=[aba, o.pk]),
        }
        for o in pagina.object_list
    ]

    vazio = cfg["form"]()

    return {
        "aba": aba,
        "cfg": cfg,
        "abas": [(chave, c["titulo"]) for chave, c in CADASTROS.items()],
        "linhas": linhas,
        **paginacao,
        "q": q,
        "form": form or vazio,
        "iniciais": json.dumps({n: vazio[n].value() for n in vazio.fields}, cls=DjangoJSONEncoder),
        "url_novo": reverse("painel_cadastros", args=[aba]),
        "modal": modal,
    }


@somente_admin
def cadastros_inicio(request):
    return redirect("painel_cadastros", aba="marcas")


@somente_admin
def cadastros(request, aba):
    """Lista a aba escolhida e, em POST, cadastra um novo registro."""
    cfg = _config(aba)
    if request.method == "POST":
        form = cfg["form"](request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{cfg['singular'].capitalize()} cadastrad{cfg['artigo']} com sucesso.")
            return redirect("painel_cadastros", aba=aba)
        modal = {"titulo": f"Cadastrar {cfg['singular']}", "botao": "Cadastrar", "acao": reverse("painel_cadastros", args=[aba])}
        return render(request, "locacao/painel/cadastros.html", _contexto_cadastros(request, aba, form, modal))
    return render(request, "locacao/painel/cadastros.html", _contexto_cadastros(request, aba))


@somente_admin
@require_POST
def cadastro_editar(request, aba, pk):
    cfg = _config(aba)
    objeto = get_object_or_404(cfg["model"], pk=pk)
    form = cfg["form"](request.POST, instance=objeto)
    if form.is_valid():
        form.save()
        messages.success(request, f"{cfg['singular'].capitalize()} atualizad{cfg['artigo']} com sucesso.")
        return redirect("painel_cadastros", aba=aba)
    modal = {"titulo": f"Editar {cfg['singular']}", "botao": "Salvar alterações",
             "acao": reverse("painel_cadastro_editar", args=[aba, pk])}
    return render(request, "locacao/painel/cadastros.html", _contexto_cadastros(request, aba, form, modal))


@somente_admin
@require_POST
def cadastro_excluir(request, aba, pk):
    cfg = _config(aba)
    objeto = get_object_or_404(cfg["model"], pk=pk)
    if cfg["em_uso"](objeto):
        messages.error(request, f"{cfg['motivo']} Remova ou altere esses registros antes de excluir.")
    else:
        nome = str(objeto)
        objeto.delete()
        messages.success(request, f"{nome} excluíd{cfg['artigo']}.")
    return redirect("painel_cadastros", aba=aba)
