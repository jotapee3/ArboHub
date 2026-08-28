from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.services.configuracoes_service import ConfiguracoesService
from app.services.qualifica.interface_72h import (
    CAMINHO_RELATIVO_DICIONARIO,
    converter_data_interface,
    criar_nome_relatorio_72h,
    formatar_data_digitada,
    obter_caminho_dicionario_municipios,
)
from app.services.qualifica.relatorio_72h_service import (
    Relatorio72hService,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class QualificaInterfaceTestCase(unittest.TestCase):
    def test_mascara_de_data_insere_barras_automaticamente(self):
        casos = {
            "": "",
            "0": "0",
            "040": "04/0",
            "0401": "04/01",
            "04012026": "04/01/2026",
            "04/01/2026": "04/01/2026",
            "04a01b202699": "04/01/2026",
        }

        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(
                    formatar_data_digitada(entrada),
                    esperado,
                )

    def test_converte_data_da_interface_e_rejeita_invalida(self):
        self.assertEqual(
            converter_data_interface("04/01/2026"),
            date(2026, 1, 4),
        )

        with self.assertRaisesRegex(ValueError, "DD/MM/AAAA"):
            converter_data_interface("31/02/2026")

    def test_nome_do_relatorio_reflete_periodo_sem_texto_livre(self):
        self.assertEqual(
            criar_nome_relatorio_72h(
                date(2026, 1, 4),
                date(2026, 1, 31),
            ),
            "Relatorio_72h_04-01-2026_a_31-01-2026.xlsx",
        )

        with self.assertRaisesRegex(ValueError, "posterior"):
            criar_nome_relatorio_72h(
                date(2026, 2, 1),
                date(2026, 1, 31),
            )

    def test_localiza_dicionario_na_raiz_da_execucao(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            with patch(
                "app.services.qualifica.interface_72h."
                "obter_raiz_projeto",
                return_value=raiz,
            ):
                self.assertEqual(
                    obter_caminho_dicionario_municipios(),
                    raiz / CAMINHO_RELATIVO_DICIONARIO,
                )

    def test_dicionario_distribuido_e_valido(self):
        caminho = RAIZ_PROJETO / CAMINHO_RELATIVO_DICIONARIO
        municipios = Relatorio72hService().carregar_municipios(
            caminho
        )

        self.assertEqual(len(municipios), 497)
        self.assertEqual(
            len({municipio.codigo_ibge for municipio in municipios}),
            497,
        )

    def test_qualifica_pode_ser_pagina_inicial(self):
        self.assertIn(
            "qualifica",
            ConfiguracoesService.PAGINAS_VALIDAS,
        )
        pagina_configuracoes = (
            RAIZ_PROJETO
            / "app"
            / "gui"
            / "pages"
            / "configuracoes_page.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '"Qualifica": "qualifica"',
            pagina_configuracoes,
        )

    def test_sidebar_possui_estado_recolhido_e_expandido(self):
        sidebar = (
            RAIZ_PROJETO
            / "app"
            / "gui"
            / "components"
            / "sidebar.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LARGURA_RECOLHIDA = 72", sidebar)
        self.assertIn("LARGURA_EXPANDIDA = 230", sidebar)
        self.assertIn("def expandir(self)", sidebar)
        self.assertIn("def recolher(self)", sidebar)
        self.assertIn("def selecionar_qualifica", sidebar)

    def test_build_inclui_dicionario_do_qualifica(self):
        especificacao = (
            RAIZ_PROJETO / "ArboHub.spec"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'RAIZ_PROJETO / "assets" / "qualifica"',
            especificacao,
        )
        self.assertIn(
            '"assets/qualifica"',
            especificacao,
        )


if __name__ == "__main__":
    unittest.main()
