from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core.database import conectar_sqlite


class DatabaseTestCase(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
