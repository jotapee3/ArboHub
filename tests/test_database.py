from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.database import (
    conectar_sqlite,
    obter_caminho_banco_padrao,
    preparar_caminho_banco_padrao,
)


class DatabaseTestCase(unittest.TestCase):
    @staticmethod
    def _criar_banco(caminho: Path, valor: str):
        with conectar_sqlite(caminho) as conexao:
            conexao.execute(
                "CREATE TABLE estado (valor TEXT NOT NULL)"
            )
            conexao.execute(
                "INSERT INTO estado (valor) VALUES (?)",
                (valor,),
            )

    @staticmethod
    def _ler_valor(caminho: Path) -> str:
        with conectar_sqlite(
            caminho,
            somente_leitura=True,
        ) as conexao:
            resultado = conexao.execute(
                "SELECT valor FROM estado"
            ).fetchone()

        return str(resultado["valor"])

    def test_caminho_padrao_usa_localappdata(self):
        with tempfile.TemporaryDirectory() as temporario:
            pasta_local = Path(temporario) / "Local"

            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": str(pasta_local)},
            ):
                esperado = (
                    pasta_local.resolve()
                    / "ArboHub"
                    / "dados"
                    / "arbohub.db"
                )
                self.assertEqual(
                    obter_caminho_banco_padrao(),
                    esperado,
                )

    def test_preparacao_migra_sem_apagar_banco_legado(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem = raiz / "projeto" / "data" / "arbohub.db"
            destino = raiz / "local" / "dados" / "arbohub.db"
            self._criar_banco(origem, "progresso preservado")

            resultado = preparar_caminho_banco_padrao(
                origem_legada=origem,
                destino=destino,
            )

            self.assertEqual(resultado, destino.resolve())
            self.assertTrue(origem.exists())
            self.assertTrue(destino.exists())
            self.assertEqual(
                self._ler_valor(origem),
                "progresso preservado",
            )
            self.assertEqual(
                self._ler_valor(destino),
                "progresso preservado",
            )

    def test_preparacao_nao_sobrescreve_banco_local(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem = raiz / "projeto" / "data" / "arbohub.db"
            destino = raiz / "local" / "dados" / "arbohub.db"
            self._criar_banco(origem, "legado")
            self._criar_banco(destino, "local")

            preparar_caminho_banco_padrao(
                origem_legada=origem,
                destino=destino,
            )

            self.assertEqual(self._ler_valor(origem), "legado")
            self.assertEqual(self._ler_valor(destino), "local")

    def test_migracao_invalida_nao_deixa_copia_parcial(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem = raiz / "arbohub_invalido.db"
            destino = raiz / "local" / "arbohub.db"
            origem.write_bytes(b"arquivo que nao e sqlite")

            with self.assertRaises(sqlite3.DatabaseError):
                preparar_caminho_banco_padrao(
                    origem_legada=origem,
                    destino=destino,
                )

            self.assertFalse(destino.exists())
            self.assertEqual(
                tuple(destino.parent.glob("*.migrando")),
                (),
            )

    def test_contexto_fecha_conexao_sqlite(self):
        with tempfile.TemporaryDirectory() as temporario:
            banco = Path(temporario) / "arbohub_teste.db"

            with conectar_sqlite(banco) as conexao:
                conexao.execute(
                    "CREATE TABLE teste (identificador INTEGER)"
                )

            self.assertTrue(banco.exists())

            with self.assertRaises(sqlite3.ProgrammingError):
                conexao.execute("SELECT 1")

    def test_somente_leitura_nao_cria_banco_ausente(self):
        with tempfile.TemporaryDirectory() as temporario:
            banco = Path(temporario) / "ausente.db"

            with self.assertRaises(FileNotFoundError):
                with conectar_sqlite(
                    banco,
                    somente_leitura=True,
                ):
                    pass

            self.assertFalse(banco.exists())

    def test_somente_leitura_bloqueia_gravacao(self):
        with tempfile.TemporaryDirectory() as temporario:
            banco = Path(temporario) / "somente_leitura.db"
            self._criar_banco(banco, "preservado")

            with conectar_sqlite(
                banco,
                somente_leitura=True,
            ) as conexao:
                with self.assertRaises(sqlite3.OperationalError):
                    conexao.execute(
                        "UPDATE estado SET valor = ?",
                        ("alterado",),
                    )

            self.assertEqual(
                self._ler_valor(banco),
                "preservado",
            )


if __name__ == "__main__":
    unittest.main()
