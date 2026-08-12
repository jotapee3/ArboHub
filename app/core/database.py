from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.core.caminhos import (
    obter_pasta_dados_arbohub,
    obter_raiz_projeto,
)


def obter_caminho_banco_padrao() -> Path:
    """Retorna o banco privado do usuário atual."""

    return obter_pasta_dados_arbohub() / "arbohub.db"


def obter_caminho_banco_na_raiz(
    raiz_projeto: str | Path,
) -> Path:
    """Monta o caminho legado para uma raiz explicitamente informada."""

    return Path(raiz_projeto) / "data" / "arbohub.db"


def migrar_banco_legado(
    origem: str | Path,
    destino: str | Path,
) -> bool:
    """
    Copia e valida o banco antigo sem remover nem alterar a origem.

    Retorna ``True`` somente quando uma nova cópia foi criada. Um
    destino já existente nunca é sobrescrito.
    """

    origem = Path(origem).expanduser().resolve()
    destino = Path(destino).expanduser().resolve()

    if destino.exists() or not origem.exists() or origem == destino:
        return False

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(
        f".{destino.name}.{uuid4().hex}.migrando"
    )

    try:
        conexao_origem = None
        conexao_destino = None

        try:
            uri_origem = f"{origem.as_uri()}?mode=ro"
            conexao_origem = sqlite3.connect(
                uri_origem,
                uri=True,
                timeout=10,
            )
            conexao_destino = sqlite3.connect(
                temporario,
                timeout=10,
            )

            conexao_origem.backup(conexao_destino)
            conexao_destino.commit()

            verificacao = conexao_destino.execute(
                "PRAGMA quick_check"
            ).fetchone()

            if (
                not verificacao
                or str(verificacao[0]).casefold() != "ok"
            ):
                raise sqlite3.DatabaseError(
                    "A cópia do banco não passou na verificação de "
                    "integridade."
                )
        finally:
            if conexao_destino is not None:
                conexao_destino.close()

            if conexao_origem is not None:
                conexao_origem.close()

        if destino.exists():
            return False

        os.replace(temporario, destino)
        return True
    finally:
        if temporario.exists():
            temporario.unlink()


def preparar_caminho_banco_padrao(
    *,
    origem_legada: str | Path | None = None,
    destino: str | Path | None = None,
) -> Path:
    """Prepara o banco local e migra uma instalação antiga uma vez."""

    caminho_destino = Path(
        destino or obter_caminho_banco_padrao()
    ).expanduser().resolve()

    if caminho_destino.exists():
        return caminho_destino

    caminho_origem = Path(
        origem_legada
        or obter_caminho_banco_na_raiz(obter_raiz_projeto())
    ).expanduser().resolve()

    if caminho_origem.exists():
        migrar_banco_legado(
            caminho_origem,
            caminho_destino,
        )

    return caminho_destino


def resolver_caminho_banco(
    caminho_banco: str | Path | None = None,
) -> Path:
    """Normaliza um caminho informado ou usa o padrão do aplicativo."""

    if caminho_banco is None:
        return preparar_caminho_banco_padrao()

    return Path(caminho_banco).expanduser().resolve()


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
