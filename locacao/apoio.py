"""Funções pequenas usadas por várias telas (site e painel)."""
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def paginar(request, lista, por_pagina):
    """Divide a lista em páginas e devolve o que os templates usam para montar a paginação.

    - pagina: a página atual (com .object_list, .number, .has_next...)
    - paginas: números das páginas, com "…" quando são muitas (1 … 4 5 6 … 12)
    - reticencias: o "…" usado em `paginas`
    - querystring: os filtros atuais (sem o número da página), para os links manterem os filtros
    """
    pagina = Paginator(lista, por_pagina).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "pagina": pagina,
        "paginas": list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
        "reticencias": pagina.paginator.ELLIPSIS,
        "querystring": params.urlencode(),
    }


def destino_seguro(request, padrao):
    """Endereço do campo "voltar" do formulário, se for do próprio site; senão, a página `padrao`.

    Evita que alguém use o site para redirecionar visitantes para um endereço externo.
    """
    destino = request.POST.get("voltar", "")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return destino
    return reverse(padrao)
