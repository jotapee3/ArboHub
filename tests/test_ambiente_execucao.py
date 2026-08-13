from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.ambiente_execucao import preparar_ambiente_execucao
from app.core.caminhos import obter_raiz_projeto


class AmbienteExecucaoTestCase(unittest.TestCase):
    def test_desenvolvimento_nao_altera_caminho_do_playwright(self):
        with patch.object(
            sys,
            "frozen",
            False,
            create=True,
        ), patch.dict(
            os.environ,
            {"PLAYWRIGHT_BROWSERS_PATH": "caminho-existente"},
        ):
            resultado = preparar_ambiente_execucao()

            self.assertIsNone(resultado)
            self.assertEqual(
                os.environ["PLAYWRIGHT_BROWSERS_PATH"],
                "caminho-existente",
            )

    def test_empacotado_usa_navegador_interno(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario).resolve()

            with patch.object(
                sys,
                "frozen",
                True,
                create=True,
            ), patch.object(
                sys,
                "_MEIPASS",
                str(raiz),
                create=True,
            ), patch.dict(
                os.environ,
                {},
                clear=True,
            ):
                resultado = preparar_ambiente_execucao()

                esperado = raiz / "ms-playwright"
                self.assertEqual(resultado, esperado)
                self.assertEqual(
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"],
                    str(esperado),
                )

    def test_raiz_empacotada_usa_meipass(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario).resolve()

            with patch.object(
                sys,
                "frozen",
                True,
                create=True,
            ), patch.object(
                sys,
                "_MEIPASS",
                str(raiz),
                create=True,
            ):
                self.assertEqual(
                    obter_raiz_projeto(),
                    raiz,
                )


if __name__ == "__main__":
    unittest.main()
