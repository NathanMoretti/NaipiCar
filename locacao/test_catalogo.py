from decimal import Decimal

from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase
from django.urls import reverse

from .fabrica import criar_veiculo
from .models import Categoria, CategoriaClasse, ClasseCarro, ModeloCarro, Veiculo


class CategoriasDaPaginaInicialTests(TestCase):
    def categorias(self):
        resposta = self.client.get(reverse("index"))
        self.assertEqual(resposta.status_code, 200)
        return resposta.context["categorias"]

    def test_categoria_sem_veiculo_nao_aparece(self):
        Categoria.objects.create(nome="Esportivo")
        self.assertEqual(self.categorias(), [])

    def test_aparece_sozinha_quando_o_primeiro_veiculo_e_cadastrado(self):
        Categoria.objects.create(nome="Esportivo")
        self.assertEqual(self.categorias(), [])
        criar_veiculo(placa="AAA1A11", categoria="Esportivo", diaria="400.00")
        self.assertEqual([c["nome"] for c in self.categorias()], ["Esportivo"])

    def test_veiculo_indisponivel_nao_faz_a_categoria_aparecer(self):
        criar_veiculo(placa="AAA1A11", disponivel=False)
        self.assertEqual(self.categorias(), [])

    def test_mostra_todas_as_categorias_com_veiculo_sem_limite_de_tres(self):
        for i, nome in enumerate(["SUV", "Sedan", "Hatch", "Premium", "Esportivo"]):
            criar_veiculo(placa=f"AAA1A1{i}", categoria=nome, modelo=f"Modelo {i}")
        self.assertEqual(len(self.categorias()), 5)

    def test_categoria_sem_foto_aparece_com_imagem_vazia(self):
        criar_veiculo()
        categoria = self.categorias()[0]
        self.assertFalse(categoria["imagem"])

    def test_preco_inicial_considera_so_combinacoes_com_veiculo(self):
        veiculo = criar_veiculo(diaria="200.00")
        barata = ClasseCarro.objects.create(nome="Classe Econômica")
        CategoriaClasse.objects.create(
            categoria=veiculo.categoria_classe.categoria, classe=barata, daily_rate=Decimal("50.00")
        )  # existe, mas nenhum veículo usa
        self.assertEqual(self.categorias()[0]["preco_minimo"], Decimal("200.00"))

    def test_quantidade_e_faixa_de_assentos(self):
        a = criar_veiculo(placa="AAA1A11", modelo="Pequeno")
        b = criar_veiculo(placa="BBB2B22", modelo="Grande")
        ModeloCarro.objects.filter(pk=a.modelo_id).update(assentos=4)
        ModeloCarro.objects.filter(pk=b.modelo_id).update(assentos=7)
        categoria = self.categorias()[0]
        self.assertEqual(categoria["quantidade"], 2)
        self.assertEqual(categoria["assentos"], "4 a 7")


