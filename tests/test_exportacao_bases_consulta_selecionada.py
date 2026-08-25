import unittest
from unittest.mock import Mock

from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)


class ExportacaoBasesConsultaSelecionadaTestCase(unittest.TestCase):
    def setUp(self):
        self.exportacao = object.__new__(ExportacaoBasesDbf)
        self.exportacao._garantir_tela_consulta_exportacoes = Mock()
        self.exportacao._validar_numero_solicitacao = Mock(
            side_effect=lambda numero: str(numero)
        )
        self.exportacao._ler_solicitacao_na_tabela = Mock(
            side_effect=lambda numero: {"numero": numero}
        )

    def test_consulta_aceita_chaves_internas_da_rotina(self):
        resultados = (
            self.exportacao.consultar_solicitacoes_selecionadas({
                "dengue": "101",
                "chikungunya": "202"
            })
        )

        self.assertEqual(
            resultados,
            {
                "dengue": {"numero": "101"},
                "chikungunya": {"numero": "202"}
            }
        )

    def test_consulta_aceita_alias_e_rotulo_do_portal(self):
        resultados = (
            self.exportacao.consultar_solicitacoes_selecionadas({
                "chiku": "303"
            })
        )
        resultado_portal = (
            self.exportacao.consultar_solicitacoes_selecionadas({
                "FEBRE DE CHIKUNGUNYA": "404"
            })
        )

        self.assertEqual(
            resultados,
            {"chikungunya": {"numero": "303"}}
        )
        self.assertEqual(
            resultado_portal,
            {"chikungunya": {"numero": "404"}}
        )

    def test_consulta_rejeita_agravo_desconhecido(self):
        with self.assertRaisesRegex(ValueError, "Agravo inválido"):
            self.exportacao.consultar_solicitacoes_selecionadas({
                "zika": "505"
            })


if __name__ == "__main__":
    unittest.main()
