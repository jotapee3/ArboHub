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
    validar_nome_relatorio_72h,
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

    def test_nome_do_relatorio_sugere_periodo_e_aceita_edicao(self):
        self.assertEqual(
            criar_nome_relatorio_72h(
                date(2026, 1, 4),
                date(2026, 1, 31),
            ),
            "Qualifica_72h_04-01-2026_a_31-01-2026.xlsx",
        )

        self.assertEqual(
            validar_nome_relatorio_72h("Indicador estadual janeiro"),
            "Indicador estadual janeiro.xlsx",
        )
        with self.assertRaisesRegex(ValueError, "caracteres"):
            validar_nome_relatorio_72h("pasta/relatorio.xlsx")

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

    def test_dicionario_personalizado_e_opcional_e_validado(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivo = Path(temporario) / "municipios_atualizados.xlsx"
            arquivo.touch()
            service = ConfiguracoesService(
                Path(temporario) / "configuracoes.json"
            )

            self.assertEqual(
                service.validar_caminho_dicionario_qualifica(""),
                "",
            )
            self.assertEqual(
                service.validar_caminho_dicionario_qualifica(arquivo),
                str(arquivo.resolve()),
            )

            with self.assertRaisesRegex(ValueError, "XLSX"):
                service.validar_caminho_dicionario_qualifica(
                    Path(temporario) / "municipios.csv"
                )

    def test_sidebar_expande_por_clique_sem_animacao_de_layout(self):
        sidebar = (
            RAIZ_PROJETO
            / "app"
            / "gui"
            / "components"
            / "sidebar.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LARGURA_RECOLHIDA = 72", sidebar)
        self.assertIn("LARGURA_EXPANDIDA = 230", sidebar)
        self.assertIn("def alternar_expansao(self)", sidebar)
        self.assertIn("command=self.alternar_expansao", sidebar)
        self.assertIn("def selecionar_qualifica", sidebar)
        self.assertIn('text=""', sidebar)
        self.assertIn("image=self._icone_expandir", sidebar)
        self.assertIn('border_width=0', sidebar)
        self.assertNotIn('text="‹ Recolher"', sidebar)
        self.assertNotIn('widget.bind("<Enter>"', sidebar)
        self.assertNotIn("PASSOS_ANIMACAO", sidebar)

        janela = (
            RAIZ_PROJETO
            / "app"
            / "gui"
            / "windows"
            / "main_window.py"
        ).read_text(encoding="utf-8")
        self.assertIn("self.sidebar.grid(", janela)
        self.assertIn("self.content_area.grid(", janela)
        self.assertNotIn("self.sidebar.place(", janela)

    def test_calendario_permite_escolher_mes_e_ano(self):
        seletor = (
            RAIZ_PROJETO
            / "app"
            / "gui"
            / "components"
            / "seletor_data.py"
        ).read_text(encoding="utf-8")
        self.assertIn("self.combo_mes = ctk.CTkComboBox", seletor)
        self.assertIn("self.combo_ano = ctk.CTkComboBox", seletor)

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