class FiltrosDoCatalogoTests(TestCase):
    def setUp(self):
        # Compass (SUV, R$ 150, 5 lugares), Kombi (Van, R$ 300, 9 lugares), Mobi (Hatch, R$ 90, 4 lugares)
        self.compass = criar_veiculo(placa="AAA1A11", marca="Jeep", modelo="Compass", ano=2023)
        self.kombi = criar_veiculo(placa="BBB2B22", marca="Volkswagen", modelo="Kombi", ano=2020,
                                   categoria="Van", diaria="300.00")
        self.mobi = criar_veiculo(placa="CCC3C33", marca="Fiat", modelo="Mobi", ano=2024,
                                  categoria="Hatch", diaria="90.00")
        for veiculo, assentos, malas in [(self.compass, 5, 3), (self.kombi, 9, 5), (self.mobi, 4, 1)]:
            ModeloCarro.objects.filter(pk=veiculo.modelo_id).update(assentos=assentos, malas=malas)

    def buscar(self, **filtros):
        resposta = self.client.get(reverse("veiculos"), filtros)
        self.assertEqual(resposta.status_code, 200)
        return resposta

    def placas(self, **filtros):
        return [v.placa for v in self.buscar(**filtros).context["veiculos"]]

    def test_sem_filtros_lista_todos_por_marca_e_modelo(self):
        self.assertEqual(self.placas(), ["CCC3C33", "AAA1A11", "BBB2B22"])  # Fiat, Jeep, Volkswagen

    def test_busca_por_texto_em_marca_ou_modelo(self):
        self.assertEqual(self.placas(q="comp"), ["AAA1A11"])
        self.assertEqual(self.placas(q="fiat"), ["CCC3C33"])
        self.assertEqual(self.placas(q="jeep compass"), ["AAA1A11"])

    def test_filtro_por_marca(self):
        self.assertEqual(self.placas(marca=self.kombi.modelo.marca_id), ["BBB2B22"])

    def test_filtro_por_categoria(self):
        self.assertEqual(self.placas(categoria=self.mobi.categoria_classe.categoria_id), ["CCC3C33"])

    def test_assentos_minimos(self):
        self.assertEqual(self.placas(assentos=5, ordem="preco_asc"), ["AAA1A11", "BBB2B22"])
        self.assertEqual(self.placas(assentos=7), ["BBB2B22"])

    def test_malas_minimas(self):
        self.assertEqual(self.placas(malas=3, ordem="preco_asc"), ["AAA1A11", "BBB2B22"])

    def test_diaria_maxima(self):
        self.assertEqual(self.placas(preco_max="100"), ["CCC3C33"])
        self.assertEqual(self.placas(preco_max="150,00", ordem="preco_asc"), ["CCC3C33", "AAA1A11"])

    def test_ordenacoes(self):
        self.assertEqual(self.placas(ordem="preco_asc"), ["CCC3C33", "AAA1A11", "BBB2B22"])
        self.assertEqual(self.placas(ordem="preco_desc"), ["BBB2B22", "AAA1A11", "CCC3C33"])
        self.assertEqual(self.placas(ordem="ano_desc"), ["CCC3C33", "AAA1A11", "BBB2B22"])
        self.assertEqual(self.placas(ordem="assentos_desc"), ["BBB2B22", "AAA1A11", "CCC3C33"])

    def test_filtros_se_combinam(self):
        self.assertEqual(self.placas(assentos=5, preco_max=200), ["AAA1A11"])
        self.assertEqual(self.placas(assentos=9, preco_max=200), [])

    def test_indisponiveis_ficam_escondidos_ate_pedir(self):
        Veiculo.objects.filter(pk=self.kombi.pk).update(disponivel=False)
        self.assertNotIn("BBB2B22", self.placas())
        self.assertIn("BBB2B22", self.placas(todos="1"))

    def test_filtro_por_motorizacao(self):
        try:
            campo = Veiculo._meta.get_field("motorizacao")
        except FieldDoesNotExist:
            self.skipTest("O modelo Veiculo ainda não tem o campo motorizacao.")
        valores = [v for v, _ in campo.choices if v]
        if len(valores) < 2:
            self.skipTest("Só há uma motorização cadastrada.")
        Veiculo.objects.filter(pk=self.kombi.pk).update(motorizacao=valores[1])
        Veiculo.objects.exclude(pk=self.kombi.pk).update(motorizacao=valores[0])
        self.assertEqual(self.placas(motorizacao=valores[1]), ["BBB2B22"])

    def test_valores_invalidos_sao_ignorados_sem_quebrar(self):
        for filtros in [
            {"assentos": "-1"}, {"assentos": "abc"}, {"malas": "x"}, {"preco_max": "abc"}, {"preco_max": "-5"},
            {"preco_max": "inf"}, {"ordem": "xpto"}, {"categoria": "abc"}, {"marca": "abc"}, {"motorizacao": "xyz"},
        ]:
            with self.subTest(filtros=filtros):
                self.assertEqual(len(self.placas(**filtros)), 3)

    def test_formulario_mantem_os_valores_escolhidos(self):
        filtro = self.buscar(q="jeep", assentos=5, ordem="preco_desc").context["filtro"]
        self.assertEqual((filtro["q"], filtro["assentos"], filtro["ordem"]), ("jeep", "5", "preco_desc"))
        self.assertTrue(filtro["avancado"])
        self.assertEqual(filtro["n_avancados"], 3)

    def test_paginacao_com_nove_por_pagina(self):
        for i in range(10):
            criar_veiculo(placa=f"ZZZ9Z{i:02d}", modelo=f"Extra {i}")
        primeira = self.buscar()
        self.assertEqual(len(primeira.context["veiculos"]), 9)
        self.assertEqual(primeira.context["pagina"].paginator.count, 13)
        segunda = self.buscar(page=2)
        self.assertEqual(len(segunda.context["veiculos"]), 4)

    def test_categorias_do_formulario_so_trazem_as_que_tem_veiculo(self):
        Categoria.objects.create(nome="Esportivo")
        nomes = [c.nome for c in self.buscar().context["todas_categorias"]]
        self.assertNotIn("Esportivo", nomes)
        self.assertEqual(sorted(nomes), ["Hatch", "SUV", "Van"])
