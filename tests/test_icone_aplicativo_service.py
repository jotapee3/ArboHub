from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.services.icone_aplicativo_service import (
    IconeAplicativoService,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


class _TemaServiceFake:
    def __init__(self, tema: str):
        self.tema = tema

    def obter_tema_sistema(self) -> str:
        return self.tema


class IconeAplicativoServiceTestCase(unittest.TestCase):
    def test_windows_claro_usa_icone_escuro(self):
        service = IconeAplicativoService(
            _TemaServiceFake("claro")
        )

        self.assertEqual(
            service.obter_nome_icone(),
            "arbohub_light.ico",
        )

    def test_windows_escuro_usa_icone_claro(self):
        service = IconeAplicativoService(
            _TemaServiceFake("escuro")
        )

        self.assertEqual(
            service.obter_nome_icone(),
            "arbohub_dark.ico",
        )

    def test_usa_icone_padrao_quando_variante_nao_existe(self):
        service = IconeAplicativoService(
            _TemaServiceFake("claro")
        )

        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            esperado = pasta / "arbohub.ico"
            esperado.touch()

            self.assertEqual(
                service.obter_caminho_icone(pasta),
                esperado,
            )

    def test_icones_possuem_tamanhos_nativos_do_windows(self):
        tamanhos_esperados = {
            (16, 16),
            (20, 20),
            (24, 24),
            (32, 32),
            (40, 40),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        }
        pasta_assets = (
            RAIZ_PROJETO / "app" / "gui" / "assets"
        )

        for nome_arquivo in (
            "arbohub_light.ico",
            "arbohub_dark.ico",
        ):
            with self.subTest(icone=nome_arquivo):
                with Image.open(
                    pasta_assets / nome_arquivo
                ) as imagem:
                    self.assertEqual(
                        set(imagem.info["sizes"]),
                        tamanhos_esperados,
                    )


if __name__ == "__main__":
    unittest.main()
