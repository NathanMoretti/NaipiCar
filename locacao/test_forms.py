from datetime import date

from django.test import TestCase

from .fabrica import criar_veiculo
from .forms import VeiculoForm


def dados_veiculo(base, **extra):
    """Dados válidos de um veículo, tomando modelo e categoria de um veículo já criado."""
    dados = {
        "modelo": base.modelo_id,
        "categoria_classe": base.categoria_classe_id,
        "placa": "XYZ9A87",
        "ano": 2023,
        "quilometragem": 0,
        "disponivel": "True",
    }
    if "motorizacao" in VeiculoForm.base_fields:  # só existe se o modelo tiver o campo
        escolhas = VeiculoForm.base_fields["motorizacao"].choices
        dados["motorizacao"] = next(valor for valor, _ in escolhas if valor)
    dados.update(extra)
    return dados


class PlacaTests(TestCase):
    def setUp(self):
        self.base = criar_veiculo(placa="AAA1A11")

    def formulario(self, **extra):
        return VeiculoForm(data=dados_veiculo(self.base, **extra))

    def test_aceita_placa_antiga_e_mercosul_em_varias_digitacoes(self):
        casos = {
            "ABC1234": "ABC1234",
            "abc-1234": "ABC1234",
            "ABC1D23": "ABC1D23",
            "abc 1d23": "ABC1D23",
        }
        for digitada, esperada in casos.items():
            with self.subTest(placa=digitada):
                form = self.formulario(placa=digitada)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["placa"], esperada)

    def test_recusa_placas_em_formato_invalido(self):
        for placa in ["AB1234", "ABCD123", "ABC12345", "1BC1234", "ABC-12E4", ""]:
            with self.subTest(placa=placa):
                self.assertIn("placa", self.formulario(placa=placa).errors)

    def test_recusa_placa_repetida_sem_diferenciar_maiusculas(self):
        self.assertIn("placa", self.formulario(placa="aaa1a11").errors)

    def test_editar_o_proprio_veiculo_mantem_a_placa(self):
        form = VeiculoForm(data=dados_veiculo(self.base, placa="AAA1A11"), instance=self.base)
        self.assertTrue(form.is_valid(), form.errors)


class OutrasValidacoesTests(TestCase):
    def setUp(self):
        self.base = criar_veiculo(placa="AAA1A11")

    def formulario(self, **extra):
        return VeiculoForm(data=dados_veiculo(self.base, **extra))

    def test_ano_fora_da_faixa(self):
        proximo = date.today().year + 1
        for ano in [1980, proximo + 1, 3000]:
            with self.subTest(ano=ano):
                self.assertIn("ano", self.formulario(ano=ano).errors)

    def test_ano_do_modelo_seguinte_e_aceito(self):
        self.assertTrue(self.formulario(ano=date.today().year + 1).is_valid())

    def test_quilometragem_nao_pode_ser_negativa(self):
        self.assertIn("quilometragem", self.formulario(quilometragem=-5).errors)

    def test_categoria_e_obrigatoria(self):
        self.assertIn("categoria_classe", self.formulario(categoria_classe="").errors)
