from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def obter_raiz_projeto() -> Path:
    """Retorna a raiz da instalação atual do ArboHub."""

    return Path(__file__).resolve().parents[2]


def obter_caminho_banco_padrao() -> Path:
    """Retorna o caminho legado utilizado pelo banco operacional."""

    return obter_caminho_banco_na_raiz(obter_raiz_projeto())


def obter_caminho_banco_na_raiz(
    raiz_projeto: str | Path,
) -> Path:
    """Monta o caminho legado para uma raiz explicitamente informada."""

    return Path(raiz_projeto) / "data" / "arbohub.db"


def resolver_caminho_banco(
    caminho_banco: str | Path | None = None,
) -> Path:
    """Normaliza um caminho informado ou usa o padrão do aplicativo."""

    caminho = (
        Path(caminho_banco)
        if caminho_banco is not None
        else obter_caminho_banco_padrao()
    )
    return caminho.expanduser().resolve()


@contextmanager
def conectar_sqlite(
    caminho_banco: str | Path,
    *,
    timeout: float = 5,
    chaves_estrangeiras: bool = False,
    somente_leitura: bool = False,
) -> Iterator[sqlite3.Connection]:
    """
    Abre uma conexão SQLite e sempre a fecha ao sair do contexto.

    O gerenciador nativo da conexão trata commit e rollback, mas não
    fecha o arquivo. Este contexto acrescenta o fechamento explícito,
    necessário especialmente no Windows.
    """

    caminho = resolver_caminho_banco(caminho_banco)

    if not somente_leitura:
        caminho.parent.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(caminho, timeout=timeout)

    try:
        conexao.row_factory = sqlite3.Row

        if chaves_estrangeiras:
            conexao.execute("PRAGMA foreign_keys = ON")

        if somente_leitura:
            conexao.execute("PRAGMA query_only = ON")

        with conexao:
            yield conexao
    finally:
        conexao.close()
