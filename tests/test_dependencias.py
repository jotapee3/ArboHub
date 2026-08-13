from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verificar_ambiente import (
    PACOTES_DESENVOLVIMENTO,
    PACOTES_OBRIGATORIOS,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


def ler_versoes(nome_arquivo: str) -> dict[str, str]:
    versoes: dict[str, str] = {}
    caminho = RAIZ_PROJETO / nome_arquivo

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()

        if not linha or linha.startswith(("#", "-r ")):
            continue

        nome, separador, versao = linha.partition("==")
        if not separador:
            raise AssertionError(
                f"Dependência sem versão exata em {nome_arquivo}: "
                f"{linha}"
            )

        versoes[nome.casefold()] = versao

    return versoes


class DependenciasTestCase(unittest.TestCase):
    def test_requisitos_diretos_correspondem_ao_verificador(self):
        self.assertEqual(
            ler_versoes("requirements.txt"),
            PACOTES_OBRIGATORIOS,
        )
        self.assertEqual(
            ler_versoes("requirements-dev.txt"),
            PACOTES_DESENVOLVIMENTO,
        )

    def test_arquivo_fechado_contem_requisitos_diretos(self):
        versoes_fechadas = ler_versoes("requirements.lock.txt")
        esperadas = {
            **PACOTES_OBRIGATORIOS,
            **PACOTES_DESENVOLVIMENTO,
        }

        for nome, versao in esperadas.items():
            self.assertEqual(
                versoes_fechadas.get(nome),
                versao,
                msg=f"Versão fechada divergente para {nome}.",
            )

    def test_ferramentas_de_build_estao_fixadas(self):
        versoes_build = ler_versoes("requirements-build.txt")

        self.assertEqual(
            versoes_build.get("pyinstaller"),
            "6.22.0",
        )
        self.assertEqual(
            versoes_build.get("pyinstaller-hooks-contrib"),
            "2026.6",
        )

    def test_build_nao_solicita_compactacao_upx(self):
        especificacao = (
            RAIZ_PROJETO / "ArboHub.spec"
        ).read_text(encoding="utf-8")

        self.assertNotIn("upx=True", especificacao)
        self.assertEqual(
            especificacao.count("upx=False"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
