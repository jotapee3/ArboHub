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


if __name__ == "__main__":
    unittest.main()
